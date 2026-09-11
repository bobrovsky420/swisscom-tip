"""Exercise a completed serving collection over a real MCP stdio server.

The script launches the server configured in the collection's ``mcp-client.json``
and records actual ``get_coverage``, ``resolve`` and ``get_evidence`` outcomes,
citations, limits and timings. It reads the prepared ``mcp-requests.json``
fixtures as input only. It does not call the extraction application, an LLM,
an embedding or ranking provider, a database or the network, and it does not
modify the completed release, the fixtures or their ``executed`` flags.

Results are written to a new output directory as ``calls.jsonl`` (every request
and full response), ``summary.json`` (aggregates) and ``README.md``.
"""

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COLLECTION = ROOT / '.local/mvp/residence-all-languages-2026-09-11-v1/collection.json'
TOOLS = {'get_coverage', 'resolve', 'get_evidence'}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True,
                              check=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def percentiles(values):
    if not values:
        return {}
    ordered = sorted(values)

    def at(fraction):
        return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]

    return dict(count=len(ordered), min=round(ordered[0], 3), median=round(statistics.median(ordered), 3),
                p90=round(at(0.9), 3), max=round(ordered[-1], 3), total=round(sum(ordered), 3))


def select_requests(requests, per_jurisdiction, random_sample, seed):
    """Deterministic jurisdiction-balanced picks first, then a seeded random tail."""
    groups = defaultdict(list)
    for index, item in enumerate(requests):
        jurisdiction = item['arguments']['jurisdiction']
        groups[jurisdiction.get('canton_code') or jurisdiction['country_code']].append((index, item))
    chosen, used = [], set()
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda pair: pair[1]['arguments']['concept_ids'])
        for index, item in ordered[:per_jurisdiction]:
            chosen.append(('jurisdiction', key, index, item))
            used.add(index)
    remaining = [(index, item) for index, item in enumerate(requests) if index not in used]
    for index, item in random.Random(seed).sample(remaining, min(random_sample, len(remaining))):
        jurisdiction = item['arguments']['jurisdiction']
        chosen.append(('random', jurisdiction.get('canton_code') or jurisdiction['country_code'], index, item))
    return chosen


class Recorder:
    def __init__(self, session, tools, sink):
        self.session, self.tools, self.sink = session, tools, sink
        self.calls = []

    async def call(self, name, payload, *, phase, label, expect=None):
        started = time.perf_counter()
        response = await self.session.call_tool(name, payload)
        seconds = time.perf_counter() - started
        data = response.structuredContent
        text = response.content[0].text if response.content else None
        record = dict(phase=phase, label=label, tool=name, arguments=payload, seconds=round(seconds, 3),
                      is_error=bool(response.isError), structured=data is not None,
                      text_parity=(json.loads(text) == data) if text and data is not None else None,
                      schema_valid=(Draft202012Validator(self.tools[name].outputSchema).is_valid(data)
                                    if name in self.tools and data is not None else None),
                      expectation=expect, result=data if data is not None else text)
        if data is not None:
            record['outcome'] = data.get('status') or data.get('code')
        record['expectation_met'] = None if expect is None else record.get('outcome') == expect
        self.calls.append(record)
        self.sink.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.sink.flush()
        return data, record


def check_resolution(item, resolved, kind, jurisdiction, index):
    check = dict(fixture_index=index, kind=kind, jurisdiction=jurisdiction,
                 source_url=item['source_url'], fixture_evidence_count=len(item['evidence_ids']))
    if not isinstance(resolved, dict) or 'status' not in resolved:
        check.update(status=None, error=resolved)
        return check, []
    evidence = resolved.get('evidence', [])
    ids = [e['evidence_id'] for e in evidence]
    trace = resolved.get('trace') or {}
    check.update(
        status=resolved['status'], evidence_count=len(ids),
        evidence_within_fixture=set(ids) <= set(item['evidence_ids']),
        citation_urls=sorted({e['citation']['url'] for e in evidence}),
        citations_match_source=all(e['citation']['url'] == item['source_url'] for e in evidence),
        evidence_languages=sorted({e['effective_source_language'] for e in evidence}),
        evidence_schema_versions=sorted({e['schema_version'] for e in evidence}),
        supported_facts=len(resolved.get('supported_portions', [])),
        unresolved_reasons=sorted({u['reason_code'] for u in resolved.get('unresolved_portions', [])}),
        fact_support=resolved.get('trust', {}).get('fact_support'),
        limitations=resolved.get('trust', {}).get('limitations', []),
        freshness=resolved.get('freshness', {}).get('status'),
        channels=trace.get('channels'), candidate_count=trace.get('candidate_count'),
        degradations=[d['reason_code'] for d in trace.get('degradations', [])],
        coverage_profile_ids=resolved.get('coverage_profile_ids'))
    return check, ids


async def discover(call, parts, active):
    """Active release, each part explicitly, one catalog walk and paging limits per part."""
    root, _ = await call('get_coverage', {}, phase='coverage', label='root-active')
    discovery = dict(root_release_id=root.get('release_id'), root_is_active=root.get('release_id') == active,
                     parts={})
    topics = {}
    for part in parts:
        rid = part['release_id']
        info = discovery['parts'][rid] = {}
        spaces, _ = await call('get_coverage', dict(release_id=rid), phase='coverage', label=f'{rid}:spaces')
        info['knowledge_spaces'] = [e['entry_id'] for e in spaces.get('entries', [])]
        info['root_profiles'] = len(spaces.get('coverage_profiles', []))
        for space in info['knowledge_spaces'][:1]:
            domains, _ = await call('get_coverage', dict(release_id=rid, parent_id=space),
                                    phase='coverage', label=f'{rid}:domains')
            info['domains'] = [e['entry_id'] for e in domains.get('entries', [])]
            for domain in info['domains'][:1]:
                topic_page, _ = await call('get_coverage', dict(release_id=rid, parent_id=domain),
                                           phase='coverage', label=f'{rid}:topics')
                info['topics'] = [e['entry_id'] for e in topic_page.get('entries', [])]
                for topic in info['topics'][:1]:
                    topics[rid] = topic
                    page, _ = await call('get_coverage', dict(release_id=rid, parent_id=topic),
                                         phase='coverage', label=f'{rid}:concepts-default')
                    info['concept_page_default'] = dict(
                        entries=len(page.get('entries', [])), profiles=len(page.get('coverage_profiles', [])),
                        context_schemas=len(page.get('context_schemas', [])),
                        has_cursor=bool(page.get('next_cursor')), default_limit=page.get('default_limit'),
                        maximum_limit=page.get('maximum_limit'))
                    if page.get('next_cursor'):
                        cont, _ = await call('get_coverage', dict(release_id=rid, parent_id=topic,
                                                                  cursor=page['next_cursor']),
                                             phase='coverage', label=f'{rid}:concepts-cursor')
                        info['concept_page_cursor'] = dict(entries=len(cont.get('entries', [])),
                                                           has_cursor=bool(cont.get('next_cursor')))
                    big, _ = await call('get_coverage', dict(release_id=rid, parent_id=topic, limit=100),
                                        phase='coverage', label=f'{rid}:concepts-limit-100')
                    info['concept_page_limit_100'] = dict(entries=len(big.get('entries', [])),
                                                          profiles=len(big.get('coverage_profiles', [])))
                    await call('get_coverage', dict(release_id=rid, parent_id=topic, limit=101),
                               phase='negative', label=f'{rid}:limit-101', expect='INVALID_ARGUMENT')
    return discovery, topics


async def negatives(call, parts, fixtures, topics, active):
    first_rid, second_rid = parts[0]['release_id'], parts[-1]['release_id']
    first = fixtures[first_rid]['resolve'][0]
    second = fixtures[second_rid]['resolve'][0]
    await call('get_evidence', dict(release_id='missing-release', evidence_ids=first['evidence_ids'][:1]),
               phase='negative', label='unknown-release', expect='RELEASE_UNAVAILABLE')
    if second_rid != first_rid:
        await call('get_evidence', dict(release_id=first_rid, evidence_ids=second['evidence_ids'][:1]),
                   phase='negative', label='cross-part-evidence', expect='INVALID_ARGUMENT')
        await call('resolve', {**second['arguments'], 'release_id': first_rid},
                   phase='negative', label='cross-part-concept', expect='INVALID_ARGUMENT')
    await call('get_evidence', dict(release_id=first_rid, evidence_ids=(first['evidence_ids'] * 6)[:6]),
               phase='negative', label='six-evidence-ids', expect='INVALID_ARGUMENT')
    await call('get_evidence', dict(release_id=first_rid, evidence_ids=['no-such-evidence']),
               phase='negative', label='unknown-evidence', expect='INVALID_ARGUMENT')
    await call('resolve', {**first['arguments'], 'question': 'free text'},
               phase='negative', label='unknown-field', expect='INVALID_ARGUMENT')
    await call('resolve', {**first['arguments'], 'jurisdiction': json.dumps(first['arguments']['jurisdiction'])},
               phase='negative', label='stringified-object', expect='INVALID_ARGUMENT')
    await call('resolve', {**first['arguments'], 'release_id': 'missing-release'},
               phase='negative', label='resolve-unknown-release', expect='RELEASE_UNAVAILABLE')
    await call('resolve', {**first['arguments'], 'as_of': '2099-12-31'},
               phase='boundary', label='as-of-far-future')
    await call('resolve', {**first['arguments'], 'as_of': '1990-01-01'},
               phase='boundary', label='as-of-far-past')
    await call('resolve', {**first['arguments'], 'source_languages': ['xx']},
               phase='boundary', label='unsupported-source-language')
    await call('resolve', {**first['arguments'], 'max_evidence': 1},
               phase='boundary', label='max-evidence-1')
    await call('resolve', {**first['arguments'], 'scope_mode': 'descendants'},
               phase='boundary', label='scope-descendants')
    await call('resolve', {**first['arguments'], 'concept_ids': []},
               phase='boundary', label='topic-without-concepts')
    await call('resolve', {**first['arguments'],
                           'retrieval_terms': [dict(text='Aufenthaltsbewilligung', language='de')]},
               phase='boundary', label='retrieval-term-de')
    await call('resolve', {**first['arguments'], 'intent': 'requirements'},
               phase='boundary', label='unpublished-intent')
    if second_rid in topics and second_rid != active:
        await call('get_coverage', dict(parent_id=topics[second_rid]),
                   phase='negative', label='inactive-part-parent-without-release', expect='INVALID_ARGUMENT')
    await call('no_such_tool', {}, phase='negative', label='unknown-tool', expect='INVALID_ARGUMENT')


async def run(args):
    collection_path = args.collection.resolve()
    base = collection_path.parent
    collection = json.loads(collection_path.read_text(encoding='utf-8'))
    client_path = args.client.resolve() if args.client else base / 'mcp-client.json'
    client = json.loads(client_path.read_text(encoding='utf-8'))
    (server_name, server), = client['mcpServers'].items()
    active = server['args'][server['args'].index('--active-release-id') + 1]
    parts = collection['parts']
    fixtures = {p['release_id']: json.loads((base / Path(p['release_file']).parent / 'mcp-requests.json')
                                            .read_text(encoding='utf-8')) for p in parts}
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f'Refusing to overwrite existing output directory: {output}')
    output.mkdir(parents=True)
    started_at = datetime.now(timezone.utc)
    release_hashes = {p['release_id']: (None if args.skip_hashes else sha256(base / p['release_file'])) for p in parts}
    identity = dict(
        collection=str(collection_path), client=str(client_path), server_name=server_name,
        command=server['command'], args=server['args'], active_release_id=active,
        git_commit=git('rev-parse', 'HEAD'), git_dirty_paths=len((git('status', '--porcelain') or '').splitlines()),
        python=platform.python_version(), mcp_package=metadata.version('mcp'),
        release_sha256=release_hashes,
        recorded_release_sha256={p['release_id']: p['release_sha256'] for p in parts},
        release_hash_match={p['release_id']: (None if args.skip_hashes else
                                              release_hashes[p['release_id']] == p['release_sha256']) for p in parts},
        fixture_executed_flags={rid: fixtures[rid].get('executed') for rid in fixtures},
        started_at=started_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        extraction_application_calls=0, llm_calls=0, provider_calls=0, database_calls=0, network_calls=0)

    params = StdioServerParameters(command=server['command'], args=server['args'], env=server.get('env'))
    selection = {rid: select_requests(fixtures[rid]['resolve'], args.per_jurisdiction, args.random_sample, args.seed)
                 for rid in fixtures}
    resolution = {rid: dict(selected=len(selection[rid]), executed=0, skipped_for_budget=0) for rid in fixtures}
    interleaved = []
    for position in range(max(len(v) for v in selection.values())):
        for rid in selection:
            if position < len(selection[rid]):
                interleaved.append((rid, *selection[rid][position]))
    budget_exhausted = False
    checks = []
    with (output / 'calls.jsonl').open('w', encoding='utf-8') as sink:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                t0 = time.perf_counter()
                await session.initialize()
                startup_seconds = time.perf_counter() - t0
                listed = await session.list_tools()
                tools = {t.name: t for t in listed.tools}
                for tool in tools.values():
                    Draft202012Validator.check_schema(tool.inputSchema)
                    Draft202012Validator.check_schema(tool.outputSchema)
                recorder = Recorder(session, tools, sink)
                call = recorder.call

                discovery, topics = await discover(call, parts, active)

                budget_started = time.perf_counter()
                for rid, kind, jurisdiction, index, item in interleaved:
                    if time.perf_counter() - budget_started > args.time_budget:
                        budget_exhausted = True
                        resolution[rid]['skipped_for_budget'] += 1
                        continue
                    label = f'{rid}:{kind}:{jurisdiction}:{index}'
                    resolved, _ = await call('resolve', item['arguments'], phase='resolve', label=label)
                    resolution[rid]['executed'] += 1
                    check, ids = check_resolution(item, resolved, kind, jurisdiction, index)
                    check['release_id'] = rid
                    if ids:
                        fetched, _ = await call('get_evidence', dict(release_id=rid, evidence_ids=ids[:5]),
                                                phase='evidence', label=label + ':parity')
                        check['evidence_parity'] = isinstance(fetched, dict) and fetched.get('evidence') == resolved['evidence'][:5]
                    if kind == 'jurisdiction':
                        rest = [e for e in item['evidence_ids'] if e not in ids][:5]
                        if rest:
                            extra, _ = await call('get_evidence', dict(release_id=rid, evidence_ids=rest),
                                                  phase='evidence', label=label + ':remaining-batch')
                            returned = extra.get('evidence', []) if isinstance(extra, dict) else []
                            check['remaining_batch'] = dict(
                                requested=len(rest), returned=len(returned),
                                same_source=bool(returned) and all(e['citation']['url'] == item['source_url']
                                                                   for e in returned))
                    checks.append(check)
                    sink.write(json.dumps(dict(phase='resolve-check', label=label, check=check), ensure_ascii=False) + '\n')
                    sink.flush()

                await negatives(call, parts, fixtures, topics, active)

    finished_at = datetime.now(timezone.utc)
    calls = recorder.calls
    by_tool = defaultdict(list)
    for record in calls:
        by_tool[record['tool']].append(record['seconds'])
    per_part = {}
    for rid in fixtures:
        part_checks = [c for c in checks if c['release_id'] == rid]
        per_part[rid] = dict(
            **resolution[rid], statuses=dict(Counter(c.get('status') for c in part_checks)),
            evidence_counts=dict(Counter(c.get('evidence_count') for c in part_checks)),
            evidence_within_fixture=sum(1 for c in part_checks if c.get('evidence_within_fixture')),
            citations_match_source=sum(1 for c in part_checks if c.get('citations_match_source')),
            evidence_parity=sum(1 for c in part_checks if c.get('evidence_parity')),
            evidence_parity_checked=sum(1 for c in part_checks if 'evidence_parity' in c),
            remaining_batches=sum(1 for c in part_checks if 'remaining_batch' in c),
            remaining_batches_complete=sum(1 for c in part_checks if c.get('remaining_batch', {}).get('same_source')
                                           and c['remaining_batch']['returned'] == c['remaining_batch']['requested']),
            fact_support=dict(Counter(c.get('fact_support') for c in part_checks)),
            channels=dict(Counter(','.join(c.get('channels') or []) for c in part_checks)),
            degradations=dict(Counter(d for c in part_checks for d in c.get('degradations', []))),
            evidence_languages=dict(Counter(l for c in part_checks for l in c.get('evidence_languages', []))),
            jurisdictions=dict(Counter(c['jurisdiction'] for c in part_checks)),
            limitations=dict(Counter(l for c in part_checks for l in c.get('limitations', []))),
            unresolved_reasons=dict(Counter(u for c in part_checks for u in c.get('unresolved_reasons', []))),
            supported_facts=percentiles([c['supported_facts'] for c in part_checks if 'supported_facts' in c]),
            fixture_evidence_counts=percentiles([c['fixture_evidence_count'] for c in part_checks]),
            resolve_seconds=percentiles([r['seconds'] for r in calls if r['tool'] == 'resolve'
                                         and r['label'].startswith(rid + ':')]),
            evidence_seconds=percentiles([r['seconds'] for r in calls if r['tool'] == 'get_evidence'
                                          and r['label'].startswith(rid + ':')]))
    summary = dict(
        schema_version='swisstip.live-mcp-check/v1', identity=identity,
        finished_at=finished_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        wall_clock_seconds=round((finished_at - started_at).total_seconds(), 1),
        server_startup_seconds=round(startup_seconds, 3), tools=sorted(tools), tools_complete=set(tools) == TOOLS,
        tool_schemas_valid=True, calls=len(calls),
        structured_content_present=sum(1 for r in calls if r['structured']),
        text_parity_failures=sum(1 for r in calls if r['text_parity'] is False),
        output_schema_failures=sum(1 for r in calls if r['schema_valid'] is False),
        latency_seconds={tool: percentiles(values) for tool, values in by_tool.items()},
        discovery=discovery, resolution=per_part,
        expectations=dict(checked=sum(1 for r in calls if r['expectation']),
                          met=sum(1 for r in calls if r['expectation_met']),
                          unmet=[dict(label=r['label'], expected=r['expectation'], outcome=r.get('outcome'))
                                 for r in calls if r['expectation'] and not r['expectation_met']]),
        boundary_outcomes={r['label']: dict(
            outcome=r.get('outcome'), is_error=r['is_error'],
            evidence=len(((r['result'] if isinstance(r['result'], dict) else {}).get('evidence') or [])),
            issues=[i.get('reason_code') for i in (r['result'] if isinstance(r['result'], dict) else {}).get('issues', [])],
            missing_context=[m.get('path') for m in (r['result'] if isinstance(r['result'], dict) else {}).get('missing_context', [])],
            unresolved=[u.get('reason_code') for u in (r['result'] if isinstance(r['result'], dict) else {}).get('unresolved_portions', [])],
            channels=(((r['result'] if isinstance(r['result'], dict) else {}).get('trace') or {}).get('channels')))
            for r in calls if r['phase'] == 'boundary'},
        sampling=dict(per_jurisdiction=args.per_jurisdiction, random_sample=args.random_sample, seed=args.seed,
                      time_budget_seconds=args.time_budget, budget_exhausted=budget_exhausted),
        limitations=[
            'Live outcomes for a sample of prepared fixture requests; not every fixture was executed.',
            'Requests use exact document concepts and empty context; no free-text question answering was tested.',
            'No provider, embedding, ranking, database, extraction application or LLM call was made.',
            'Serving success does not establish corpus completeness, semantic review or legal validity.'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'README.md').write_text(render(summary), encoding='utf-8')
    return summary


def render(summary):
    lines = ['# Live MCP check', '',
             f"Started {summary['identity']['started_at']}, finished {summary['finished_at']} "
             f"({summary['wall_clock_seconds']} s wall clock). Commit `{summary['identity']['git_commit']}`.",
             '', 'Real stdio round trips against the configured server. '
             'No application, LLM, provider, database or network call.', '',
             '| Measure | Result |', '| --- | ---: |',
             f"| Server startup (initialize) | {summary['server_startup_seconds']} s |",
             f"| Tool calls recorded | {summary['calls']} |",
             f"| Output schema failures / text parity failures | "
             f"{summary['output_schema_failures']} / {summary['text_parity_failures']} |",
             f"| Expectations met | {summary['expectations']['met']} / {summary['expectations']['checked']} |"]
    for tool, stats in summary['latency_seconds'].items():
        lines.append(f"| `{tool}` latency s (n: min / median / p90 / max) | "
                     f"{stats['count']}: {stats['min']} / {stats['median']} / {stats['p90']} / {stats['max']} |")
    lines += ['', '## Resolution by release part', '']
    for rid, part in summary['resolution'].items():
        lines += [f'### {rid}', '',
                  f"Selected {part['selected']}, executed {part['executed']}, "
                  f"skipped for budget {part['skipped_for_budget']}.",
                  f"Statuses: {part['statuses']}. Evidence counts: {part['evidence_counts']}.",
                  f"Evidence within fixture: {part['evidence_within_fixture']}/{part['executed']}. "
                  f"Citations match source: {part['citations_match_source']}/{part['executed']}. "
                  f"Evidence parity: {part['evidence_parity']}/{part['evidence_parity_checked']}. "
                  f"Remaining batches complete: {part['remaining_batches_complete']}/{part['remaining_batches']}.",
                  f"Fact support: {part['fact_support']}. Channels: {part['channels']}. "
                  f"Degradations: {part['degradations']}.",
                  f"Unresolved reasons: {part['unresolved_reasons']}.",
                  f"Evidence languages: {part['evidence_languages']}.", '']
    lines += ['## Boundary outcomes', '']
    for label, outcome in summary['boundary_outcomes'].items():
        lines.append(f"- `{label}`: {outcome}")
    if summary['expectations']['unmet']:
        lines += ['', '## Unmet expectations', ''] + [f'- {u}' for u in summary['expectations']['unmet']]
    lines += ['', '## Limitations', ''] + [f'- {l}' for l in summary['limitations']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument('--client', type=Path, help='mcp-client.json; default is next to the collection')
    parser.add_argument('--output', type=Path, required=True, help='New results directory; must not exist')
    parser.add_argument('--per-jurisdiction', type=int, default=1)
    parser.add_argument('--random-sample', type=int, default=15)
    parser.add_argument('--seed', type=int, default=20260911)
    parser.add_argument('--time-budget', type=float, default=1800.0, help='Seconds for the resolve/evidence phase')
    parser.add_argument('--skip-hashes', action='store_true')
    args = parser.parse_args(argv)
    summary = asyncio.run(run(args))
    print(json.dumps(dict(calls=summary['calls'], startup=summary['server_startup_seconds'],
                          expectations=summary['expectations'], latency=summary['latency_seconds'],
                          resolution={rid: dict(executed=p['executed'], statuses=p['statuses'])
                                      for rid, p in summary['resolution'].items()}), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
