"""Binary-safe backup of the Compose database, optionally restore and smoke it.

The verification database is newly created with a UUID name and removed only
after the restore attempt. The pilot database and Docker volume are not deleted.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from swisstip.runtime.postgres import sha256

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-restore', action='store_true')
    args = parser.parse_args()
    folder = ROOT / '.local/database/backups'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / ('swisstip-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.dump')
    docker = ['docker'] + (['--context', 'desktop-linux'] if sys.platform == 'win32' else [])
    compose = docker + ['compose', '--env-file', str(ROOT / '.local/postgres.env'), 'exec', '-T', 'db']
    with output.open('xb') as archive:
        subprocess.run(compose + ['pg_dump', '-U', 'swisstip', '-d', 'swisstip', '-Fc'],
                       stdout=archive, check=True, cwd=ROOT)
    report = dict(backup=str(output), sha256=sha256(output.read_bytes()), bytes=output.stat().st_size,
                  restore_verified=False)
    if args.verify_restore:
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        dsn = (ROOT / '.local/postgres-dsn.txt').read_text().strip()
        database = 'swisstip_restore_' + uuid4().hex
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        try:
            with output.open('rb') as archive:
                subprocess.run(compose + ['pg_restore', '-U', 'swisstip', '-d', database, '--exit-on-error'],
                               stdin=archive, check=True, cwd=ROOT)
            environment = os.environ.copy()
            environment['SWISSTIP_DATABASE_URL'] = make_conninfo(dsn, dbname=database)
            subprocess.run([sys.executable, str(ROOT / 'scripts/storage/smoke_pilot.py')],
                           env=environment, cwd=ROOT, check=True)
            report['restore_verified'] = True
        finally:
            assert database.startswith('swisstip_restore_') and len(database) == 49
            with psycopg.connect(dsn, autocommit=True) as conn:
                conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
    output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
