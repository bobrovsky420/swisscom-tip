"""Single local worker with a PostgreSQL lock, persisted queue and bounded jobs.

CLI subprocesses perform all network/model work, never an API request handler.
Interrupted jobs are never automatically retried; starting a new job is explicit.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from swisstip.runtime.postgres import connect, sha256
from .store import ROOT, add_asset, database_url, rows, materialize_asset


def stopping():
    path = os.environ.get('SWISSTIP_WORKER_STOP_FILE')
    return bool(path and Path(path).exists())


def clean_log(text):
    values = [database_url()]
    values += [v for k, v in os.environ.items() if any(word in k.upper() for word in ('TOKEN', 'KEY', 'PASSWORD'))]
    for value in values:
        if len(value) > 6:
            text = text.replace(value, '[redacted]')
    return text[-64000:]


def finish(identifier, status, log, result=None, error=None):
    with connect(database_url()) as conn:
        conn.execute('UPDATE swisstip.admin_jobs SET status=%s,log=%s,result=%s,error=%s,finished_at=now() WHERE job_id=%s',
                     (status, clean_log(log), Jsonb(result) if result is not None else None, error, identifier))


def execute(job):
    folder = ROOT / '.local/admin/jobs' / job['job_id']
    folder.mkdir(parents=True, exist_ok=False)
    request = job['request']
    output, log_path = folder / 'result.json', folder / 'progress.log'
    prefix = [sys.executable, '-u', '-m']
    if job['kind'] == 'crawl':
        config = folder / 'catalog.json'
        config.write_text(job['config_text'], encoding='utf-8')
        command = prefix + ['swisstip.builder.source_cli', '--catalog', str(config), '--crawl',
                            '--profile', request['crawl_profile'], '--output', str(folder / 'crawl')]
        for source in request['source_ids']:
            command += ['--source', source]
    else:
        config = folder / 'semantic-models.toml'
        config.write_text(job['config_text'], encoding='utf-8')
        paths = []
        for asset_id in request['asset_ids']:
            asset = rows('SELECT * FROM swisstip.admin_assets WHERE asset_id=%s', (asset_id,))[0]
            path = materialize_asset(asset, folder)
            paths.append(str(path))
        # The frozen config selects the extraction workflow, including older V4 jobs.
        command = prefix + ['swisstip.builder.concept_cli', *paths, '--config', str(config),
                            '--verbose', '--checkpoint-dir', str(folder / 'checkpoints')]
        if job['kind'] == 'plan':
            command += ['--dry-run']
    environment = os.environ.copy()
    environment['PYTHONUTF8'] = '1'
    with output.open('wb') as stdout, log_path.open('wb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        started = time.monotonic()
        stopped = None
        try:
            while process.poll() is None:
                state = rows('SELECT cancel_requested FROM swisstip.admin_jobs WHERE job_id=%s', (job['job_id'],))[0]
                if stopping():
                    stopped = 'interrupted'
                elif state['cancel_requested']:
                    stopped = 'cancelled'
                elif time.monotonic() - started > 3600 or max(output.stat().st_size, log_path.stat().st_size) > 20_000_000:
                    stopped = 'failed'
                if stopped:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    break
                with log_path.open('rb') as reader:
                    reader.seek(max(0, log_path.stat().st_size - 64000))
                    log = clean_log(reader.read().decode('utf-8', errors='replace'))
                with connect(database_url()) as conn:
                    conn.execute('UPDATE swisstip.admin_jobs SET log=%s WHERE job_id=%s', (log, job['job_id']))
                time.sleep(0.5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    log = log_path.read_text(encoding='utf-8', errors='replace')
    if stopped:
        finish(job['job_id'], stopped, log, error='Worker stopped; no automatic retry' if stopped == 'interrupted' else
               'Stopped by operator' if stopped == 'cancelled' else 'Job time/output limit exceeded')
        return
    try:
        result = json.loads(output.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        finish(job['job_id'], 'failed', log, error='Builder produced no valid report. See progress log.')
        return
    if job['kind'] == 'crawl':
        for source in result.get('results', []):
            for snapshot in source['snapshots']:
                path = (folder / 'crawl' / snapshot['relative_path']).resolve()
                if not path.is_relative_to((folder / 'crawl').resolve()):
                    raise ValueError('Invalid crawl output path')
                raw = path.read_bytes()
                if sha256(raw) != snapshot['sha256']:
                    raise ValueError('Crawl snapshot hash mismatch')
                add_asset(snapshot['source_id'], path.name, raw, f"Crawl job {job['job_id']}")
    attention = job['kind'] == 'extract' and (
        not result.get('quality_summary', {}).get('candidate_count') or
        any(r.get('warnings') or r.get('rejected_candidates') for r in result.get('reports', [])))
    status = 'failed' if process.returncode else 'needs_attention' if attention else 'completed'
    finish(job['job_id'], status, log, result,
           f'Builder exited with code {process.returncode}' if process.returncode else None)


def run():
    # Holding this connection prevents two local workers from recovering each
    # other's running jobs. Process death releases the advisory lock in PostgreSQL.
    with connect(database_url()) as lock:
        lock.autocommit = True
        if not lock.execute('SELECT pg_try_advisory_lock(20260910)').fetchone()[0]:
            raise SystemExit('A control worker is already running')
        lock.execute("UPDATE swisstip.admin_jobs SET status='interrupted',finished_at=now(), "
                     "error='Worker stopped before completion; no automatic retry was sent' WHERE status='running'")
        print('Control worker ready', flush=True)
        while not stopping():
            with connect(database_url()) as conn:
                conn.row_factory = dict_row
                job = conn.execute("SELECT * FROM swisstip.admin_jobs WHERE status='queued' AND NOT cancel_requested "
                                   "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
                if job:
                    conn.execute("UPDATE swisstip.admin_jobs SET status='running',started_at=now() WHERE job_id=%s", (job['job_id'],))
            if job:
                try:
                    execute(job)
                except Exception as exc:
                    previous = rows('SELECT log FROM swisstip.admin_jobs WHERE job_id=%s', (job['job_id'],))[0]['log']
                    finish(job['job_id'], 'failed', previous,
                           error=f'Worker failed ({type(exc).__name__}); retained files are in the job folder')
            else:
                time.sleep(1)


if __name__ == '__main__':
    run()
