"""Real PostgreSQL/pgvector smoke with archived provider replay, zero inference.

All corpus, vectors and replay controls are read from PostgreSQL. Local source
files are not needed. This is storage parity, not fresh semantic evaluation.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from swisstip.runtime.postgres import PostgresReleaseStore, connect, sha256
from swisstip.runtime.release import ReleaseStore
from swisstip.runtime.retrieval import EmbeddingResponse, RankingResponse, _unit
from swisstip.runtime.service import KnowledgeService

ZH = 'zh-runtime-harness-20260908-190309-949650'
SEM = 'sem-answer-relevance-20260908-182238-130324'
ROOT = Path(__file__).resolve().parents[2]


class Replay:
    def __init__(self, bundle, case):
        self.bundle, self.case = bundle, case
        self.embedding_calls = self.ranking_calls = 0

    def embed(self, texts, *, model):
        assert tuple(texts) == tuple(t['text'] for t in self.case['request']['retrieval_terms'])
        assert model == self.bundle.retrieval_providers.embedding_model
        self.embedding_calls += 1
        return EmbeddingResponse(model, (tuple(self.case['query_vector']),))

    def rank(self, query, candidates, *, model):
        assert model == self.bundle.retrieval_providers.ranking_model
        assert {c.evidence_id for c in candidates} == set(self.case['ranking_scores'])
        self.ranking_calls += 1
        return RankingResponse(model, self.case['ranking_scores'])


def service(store, bundle, case, *, database):
    embedder, ranker = Replay(bundle, case), Replay(bundle, case)
    embedder.provider_id = bundle.retrieval_providers.embedding_provider
    ranker.provider_id = bundle.retrieval_providers.ranking_provider
    return KnowledgeService(store, embedding_provider=embedder, ranking_provider=ranker,
                            vector_store=store if database else None,
                            clock=lambda: datetime(2026, 9, 8, 20, tzinfo=timezone.utc))


async def mcp_check(dsn, expected):
    params = StdioServerParameters(command=sys.executable,
        args=['-m', 'swisstip.mcp_server.server', '--database-dsn-env', 'SWISSTIP_DATABASE_URL',
              '--active-release-id', ZH], env={'SWISSTIP_DATABASE_URL': dsn})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            assert tools == {'get_coverage', 'resolve', 'get_evidence'}
            root = await session.call_tool('get_coverage', {})
            assert not root.isError and root.structuredContent['release_id'] == ZH
            fetched = await session.call_tool('get_evidence', dict(release_id=ZH, evidence_ids=['zh-e002']))
            assert not fetched.isError and fetched.structuredContent['evidence'] == [expected]
            missing = await session.call_tool('get_evidence', dict(release_id='absent', evidence_ids=['zh-e002']))
            assert missing.isError and missing.structuredContent['code'] == 'RELEASE_UNAVAILABLE'
    return dict(database_discovery=True, exact_evidence=True, unknown_release_rejected=True,
                live_model_calls=0, note='MCP discovery/evidence only; runtime resolution uses replay below.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dsn-file', type=Path)
    args = parser.parse_args()
    dsn = args.dsn_file.read_text().strip() if args.dsn_file else os.environ['SWISSTIP_DATABASE_URL'].strip()
    store = PostgresReleaseStore(dsn, active_release_id=ZH)
    bundle = store.get(ZH)
    with connect(dsn) as conn:
        attachment = conn.execute('SELECT original_bytes,file_sha256 FROM swisstip.attachments '
                                  'WHERE release_id=%s AND path=%s', (ZH, 'database-replay.json')).fetchone()
        assert sha256(bytes(attachment[0])) == attachment[1]
        replay = json.loads(bytes(attachment[0]))
        counts = {table: conn.execute(f'SELECT count(*) FROM swisstip.{table}').fetchone()[0]
                  for table in ['releases', 'evidence', 'embeddings', 'attachments']}
        version = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]
        assert conn.execute("SELECT release_id FROM swisstip.active_release WHERE slot='pilot'").fetchone()[0] == ZH
        # Every migrated blob is independently hash-verified on the real database.
        blobs = conn.execute('SELECT original_bytes,file_sha256 FROM swisstip.attachments').fetchall()
        assert all(sha256(bytes(raw)) == digest for raw, digest in blobs)
    assert store.get(SEM) is not None and store.get('absent') is None
    for identifier, digest in [(ZH, 'e822e48737c661cf87ddd2a910c4ad79b5a52addd3e9f2b1c4b3bcc0af40ac6c'),
                               (SEM, 'c5b8ece8a347ad75cf06f27f37045a0c7a71dbee5ab745c3226750f23e242046')]:
        assert sha256(store.export_bytes(identifier)) == digest
    file_store = ReleaseStore([bundle], active_release_id=ZH)
    evidence = {e.evidence_id: e.model_dump(mode='json') for e in bundle.evidence}
    checks = []
    max_error = 0
    for case in replay['cases']:
        print('Database replay:', case['case_id'], flush=True)
        database_service = service(store, bundle, case, database=True)
        actual = database_service.resolve(case['request']).model_dump(mode='json')
        baseline = service(file_store, bundle, case, database=False).resolve(case['request']).model_dump(mode='json')
        assert actual == baseline, case['case_id']
        expected = [evidence[eid] for eid in case['expected_evidence_ids']]
        assert actual['evidence'] == expected
        assert actual['status'] == 'INSUFFICIENT_VERIFIED_EVIDENCE'
        assert actual['trust']['fact_support'] == ('EXCERPTS_ONLY' if expected else 'NONE')
        assert actual['supported_portions'] == actual['trace']['degradations'] == []
        assert actual['trace']['candidate_count'] == 12
        if expected:
            fetched = database_service.get_evidence(dict(release_id=ZH, evidence_ids=case['expected_evidence_ids']))
            assert fetched.model_dump(mode='json')['evidence'] == expected
        # Also check actual pgvector math against Python for every eligible row.
        vector = _unit(case['query_vector'], bundle.retrieval_index.dimensions)
        scores = store.score_vectors(bundle, tuple(evidence), [vector])
        for item in bundle.retrieval_index.vectors:
            eid = next(e.evidence_id for e in bundle.evidence if e.identity == item.evidence_ref)
            reference = sum(a*b for a,b in zip(_unit(item.values, len(vector)), vector))
            error = abs(scores[eid] - reference)
            assert error < 2e-6, (eid, error)
            max_error = max(max_error, error)
        checks.append(dict(case_id=case['case_id'], passed=True, evidence_ids=case['expected_evidence_ids']))
    # Query isolation independent of ranking: excluded IDs cannot appear.
    vector = replay['cases'][0]['query_vector']
    assert set(store.score_vectors(bundle, ['zh-e012'], [vector])) == {'zh-e012'}
    assert store.score_vectors(bundle, [], [vector]) == {}
    mcp = asyncio.run(asyncio.wait_for(mcp_check(dsn, evidence['zh-e002']), timeout=60))
    report = dict(mode='REAL DATABASE + RECORDED PROVIDER REPLAY', passed=True, model_calls=0,
                  pgvector_version=version, database_counts=counts, release_export_hashes_match=True,
                  attachment_hashes_verified=len(blobs), cases=checks, pgvector_queries=store.vector_queries,
                  max_cosine_error=max_error, mcp=mcp, governed_release=False,
                  replay_limitations=replay['limitations'])
    folder = ROOT / '.local/database'
    folder.mkdir(exist_ok=True)
    output = folder / ('smoke-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Saved:', output)


if __name__ == '__main__':
    main()
