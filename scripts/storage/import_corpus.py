"""Import a downloaded corpus into PostgreSQL with an immutable run label."""
import argparse
import json
from pathlib import Path
from swisstip.runtime.corpus import prepare_corpus, import_corpus
from swisstip.runtime.postgres import migrate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--corpus-id', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--dsn-file', type=Path, default=Path('.local/postgres-dsn.txt'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.resolve().is_relative_to(args.corpus.resolve()):
        parser.error('Store the import report outside the immutable input corpus')
    corpus = prepare_corpus(args.corpus, args.corpus_id, args.title)
    dsn = args.dsn_file.read_text().strip()
    migrate(dsn)
    result = import_corpus(dsn, corpus)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
