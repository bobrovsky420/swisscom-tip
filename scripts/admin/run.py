"""Run the loopback API and a separate persisted-queue worker. Ctrl+C stops both."""
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
from swisstip.runtime.postgres import migrate
from swisstip.control.store import database_url

ROOT = Path(__file__).resolve().parents[2]


def main():
    if not (ROOT / 'apps/admin-console/dist/index.html').is_file():
        raise SystemExit('Build the frontend first: npm.cmd --prefix apps/admin-console run build')
    migrate(database_url())
    children = []
    stop_file = ROOT / '.local/admin' / ('stop-' + uuid4().hex)
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment['SWISSTIP_WORKER_STOP_FILE'] = str(stop_file)
    try:
        for module in [['swisstip.control.worker'], ['uvicorn', 'swisstip.control.api:app', '--host', '127.0.0.1', '--port', '8000']]:
            children.append(subprocess.Popen([sys.executable, '-m', *module], cwd=ROOT, env=environment,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        print('SwissTIP console: http://127.0.0.1:8000 - Ctrl+C to stop', flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_file.touch()
        if children:
            try:
                children[0].wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        stop_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
