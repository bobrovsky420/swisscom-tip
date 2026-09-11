import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from swisstip.runtime.corpus import prepare_corpus, import_corpus
from swisstip.runtime.postgres import connect, migrate, sha256


def fixture(root):
    catalogue = b'[Law](https://example.gov/law)'
    (root / 'catalogue.md').write_bytes(catalogue)
    (root / 'plan.json').write_text(json.dumps({'created_at': '2026-09-10T00:00:00Z',
                                               'catalogue_sha256': sha256(catalogue)}))
    for name, raw, flags in [('law.html', b'<h1>Permit</h1><p>Apply online.</p>', []),
                              ('law.pdf', b'%PDF-1.7 test', []),
                              ('shell.html', b'<title>Application</title>', ['javascript_application_shell'])]:
        folder = root / 'pages' / name / 'attempt-001'
        folder.mkdir(parents=True)
        path = folder / name
        path.write_bytes(raw)
        manifest = dict(url='https://example.gov/' + name, references=[{'label': name}],
                        status='saved', snapshots=[dict(relative_path=path.relative_to(root).as_posix(),
                        sha256=sha256(raw), bytes_downloaded=len(raw), review_flags=flags)])
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        (folder.parent / 'latest.json').write_text(json.dumps(manifest))


class CorpusPreparationTests(unittest.TestCase):
    def test_all_formats_preserved_and_classified(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            corpus = prepare_corpus(root, 'test-run', 'Test')
            self.assertEqual(corpus.metadata['snapshot_count'], 3)
            self.assertEqual(corpus.metadata['eligible_count'], 1)
            self.assertEqual(corpus.metadata['archive_only_count'], 2)
            self.assertEqual(len(corpus.files), 11)
            self.assertEqual(prepare_corpus(root, 'test-run', 'Test').inventory_sha256, corpus.inventory_sha256)
            next(root.rglob('law.html/attempt-001/law.html')).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash or size'):
                prepare_corpus(root, 'test-run', 'Test')

    def test_unsafe_manifest_path_and_catalogue_change_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            path = next(root.rglob('manifest.json'))
            manifest = json.loads(path.read_text())
            manifest['snapshots'][0]['relative_path'] = '../escape.html'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                prepare_corpus(root, 'test-run', 'Test')
            (root / 'catalogue.md').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Catalogue'):
                prepare_corpus(root, 'test-run', 'Test')


@unittest.skipUnless(os.environ.get('SWISSTIP_TEST_DATABASE_URL'), 'Real PostgreSQL URL required')
class CorpusDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        cls.admin = os.environ['SWISSTIP_TEST_DATABASE_URL']
        cls.name = 'swisstip_corpus_test_' + uuid4().hex
        with psycopg.connect(cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(cls.name)))
        cls.addClassCleanup(cls.drop_database)
        cls.dsn = make_conninfo(cls.admin, dbname=cls.name)
        migrate(cls.dsn)

    @classmethod
    def drop_database(cls):
        import psycopg
        from psycopg import sql
        assert cls.name.startswith('swisstip_corpus_test_') and len(cls.name.removeprefix('swisstip_corpus_test_')) == 32
        with psycopg.connect(cls.admin, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.name)))

    def test_atomic_idempotent_separate_runs_and_immutable_bytes(self):
        import psycopg
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            corpus = prepare_corpus(root, 'new-pilot', 'New pilot')
            first = import_corpus(self.dsn, corpus)
            self.assertTrue(first['created'])
            self.assertFalse(import_corpus(self.dsn, corpus)['created'])
            second = prepare_corpus(root, 'another-run', 'Another run')
            import_corpus(self.dsn, second)
            with connect(self.dsn) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM swisstip.admin_assets').fetchone()[0], 6)
                self.assertEqual(conn.execute('SELECT count(*) FROM swisstip.releases').fetchone()[0], 0)
            (root / 'extra.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'different content'):
                import_corpus(self.dsn, prepare_corpus(root, 'new-pilot', 'New pilot'))
            for table in ('corpora', 'corpus_files'):
                with self.assertRaises(psycopg.Error), connect(self.dsn) as conn:
                    conn.execute('DELETE FROM swisstip.' + table)
            # Failure after corpus/file insertion rolls back the entire run.
            broken = prepare_corpus(root, 'broken-run', 'Broken')
            broken.assets[0]['asset_id'] = corpus.assets[0]['asset_id']
            with self.assertRaises(psycopg.Error):
                import_corpus(self.dsn, broken)
            with connect(self.dsn) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM swisstip.corpora WHERE corpus_id='broken-run'").fetchone()[0], 0)
