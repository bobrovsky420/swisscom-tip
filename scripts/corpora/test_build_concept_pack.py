"""Concept-pack conversion and collection assembly on a synthetic V3 batch result; no network."""

import json
from pathlib import Path
import tempfile
import unittest

from swisstip.ingestion.source_snapshots import normalize_source_snapshot

from audit_source_languages import sha
import assemble_collection
import build_concept_pack

HTML = ('<html lang="de-CH"><head><title>Aufenthaltsbewilligung Kanton Test</title></head><body>'
        '<main><h1>Aufenthaltsbewilligung</h1><p>Wer sich laenger als drei Monate im Kanton aufhaelt, '
        'muss sich innert 14 Tagen bei der Gemeinde anmelden.</p><h2>Gebuehren</h2>'
        '<p>Die Gebuehr betraegt 65 Franken und ist bei der Anmeldung zu bezahlen.</p></main></body></html>')


def stage_page(root):
    page_dir = root / 'inputs' / 'pages' / 'p1'
    (page_dir / 'attempt-001').mkdir(parents=True)
    raw = HTML.encode('utf-8')
    path = page_dir / 'attempt-001' / 'response.html'
    path.write_bytes(raw)
    (page_dir / 'manifest.json').write_text(json.dumps(dict(
        url='https://www.zh.ch/test', status='saved', references=[], registry_entries=[], discoveries=[],
        snapshots=[dict(relative_path='pages/p1/attempt-001/response.html', requested_url='https://www.zh.ch/test',
                        final_url='https://www.zh.ch/test', content_type='text/html', sha256=sha(raw),
                        bytes_downloaded=len(raw), retrieved_at='2026-09-11T12:00:00+00:00', review_flags=[])],
        corpus_id='test-corpus', corpus_path='pages/p1/attempt-001/response.html')), encoding='utf-8')
    return path, raw


def synthetic_result(path, raw):
    page = normalize_source_snapshot(path, preserve_structure=True)
    section = next(s for s in page.sections if 'anmelden' in s.evidence_text)
    quote = section.evidence_text
    candidate = dict(candidate_id='candidate-0123456789abcdef', preferred_label='Anmeldung bei der Gemeinde',
                     alternative_labels=['Anmeldepflicht'], concept_type='RULE', granularity='ANSWERABLE',
                     description='Wer sich laenger als drei Monate im Kanton aufhaelt, muss sich innert 14 Tagen anmelden.',
                     scope='Personen mit Aufenthalt im Kanton von mehr als drei Monaten',
                     user_questions=['Bis wann muss ich mich anmelden?'], confidence=0.8,
                     evidence=[dict(section_id=section.section_id, quote=quote, start=0, end=len(quote))],
                     relations=[], validation_state='CANDIDATE', primary_section_id=section.section_id)
    report = dict(schema_version='swisstip.concept-proposal-report/v1', document_id=page.document_id, source=str(path),
                  title=page.title, language=page.language, input_hash=page.content_hash, prompt_profile='concept_extraction_v3',
                  effective_prompts=dict(extraction=dict(sha256='e' * 64), review=dict(sha256='r' * 64)),
                  model_identities=[dict(provider='anthropic-assistant', model='claude-fable-5-1')],
                  provenance=dict(source_url='https://www.zh.ch/test', final_url='https://www.zh.ch/test',
                                  retrieved_at='2026-09-11T12:00:00+00:00', sha256=sha(raw)),
                  candidates=[candidate], semantic_reviews=[dict(chunk_index=1, candidate_index=1, decision='supported',
                                                                 issue='none', reason='ok', preferred_label=candidate['preferred_label'])],
                  warnings=[])
    return dict(schema_version='swisstip.concept-proposal-batch/v1', reports=[report])


class ConceptPackTests(unittest.TestCase):
    def test_candidates_become_a_validated_part_and_assemble_into_a_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, raw = stage_page(root)
            run_dir = root / 'runs' / 'batch-001'
            run_dir.mkdir(parents=True)
            (run_dir / 'result.json').write_text(json.dumps(synthetic_result(path, raw), ensure_ascii=False), encoding='utf-8')
            output = root / 'part-test'
            report = build_concept_pack.build(root, output, 'concept-test-part')
            self.assertTrue(report['validated'])
            self.assertEqual((report['documents'], report['facts'], report['evidence'], report['concepts']), (1, 1, 1, 1))
            self.assertEqual(report['preflight_statuses'], {'READY': 1})
            self.assertEqual(report['completion_identities'], {'anthropic-assistant/claude-fable-5-1': 1})
            bundle = json.loads((output / 'release.json').read_text(encoding='utf-8'))
            evidence = bundle['evidence'][0]
            document = bundle['documents'][0]
            self.assertEqual(document['text'][evidence['start_offset']:evidence['end_offset']], evidence['original_excerpt'])
            self.assertEqual(evidence['effective_source_language'], 'de-CH')
            self.assertEqual(evidence['jurisdiction'], {'country_code': 'CH', 'canton_code': 'CH-ZH', 'municipality_id': None})
            entries = {e['entry_id']: e for e in bundle['catalog']['entries']}
            self.assertEqual(entries['candidate-0123456789abcdef']['parent_ids'], ['candidate-type-rule'])
            self.assertEqual(entries['candidate-type-rule']['parent_ids'], ['residence'])
            self.assertTrue(all(e['lifecycle'] == 'VERIFIED_AUTOMATIC' for e in bundle['catalog']['entries']))
            requests = json.loads((output / 'mcp-requests.json').read_text(encoding='utf-8'))
            self.assertFalse(requests['executed'])
            self.assertEqual(requests['resolve'][0]['arguments']['intent'], 'read-concept-candidates')
            with self.assertRaises(ValueError):
                build_concept_pack.build(root, output, 'concept-test-part')

            collection_dir = root / 'collection'
            collection = assemble_collection.assemble(collection_dir, [('part-001', output)], {'part-001': 'test'})
            self.assertEqual(collection['part_actions'], {'part-001': 'copied'})
            self.assertEqual(collection['parts'][0]['release_file'], 'part-001/release.json')
            self.assertEqual(collection['parts'][0]['release_sha256'], sha((collection_dir / 'part-001' / 'release.json').read_bytes()))
            client = json.loads((collection_dir / 'mcp-client.json').read_text(encoding='utf-8'))
            args = client['mcpServers']['residence-expanded']['args']
            self.assertEqual(args[-1], 'concept-test-part')
            again = assemble_collection.assemble(collection_dir, [('part-001', output)], {})
            self.assertEqual(again['part_actions'], {'part-001': 'kept'})


if __name__ == '__main__':
    unittest.main()
