"""Create ignored local database credentials; never print or replace existing secrets."""
from pathlib import Path
import secrets


def main():
    root = Path(__file__).resolve().parents[2]
    folder = root / '.local'
    folder.mkdir(exist_ok=True)
    env, dsn = folder / 'postgres.env', folder / 'postgres-dsn.txt'
    if env.exists() or dsn.exists():
        if not (env.is_file() and dsn.is_file()):
            raise SystemExit('Incomplete local database configuration; inspect existing files.')
        print('Existing database configuration retained.')
        return
    password = secrets.token_hex(24)
    with env.open('x', encoding='utf-8') as output:
        output.write(f'POSTGRES_PASSWORD={password}\nSWISSTIP_DB_PORT=55432\n')
    with dsn.open('x', encoding='utf-8') as output:
        output.write(f'postgresql://swisstip:{password}@127.0.0.1:55432/swisstip')
    print('Created .local/postgres.env and .local/postgres-dsn.txt (Git ignored).')


if __name__ == '__main__':
    main()
