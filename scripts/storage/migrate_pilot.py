"""Import frozen SEM/Zurich corpora and pilot evidence into the local database.

Reads local artifacts only; never calls a model or changes publication status.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from swisstip.runtime.postgres import import_release, migrate, sha256, PostgresReleaseStore
from swisstip.runtime.release import ReleaseBundle

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / '.local/live-retrieval-20260907-161418'
SEM = 'sem-answer-relevance-20260908-182238-130324'
ZH = 'zh-runtime-harness-20260908-190309-949650'
PACKET = 'zh-ranking-packet-20260908-183716-424632'
RELEASE_HASHES = {
    SEM: 'c5b8ece8a347ad75cf06f27f37045a0c7a71dbee5ab745c3226750f23e242046',
    ZH: 'e822e48737c661cf87ddd2a910c4ad79b5a52addd3e9f2b1c4b3bcc0af40ac6c',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_replay(pilot):
    """Freeze recorded provider inputs/outputs for database parity, not new eval."""
    audit = read(pilot / ZH / 'runtime-checkpoint-audit.json')
    packet_path = pilot / PACKET / 'packet.json'
    assert sha256(packet_path.read_bytes()) == '87e4a0b11a0eb503ba377b71ba78a9d2cfd363b78a99808ada0984912eddb209'
    packet = read(packet_path)
    vector_path = pilot / PACKET / 'embeddings-20260908-185929-413480/embeddings.json'
    assert sha256(vector_path.read_bytes()) == '03dc9aefda06cf9b550185fdcda32bcdcda4457ba8f3f73b1e50a7c6610a1c54'
    saved = read(vector_path)
    query_vectors = dict(zip(saved['query_ids'], saved['vectors'][len(saved['document_ids']):], strict=True))
    cases = {c['case_id']: c for c in read(pilot / ZH / 'cases.json')['cases']}
    cases.update({c['case_id']: c for c in read(pilot / ZH / 'remaining-runtime-cases-v2.json')})
    output = []
    for check in audit['checks']:
        identifier = check['case_id']
        folder = pilot / ZH / check['run']
        assert sha256((folder / 'summary.json').read_bytes()) == check['summary_sha256']
        if check['provider_observations_sha256']:
            source = folder / (identifier + '-providers.json')
            assert sha256(source.read_bytes()) == check['provider_observations_sha256']
            scores = next(o['scores'] for o in read(source) if o['kind'] == 'ranking')
            score_origin = 'recorded runtime ranking'
        else:
            source = pilot / PACKET / 'ranking-20260908-185439-703627/summary.json'
            previous = read(source)
            assert previous['packet_sha256'] == sha256(packet_path.read_bytes())
            scores = next(c['ranking_scores'] for c in previous['checks'] if c['case_id'] == identifier)
            score_origin = 'recorded ranking-only partial-answer control; not an MCP provider transcript'
        vector_id = 'de-notification' if identifier == 'de-notification-short' else identifier
        output.append(dict(**cases[identifier], query_vector=query_vectors[vector_id],
                           query_vector_case=vector_id, ranking_scores=scores, ranking_origin=score_origin,
                           ranking_source_sha256=sha256(source.read_bytes())))
    assert len(output) == 10
    return dict(mode='RECORDED PROVIDER REPLAY FOR DATABASE PARITY', model_calls=0,
                limitations=['Notification vector predates the shortened runtime query.',
                             'Partial-answer ranking is replayed from the earlier ranking-only check.',
                             'These controls verify database parity, not fresh semantic quality.'],
                cases=output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, default=PILOT)
    parser.add_argument('--dsn-file', type=Path, help='Ignored local file; alternatively SWISSTIP_DATABASE_URL')
    args = parser.parse_args()
    dsn = args.dsn_file.read_text().strip() if args.dsn_file else os.environ.get('SWISSTIP_DATABASE_URL', '').strip()
    if not dsn:
        parser.error('Database URL is required')
    # Collect and verify all frozen input before starting imports.
    archive = {}
    raw_hashes = set()
    for path in sorted((args.pilot / 'crawl').rglob('*')):
        if path.is_file() and path.suffix in {'.html', '.json'}:
            raw = path.read_bytes()
            archive[path.relative_to(args.pilot).as_posix()] = raw
            if path.suffix == '.html':
                raw_hashes.add(sha256(raw))
    for manifest in (args.pilot / 'crawl').glob('*/manifest.json'):
        for snapshot in read(manifest)['snapshots']:
            assert snapshot['sha256'] in raw_hashes, 'Missing or changed raw crawl snapshot'
    for folder in [args.pilot / SEM, args.pilot / ZH, args.pilot / PACKET]:
        for path in sorted(folder.rglob('*')):
            if path.is_file() and path.suffix in {'.json', '.txt', '.md', '.log'}:
                archive[path.relative_to(args.pilot).as_posix()] = path.read_bytes()
    for path in [ROOT / 'docs/pilots/2026-09-08-retrieval-pilot.md',
                 ROOT / 'docs/experiments/2026-09-06-structured-extraction.md']:
        raw = path.read_bytes()
        archive[f'handover/{sha256(raw)}-{path.name}'] = raw
    archive['database-replay.json'] = json.dumps(build_replay(args.pilot), ensure_ascii=True, indent=2).encode()
    inputs = {}
    for name, expected_hash in RELEASE_HASHES.items():
        raw = (args.pilot / name / 'release.json').read_bytes()
        if sha256(raw) != expected_hash:
            raise ValueError('Frozen pilot release hash mismatch')
        inputs[name] = raw
    migrate(dsn)
    results = []
    for name, raw in inputs.items():
        result = import_release(dsn, raw, classification='experimental',
                                attachments=archive if name == ZH else {
                                    k: v for k, v in archive.items() if k.startswith(('crawl/ch-sem-', SEM + '/'))})
        bundle = ReleaseBundle.model_validate_json(raw)
        result['external_snapshot_hashes_without_raw_byte_match'] = sorted(
            {d.snapshot_ref.sha256 for d in bundle.documents} - raw_hashes)
        results.append(result)
    PostgresReleaseStore(dsn, active_release_id=ZH).activate(slot='pilot')
    folder = ROOT / '.local/database'
    folder.mkdir(exist_ok=True)
    output = folder / ('migration-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.json')
    report = dict(mode='LOCAL DATABASE IMPORT', model_calls=0, publication_approval=False,
                  active_slot='pilot', releases=results, archived_raw_html=len(raw_hashes),
                  archive_files=len(archive))
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Saved:', output)


if __name__ == '__main__':
    main()
