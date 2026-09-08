"""Optional real-database tests. Each run owns a separate disposable database."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import unittest
from uuid import uuid4

from swisstip.runtime.fixture import fixture
from swisstip.runtime.hybrid_fixture import hybrid_fixture
from swisstip.runtime.postgres import connect, import_release, migrate, PostgresReleaseStore
from swisstip.runtime.retrieval import RetrievalFailure


@unittest.skipUnless(os.environ.get('SWISSTIP_TEST_DATABASE_URL'), 'Set SWISSTIP_TEST_DATABASE_URL for real PostgreSQL tests')
class PostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        cls.admin_dsn = os.environ['SWISSTIP_TEST_DATABASE_URL']
        cls.database = 'swisstip_test_' + uuid4().hex
        cls.dsn = make_conninfo(cls.admin_dsn, dbname=cls.database)
        with psycopg.connect(cls.admin_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(cls.database)))
        cls.addClassCleanup(cls.drop_database)
        migrate(cls.dsn)
        cls.bundle, _ = hybrid_fixture(fallback=False)
        cls.raw = cls.bundle.model_dump_json().encode()
        import_release(cls.dsn, cls.raw, classification='synthetic')

    @classmethod
    def drop_database(cls):
        import psycopg
        from psycopg import sql
        # Only the UUID database created by this class can be removed.
        assert cls.database.startswith('swisstip_test_') and len(cls.database) == 46
        with psycopg.connect(cls.admin_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.database)))

    def test_idempotent_migrations_and_import_preserve_exact_bytes(self):
        migrate(self.dsn)
        result = import_release(self.dsn, self.raw, classification='synthetic')
        self.assertFalse(result['created'])
        store = PostgresReleaseStore(self.dsn, active_release_id=self.bundle.release.release_id)
        self.assertEqual(store.export_bytes(self.bundle.release.release_id), self.raw)
        self.assertEqual(store.get(self.bundle.release.release_id), self.bundle)

    def test_replacement_and_invalid_content_rejected(self):
        # Even equivalent JSON formatting cannot replace archived file bytes.
        alternate = json.dumps(json.loads(self.raw), indent=2).encode()
        with self.assertRaisesRegex(ValueError, 'different_content'):
            import_release(self.dsn, alternate, classification='synthetic')
        bad = json.loads(self.raw)
        bad['evidence'][0]['original_excerpt'] = 'tampered'
        with self.assertRaises(ValueError):
            import_release(self.dsn, json.dumps(bad).encode(), classification='synthetic')

    def test_attachment_conflict_rolls_back_entire_transaction(self):
        import_release(self.dsn, self.raw, classification='synthetic', attachments={'existing': b'one'})
        with self.assertRaisesRegex(ValueError, 'attachment_content_conflict'):
            import_release(self.dsn, self.raw, classification='synthetic',
                           attachments={'must-roll-back': b'two', 'existing': b'different'})
        with connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM swisstip.attachments WHERE path='must-roll-back'").fetchone()[0], 0)

    def test_database_updates_and_deletes_are_rejected(self):
        import psycopg
        for statement in ["UPDATE swisstip.releases SET classification='experimental'",
                          'DELETE FROM swisstip.evidence', 'TRUNCATE swisstip.attachments',
                          "UPDATE swisstip.embeddings SET model='changed'"]:
            with self.subTest(statement=statement), self.assertRaises(psycopg.Error):
                with connect(self.dsn) as conn:
                    conn.execute(statement)

    def test_concurrent_import_and_historical_selection(self):
        newer, _ = fixture('concurrent-history')
        raw = newer.model_dump_json().encode()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: import_release(self.dsn, raw, classification='synthetic'), range(2)))
        self.assertEqual(sum(r['created'] for r in results), 1)
        old = PostgresReleaseStore(self.dsn, active_release_id=self.bundle.release.release_id)
        new = PostgresReleaseStore(self.dsn, active_release_id=newer.release.release_id)
        old.activate(slot='test')
        new.activate(slot='test')
        self.assertEqual(old.active_release_id, self.bundle.release.release_id)
        self.assertEqual(old.get(newer.release.release_id), newer)
        self.assertIsNone(old.get('absent'))
        with self.assertRaisesRegex(ValueError, 'active_release_unavailable'):
            PostgresReleaseStore(self.dsn, active_release_id='absent')

    def test_exact_vector_scope_and_missing_revision_rejection(self):
        store = PostgresReleaseStore(self.dsn, active_release_id=self.bundle.release.release_id)
        first = self.bundle.retrieval_index.vectors[0]
        identifier = next(e.evidence_id for e in self.bundle.evidence if e.identity == first.evidence_ref)
        scores = store.score_vectors(self.bundle, [identifier], [first.values])
        self.assertEqual(set(scores), {identifier})
        self.assertAlmostEqual(scores[identifier], 1, places=6)
        self.assertEqual(store.score_vectors(self.bundle, [], [first.values]), {})
        with self.assertRaises(RetrievalFailure):
            store.score_vectors(self.bundle, ['invented'], [first.values])
        with self.assertRaises(RetrievalFailure):
            store.score_vectors(self.bundle, [identifier], [[0] * len(first.values)])
        changed = self.bundle.model_copy(deep=True)
        changed.retrieval_index.identity = changed.retrieval_index.identity.model_copy(update={'sha256': 'f' * 64})
        with self.assertRaisesRegex(RetrievalFailure, 'membership_mismatch'):
            store.score_vectors(changed, [identifier], [first.values])


if __name__ == '__main__':
    unittest.main()
