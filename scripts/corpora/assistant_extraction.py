"""Run the app's V3 concept extraction with assistant-authored completions.

The knowledge-builder CLI (``swisstip.builder.concept_cli``) runs unchanged. Its
provider is replaced by a file exchange: every model request the app would send
(its own system prompt, chunk sections, evidence spans and response schema) is
written to ``requests/<key>.json``; the assistant reads it and writes the
completion to ``responses/<key>.json``; on the next run the app receives that
completion, validates it, attaches exact quotations, runs its review step and
writes its ordinary ``swisstip.concept-proposal-batch/v1`` result. No DeepSeek,
Hugging Face, Groq or Ollama provider is created and no network call is made.
Completions are labelled with the assistant's own identity.

Subcommands: ``stage`` (copy recovered HTML pages with manifests and plan
batches), ``run`` (execute batches; ``--on-missing capture`` writes request files
and returns placeholders, ``--on-missing fail`` stops a batch whose completion
is missing), ``check`` (validate authored responses against their requests),
``status`` (counts).
"""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit

from audit_source_languages import OUT as RAW, ROOT, sha, write

PROVIDER = 'anthropic-assistant'
MODEL = 'claude-fable-5-1'
PROFILE = 'assistant_claude'
DEFAULT_WORKDIR = ROOT / '.local/extraction/assistant-v3-2026-09-11'
EXCLUDE = re.compile(r'/print/html|weiterempfehlen|redirectEmailLink|govisShortLink|sharer\.php|/route/cms-index', re.I)


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def ensure_config(workdir):
    """Write a semantic-model configuration whose active profile is the assistant identity."""
    catalog = (ROOT / 'config/model-profiles.toml').read_text(encoding='utf-8')
    if f'[profiles.{PROFILE}]' not in catalog:
        catalog += (f'\n[profiles.{PROFILE}]\n# Assistant-authored completions through an injected provider; never contacted.\n'
                    f'adapter = "huggingface"\nmodel = "{MODEL}"\nbase_url = "https://assistant.invalid/v1"\n'
                    f'provider = "{PROVIDER}"\ntoken_env = "HF_TOKEN"\n')
    semantic = (ROOT / 'config/semantic-models.toml').read_text(encoding='utf-8')
    semantic = re.sub(r'active_profile = "[^"]+"', f'active_profile = "{PROFILE}"', semantic, count=1)
    if f'[profiles.{PROFILE}]' not in semantic:
        semantic += f'\n[profiles.{PROFILE}]\nmodel_profile = "{PROFILE}"\ntimeout_seconds = 60.0\n'
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / 'model-profiles.toml').write_text(catalog, encoding='utf-8', newline='\n')
    (workdir / 'semantic-models.toml').write_text(semantic, encoding='utf-8', newline='\n')
    return workdir / 'semantic-models.toml'


def load_app(config_path):
    from swisstip.builder.model_profiles import load_model_profiles
    from swisstip.ingestion.prompt_templates import load_prompts
    from swisstip.ingestion.concepts import CandidateConceptExtractor
    config = load_model_profiles(config_path)
    extraction = config.extraction
    prompts = load_prompts(extraction.prompt_profile, extraction_prompt_file=extraction.extraction_prompt_file,
                           review_prompt_file=extraction.review_prompt_file)
    extractor = CandidateConceptExtractor(None, active_profile=config.active_profile.name,
                                          prompt_profile=extraction.prompt_profile, prompts=prompts,
                                          chunk_content_characters=extraction.chunk_content_characters,
                                          chunk_overlap_characters=extraction.chunk_overlap_characters,
                                          max_concepts_per_chunk=extraction.max_concepts_per_chunk,
                                          max_model_requests_per_page=extraction.max_model_requests_per_page,
                                          max_repair_attempts=extraction.max_repair_attempts,
                                          max_review_input_characters=extraction.max_review_input_characters,
                                          max_repair_input_characters=extraction.max_repair_input_characters)
    return config, prompts, extractor


def recovered_html(retrieved_after):
    for pointer in sorted(RAW.glob('pages/*/latest.json')):
        manifest = json.loads(pointer.read_text(encoding='utf-8'))
        if manifest.get('status') != 'saved':
            continue
        for snapshot in manifest.get('snapshots', []):
            if (snapshot['relative_path'].endswith('.html') and snapshot['bytes_downloaded'] > 0
                    and snapshot['retrieved_at'] >= retrieved_after and not snapshot.get('review_flags')):
                yield pointer.parent.name, manifest, snapshot


def stage(args):
    from swisstip.ingestion.source_snapshots import normalize_source_snapshot
    from swisstip.ingestion.concepts import PageNormalizationError
    workdir = args.workdir.resolve()
    config_path = ensure_config(workdir)
    config, prompts, extractor = load_app(config_path)
    limits = config.extraction
    inputs = workdir / 'inputs'
    staged, skipped, seen = [], [], {}
    for url_id, manifest, snapshot in recovered_html(args.retrieved_after):
        url = manifest['url']
        if args.only_host and urlsplit(url).hostname not in args.only_host:
            continue
        if EXCLUDE.search(url):
            skipped.append(dict(url=url, reason='excluded-url-pattern'))
            continue
        relative = Path(snapshot['relative_path'])
        target = inputs / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source = RAW / relative
        raw = source.read_bytes()
        if sha(raw) != snapshot['sha256']:
            raise ValueError('Raw snapshot hash mismatch: ' + url)
        target.write_bytes(raw)
        write(inputs / 'pages' / url_id / 'manifest.json',
              manifest | dict(corpus_id=RAW.name, corpus_path=snapshot['relative_path']))
        try:
            page = normalize_source_snapshot(target, preserve_structure=True)
        except PageNormalizationError as exc:
            skipped.append(dict(url=url, reason='normalization-failed', detail=str(exc)[:200]))
            continue
        characters = sum(len(s.evidence_text) for s in page.sections)
        if characters < args.min_characters:
            skipped.append(dict(url=url, reason='too-little-text', characters=characters))
            continue
        if re.fullmatch(r'.*(404|not found|nicht gefunden|introuvable).*', page.title or '', re.I):
            skipped.append(dict(url=url, reason='error-title', title=page.title))
            continue
        if page.content_hash in seen:
            skipped.append(dict(url=url, reason='duplicate-normalized-content', duplicate_of=seen[page.content_hash]))
            continue
        seen[page.content_hash] = url
        requests = extractor.planned_request_count(page)
        staged.append(dict(url=url, url_id=url_id, path=str(target), input_hash=page.content_hash,
                           title=page.title, language=page.language, sections=len(page.sections),
                           characters=characters, planned_requests=requests, retrieved_at=snapshot['retrieved_at'],
                           jurisdiction=urlsplit(url).hostname))
    staged.sort(key=lambda s: s['url'])
    batches, batch, chars, reqs = [], [], 0, 0
    for item in staged:
        if batch and (len(batch) >= limits.max_pages_per_run or chars + item['characters'] > limits.max_total_input_characters
                      or reqs + item['planned_requests'] > limits.max_model_requests_per_run):
            batches.append(batch); batch, chars, reqs = [], 0, 0
        batch.append(item['url']); chars += item['characters']; reqs += item['planned_requests']
    if batch:
        batches.append(batch)
    plan = dict(schema_version='swisstip.assistant-extraction-staging/v1', staged_at=now(), workdir=str(workdir),
                config=str(config_path), prompt_profile=limits.prompt_profile,
                extraction_prompt_sha256=prompts.to_dict()['extraction']['sha256'],
                review_prompt_sha256=prompts.to_dict()['review']['sha256'],
                retrieved_after=args.retrieved_after, provider=PROVIDER, model=MODEL,
                pages=staged, skipped=skipped,
                batches=[dict(batch_id=f'batch-{n:03d}', urls=urls) for n, urls in enumerate(batches, 1)],
                totals=dict(staged=len(staged), skipped=len(skipped), characters=sum(s['characters'] for s in staged),
                            planned_requests=sum(s['planned_requests'] for s in staged), batches=len(batches)))
    write(workdir / 'staging.json', plan)
    print(json.dumps(plan['totals'] | dict(skipped_reasons={r: sum(1 for s in skipped if s['reason'] == r)
                                                             for r in sorted({s['reason'] for s in skipped})}), indent=2))
    return plan


class ExchangeProvider:
    """Serve assistant-authored completions from files; capture or refuse missing ones."""

    def __init__(self, workdir, on_missing):
        from swisstip.ingestion.concepts import ModelCompletion, SemanticModelError
        self.workdir, self.on_missing = workdir, on_missing
        self.ModelCompletion, self.SemanticModelError = ModelCompletion, SemanticModelError
        (workdir / 'requests').mkdir(parents=True, exist_ok=True)
        (workdir / 'responses').mkdir(parents=True, exist_ok=True)
        self.served, self.missing = [], []

    def generate_structured(self, *, system_prompt, user_prompt, response_schema):
        key = sha(json.dumps(dict(system_prompt=system_prompt, user_prompt=user_prompt, response_schema=response_schema),
                             sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        payload = json.loads(user_prompt)
        kind = 'review' if 'untrusted_review' in payload else 'extraction'
        response_path = self.workdir / 'responses' / f'{key}.json'
        if response_path.exists():
            content = json.loads(response_path.read_text(encoding='utf-8'))['content']
            if not isinstance(content, str) or not content.strip():
                raise self.SemanticModelError(f'assistant response {key[:16]} has no content')
            self.served.append(dict(key=key, kind=kind))
            return self.ModelCompletion(content=content, provider=PROVIDER, model=MODEL,
                                        requested_model=f'{MODEL}:{PROVIDER}', observed_model=MODEL,
                                        request_id='assistant-' + key[:16])
        request_path = self.workdir / 'requests' / f'{key}.json'
        if not request_path.exists():
            page = payload.get('untrusted_page') or payload.get('untrusted_review', {})
            write(request_path, dict(schema_version='swisstip.assistant-extraction-request/v1', key=key, kind=kind,
                                     document_id=page.get('document_id'), title=page.get('title'),
                                     chunk_index=page.get('chunk_index'), chunk_count=page.get('chunk_count'),
                                     proposal_count=len(page.get('proposals', [])) if kind == 'review' else None,
                                     captured_at=now(), system_prompt=system_prompt, user_prompt=user_prompt,
                                     response_schema=response_schema))
        self.missing.append(dict(key=key, kind=kind))
        if self.on_missing == 'fail':
            raise self.SemanticModelError(f'assistant completion missing for {kind} request {key[:16]}')
        if kind == 'review':
            count = len(payload['untrusted_review']['proposals'])
            content = json.dumps(dict(verdicts=[dict(review_id=i, decision='uncertain', issue='insufficient_context',
                                                     reason='Placeholder until the assistant review is authored.')
                                                for i in range(1, count + 1)]))
        else:
            content = json.dumps(dict(concepts=[]))
        return self.ModelCompletion(content=content, provider=PROVIDER, model=MODEL,
                                    requested_model=f'{MODEL}:{PROVIDER}', observed_model=MODEL,
                                    request_id='placeholder-' + key[:16])


def run(args):
    from swisstip.builder import concept_cli
    workdir = args.workdir.resolve()
    plan = json.loads((workdir / 'staging.json').read_text(encoding='utf-8'))
    pages = {p['url']: p for p in plan['pages']}
    config_path = ensure_config(workdir)
    selected = [b for b in plan['batches'] if not args.batch or b['batch_id'] in args.batch]
    summary = []
    for batch in selected:
        run_dir = workdir / 'runs' / batch['batch_id']
        run_dir.mkdir(parents=True, exist_ok=True)
        if args.on_missing == 'fail' and (run_dir / 'result.json').exists() and not args.force:
            summary.append(dict(batch_id=batch['batch_id'], status='already-complete'))
            continue
        provider = ExchangeProvider(workdir, args.on_missing)
        argv = [pages[url]['path'] for url in batch['urls']] + ['--config', str(config_path), '--verbose']
        stdout, stderr = io.StringIO(), io.StringIO()
        started = now()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = concept_cli.main(argv, provider_factory=lambda config: provider)
        (run_dir / f'progress-{args.on_missing}.log').write_text(stderr.getvalue(), encoding='utf-8', newline='\n')
        complete = code == 0 and not provider.missing
        if code == 0 and args.on_missing == 'fail':
            (run_dir / 'result.json').write_text(stdout.getvalue(), encoding='utf-8', newline='\n')
        manifest = dict(schema_version='swisstip.assistant-extraction-run/v1', batch_id=batch['batch_id'],
                        on_missing=args.on_missing, started_at=started, finished_at=now(), exit_code=code,
                        complete=complete, pages=batch['urls'], served=provider.served, missing=provider.missing,
                        provider=PROVIDER, model=MODEL, network_calls=0, model_provider_created=False,
                        note='The app CLI ran unchanged with an injected file-exchange provider; '
                             'execution.network_attempts in result.json counts provider calls served from files.')
        write(run_dir / f'manifest-{args.on_missing}.json', manifest)
        summary.append(dict(batch_id=batch['batch_id'], exit_code=code, complete=complete,
                            served=len(provider.served), missing=len(provider.missing),
                            missing_kinds={k: sum(1 for m in provider.missing if m['kind'] == k) for k in ('extraction', 'review')}))
        print(json.dumps(summary[-1]), flush=True)
    write(workdir / f'run-summary-{args.on_missing}.json', dict(finished_at=now(), batches=summary))
    print(json.dumps(dict(batches=len(summary), complete=sum(1 for s in summary if s.get('complete')),
                          missing=sum(s.get('missing', 0) for s in summary)), indent=2))
    return 0 if all(s.get('complete') or s.get('status') == 'already-complete' for s in summary) else 1


def check_extraction(request, content, max_concepts):
    issues = []
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        return [f'invalid JSON: {exc}']
    if not isinstance(payload, dict) or set(payload) != {'concepts'} or not isinstance(payload['concepts'], list):
        return ['response must be an object with only a concepts array']
    schema = request['response_schema']['properties']['concepts']['items']['properties']
    evidence_ids = set(schema['evidence']['items']['properties']['evidence_id']['enum'])
    sections = set(schema['primary_section_id']['enum'])
    if len(payload['concepts']) > max_concepts:
        issues.append(f'more than {max_concepts} concepts')
    required = {'preferred_label', 'alternative_labels', 'concept_type', 'granularity', 'description', 'scope',
                'user_questions', 'confidence', 'evidence', 'relations', 'primary_section_id'}
    for index, concept in enumerate(payload['concepts'], 1):
        prefix = f'concept {index}: '
        if not isinstance(concept, dict) or set(concept) != required:
            issues.append(prefix + 'keys must be exactly ' + ', '.join(sorted(required)))
            continue
        for name, maximum in (('preferred_label', 200), ('description', 1200), ('scope', 500)):
            value = concept[name]
            if not isinstance(value, str) or not ' '.join(value.split()) or len(' '.join(value.split())) > maximum:
                issues.append(prefix + f'{name} must be a non-empty string of at most {maximum} characters')
        if concept['concept_type'] not in ('ENTITY', 'PROCESS', 'RULE', 'SERVICE', 'DOCUMENT', 'OTHER'):
            issues.append(prefix + 'invalid concept_type')
        if concept['granularity'] not in ('DOMAIN', 'TOPIC', 'ANSWERABLE', 'DETAIL'):
            issues.append(prefix + 'invalid granularity')
        questions = concept['user_questions']
        if not isinstance(questions, list) or not 1 <= len(questions) <= 5 or any(
                not isinstance(q, str) or not q.strip() or len(q) > 300 for q in questions):
            issues.append(prefix + 'user_questions must contain 1-5 strings of at most 300 characters')
        labels = concept['alternative_labels']
        if not isinstance(labels, list) or len(labels) > 10 or any(not isinstance(l, str) or not l.strip() or len(l) > 200 for l in labels):
            issues.append(prefix + 'alternative_labels must contain at most 10 non-empty strings')
        confidence = concept['confidence']
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            issues.append(prefix + 'confidence must be a number between 0 and 1')
        if isinstance(concept['scope'], str) and re.search(r'section-\d+|^page$', concept['scope'].strip(), re.I):
            issues.append(prefix + 'scope must describe applicability, not a section or page')
        evidence = concept['evidence']
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 5:
            issues.append(prefix + 'evidence must contain 1-5 items')
            evidence = []
        primary = concept['primary_section_id']
        if primary not in sections:
            issues.append(prefix + 'unknown primary_section_id')
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {'evidence_id'} or item['evidence_id'] not in evidence_ids:
                issues.append(prefix + 'evidence items must select a supplied evidence_id')
            elif item['evidence_id'].rsplit(':', 2)[0] != primary:
                issues.append(prefix + f"evidence {item['evidence_id']} is outside the primary section")
        relations = concept['relations']
        if not isinstance(relations, list) or len(relations) > 10 or any(
                not isinstance(r, dict) or set(r) != {'relation_type', 'target_label', 'confidence'}
                or r['relation_type'] not in ('BROADER', 'NARROWER', 'RELATED', 'SAME_AS') for r in relations):
            issues.append(prefix + 'relations must be at most 10 objects with relation_type, target_label, confidence')
    return issues


def check(args):
    from swisstip.ingestion.concept_review import parse_verdicts
    workdir = args.workdir.resolve()
    config, _, _ = load_app(ensure_config(workdir))
    report, counts = [], dict(extraction=0, review=0, missing=0, invalid=0)
    for request_path in sorted((workdir / 'requests').glob('*.json')):
        request = json.loads(request_path.read_text(encoding='utf-8'))
        response_path = workdir / 'responses' / request_path.name
        if not response_path.exists():
            counts['missing'] += 1
            continue
        try:
            response = json.loads(response_path.read_text(encoding='utf-8'))
            content = response['content']
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False)
                write(response_path, response | dict(content=content))
            if request['kind'] == 'review':
                parse_verdicts(content, request['proposal_count'])
                issues = []
            else:
                issues = check_extraction(request, content, config.extraction.max_concepts_per_chunk)
        except (ValueError, KeyError, TypeError) as exc:
            issues = [f'{type(exc).__name__}: {exc}'[:300]]
        counts[request['kind']] += 1
        if issues:
            counts['invalid'] += 1
            report.append(dict(key=request['key'], kind=request['kind'], document_id=request.get('document_id'), issues=issues))
            if args.quarantine:
                shutil.move(response_path, workdir / 'responses' / (request_path.stem + '.invalid.json.bak'))
    write(workdir / 'check-report.json', dict(checked_at=now(), counts=counts, invalid=report))
    print(json.dumps(dict(counts=counts, invalid=[dict(key=r['key'][:16], issues=r['issues'][:3]) for r in report[:20]]), indent=2))
    return 0 if not report else 1


def status(args):
    workdir = args.workdir.resolve()
    requests = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((workdir / 'requests').glob('*.json'))]
    responses = {p.stem for p in (workdir / 'responses').glob('*.json')}
    by_kind = {}
    for request in requests:
        entry = by_kind.setdefault(request['kind'], dict(requests=0, answered=0))
        entry['requests'] += 1
        entry['answered'] += request['key'] in responses
    results = sorted(p.parent.name for p in (workdir / 'runs').glob('*/result.json'))
    print(json.dumps(dict(by_kind=by_kind, completed_batches=results), indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path, default=DEFAULT_WORKDIR)
    commands = parser.add_subparsers(dest='command', required=True)
    staging = commands.add_parser('stage')
    staging.add_argument('--retrieved-after', default='2026-09-11T11:39:00')
    staging.add_argument('--only-host', action='append', default=[])
    staging.add_argument('--min-characters', type=int, default=300)
    staging.set_defaults(func=stage)
    runner = commands.add_parser('run')
    runner.add_argument('--on-missing', choices=['capture', 'fail'], default='capture')
    runner.add_argument('--batch', action='append', default=[])
    runner.add_argument('--force', action='store_true')
    runner.set_defaults(func=run)
    checker = commands.add_parser('check')
    checker.add_argument('--quarantine', action='store_true', help='move invalid responses aside')
    checker.set_defaults(func=check)
    commands.add_parser('status').set_defaults(func=status)
    args = parser.parse_args(argv)
    result = args.func(args)
    return result if isinstance(result, int) else 0


if __name__ == '__main__':
    raise SystemExit(main())
