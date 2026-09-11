"""Exercise GUI profile selection through real normalization and offline CLI jobs."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import tomli_w

from swisstip.control import api, worker
from swisstip.core.model_profiles import load_model_config
from swisstip.ingestion.concepts import (
    CandidateConceptExtractor,
    REVIEW_PROMPT_PROFILE,
    STRUCTURED_PROMPT_PROFILE,
    normalize_downloaded_page,
    select_content_sections,
)
from swisstip.ingestion.structured_extraction import StructuredExtraction
from swisstip.runtime.postgres import sha256


ROOT = Path(__file__).resolve().parents[3]
HTML = b"""<html lang="en"><title>Residence permits</title>
<nav>Menu distraction</nav><main><h1>Residence permits</h1>
<h2>Eligibility</h2><p>A permit is required for stays longer than three months.</p>
<ol><li>Register with the municipality.</li><li>Bring your passport.</li></ol>
<h2>Contact</h2><p>Permit office: call 044 123 45 67.</p>
<h2>News</h2><p>The department published its annual report yesterday.</p>
</main></html>"""


class ExtractionProfileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'config').mkdir()
        self.config = load_model_config(ROOT / 'config/semantic-models.toml')
        self.asset = dict(asset_id='fixture-asset', filename='residence.html', original_bytes=HTML,
                          sha256=sha256(HTML), processing_eligible=True, acquisition_metadata={})
        for module in (api, worker):
            root_patch = patch.object(module, 'ROOT', self.root)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def set_profile(self, profile):
        self.config['extraction']['prompt_profile'] = profile
        (self.root / 'config/semantic-models.toml').write_text(tomli_w.dumps(self.config), encoding='utf-8')

    def test_catalog_and_preview_follow_active_extraction_profile(self):
        source = self.root / 'residence.html'
        source.write_bytes(HTML)
        for profile in (REVIEW_PROMPT_PROFILE, STRUCTURED_PROMPT_PROFILE):
            with self.subTest(profile=profile):
                self.set_profile(profile)
                with patch.object(api, 'rows', return_value=[self.asset]), patch.object(
                    api, 'catalog_data', return_value={'sources': []}
                ):
                    preview = api.preview('fixture-asset')
                    catalog = api.catalog()
                self.assertEqual(catalog['extraction_profile'], profile)
                self.assertEqual(preview['extraction_profile'], profile)
                page = normalize_downloaded_page(
                    source, preserve_structure=profile == REVIEW_PROMPT_PROFILE,
                    logical_blocks=profile == STRUCTURED_PROMPT_PROFILE,
                )
                if profile == REVIEW_PROMPT_PROFILE:
                    visible, excluded = select_content_sections(page, exclude_embedded_news=True)
                    expected = [dict(section_id=s.section_id, text=s.evidence_text) for s in visible]
                    excluded_count = len(excluded)
                    self.assertNotIn('Permit office', json.dumps(preview))
                    self.assertNotIn('annual report', json.dumps(preview))
                else:
                    _, inventory = StructuredExtraction(CandidateConceptExtractor(
                        None, active_profile='preview', prompt_profile=profile,
                    )).plan(page)
                    visible = [s for s in inventory if s['status'] != 'excluded_policy']
                    expected = [dict(section_id=s['section_id'], text=s['evidence_text']) for s in visible]
                    excluded_count = len(inventory) - len(visible)
                    self.assertIn('Permit office', json.dumps(preview))
                self.assertEqual(preview['sections'], expected)
                self.assertEqual(preview['characters'], sum(len(s['text']) for s in expected))
                self.assertEqual(preview['excluded_sections'], excluded_count)
                self.assertIn('three months', json.dumps(preview))
                self.assertNotIn('Menu distraction', json.dumps(preview))
                self.assertEqual(self.asset['original_bytes'], HTML)
                self.assertEqual(source.read_bytes(), HTML)

    def test_offline_worker_honors_frozen_v3_and_v4_profiles(self):
        for profile, later_profile in (
            (REVIEW_PROMPT_PROFILE, STRUCTURED_PROMPT_PROFILE),
            (STRUCTURED_PROMPT_PROFILE, REVIEW_PROMPT_PROFILE),
        ):
            with self.subTest(profile=profile):
                self.set_profile(profile)
                frozen = api.config_text('deepseek_v4_1_flash')
                self.set_profile(later_profile)
                identifier = uuid4().hex
                job = dict(job_id=identifier, kind='plan', config_text=frozen,
                           request=dict(asset_ids=['fixture-asset']))

                def rows(query, params):
                    if 'admin_assets' in query:
                        return [self.asset]
                    return [dict(cancel_requested=False)]

                with patch.object(worker, 'rows', side_effect=rows), patch.object(
                    worker, 'connect'
                ), patch.object(worker, 'database_url', return_value='offline-fixture'), patch.object(
                    worker, 'finish'
                ) as finish, patch.object(worker, 'stopping', return_value=False):
                    worker.execute(job)
                finish.assert_called_once()
                args = finish.call_args.args
                self.assertEqual(args[1], 'completed', args)
                result = args[3]
                self.assertEqual(result['prompt_profile'], profile)
                self.assertEqual(result['model_requests_sent'], 0)
                self.assertGreater(result['planned_request_ceiling'], 0)
                self.assertEqual(bool(result['pages'][0]['source_inventory']), profile == STRUCTURED_PROMPT_PROFILE)
                folder = self.root / '.local/admin/jobs' / identifier
                self.assertEqual((folder / 'semantic-models.toml').read_text(encoding='utf-8'), frozen)
                self.assertEqual((folder / 'fixture-asset.html').read_bytes(), HTML)
                self.assertNotIn('Provider attempt', args[2])
                self.assertIn('model=deepseek-flash', args[2])


if __name__ == '__main__':
    unittest.main()
