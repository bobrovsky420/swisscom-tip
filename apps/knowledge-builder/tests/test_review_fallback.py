from __future__ import annotations

import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from swisstip.builder.concept_recovery import RecoverableProvider
from swisstip.builder.huggingface_provider import HuggingFaceHTTPError, HuggingFaceIncompleteCompletionError
from swisstip.builder.model_profiles import load_model_profiles
from swisstip.ingestion.concept_review import REVIEW_SYSTEM_PROMPT, parse_verdicts, review_schema
from swisstip.ingestion.concepts import CandidateConceptExtractor, REVIEW_PROMPT_PROFILE, ModelCompletion, NormalizedPage, NormalizedSection, SemanticModelError

ROOT = Path(__file__).resolve().parents[3]
MODEL = "swiss-ai/Apertus-8B-Instruct-2509"
REQUESTED_MODEL = f"{MODEL}:publicai"
MODEL_ALIAS = "swiss-ai/apertus-8b-instruct"
PAGE = NormalizedPage("page-1", "source.html", "Title", "en", "a" * 64,
                      (NormalizedSection("section-0001", "Heading", "Content"),))


def model_identity(request_id, observed_model=MODEL):
    return {"provider": "publicai", "model": MODEL, "requested_model": REQUESTED_MODEL,
            "observed_model": observed_model, "request_id": request_id}


def truncated(reason="length"):
    return HuggingFaceIncompleteCompletionError(finish_reason=reason, prompt_tokens=50,
        output_tokens=4096, content_characters=6000, response_bytes=7000, max_output_tokens=4096)


def request(count=4):
    payload = {"title": "Title", "language": "en",
               "primary_sections": [{"section_id": f"section-{i:04d}", "text": f"Context {i}"}
                                    for i in range(1, count + 1)],
               "proposals": [{"review_id": i, "candidate": {"preferred_label": f"Proposal {i}",
                              "primary_section_id": f"section-{i:04d}"}}
                             for i in range(1, count + 1)]}
    return {"system_prompt": REVIEW_SYSTEM_PROMPT,
            "user_prompt": json.dumps({"untrusted_review": payload}, ensure_ascii=False, separators=(",", ":")),
            "response_schema": review_schema(count)}


class ReviewProvider:
    def __init__(self, *, threshold=2, fail_label=None, malformed=False, observed_models=None):
        self.calls = []
        self.threshold, self.fail_label, self.malformed = threshold, fail_label, malformed
        self.observed_models = observed_models or {}

    def generate_structured(self, **request):
        review = json.loads(request["user_prompt"])["untrusted_review"]
        self.calls.append(review)
        proposals = review["proposals"]
        if len(proposals) > self.threshold:
            raise truncated()
        if proposals[0]["candidate"]["preferred_label"] == self.fail_label:
            raise HuggingFaceHTTPError(403)
        verdicts = [{"review_id": p["review_id"], "decision": "supported", "issue": "none",
                     "reason": p["candidate"]["preferred_label"]} for p in proposals]
        if self.malformed:
            verdicts = []
        return ModelCompletion(json.dumps({"verdicts": verdicts}), "publicai", MODEL, 10, 5,
                               f"request-{len(self.calls)}", requested_model=REQUESTED_MODEL,
                               observed_model=self.observed_models.get(
                                   proposals[0]["candidate"]["preferred_label"], MODEL))


class ReviewFallbackTests(unittest.TestCase):
    def test_custom_review_prompt_preserves_split_recovery(self):
        provider = ReviewProvider()
        run = self.wrapper(provider, review_system_prompt="Custom review instructions.")
        custom_request = dict(request(), system_prompt="Custom review instructions.")
        result = run.generate_structured(**custom_request)
        self.assertEqual(len(parse_verdicts(result.content, 4)), 4)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(len(run.statistics()["review_fallbacks"]), 1)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        # Fake completions below identify the HF 8B profile, independently of
        # the operator's selected profile in the repository configuration.
        with tempfile.TemporaryDirectory() as config_directory:
            config_path = Path(config_directory) / "semantic-models.toml"
            document = (ROOT / "config/semantic-models.toml").read_text(encoding="utf-8")
            document = re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "apertus_8b"', document)
            config_path.write_text(document, encoding="utf-8")
            self.config = load_model_profiles(config_path)
        self.logs = []

    def wrapper(self, provider, config=None, **kwargs):
        result = RecoverableProvider(provider, config or self.config, checkpoint_dir=self.path,
                                     progress=self.logs.append, sleep=lambda _: None, **kwargs)
        result.begin_page(PAGE)
        return result

    def test_split_restores_ids_preserves_scope_and_reports_usage(self):
        provider = ReviewProvider()
        run = self.wrapper(provider)
        result = run.generate_structured(**request())
        verdicts = parse_verdicts(result.content, 4)
        self.assertEqual([v["reason"] for v in verdicts], [f"Proposal {i}" for i in range(1, 5)])
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual([s["section_id"] for s in provider.calls[1]["primary_sections"]], ["section-0001", "section-0002"])
        self.assertEqual([p["review_id"] for p in provider.calls[2]["proposals"]], [1, 2])
        self.assertEqual((result.prompt_tokens, result.output_tokens), (20, 10))
        self.assertIsNone(result.request_id)
        self.assertEqual((result.provider, result.model), ("publicai", MODEL))
        self.assertEqual(result.requested_model, REQUESTED_MODEL)
        self.assertEqual(result.observed_model, MODEL)
        stats = run.statistics()
        self.assertEqual(stats["network_attempts"], 3)
        self.assertEqual(stats["retry_attempts"], 0)
        self.assertEqual(len(stats["incomplete_completions"]), 1)
        self.assertEqual(stats["review_fallbacks"][0]["status"], "complete")
        self.assertEqual(stats["review_fallbacks"][0]["child_request_ids"], ["request-2", "request-3"])
        self.assertEqual(stats["review_fallbacks"][0]["child_model_identities"],
                         [model_identity("request-2"), model_identity("request-3")])

    def test_split_preserves_distinct_approved_observed_models(self):
        provider = ReviewProvider(observed_models={"Proposal 3": MODEL_ALIAS})
        run = self.wrapper(provider)
        result = run.generate_structured(**request())

        self.assertEqual(len(parse_verdicts(result.content, 4)), 4)
        self.assertEqual((result.provider, result.model), ("publicai", MODEL))
        self.assertEqual(result.requested_model, REQUESTED_MODEL)
        self.assertIsNone(result.observed_model)
        self.assertIsNone(result.request_id)
        self.assertEqual(run.statistics()["review_fallbacks"][0]["child_model_identities"],
                         [model_identity("request-2"), model_identity("request-3", MODEL_ALIAS)])

    def test_nested_splits_preserve_exact_leaf_model_identities(self):
        provider = ReviewProvider(threshold=1, observed_models={
            "Proposal 2": MODEL_ALIAS, "Proposal 4": REQUESTED_MODEL,
        })
        run = self.wrapper(provider)
        result = run.generate_structured(**request())

        self.assertEqual(len(parse_verdicts(result.content, 4)), 4)
        self.assertEqual((result.provider, result.model), ("publicai", MODEL))
        self.assertEqual(result.requested_model, REQUESTED_MODEL)
        self.assertIsNone(result.observed_model)
        self.assertIsNone(result.request_id)
        events = run.statistics()["review_fallbacks"]
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["child_model_identities"],
                         [model_identity(None, None), model_identity(None, None)])
        self.assertEqual(events[1]["child_model_identities"],
                         [model_identity("request-3"), model_identity("request-4", MODEL_ALIAS)])
        self.assertEqual(events[2]["child_model_identities"],
                         [model_identity("request-6"), model_identity("request-7", REQUESTED_MODEL)])

    def test_interrupted_split_resumes_only_unfinished_child(self):
        provider = ReviewProvider(fail_label="Proposal 3")
        with self.assertRaises(HuggingFaceHTTPError):
            self.wrapper(provider).generate_structured(**request())
        self.assertEqual(len(provider.calls), 3)
        resumed_provider = ReviewProvider()
        run = self.wrapper(resumed_provider)
        result = run.generate_structured(**request())
        self.assertEqual(len(resumed_provider.calls), 1)
        self.assertEqual(run.hits, 1)
        self.assertEqual(len(parse_verdicts(result.content, 4)), 4)
        cached_provider = ReviewProvider()
        cached = self.wrapper(cached_provider)
        cached.generate_structured(**request())
        self.assertEqual(cached_provider.calls, [])
        self.assertEqual(cached.hits, 2)

    def test_nested_splits_end_at_single_proposals(self):
        provider = ReviewProvider(threshold=1)
        run = self.wrapper(provider)
        result = run.generate_structured(**request())
        self.assertEqual(len(parse_verdicts(result.content, 4)), 4)
        self.assertEqual(len(provider.calls), 7)
        self.assertEqual(len(run.review_fallbacks), 3)

    def test_single_proposal_truncation_stops(self):
        provider = ReviewProvider(threshold=0)
        run = self.wrapper(provider)
        with self.assertRaises(HuggingFaceIncompleteCompletionError):
            run.generate_structured(**request(1))
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(list(self.path.iterdir()), [])

    def test_budget_stops_split_without_losing_completed_child(self):
        config = replace(self.config, extraction=replace(self.config.extraction, max_model_requests_per_page=2))
        provider = ReviewProvider()
        with self.assertRaisesRegex(SemanticModelError, "budget exhausted"):
            self.wrapper(provider, config).generate_structured(**request())
        self.assertEqual(len(provider.calls), 2)
        resumed_provider = ReviewProvider()
        self.wrapper(resumed_provider, config).generate_structured(**request())
        self.assertEqual(len(resumed_provider.calls), 1)

    def test_invalid_child_is_not_cached_and_does_not_trigger_more_splitting(self):
        provider = ReviewProvider(malformed=True)
        with self.assertRaises(ValueError):
            self.wrapper(provider).generate_structured(**request())
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(len(list(self.path.glob("*.json"))), 1)  # Split marker only.
        another = ReviewProvider(malformed=True)
        with self.assertRaises(ValueError):
            self.wrapper(another).generate_structured(**request())
        self.assertEqual(len(another.calls), 1)  # Never retry the parent after bad child validation.

    def test_fresh_mode_ignores_split_markers_and_child_cache(self):
        self.wrapper(ReviewProvider()).generate_structured(**request())
        fresh_provider = ReviewProvider()
        self.wrapper(fresh_provider, fresh=True).generate_structured(**request())
        self.assertEqual(len(fresh_provider.calls), 3)

    def test_non_length_finish_reason_does_not_split(self):
        class FilteredProvider:
            def generate_structured(self, **kwargs):
                raise truncated("content_filter")
        run = self.wrapper(FilteredProvider())
        with self.assertRaises(HuggingFaceIncompleteCompletionError):
            run.generate_structured(**request())
        self.assertEqual(run.attempts, 1)
        self.assertEqual(list(self.path.iterdir()), [])

    def test_extractor_accepts_only_complete_mapped_review_results(self):
        class ExtractionProvider(ReviewProvider):
            def generate_structured(self, **kwargs):
                payload = json.loads(kwargs["user_prompt"])
                if "untrusted_page" not in payload:
                    completion = super().generate_structured(**kwargs)
                    result = json.loads(completion.content)
                    for verdict in result["verdicts"]:
                        if verdict["reason"] == "Proposal 2":
                            verdict.update(decision="unsupported", issue="wrong_scope")
                    return replace(completion, content=json.dumps(result))
                span = payload["untrusted_page"]["evidence_spans"][0]
                candidates = [{"preferred_label": f"Proposal {i}", "alternative_labels": [],
                    "concept_type": "PROCESS", "granularity": "ANSWERABLE", "description": "Apply online.",
                    "scope": "Residents", "user_questions": ["How do I apply?"], "confidence": 0.8,
                    "primary_section_id": span["section_id"], "evidence": [{"evidence_id": span["evidence_id"]}],
                    "relations": []} for i in range(1, 5)]
                return ModelCompletion(json.dumps({"concepts": candidates}), "publicai", MODEL, 10, 5,
                                       requested_model=REQUESTED_MODEL, observed_model=MODEL)

        run = self.wrapper(ExtractionProvider())
        result = CandidateConceptExtractor(run, active_profile="apertus_8b", prompt_profile=REVIEW_PROMPT_PROFILE).extract(PAGE)
        self.assertEqual([c.preferred_label for c in result.candidates], ["Proposal 1", "Proposal 3", "Proposal 4"])
        self.assertEqual(len(result.semantic_reviews), 4)
        self.assertEqual(result.rejected_candidates[0]["proposal"]["preferred_label"], "Proposal 2")
        self.assertEqual(result.request_count, 2)  # Logical generation + combined review.
        self.assertEqual(run.attempts, 4)  # Generation + truncated review + two smaller reviews.
        self.assertEqual((result.prompt_tokens, result.output_tokens), (30, 15))


if __name__ == "__main__":
    unittest.main()
