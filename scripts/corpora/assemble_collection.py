"""Assemble a multi-part serving collection from existing validated parts.

Copies each named part directory into the collection unchanged, recomputes the
release hash, and writes ``collection.json``, a root ``mcp-client.json`` that
loads every part with the first part active, and a README. Parts already
present with an identical release hash are kept, so the assembler can be run
again to add parts. Nothing inside a part is modified; no application,
provider or database is involved.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from audit_source_languages import ROOT, sha, write


def copy_part(source, target):
    if target.exists():
        existing = sha((target / 'release.json').read_bytes()) if (target / 'release.json').exists() else None
        if existing == sha((source / 'release.json').read_bytes()):
            return 'kept'
        raise ValueError(f'{target} exists with a different release; choose a new collection directory')
    shutil.copytree(source, target)
    return 'copied'


DEFAULT_SCOPE = 'Unchanged v1 source-assertion parts plus parts built only from pages recovered on 2026-09-11.'


def assemble(output, parts, notes, *, title='Residence serving collection v2', scope=DEFAULT_SCOPE, unchanged=''):
    output.mkdir(parents=True, exist_ok=True)
    reports, actions = [], {}
    for name, source in parts:
        source = source.resolve()
        target = output / name
        actions[name] = copy_part(source, target)
        report = json.loads((target / 'validation.json').read_text(encoding='utf-8'))
        release = target / 'release.json'
        digest = sha(release.read_bytes())
        if report.get('release_sha256') not in (None, digest):
            raise ValueError(f'{name}: validation.json hash does not match release.json')
        report = report | dict(release_file=f'{name}/release.json', release_sha256=digest)
        reports.append(report)
        for ledger in ('document-aliases.json', 'unresolved-assertions.json', 'provenance.json'):
            if (target / ledger).exists() and ledger != 'provenance.json':
                shutil.copyfile(target / ledger, output / f'{name}-{ledger}')
    server_args = ['-m', 'swisstip.mcp_server.server']
    for report in reports:
        server_args.extend(['--release', str(output / report['release_file'])])
    server_args.extend(['--active-release-id', reports[0]['release_id']])
    write(output / 'mcp-client.json', {'mcpServers': {'residence-expanded': {
        'command': str(ROOT / '.venv/Scripts/python.exe'), 'args': server_args}}})
    collection = dict(schema_version='swisstip.experimental-release-collection/v1', assembled_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                      parts=reports, part_actions=actions, application_calls=0, llm_calls=0, semantic_review_complete=False,
                      scope=scope,
                      notes=notes,
                      acquisition_completeness='Serving validity does not establish corpus completeness; see the recovery record.')
    write(output / 'collection.json', collection)
    lines = ['# ' + title, '',
             'Every listed part is an app-ingestible `serving-release/v1` release, validated when built. Parts are',
             'loaded explicitly by the root `mcp-client.json`; requests pin one release ID and parts are never',
             'implicitly combined.' + (' ' + unchanged if unchanged else ''), '',
             '| Part | Release ID | Documents | Facts | Evidence | Concepts | Origin |', '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for report in reports:
        origin = notes.get(report['release_file'].split('/')[0], '')
        lines.append(f"| {report['release_file'].split('/')[0]} | `{report['release_id']}` | {report['documents']} | {report['facts']} | "
                     f"{report['evidence']} | {report['concepts']} | {origin} |")
    lines += ['', 'APPROVED and VERIFIED_AUTOMATIC flags enable experimental loading only; no human review, legal review',
              'or eligibility decision is implied. No database import or activation occurred.', '']
    (output / 'README.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    return collection


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--part', action='append', required=True, metavar='NAME=DIR',
                        help='part name inside the collection and the validated part directory to copy')
    parser.add_argument('--note', action='append', default=[], metavar='NAME=TEXT', help='origin note per part')
    parser.add_argument('--title', default='Residence serving collection v2', help='README title')
    parser.add_argument('--scope', default=DEFAULT_SCOPE, help='one-line scope recorded in collection.json')
    parser.add_argument('--unchanged', default='The v1 parts are byte-identical copies with unchanged hashes.',
                        help='README sentence about parts copied from an earlier collection; empty to omit')
    args = parser.parse_args()
    parts = [(p.split('=', 1)[0], Path(p.split('=', 1)[1])) for p in args.part]
    notes = dict(n.split('=', 1) for n in args.note)
    result = assemble(args.output.resolve(), parts, notes, title=args.title, scope=args.scope, unchanged=args.unchanged)
    print(json.dumps(dict(parts=[(r['release_id'], r['release_sha256'][:16], r['documents'], r['facts']) for r in result['parts']],
                          actions=result['part_actions']), indent=2))
