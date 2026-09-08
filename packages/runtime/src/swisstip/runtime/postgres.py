"""Append-only PostgreSQL release storage and exact, scoped pgvector scoring.

Original bytes remain authoritative for file export. JSONB and float32 vectors
are derived query representations. Importing a pilot does not approve knowledge.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.resources import files
import json
import math
import os
from pathlib import Path

from .release import ReleaseBundle, validate_release
from .retrieval import RetrievalFailure, _unit


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def connect(dsn):
    import psycopg
    return psycopg.connect(dsn, connect_timeout=10,
                           options='-c statement_timeout=30000 -c lock_timeout=10000')


def migrate(dsn):
    """Transactional, checksum-bound migrations, serialized across importers."""
    with connect(dsn) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(20260908)')
        conn.execute('CREATE SCHEMA IF NOT EXISTS swisstip')
        conn.execute('CREATE TABLE IF NOT EXISTS swisstip.schema_migrations '
                     '(name text PRIMARY KEY, sha256 text NOT NULL)')
        for migration in sorted(files('swisstip.runtime').joinpath('migrations').iterdir(), key=lambda p: p.name):
            if not migration.name.endswith('.sql'):
                continue
            # Git checkouts may use CRLF on Windows; SQL migration identity must
            # survive transfer between Windows and Linux.
            raw = migration.read_bytes().replace(b'\r\n', b'\n')
            previous = conn.execute('SELECT sha256 FROM swisstip.schema_migrations WHERE name=%s',
                                    (migration.name,)).fetchone()
            if previous:
                if previous[0] != sha256(raw):
                    raise ValueError('migration_checksum_mismatch')
                continue
            conn.execute(raw.decode('utf-8'))
            conn.execute('INSERT INTO swisstip.schema_migrations VALUES (%s,%s)',
                         (migration.name, sha256(raw)))


def import_release(dsn, raw: bytes, *, classification: str, attachments=None):
    """Validate first, then insert every component atomically; never overwrite."""
    from psycopg.types.json import Jsonb
    if classification not in {'experimental', 'synthetic'}:
        raise ValueError('only_explicit_test_classifications_supported')
    bundle = ReleaseBundle.model_validate_json(raw)
    validate_release(bundle)
    identifier = bundle.release.release_id
    attachments = attachments or {}
    if any(not name or name.startswith('/') or '..' in Path(name).parts for name in attachments):
        raise ValueError('invalid_attachment_name')
    payload = bundle.model_dump(mode='json')
    with connect(dsn) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(20260909)')
        previous = conn.execute('SELECT file_sha256,classification FROM swisstip.releases WHERE release_id=%s',
                                (identifier,)).fetchone()
        created = previous is None
        if previous:
            if previous != (sha256(raw), classification):
                raise ValueError('release_id_already_has_different_content_or_classification')
        else:
            conn.execute('INSERT INTO swisstip.releases '
                         '(release_id,file_sha256,canonical_sha256,original_bytes,payload,classification) '
                         'VALUES (%s,%s,%s,%s,%s,%s)',
                         (identifier, sha256(raw), sha256(bundle.model_dump_json().encode()), raw,
                          Jsonb(payload), classification))
            collections = {'release': [bundle.release], 'catalog': [bundle.catalog],
                           'language_policy': [bundle.language_policy], 'graph': [bundle.graph],
                           'document': bundle.documents, 'projection': bundle.projections,
                           'fact': bundle.facts, 'rule': bundle.rules,
                           'context_schema': bundle.catalog.context_schemas,
                           'terminology': bundle.terminology, 'equivalence': bundle.equivalences,
                           'retrieval_index': [bundle.retrieval_index] if bundle.retrieval_index else [],
                           'retrieval_providers': [bundle.retrieval_providers] if bundle.retrieval_providers else [],
                           'retrieval_configuration': [bundle.retrieval_configuration] if bundle.retrieval_configuration else []}
            for kind, artifacts in collections.items():
                for artifact in artifacts:
                    conn.execute('INSERT INTO swisstip.artifacts VALUES (%s,%s,%s,%s)',
                                 (identifier, kind, artifact.identity.artifact_id,
                                  Jsonb(artifact.model_dump(mode='json'))))
            for entry in bundle.catalog.entries:
                conn.execute('INSERT INTO swisstip.artifacts VALUES (%s,%s,%s,%s)',
                             (identifier, 'catalog_entry', entry.entry_id, Jsonb(entry.model_dump(mode='json'))))
            for evidence in bundle.evidence:
                conn.execute('INSERT INTO swisstip.evidence VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                             (identifier, evidence.evidence_id, evidence.identity.sha256,
                              evidence.citation.source_id, evidence.effective_source_language,
                              evidence.original_excerpt, evidence.citation.url,
                              Jsonb(evidence.model_dump(mode='json'))))
            evidence_ids = {e.identity: e.evidence_id for e in bundle.evidence}
            if bundle.retrieval_index:
                index = bundle.retrieval_index
                for vector in index.vectors:
                    # Validate before PostgreSQL narrows to float32. The original
                    # float values remain in original_bytes and the sealed index.
                    _unit(vector.values, index.dimensions)
                    conn.execute('INSERT INTO swisstip.embeddings VALUES (%s,%s,%s,%s,%s,%s,%s::vector)',
                                 (identifier, evidence_ids[vector.evidence_ref], vector.evidence_ref.sha256,
                                  index.identity.sha256, bundle.retrieval_providers.embedding_model,
                                  index.dimensions, json.dumps(vector.values, allow_nan=False)))
        for name, data in attachments.items():
            existing = conn.execute('SELECT file_sha256 FROM swisstip.attachments WHERE release_id=%s AND path=%s',
                                    (identifier, name)).fetchone()
            if existing and existing[0] != sha256(data):
                raise ValueError('attachment_content_conflict')
            if not existing:
                conn.execute('INSERT INTO swisstip.attachments VALUES (%s,%s,%s,%s)',
                             (identifier, name, sha256(data), data))
    return dict(release_id=identifier, created=created, file_sha256=sha256(raw),
                classification=classification, evidence_count=len(bundle.evidence),
                vector_count=len(bundle.retrieval_index.vectors) if bundle.retrieval_index else 0,
                attachment_count=len(attachments))


class PostgresReleaseStore:
    """Explicitly pinned store. No active-release substitution or model calls."""

    def __init__(self, dsn: str, *, active_release_id: str):
        self.dsn = dsn
        self._active_release_id = active_release_id
        self.vector_queries = 0
        if self.get(active_release_id) is None:
            raise ValueError('active_release_unavailable')

    @property
    def active_release_id(self):
        return self._active_release_id

    def export_bytes(self, identifier):
        with connect(self.dsn) as conn:
            row = conn.execute('SELECT original_bytes,file_sha256 FROM swisstip.releases WHERE release_id=%s',
                               (identifier,)).fetchone()
        if row is None:
            return None
        raw = bytes(row[0])
        if sha256(raw) != row[1]:
            raise ValueError('stored_release_file_hash_mismatch')
        return raw

    def get(self, identifier):
        raw = self.export_bytes(identifier)
        if raw is None:
            return None
        bundle = ReleaseBundle.model_validate_json(raw)
        validate_release(bundle)
        if bundle.release.release_id != identifier:
            raise ValueError('stored_release_identity_mismatch')
        return bundle

    def activate(self, *, slot='pilot'):
        # Operational selection only, not a knowledge approval transition.
        with connect(self.dsn) as conn:
            conn.execute('INSERT INTO swisstip.active_release VALUES (%s,%s) '
                         'ON CONFLICT (slot) DO UPDATE SET release_id=EXCLUDED.release_id',
                         (slot, self.active_release_id))

    def score_vectors(self, bundle, eligible_ids, query_vectors):
        """Exact cosine over the runtime's already scoped IDs and pinned index."""
        ids = set(eligible_ids)
        index = bundle.retrieval_index
        expected = {e.evidence_id: e.identity.sha256 for e in bundle.evidence if e.evidence_id in ids}
        if ids != set(expected):
            raise RetrievalFailure('unknown_eligible_evidence')
        if not ids:
            return {}
        scores = {}
        with connect(self.dsn) as conn:
            for query in query_vectors:
                unit = _unit(query, index.dimensions)
                rows = conn.execute(
                    'SELECT evidence_id,evidence_sha256,1-(embedding <=> %s::vector) '
                    'FROM swisstip.embeddings WHERE release_id=%s AND evidence_id=ANY(%s) '
                    'AND model=%s AND dimensions=%s AND index_sha256=%s',
                    (json.dumps(unit, allow_nan=False), bundle.release.release_id, sorted(ids),
                     bundle.retrieval_providers.embedding_model, index.dimensions, index.identity.sha256)).fetchall()
                self.vector_queries += 1
                if {r[0] for r in rows} != ids:
                    raise RetrievalFailure('database_index_membership_mismatch')
                for identifier, evidence_hash, score in rows:
                    if evidence_hash != expected[identifier] or score is None or not math.isfinite(score):
                        raise RetrievalFailure('database_vector_result_invalid')
                    scores[identifier] = max(scores.get(identifier, -math.inf), score)
        return scores


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dsn-env', default='SWISSTIP_DATABASE_URL')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('migrate')
    load = commands.add_parser('import')
    load.add_argument('--release', type=Path, required=True)
    load.add_argument('--classification', choices=['experimental', 'synthetic'], required=True)
    export = commands.add_parser('export')
    export.add_argument('--release-id', required=True)
    export.add_argument('--output', type=Path, required=True)
    activate = commands.add_parser('activate')
    activate.add_argument('--release-id', required=True)
    activate.add_argument('--slot', default='pilot')
    args = parser.parse_args(argv)
    dsn = os.environ.get(args.dsn_env, '').strip()
    if not dsn:
        parser.error('Database URL environment variable is missing')
    try:
        if args.command == 'migrate':
            migrate(dsn)
            result = dict(migrations='applied')
        elif args.command == 'import':
            result = import_release(dsn, args.release.read_bytes(), classification=args.classification)
        else:
            store = PostgresReleaseStore(dsn, active_release_id=args.release_id)
            if args.command == 'activate':
                store.activate(slot=args.slot)
                result = dict(active_release_id=args.release_id, slot=args.slot, publication_approval=False)
            else:
                with args.output.open('xb') as output:
                    output.write(store.export_bytes(args.release_id))
                result = dict(exported=str(args.output))
    except Exception as error:
        # Database driver errors can include connection details. Do not echo DSNs.
        parser.exit(1, f'Database operation failed ({type(error).__name__}).\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
