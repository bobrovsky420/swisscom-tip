"""Operational persistence; no mutation of serving releases."""
import json
import os
from pathlib import Path
from uuid import uuid4
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from swisstip.runtime.postgres import connect, sha256

ROOT = Path(os.environ.get('SWISSTIP_ROOT', Path(__file__).resolve().parents[5])).resolve()


def database_url():
    value = os.environ.get('SWISSTIP_DATABASE_URL', '').strip()
    return value or (ROOT / '.local/postgres-dsn.txt').read_text().strip()


def rows(query, params=()):
    with connect(database_url()) as conn:
        conn.row_factory = dict_row
        return conn.execute(query, params).fetchall()


def result_hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def jobs(identifier=None):
    query = 'SELECT job_id,kind,status,request,log,result,error,cancel_requested,created_at,started_at,finished_at FROM swisstip.admin_jobs'
    found = rows(query + (' WHERE job_id=%s' if identifier else ' ORDER BY created_at DESC LIMIT 100'),
                 (identifier,) if identifier else ())
    for row in found:
        row['result_sha256'] = result_hash(row['result']) if row['result'] is not None else None
        if identifier is None:
            row['result'] = None
            row['log'] = ''
    return found


def add_asset(source_id, filename, raw, origin):
    if len(raw) > 2_000_000:
        raise ValueError('Page exceeds the 2 MB limit')
    raw.decode('utf-8-sig')
    identifier = uuid4().hex
    with connect(database_url()) as conn:
        row = conn.execute('INSERT INTO swisstip.admin_assets '
                           '(asset_id,source_id,filename,sha256,original_bytes,origin) VALUES (%s,%s,%s,%s,%s,%s) '
                           'ON CONFLICT (source_id,filename,sha256) DO NOTHING RETURNING asset_id',
                           (identifier, source_id, filename, sha256(raw), raw, origin)).fetchone()
        if row:
            return row[0]
        return conn.execute('SELECT asset_id FROM swisstip.admin_assets WHERE source_id=%s AND filename=%s AND sha256=%s',
                            (source_id, filename, sha256(raw))).fetchone()[0]


def save_job(request, config_text):
    identifier = uuid4().hex
    payload = request.model_dump()
    with connect(database_url()) as conn:
        if request.asset_ids:
            payload['corpus_ids'] = [r[0] for r in conn.execute(
                'SELECT DISTINCT corpus_id FROM swisstip.admin_assets WHERE asset_id=ANY(%s) AND corpus_id IS NOT NULL '
                'ORDER BY corpus_id', (request.asset_ids,)).fetchall()]
        conn.execute('INSERT INTO swisstip.admin_jobs (job_id,kind,status,request,config_text) VALUES (%s,%s,%s,%s,%s)',
                     (identifier, request.kind, 'queued', Jsonb(payload), config_text))
    return jobs(identifier)[0]


def materialize_asset(asset, folder):
    """Restore database bytes and the acquisition manifest for the standard extractor."""
    if not asset.get('processing_eligible', True):
        raise ValueError('Archive-only page: ' + asset.get('processing_reason', 'unsupported input'))
    raw = bytes(asset['original_bytes'])
    if sha256(raw) != asset['sha256']:
        raise ValueError('Input snapshot hash mismatch')
    metadata = asset.get('acquisition_metadata')
    target = Path(folder) / asset['asset_id'] if metadata else Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    path = target / (('response' if metadata else asset['asset_id']) + Path(asset['filename']).suffix)
    path.write_bytes(raw)
    if metadata:
        snapshot = {**metadata['snapshots'][0], 'relative_path': path.name}
        manifest = {**metadata, 'snapshots': [snapshot], 'corpus_id': asset.get('corpus_id')}
        (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return path
