"""Real PostgreSQL and builder tests; no external HTTP or model inference."""
import json
import os
import unittest
import subprocess
import sys
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from swisstip.runtime.postgres import migrate, sha256
from swisstip.runtime.corpus import prepare_corpus, import_corpus
from swisstip.control.api import app
from swisstip.control.store import rows
from swisstip.control.worker import execute, clean_log


@unittest.skipUnless(os.environ.get('SWISSTIP_TEST_DATABASE_URL'), 'Set SWISSTIP_TEST_DATABASE_URL for database integration tests')
class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = os.environ['SWISSTIP_TEST_DATABASE_URL']
        cls.name = 'swisstip_admin_test_' + uuid4().hex
        with psycopg.connect(cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(cls.name)))
        cls.dsn = make_conninfo(cls.admin, dbname=cls.name)
        cls.environment = patch.dict(os.environ, {'SWISSTIP_DATABASE_URL': cls.dsn})
        cls.environment.start()
        migrate(cls.dsn)
        cls.client = TestClient(app, base_url='http://127.0.0.1:8000')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.environment.stop()
        assert cls.name.startswith('swisstip_admin_test_') and len(cls.name.removeprefix('swisstip_admin_test_')) == 32
        with psycopg.connect(cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.name)))

    def post(self, path, body):
        return self.client.post(path, json=body, headers={'X-Swisstip-Local': '1'})

    def asset(self):
        filename = uuid4().hex + '.html'
        response = self.post('/api/assets', dict(source_id='ch-sem-residence-en', filename=filename,
                  text='<html lang="en"><title>Permit example</title><nav>Menu distraction</nav><main><h1>Residence</h1><p>A permit is required for a stay longer than three months.</p></main></html>'))
        self.assertEqual(response.status_code, 200, response.text)
        return next(a for a in self.client.get('/api/assets').json() if a['filename'] == filename)

    def job(self):
        asset = self.asset()
        response = self.post('/api/jobs', dict(kind='plan', asset_ids=[asset['asset_id']]))
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_catalog_has_proposed_demo_and_no_credentials(self):
        response = self.client.get('/api/catalog')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(s['selected'] for s in response.json()['sources']), 3)
        self.assertNotIn(self.dsn, response.text)

    def test_corpus_filter_archive_gate_and_worker_provenance(self):
        corpus_id = 'test-corpus-' + uuid4().hex
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalogue = b'[Law](https://example.gov/law)'
            (root / 'catalogue.md').write_bytes(catalogue)
            (root / 'plan.json').write_text(json.dumps({'created_at': '2026-09-10T00:00:00Z',
                                                       'catalogue_sha256': sha256(catalogue)}))
            for suffix, raw in [('html', b'<h1>Permit</h1><p>Apply online.</p>'), ('pdf', b'%PDF-1.7 test')]:
                folder = root / 'pages' / suffix / 'attempt-001'
                folder.mkdir(parents=True)
                path = folder / ('response.' + suffix)
                path.write_bytes(raw)
                manifest = dict(url='https://example.gov/law', references=[{'label': 'Law'}], status='saved',
                                snapshots=[dict(relative_path=path.relative_to(root).as_posix(), sha256=sha256(raw),
                                bytes_downloaded=len(raw), review_flags=[], requested_url='https://example.gov/law',
                                final_url='https://example.gov/law', retrieved_at='2026-09-10T00:00:00Z',
                                content_type='text/html' if suffix == 'html' else 'application/pdf')])
                (folder / 'manifest.json').write_text(json.dumps(manifest))
                (folder.parent / 'latest.json').write_text(json.dumps(manifest))
            import_corpus(self.dsn, prepare_corpus(root, corpus_id, 'Corpus test'))
        saved = self.client.get('/api/assets', params={'corpus_id': corpus_id}).json()
        self.assertEqual(len(saved), 2)
        self.assertTrue(all(a['corpus_id'] == corpus_id for a in saved))
        self.assertIn(corpus_id, [c['corpus_id'] for c in self.client.get('/api/corpora').json()])
        self.assertFalse(any(a['corpus_id'] for a in self.client.get('/api/assets?corpus_id=__legacy__').json()))
        pdf = next(a for a in saved if not a['processing_eligible'])
        html = next(a for a in saved if a['processing_eligible'])
        self.assertEqual(self.post('/api/jobs', dict(kind='plan', asset_ids=[pdf['asset_id']])).status_code, 422)
        self.assertEqual(self.client.get('/api/assets/' + pdf['asset_id'] + '/preview').status_code, 422)
        self.assertEqual(self.client.get('/api/assets/' + html['asset_id'] + '/preview').status_code, 200)
        created = self.post('/api/jobs', dict(kind='plan', asset_ids=[html['asset_id']])).json()
        self.assertEqual(created['request']['corpus_ids'], [corpus_id])
        execute(rows('SELECT * FROM swisstip.admin_jobs WHERE job_id=%s', (created['job_id'],))[0])
        job = self.client.get('/api/jobs/' + created['job_id']).json()
        self.assertEqual(job['status'], 'completed', job)
        self.assertEqual(job['result']['model_requests_sent'], 0)
        self.assertEqual(job['result']['pages'][0]['provenance']['corpus_id'], corpus_id)

    def test_cross_origin_and_bad_host_cannot_write(self):
        self.assertEqual(self.client.post('/api/assets/pilot', json={}).status_code, 403)
        response = self.client.post('/api/assets/pilot', json={}, headers={'X-Swisstip-Local': '1', 'Origin': 'https://example.org'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get('/api/catalog', headers={'Host': 'attacker.example'}).status_code, 400)

    def test_upload_path_and_source_are_constrained(self):
        for filename, source in [('../escape.html', 'ch-sem-residence-en'), ('script.exe', 'ch-sem-residence-en'), ('ok.html', 'unknown')]:
            self.assertEqual(self.post('/api/assets', dict(source_id=source, filename=filename, text='hello')).status_code, 422)

    def test_preview_uses_real_filter_and_keeps_original_bytes(self):
        asset = self.asset()
        before = rows('SELECT original_bytes FROM swisstip.admin_assets WHERE asset_id=%s', (asset['asset_id'],))[0]
        response = self.client.get(f"/api/assets/{asset['asset_id']}/preview")
        self.assertEqual(response.status_code, 200)
        text = json.dumps(response.json())
        self.assertIn('three months', text)
        self.assertNotIn('Menu distraction', text)
        self.assertEqual(before, rows('SELECT original_bytes FROM swisstip.admin_assets WHERE asset_id=%s', (asset['asset_id'],))[0])

    def test_offline_plan_executes_real_cli_and_persists_result(self):
        job = self.job()
        record = rows('SELECT * FROM swisstip.admin_jobs WHERE job_id=%s', (job['job_id'],))[0]
        execute(record)
        response = self.client.get('/api/jobs/' + job['job_id']).json()
        self.assertEqual(response['status'], 'completed', response)
        self.assertEqual(response['result']['model_requests_sent'], 0)
        self.assertGreater(response['result']['planned_request_ceiling'], 0)
        self.assertEqual(len(response['result_sha256']), 64)
        self.assertIn('Normalizing page', response['log'])

    def test_queued_cancellation_and_invalid_inputs(self):
        job = self.job()
        self.assertEqual(self.post('/api/jobs/' + job['job_id'] + '/cancel', {}).status_code, 200)
        self.assertEqual(self.client.get('/api/jobs/' + job['job_id']).json()['status'], 'cancelled')
        self.assertEqual(self.post('/api/jobs', dict(kind='plan', asset_ids=['missing'])).status_code, 422)
        self.assertEqual(self.post('/api/jobs', dict(kind='crawl', source_ids=['ai-residence'])).status_code, 422)
        response = self.post('/api/jobs', dict(kind='crawl', source_ids=['ch-sem-residence-en']))
        self.assertEqual(response.status_code, 202, response.text)
        record = rows('SELECT config_text FROM swisstip.admin_jobs WHERE job_id=%s', (response.json()['job_id'],))[0]
        self.assertEqual(json.loads(record['config_text'])['schema_version'], 'swisstip.source-catalog/v1')

    def test_review_is_bound_to_result_and_candidate(self):
        job = self.job()
        result = {'reports': [{'candidates': [{'candidate_id': 'candidate-test', 'preferred_label': 'Test draft'}]}]}
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE swisstip.admin_jobs SET status='completed',result=%s WHERE job_id=%s", (Jsonb(result), job['job_id']))
        digest = self.client.get('/api/jobs/' + job['job_id']).json()['result_sha256']
        path = '/api/jobs/' + job['job_id'] + '/reviews'
        body = dict(result_sha256='0'*64, candidate_id='candidate-test', reviewer='Test reviewer', decision='accept_draft', notes='Fixture only')
        self.assertEqual(self.post(path, body).status_code, 409)
        body['result_sha256'] = digest
        body['candidate_id'] = 'other'
        self.assertEqual(self.post(path, body).status_code, 422)
        body['candidate_id'] = 'candidate-test'
        self.assertEqual(self.post(path, body).status_code, 200)
        self.assertEqual(len(self.client.get(path).json()), 1)
        self.assertEqual(rows('SELECT count(*) AS n FROM swisstip.releases')[0]['n'], 0)

    def test_logs_redact_keys_and_database_connection(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-secret-key-value'}):
            result = clean_log(self.dsn + ' test-secret-key-value')
        self.assertNotIn(self.dsn, result)
        self.assertNotIn('test-secret-key-value', result)

    def test_active_cancellation_stops_child(self):
        job = self.job()
        record = rows('SELECT * FROM swisstip.admin_jobs WHERE job_id=%s', (job['job_id'],))[0]
        original = subprocess.Popen
        started = threading.Event()
        processes = []

        def slow_child(command, **kwargs):
            process = original([sys.executable, '-c', 'import time; time.sleep(20)'], **kwargs)
            processes.append(process)
            started.set()
            return process

        with patch('swisstip.control.worker.subprocess.Popen', side_effect=slow_child):
            thread = threading.Thread(target=execute, args=(record,))
            thread.start()
            try:
                self.assertTrue(started.wait(5))
                self.post('/api/jobs/' + job['job_id'] + '/cancel', {})
            finally:
                thread.join(10)
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            self.assertFalse(thread.is_alive())
        self.assertEqual(self.client.get('/api/jobs/' + job['job_id']).json()['status'], 'cancelled')
        self.assertIsNotNone(processes[0].returncode)

    def test_exit_zero_with_empty_extraction_needs_attention(self):
        job = self.job()
        record = rows('SELECT * FROM swisstip.admin_jobs WHERE job_id=%s', (job['job_id'],))[0]
        record['kind'] = 'extract'
        original = subprocess.Popen
        report = {'reports': [{'candidates': [], 'warnings': ['Provider did not complete']}], 'quality_summary': {'candidate_count': 0}}
        def empty_completion(command, **kwargs):
            return original([sys.executable, '-c', 'print(' + repr(json.dumps(report)) + ')'], **kwargs)
        with patch('swisstip.control.worker.subprocess.Popen', side_effect=empty_completion):
            execute(record)
        response = self.client.get('/api/jobs/' + job['job_id']).json()
        self.assertEqual(response['status'], 'needs_attention')
        self.assertEqual(response['result']['reports'][0]['warnings'], report['reports'][0]['warnings'])


if __name__ == '__main__':
    unittest.main()
