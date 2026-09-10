"""Lossless request serialization replay; invalid live verdicts stay invalid."""
import copy
import json
from pathlib import Path
import unittest

from swisstip.ingestion.concepts import CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection
from swisstip.ingestion.source_structure import VERSION as NORMALIZATION_VERSION
import test_structured_extraction as helpers


class SavedProvider:
    def __init__(self, saved, *, oversized=False):
        self.saved, self.oversized, self.calls = saved, oversized, []

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request['user_prompt'])
        if 'concepts' in payload:
            # Repeat the actual contradictory review, not a new approval.
            content = self.saved['failed_review']['raw_completion']
        else:
            # The post-feedback extraction is a replay control: no live repair
            # exists because the original attempt stopped before that call.
            content = self.saved['raw_extraction']
            if self.oversized:
                response = json.loads(content)
                for concept in response['concepts']:
                    concept['limitations'] = ['Offline length control. ' * 30]
                content = json.dumps(response)
        return ModelCompletion(content, 'offline-replay', 'offline-replay')


class CompactRepairInputTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((Path(__file__).parent / 'fixtures/deepseek_v4_zh_ed64c431.json').read_text(encoding='utf-8'))
        self.page = NormalizedPage('saved-zurich', 'fixture', 'Zurich', 'de',
            self.saved['provenance']['input_hash'],
            tuple(NormalizedSection(b['section_id'], '', b['text'], block_kind='paragraph', scope_id=b['scope_id'])
                  for b in self.saved['evidence'].values()), normalization_version=NORMALIZATION_VERSION,
            source_sha256=self.saved['provenance']['source_sha256'])

    def run_saved(self, *, oversized=False):
        original = copy.deepcopy(self.saved)
        provider = SavedProvider(self.saved, oversized=oversized)
        progress = []
        engine = CandidateConceptExtractor(provider, active_profile='offline-replay',
            prompt_profile='concept_extraction_v4', chunk_content_characters=6400,
            max_concepts_per_chunk=6, max_review_input_characters=64000, progress=progress.append)
        report = engine.extract(self.page)
        self.assertLessEqual(len(provider.calls), engine.planned_request_count(self.page))
        self.assertEqual(self.saved, original)
        return provider, report, progress

    def test_saved_repair_fits_with_identical_source_and_feedback_values(self):
        provider, report, progress = self.run_saved()
        self.assertEqual(len(provider.calls), 4)
        initial = json.loads(provider.calls[0]['user_prompt'])
        repair_text = provider.calls[2]['user_prompt']
        repair = json.loads(repair_text)
        self.assertEqual(repair['untrusted_source'], initial['untrusted_source'])
        failure = self.saved['failed_review']
        self.assertEqual(repair['repair'], {
            'revision': 0, 'failure_stage': 'review_validation', 'proposals': failure['proposals'],
            'structural_rejections': [], 'saturated': failure['saturated'],
            'validation_error': failure['error']})
        self.assertEqual(len(repair_text), self.saved['compact_repair_characters'])
        self.assertEqual(len(json.dumps(repair, ensure_ascii=False)), self.saved['original_repair_characters'])
        self.assertLessEqual(len(repair_text), 25600)
        self.assertTrue(any('from 25775 to 24755 characters' in line for line in progress))
        self.assertEqual(report.quality_metrics['repair_request_count'], 1)
        self.assertEqual(report.quality_metrics['review_request_count'], 2)
        self.assertFalse(report.candidates)
        self.assertEqual([h['error'] for h in report.semantic_reviews[0]['history']], [failure['error']] * 2)
        # The contradiction is preserved, not normalized into an approval.
        self.assertIn('unconditional source assertion cannot have supported added conditions', failure['error'])
        next_review = json.loads(provider.calls[3]['user_prompt'])
        self.assertEqual(next_review['review_validation_feedback']['validation_error'], failure['error'])

    def test_payload_still_over_limit_sends_no_partial_repair(self):
        provider, report, progress = self.run_saved(oversized=True)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(report.quality_metrics['repair_request_count'], 0)
        last = report.semantic_reviews[0]['history'][-1]
        self.assertEqual(last['failure_stage'], 'extraction_input')
        self.assertIn('extraction input exceeds bounded source/feedback allowance', last['error'])
        self.assertIn('25600', last['error'])
        self.assertFalse(report.candidates)
        self.assertFalse(any('compacted extraction JSON whitespace' in line for line in progress))

    def test_normal_sized_requests_keep_previous_serialization(self):
        helper = helpers.StructuredTests()
        provider = helpers.Provider(generate=lambda response, payload: response.update(saturated=True))
        helper.engine(provider).extract(helper.page('<p>Apply online.</p>'))
        self.assertEqual(len(provider.calls), 4)
        for request in provider.calls:
            text = request['user_prompt']
            self.assertEqual(text, json.dumps(json.loads(text), ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
