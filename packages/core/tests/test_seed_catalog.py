from __future__ import annotations

import json
from pathlib import Path
import unittest

from swisstip.core.contracts import ArtifactRef, KnowledgeCatalog, LanguagePolicy
from swisstip.core.identity import json_content_hash
from swisstip.core.validation import validate_catalog, validate_request


ROOT = Path(__file__).resolve().parents[3]


class DraftSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = ROOT / "config/catalogs"
        self.catalog = KnowledgeCatalog.model_validate_json((directory / "zh-residence.seed.json").read_bytes())
        self.policy = LanguagePolicy.model_validate_json((directory / "zh-residence.language-policy.json").read_bytes())
        self.authoring_ref = ArtifactRef(
            artifact_id="zh-residence-seed-authoring", version="1",
            sha256=json_content_hash(json.loads((directory / "zh-residence.authoring.json").read_text(encoding="utf-8"))),
        )

    def test_seed_is_integral_but_has_no_approved_coverage(self) -> None:
        self.assertEqual(validate_catalog(self.catalog, self.policy, artifacts={
            self.authoring_ref.artifact_id: self.authoring_ref,
        }), ())
        self.assertEqual(len([entry for entry in self.catalog.entries if entry.kind == "concept"]), 6)
        self.assertTrue(all(entry.lifecycle == "CANDIDATE" for entry in self.catalog.entries))
        self.assertEqual(self.catalog.coverage_profiles, [])
        self.assertEqual(self.policy.approval_status, "DRAFT")
        self.assertEqual(self.policy.term_languages, [])

    def test_draft_candidate_is_not_a_selectable_public_concept(self) -> None:
        assessment = validate_request({
            "schema_version": "structured-grounding/v1", "release_id": self.catalog.release_id,
            "knowledge_space_id": "swiss-public", "domain_id": "immigration", "topic_id": "residence",
            "concept_ids": ["residence-eu-efta"], "intent": "requirements",
            "jurisdiction": {"country_code": "CH", "canton_code": "CH-ZH"},
            "context": {}, "as_of": "2026-09-06", "scope_mode": "exact",
        }, self.catalog, self.policy)
        self.assertEqual(assessment.status, "INVALID_ARGUMENT")
        self.assertEqual(assessment.issues[0].reason, "unknown_id")


if __name__ == "__main__":
    unittest.main()
