"""Replay blocked Zurich repair inputs with explicitly uncertain offline controls."""
import copy
import json
from pathlib import Path
import unittest

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection
from test_review_input_limit import uncertain_review
import test_structured_extraction as helpers


class RepairReplayProvider:
    def __init__(self, saved):
        self.saved, self.calls, self.repair_started = saved, [], False
        self.offline_controls = []

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request["user_prompt"])
        if "concepts" in payload:
            if self.repair_started:
                # No live response exists after the blocked repair. This control
                # exercises validation without approving any saved proposals.
                content = json.dumps(uncertain_review(payload))
                self.offline_controls.append("uncertain_review")
            else:
                content = self.saved["raw_initial_review"]
                if content is None:
                    raise AssertionError("The initial structurally invalid bundle must not be reviewed")
        else:
            if payload["repair"]:
                self.repair_started = True
                self.offline_controls.append("repeated_initial_extraction")
            # Repeating the initial response after repair is an offline control,
            # never evidence that the model corrected its live output.
            content = self.saved["raw_initial_completion"]
        return ModelCompletion(content, "offline-replay", "offline-replay")


class RepairInputLimitTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((Path(__file__).parent /
            "fixtures/deepseek_v4_zh_56850144.json").read_text(encoding="utf-8"))

    def replay(self, group, **options):
        original = copy.deepcopy(group)
        source = group["source"]
        page = NormalizedPage("saved-zurich", "fixture", "Zurich", source["language_hint"], source["input_hash"],
            tuple(NormalizedSection(b["section_id"], "", b["text"], block_kind="paragraph", scope_id=b["scope_id"])
                  for b in source["evidence"].values()), normalization_version=source["normalization_version"],
            source_sha256=source["source_sha256"])
        provider, progress = RepairReplayProvider(group), []
        engine = CandidateConceptExtractor(provider, active_profile="offline-replay",
            prompt_profile="concept_extraction_v4", chunk_content_characters=6400,
            max_concepts_per_chunk=6, max_model_requests_per_page=12,
            max_review_input_characters=64000, progress=progress.append, **options)
        ceiling = engine.planned_request_count(page)
        report = engine.extract(page)
        self.assertEqual(group, original)
        self.assertLessEqual(len(provider.calls), ceiling)
        self.assertEqual(json.loads(provider.calls[0]["user_prompt"])["untrusted_source"], source)
        return provider, report, progress

    def assert_complete_repair(self, group, request):
        payload = json.loads(request["user_prompt"])
        self.assertEqual(payload["untrusted_source"], group["source"])
        feedback, initial = payload["repair"], group["initial_history"]
        self.assertEqual(feedback["proposals"], initial["proposals"])
        self.assertEqual(feedback["structural_rejections"],
            [{k: v for k, v in rejection.items() if k != "proposal"}
             for rejection in initial["structural_rejections"]])
        for key in ("revision", "saturated", "review", "failure_stage", "review_skipped"):
            if key in initial:
                self.assertEqual(feedback[key], initial[key])
        if "error" in initial:
            self.assertEqual(feedback["validation_error"], initial["error"])
        self.assertEqual(len(json.dumps(payload, ensure_ascii=False)), group["original_repair_characters"])
        self.assertEqual(len(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            group["compact_repair_characters"])

    def test_omitted_and_explicit_legacy_limits_preserve_saved_overflow(self):
        for group in self.saved["groups"]:
            for options in ({}, {"max_repair_input_characters": 25600}):
                with self.subTest(group=group["number"], options=options):
                    provider, report, _ = self.replay(group, **options)
                    self.assertEqual(len(provider.calls), 1 if group["number"] == 2 else 2)
                    self.assertFalse(provider.offline_controls)
                    self.assertEqual(report.quality_metrics["repair_request_count"], 0)
                    last = report.semantic_reviews[0]["history"][-1]
                    self.assertEqual(last["failure_stage"], "extraction_input")
                    self.assertTrue(last["error"].startswith(group["original_failure"]))
                    self.assertIn("max_repair_input_characters=25600", last["error"])
                    self.assertFalse(report.candidates)

    def test_64000_limit_sends_complete_saved_repairs_and_keeps_controls_uncertain(self):
        for group in self.saved["groups"]:
            with self.subTest(group=group["number"]):
                provider, report, progress = self.replay(group, max_repair_input_characters=64000)
                self.assertEqual(len(provider.calls), 3 if group["number"] == 2 else 4)
                repair = next(r for r in provider.calls if json.loads(r["user_prompt"]).get("repair"))
                self.assert_complete_repair(group, repair)
                self.assertEqual(len(repair["user_prompt"]), group["original_repair_characters"])
                self.assertEqual(provider.offline_controls, ["repeated_initial_extraction", "uncertain_review"])
                self.assertFalse(any("compacted extraction JSON" in line for line in progress))
                self.assertEqual(report.quality_metrics["repair_request_count"], 1)
                self.assertFalse(report.candidates)
                self.assertFalse(report.quality_metrics["publication_eligible"])
                history = report.semantic_reviews[0]["history"]
                if group["number"] == 2:
                    # The unchanged invalid conditions still fail validation.
                    self.assertEqual(len(history[-1]["structural_rejections"]), 2)
                else:
                    # A prior supported live assessment does not override the
                    # later uncertain offline control or reinstate candidates.
                    self.assertEqual(history[0]["review"], group["initial_history"]["review"])
                    self.assertTrue(all(contracts.review_passes(r) for r in history[0]["review"]["concept_reviews"]))
                self.assertTrue(all(not contracts.review_passes(r) for r in history[-1]["review"]["concept_reviews"]))

    def test_compact_repair_boundary_rejects_one_character_less(self):
        for group in self.saved["groups"]:
            limit = group["compact_repair_characters"]
            for cap, sends_repair in ((limit, True), (limit - 1, False)):
                with self.subTest(group=group["number"], cap=cap):
                    provider, report, progress = self.replay(group, max_repair_input_characters=cap)
                    repairs = [r for r in provider.calls if json.loads(r["user_prompt"]).get("repair")]
                    self.assertEqual(len(repairs), int(sends_repair))
                    if sends_repair:
                        self.assert_complete_repair(group, repairs[0])
                        self.assertEqual(len(repairs[0]["user_prompt"]), cap)
                        self.assertTrue(any("compacted extraction JSON" in line for line in progress))
                    else:
                        self.assertIn(f"max_repair_input_characters={cap}", report.warnings[-2])
                    self.assertFalse(report.candidates)

    def test_large_repair_cap_cannot_bypass_oversized_initial_source(self):
        helper = helpers.StructuredTests()
        page = helper.page("<p>Apply online.</p>" * 20)
        for cap in (None, 64000):
            with self.subTest(cap=cap):
                provider = helpers.Provider()
                engine = helper.engine(provider, chunk_content_characters=500, chunk_overlap_characters=0,
                    max_repair_input_characters=cap)
                report = engine.extract(page)
                self.assertFalse(provider.calls)
                self.assertEqual(report.quality_metrics["request_attempt_count"], 0)
                history = report.semantic_reviews[0]["history"]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["failure_stage"], "extraction_input")
                self.assertIn("> 2000", history[0]["error"])
                self.assertFalse(report.candidates)

    def test_optional_repair_cap_is_strict_and_defaults_to_chunk_multiple(self):
        for invalid in (0, -1, True, False, 64000.0, "64000"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CandidateConceptExtractor(None, active_profile="fixture", max_repair_input_characters=invalid)
        for chunk in (500, 6400):
            engine = CandidateConceptExtractor(None, active_profile="fixture", chunk_content_characters=chunk,
                chunk_overlap_characters=0)
            self.assertEqual(engine._max_repair_input_characters, chunk * 4)
        self.assertEqual(CandidateConceptExtractor(None, active_profile="fixture",
            max_repair_input_characters=1)._max_repair_input_characters, 1)


if __name__ == "__main__":
    unittest.main()
