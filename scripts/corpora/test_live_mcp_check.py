"""Live MCP check against a synthetic single-part collection; no remote services."""

import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from swisstip.runtime.fixture import fixture

import live_mcp_check as live


def synthetic_requests(cantons):
    return [dict(tool='resolve', source_url='https://example.invalid/x', evidence_ids=[],
                 arguments=dict(concept_ids=[f'concept-{index}'],
                                jurisdiction=dict(country_code='CH', **({'canton_code': canton} if canton else {}))))
            for index, canton in enumerate(cantons)]


class LiveMcpCheckTests(unittest.TestCase):
    def test_selection_is_jurisdiction_balanced_then_seeded_and_deterministic(self):
        requests = synthetic_requests(['CH-ZH', 'CH-ZH', 'CH-BE', None, 'CH-BE', 'CH-ZH'])
        chosen = live.select_requests(requests, 1, 2, 7)
        self.assertEqual([(kind, key) for kind, key, _, _ in chosen[:3]],
                         [('jurisdiction', 'CH'), ('jurisdiction', 'CH-BE'), ('jurisdiction', 'CH-ZH')])
        self.assertEqual([kind for kind, *_ in chosen[3:]], ['random', 'random'])
        self.assertEqual(len({index for _, _, index, _ in chosen}), 5)
        self.assertEqual(chosen, live.select_requests(requests, 1, 2, 7))
        self.assertEqual(len(live.select_requests(requests, 5, 50, 1)), len(requests))

    def test_percentiles_and_empty_input(self):
        self.assertEqual(live.percentiles([]), {})
        stats = live.percentiles([3.0, 1.0, 2.0, 10.0])
        self.assertEqual((stats['count'], stats['min'], stats['median'], stats['max'], stats['total']),
                         (4, 1.0, 2.5, 10.0, 16.0))

    def test_check_resolution_reports_error_payloads_and_fixture_membership(self):
        item = dict(source_url='https://example.invalid/a', evidence_ids=['e1', 'e2'])
        check, ids = live.check_resolution(item, dict(code='INVALID_ARGUMENT'), 'random', 'CH', 0)
        self.assertIsNone(check['status'])
        self.assertEqual(ids, [])
        resolved = dict(status='SUPPORTED', evidence=[dict(
            evidence_id='e3', citation=dict(url='https://example.invalid/b'), effective_source_language='de',
            schema_version='evidence-object/v2')], supported_portions=[{}], unresolved_portions=[],
            trust=dict(fact_support='PUBLISHED_FACTS_OR_RULES', limitations=['x']),
            freshness=dict(status='FRESH'), trace=dict(channels=['lexical'], candidate_count=1, degradations=[]))
        check, ids = live.check_resolution(item, resolved, 'jurisdiction', 'CH-ZH', 3)
        self.assertEqual(ids, ['e3'])
        self.assertFalse(check['evidence_within_fixture'])
        self.assertFalse(check['citations_match_source'])
        self.assertEqual(check['evidence_languages'], ['de'])
        self.assertEqual(check['supported_facts'], 1)

    def test_end_to_end_stdio_round_trips_against_synthetic_collection(self):
        bundle, request = fixture()
        release_id = bundle.release.release_id
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            part = root / 'part-001'
            part.mkdir()
            release = part / 'release.json'
            release.write_text(bundle.model_dump_json(), encoding='utf-8')
            (root / 'collection.json').write_text(json.dumps(dict(parts=[dict(
                release_id=release_id, release_file='part-001/release.json',
                release_sha256=live.sha256(release))])), encoding='utf-8')
            (root / 'mcp-client.json').write_text(json.dumps(dict(mcpServers=dict(fixture=dict(
                command=sys.executable, args=['-m', 'swisstip.mcp_server.server', '--release', str(release),
                                              '--active-release-id', release_id])))), encoding='utf-8')
            fixture_requests = dict(executed=False, resolve=[dict(
                tool='resolve', arguments={**request, 'retrieval_terms': [], 'max_evidence': 5},
                source_url='https://example.invalid/parent', evidence_ids=['evidence-parent', 'evidence-child'])])
            (part / 'mcp-requests.json').write_text(json.dumps(fixture_requests), encoding='utf-8')
            output = root / 'results'
            args = SimpleNamespace(collection=root / 'collection.json', client=None, output=output,
                                   per_jurisdiction=1, random_sample=0, seed=1, time_budget=120.0, skip_hashes=False)
            summary = asyncio.run(asyncio.wait_for(live.run(args), timeout=180))

            self.assertTrue(summary['tools_complete'])
            self.assertEqual(summary['output_schema_failures'], 0)
            self.assertEqual(summary['text_parity_failures'], 0)
            self.assertEqual(summary['expectations']['unmet'], [])
            self.assertTrue(summary['identity']['release_hash_match'][release_id])
            self.assertTrue(summary['discovery']['root_is_active'])
            self.assertEqual(summary['discovery']['parts'][release_id]['knowledge_spaces'], ['fixture-space'])
            part_summary = summary['resolution'][release_id]
            self.assertEqual(part_summary['executed'], 1)
            self.assertEqual(part_summary['skipped_for_budget'], 0)
            self.assertEqual(sum(part_summary['statuses'].values()), 1)
            self.assertEqual(part_summary['evidence_parity_checked'], 1)
            self.assertEqual(part_summary['evidence_parity'], 1)
            self.assertIn('max-evidence-1', summary['boundary_outcomes'])
            self.assertLessEqual(summary['boundary_outcomes']['max-evidence-1']['evidence'], 1)
            self.assertTrue((output / 'calls.jsonl').exists())
            self.assertIn('# Live MCP check', (output / 'README.md').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((output / 'summary.json').read_text(encoding='utf-8'))['calls'], summary['calls'])
            self.assertFalse(json.loads((part / 'mcp-requests.json').read_text(encoding='utf-8'))['executed'])
            with self.assertRaises(SystemExit):
                asyncio.run(live.run(args))


if __name__ == '__main__':
    unittest.main()
