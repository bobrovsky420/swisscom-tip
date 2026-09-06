from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from pathlib import Path

from swisstip.builder.experimental_knowledge import ExperimentalKnowledge, build_bundle, main, _bytes, _sha
from test_concept_batch import report


class ExperimentalKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "proposals.json"
        self.bundle = self.root / "bundle"
        self.payload = report("page.html").to_dict()
        self.write(self.payload)

    def write(self, payload):
        self.input.write_text(json.dumps(payload), encoding="utf-8")

    def build(self):
        build_bundle([self.input], self.bundle)
        return ExperimentalKnowledge(self.bundle)

    def test_unreviewed_candidates_are_usable_and_exact_evidence_round_trips(self):
        original = self.input.read_bytes()
        knowledge = self.build()
        results = knowledge.search("permit")
        self.assertEqual(results["total"], 1)
        self.assertEqual(results["mode"], "EXPERIMENTAL_UNREVIEWED")
        self.assertFalse(results["publication_eligible"])
        item = results["matches"][0]
        self.assertEqual(item["candidate"]["validation_state"], "CANDIDATE")
        result = knowledge.get_concept(item["concept_id"])
        citation = knowledge.get_evidence(item["evidence_ids"][0])["evidence"]
        self.assertEqual(result["evidence"][0], citation)
        self.assertEqual(citation["quote"], "Apply online.")
        self.assertEqual(citation["input_hash"], self.payload["input_hash"])
        self.assertEqual(self.input.read_bytes(), original)
        self.assertEqual(next((self.bundle / "reports").glob("*.json")).read_bytes(), original)
        self.assertEqual(result["source"]["prompt_profile"], "concept_extraction_v2")

    def test_multiple_models_and_conflicting_scopes_are_preserved(self):
        second = replace(report("page.html", scope="Other residents"), model="other-model").to_dict()
        self.write({"schema_version": "swisstip.concept-proposal-batch/v1", "reports": [self.payload, second]})
        knowledge = self.build()
        items = knowledge.search("permit")["matches"]
        self.assertEqual(len(items), 2)
        self.assertEqual(len({c["concept_id"] for c in items}), 2)
        self.assertEqual({c["candidate"]["scope"] for c in items}, {"EU/EFTA residents", "Other residents"})

    def test_rejected_proposals_are_archived_but_not_loaded_as_concepts(self):
        self.payload["rejected_candidates"] = [{"proposal": self.payload["candidates"][0], "reason": "scope error"}]
        self.payload["candidates"] = []
        self.write(self.payload)
        knowledge = self.build()
        self.assertEqual(knowledge.list_concepts()["total"], 0)
        self.assertEqual(knowledge.search("permit")["matches"], [])

    def test_repeated_input_is_deduplicated_and_rebuild_identity_is_deterministic(self):
        first = build_bundle([self.input, self.input], self.bundle)
        second = build_bundle([self.input], self.root / "second")
        self.assertEqual(first, second)
        self.assertEqual(first["concept_count"], 1)
        with self.assertRaises(FileExistsError):
            build_bundle([self.input], self.bundle)

    def test_v4_conditions_and_gaps_survive_without_human_decisions(self):
        self.payload.update(schema_version="swisstip.concept-proposal-report/v2", prompt_profile="concept_extraction_v4",
                            source_inventory=[{"section_id": "section-0001", "evidence_text": "Apply online.", "status": "covered"},
                                              {"section_id": "section-0002", "evidence_text": "Missing rule.", "status": "missing"}],
                            human_review_queue=[{"candidate_id": "candidate-1", "reason": "human_review_required"}])
        self.payload["candidates"][0]["structured_claims"] = [{"conditions": [{"operator": "gt", "value": "90", "unit": "working days"}]}]
        self.write(self.payload)
        knowledge = self.build()
        result = knowledge.get_concept(knowledge.list_concepts()["concepts"][0]["concept_id"])
        self.assertEqual(result["concept"]["candidate"]["structured_claims"], self.payload["candidates"][0]["structured_claims"])
        self.assertEqual(result["source"]["source_inventory"][1]["status"], "missing")
        self.assertEqual(result["evidence"][0]["location_validation"], "matched_source_inventory")

    def test_v4_mismatched_citation_and_malformed_offsets_fail_before_output(self):
        for mutation in ("offset", "inventory"):
            payload = copy.deepcopy(self.payload)
            if mutation == "offset":
                payload["candidates"][0]["evidence"][0]["end"] = 999
            else:
                payload.update(schema_version="swisstip.concept-proposal-report/v2", prompt_profile="concept_extraction_v4", source_inventory=[])
            self.write(payload)
            with self.assertRaises(ValueError):
                build_bundle([self.input], self.bundle)
            self.assertFalse(self.bundle.exists())

    def test_tampered_knowledge_or_archived_report_is_rejected(self):
        self.build()
        for path in [self.bundle / "knowledge.json", next((self.bundle / "reports").glob("*.json"))]:
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                ExperimentalKnowledge(self.bundle)
            path.write_bytes(original)

    def test_manifest_path_traversal_is_rejected(self):
        self.build()
        path = self.bundle / "manifest.json"
        manifest = json.loads(path.read_bytes())
        manifest["files"]["../proposals.json"] = _sha(self.input.read_bytes())
        path.write_bytes(_bytes(manifest))
        with self.assertRaisesRegex(ValueError, "artifact path"):
            ExperimentalKnowledge(self.bundle)

    def test_language_filter_pagination_and_unknown_ids(self):
        second = copy.deepcopy(self.payload)
        second["language"] = "de"
        self.write({"schema_version": "swisstip.concept-proposal-batch/v1", "reports": [self.payload, second]})
        knowledge = self.build()
        self.assertEqual(knowledge.list_concepts(limit=1)["next_offset"], 1)
        self.assertIsNone(knowledge.list_concepts(limit=1, offset=1)["next_offset"])
        self.assertEqual(knowledge.search("permit", language="de")["total"], 1)
        self.assertEqual(knowledge.search("permit", language="fr")["total"], 0)
        for method in (knowledge.get_concept, knowledge.get_evidence):
            with self.assertRaises(ValueError):
                method("missing")
        for query in ("", "!", "word" * 1000):
            with self.assertRaises(ValueError):
                knowledge.search(query)

    def test_return_values_cannot_mutate_loaded_evidence(self):
        knowledge = self.build()
        concept = knowledge.list_concepts()["concepts"][0]
        concept["candidate"]["description"] = "Changed"
        self.assertEqual(knowledge.get_concept(concept["concept_id"])["concept"]["candidate"]["description"], "Apply online.")

    def test_duplicate_candidates_and_non_extractor_input_are_rejected(self):
        for payload in ({"schema_version": "knowledge-release/v1"},
                        {**self.payload, "candidates": [self.payload["candidates"][0]] * 2}):
            self.write(payload)
            with self.assertRaises(ValueError):
                build_bundle([self.input], self.bundle)

    def test_cli_build_search_get_and_evidence(self):
        def run(args):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args), 0)
            return json.loads(out.getvalue())
        run(["build", str(self.input), "--output-dir", str(self.bundle)])
        candidate = run(["search", str(self.bundle), "permit"])["matches"][0]
        self.assertEqual(run(["get", str(self.bundle), candidate["concept_id"]])["concept"]["concept_id"], candidate["concept_id"])
        self.assertEqual(run(["evidence", str(self.bundle), candidate["evidence_ids"][0]])["evidence"]["quote"], "Apply online.")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["get", str(self.bundle), "missing"]), 2)


if __name__ == "__main__":
    unittest.main()
