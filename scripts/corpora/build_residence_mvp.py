"""Package assistant-curated claims into an offline experimental serving release.

No application, database, network, extraction provider or model is invoked.
Only the existing data contracts, artifact sealer and release validator are used.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from swisstip.core.contracts import (
    ArtifactRef, ContextSchema, EvidenceObject, GetCoverageRequest,
    GetEvidenceRequest, KnowledgeCatalog, KnowledgeRelease, LanguagePolicy,
    NormalizedEvidenceDocument, PublishedFact, PublishedRule, ResolutionGraph,
    StructuredGroundingRequest,
)
from swisstip.core.identity import seal_artifact
from swisstip.core.validation import validate_request
from swisstip.runtime.release import ReleaseBundle, validate_release

from residence_mvp_curated import CONCEPTS, CONTACT_ROWS, DIRECTORY, SCOPE, SELECTOR_VALUES, claim, concept

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = 'hackathon-residence-semantic-2026-09-12-v6'
# Default snapshot-age limit: a result whose oldest selected citation was saved
# more than this many days before the read time is reported STALE.
FRESHNESS_DAYS = 60
# Validity is unbounded unless the cited source states a commencement or expiry
# date; each concept in residence_mvp_curated.py may declare such a `validity`.
BUILD_DATE = datetime.now(timezone.utc).strftime('%Y-%m-%d')
DISCLAIMER = 'Assistant-curated experimental MVP data; no independent human or legal review.'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def ref(identifier, sha256='a' * 64):
    return ArtifactRef(artifact_id=identifier, version='1', sha256=sha256)


def span(doc, selection):
    blocks = doc['blocks'][selection['first_block'] - 1:selection['last_block']]
    if len(blocks) != selection['last_block'] - selection['first_block'] + 1:
        raise ValueError('Curated block range missing')
    start, end = blocks[0]['start'], blocks[-1]['end']
    quote = doc['content_text'][start:end]
    if quote != '\n\n'.join(b['text'] for b in blocks):
        raise ValueError('Curated block text or offsets changed')
    return start, end, quote, blocks


def build(intermediate, corpus, output):
    if output.exists():
        raise ValueError('Choose a new output directory; existing releases are not overwritten')
    records = [json.loads(line) for line in (intermediate / 'documents.jsonl').read_text(encoding='utf-8').splitlines()]
    docs = {d['document_id']: d for d in records}
    # Block coordinates are deliberately bound to the reviewed intermediate export.
    if digest((intermediate / 'documents.jsonl').read_bytes()) != 'cef10ea61ab3025cb2753afb7d93ea7c2b1302e4fd73d8b709ee0bfd0a564f3e':
        raise ValueError('Intermediate export differs from the semantically reviewed version')
    selected = deepcopy(CONCEPTS)
    contacts = []
    for canton, name, first, last in CONTACT_ROWS:
        selection = claim('', DIRECTORY, first, last)
        _, _, quote, blocks = span(docs[DIRECTORY], selection)
        selection['statement'] = f"SEM's directory lists this migration contact for Canton {name}: " + quote.replace('\n\n', ' ')
        row = concept('cantonal-migration-contact', 'Cantonal migration-office contact', [selection],
                      canton='CH-' + canton, intent='contacts')
        row['instance'] = 'cantonal-migration-contact-' + canton.lower()
        selected.append(row)
        contacts.append(dict(canton='CH-' + canton, name=name, original_contact_text=quote,
                             source_url=docs[DIRECTORY]['source_url'],
                             source_block_ids=[b['block_id'] for b in blocks]))
    used_ids = sorted({c['document_id'] for row in selected for c in row['claims']})
    output.mkdir(parents=True)
    external = []
    external_files = []

    def external_bytes(identifier, data, relative):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        identity = ref(identifier, digest(data))
        external.append(identity)
        external_files.append(dict(identity=identity.model_dump(), path=relative))
        return identity

    def control(identifier, value):
        return external_bytes(identifier, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode(),
                              'controls/' + identifier + '.json')

    curation_ref = external_bytes('mvp-curation-source', Path(__file__).with_name('residence_mvp_curated.py').read_bytes(),
                                  'controls/residence_mvp_curated.py')
    evaluation = control('mvp-experimental-test-policy', dict(
        classification='experimental', authoring='Assistant directly curated saved official source text.',
        human_review=False, legal_quality_evaluation=False, disclaimer=DISCLAIMER,
        approval_status_semantics='APPROVED flags satisfy the serving test-fixture contract only; no production approval is asserted.',
        temporal_coverage_semantics='Unbounded unless the cited source states a commencement or expiry date; each citation records its snapshot time (accessed_at) and the freshness policy governs staleness.',
        freshness_policy_semantics=f'Snapshot-age limit of {FRESHNESS_DAYS} days, counted from the oldest accessed_at among the selected evidence to the read time; older results are reported STALE with their facts retained. The limit measures the age of the saved copy, not whether the page changed; refresh by re-downloading and rebuilding.',
        context_semantics='Selectors route populations; they do not decide eligibility.',
        retrieval_terms_semantics='Optional relevance signals only; they never set or override scope, context, dates or facts. A term is accepted in each source language of the release and ranks, by lexical overlap with the original excerpt, only evidence written in that same language. No translation, projection or semantic model is involved, so a term in another language, or against sources in another language, is refused as unevaluated.',
        semantic_search=False, runtime_tests_executed=False))
    provider = control('mvp-no-providers', dict(mode='none', model_calls=0, embedding_calls=0))
    ranking = control('mvp-baseline-ranking', dict(mode='BUILD-03 deterministic concept/fact baseline', hybrid=False))
    contract = external_bytes('mvp-contract-schema', (ROOT / 'packages/core/schemas/contracts-v1.schema.json').read_bytes(),
                              'controls/contracts-v1.schema.json')
    document_models = {}
    metadata = {}
    for identifier in used_ids:
        d = docs[identifier]
        if not d['eligible_for_processing']:
            raise ValueError('Excluded response selected as evidence')
        raw = (corpus / d['acquisition']['path']).read_bytes()
        if digest(raw) != d['acquisition']['raw_sha256']:
            raise ValueError('Raw snapshot hash mismatch')
        if digest(d['content_text'].encode()) != d['content_sha256']:
            raise ValueError('Intermediate content hash mismatch')
        snapshot = external_bytes('mvp-snapshot-' + identifier, raw, 'sources/' + identifier + Path(d['acquisition']['path']).suffix)
        registry = d['source_registry'][0]['definition'] if d['source_registry'] else {}
        authority = registry.get('canonical_authority')
        if not authority:
            authority = 'State Secretariat for Migration (SEM)' if 'sem.admin.ch' in d['source_url'] else None
        if not authority:
            raise ValueError('Missing reviewed authority: ' + identifier)
        language = (d.get('language_declared') or d.get('language_hint') or registry.get('language')).split('-')[0]
        metadata[identifier] = dict(source_id=registry.get('source_id', 'mvp-source-' + identifier),
                                    authority=authority, language=language)
        document_models[identifier] = seal_artifact(NormalizedEvidenceDocument(
            identity=ref('mvp-normalized-' + identifier), snapshot_ref=snapshot,
            source_id=metadata[identifier]['source_id'], text=d['content_text'],
            sections=[dict(section_id='full-document', start_offset=0, end_offset=len(d['content_text']))]))

    saved = sorted({datetime.fromisoformat(docs[i]['acquisition']['retrieved_at']).astimezone(timezone.utc).strftime('%Y-%m-%d')
                    for i in used_ids})
    saved_note = ('Curated from official pages saved on ' + saved[0] if len(saved) == 1
                  else 'Curated from official pages saved between ' + saved[0] + ' and ' + saved[-1]) + '; not complete Swiss legal coverage.'
    # Same-language term routes only: a term tagged with a source language ranks
    # evidence written in that language by lexical overlap with the original
    # excerpt, which is its own complete projection. Cross-language routes would
    # need projections and a hybrid configuration that this release does not have.
    languages = sorted({m['language'] for m in metadata.values()})
    policy = seal_artifact(LanguagePolicy(identity=ref('mvp-language-policy'),
        term_languages=languages, source_languages=languages, projection_languages=languages,
        routes=[dict(term_language=l, projection_language=l) for l in languages],
        approval_status='APPROVED', evaluation_ref=evaluation))
    entries, schemas, profiles, plans, facts, rules, evidence, provenance, requests = [], [], [], [], [], [], [], [], []

    def entry(identifier, kind, parent, label):
        return dict(entry_id=identifier, kind=kind, parent_ids=[parent] if parent else [], lifecycle='CURATED',
                    labels={'en': dict(label=label, description=DISCLAIMER, provenance=[curation_ref])})

    entries.extend([entry('hackathon', 'knowledge_space', None, 'Experimental residence MVP'),
                    entry('immigration', 'domain', 'hackathon', 'Immigration'),
                    entry('residence', 'topic', 'immigration', 'Residence permits in Switzerland')])
    seen_concepts = set()
    for row in selected:
        instance = row.get('instance', row['key'])
        cid = 'residence-' + row['key']
        if cid not in seen_concepts:
            entries.append(entry(cid, 'concept', 'residence', row['label']))
            seen_concepts.add(cid)
        jurisdiction = dict(country_code='CH')
        if row['canton']:
            jurisdiction['canton_code'] = row['canton']
        if row['municipality']:
            jurisdiction['municipality_id'] = row['municipality']
        fields, context, rule_refs = [], {}, []
        validity = dict(row.get('validity') or {})
        fact_ids = [f'mvp-fact-{instance}-{n}' for n in range(1, len(row['claims']) + 1)]
        if row['selector']:
            field, value = row['selector']
            context[field] = value
            fields = [dict(name=field, kind='string', description='Population/scope selector; not a full eligibility assessment.',
                           required=True, enum=SELECTOR_VALUES[field], reason_code=field + '_required')]
            rule = seal_artifact(PublishedRule(identity=ref('mvp-rule-' + instance), rule_id='mvp-rule-' + instance,
                when=[dict(field=field, operator='equals', values=[value])], fact_ids=fact_ids))
            rules.append(rule)
            rule_refs = [rule.identity]
        schema = seal_artifact(ContextSchema(identity=ref('mvp-context-' + instance), fields=fields))
        schemas.append(schema)
        row_evidence = []
        for n, selection in enumerate(row['claims'], 1):
            d = docs[selection['document_id']]
            doc = document_models[d['document_id']]
            meta = metadata[d['document_id']]
            start, end, quote, blocks = span(d, selection)
            eid = f'mvp-evidence-{instance}-{n}'
            accessed = datetime.fromisoformat(d['acquisition']['retrieved_at']).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            item = seal_artifact(EvidenceObject(identity=ref(eid), evidence_id=eid, release_id=RELEASE_ID,
                snapshot_ref=doc.snapshot_ref, normalized_document_ref=doc.identity, section_id='full-document',
                start_offset=start, end_offset=end, original_excerpt=quote,
                citation=dict(source_id=meta['source_id'], authority=meta['authority'], url=d['document_url'],
                              title=d['title'][:500], accessed_at=accessed),
                declared_language=[d['language_declared']] if d.get('language_declared') else [],
                detected_language=None, effective_source_language=meta['language'],
                language_detection_method='declared-metadata-or-source-registry', language_confidence=0.0,
                canonical_concept_ids=[cid], jurisdiction=jurisdiction, temporal_coverage=validity,
                provenance_refs=[curation_ref, evaluation]))
            evidence.append(item)
            row_evidence.append(item)
            facts.append(seal_artifact(PublishedFact(identity=ref(fact_ids[n-1]), fact_id=fact_ids[n-1],
                statement=selection['statement'], language='en', evidence_ids=[eid], rule_refs=rule_refs,
                applicability_conditions=row['notes'] + [f'{k}={v}' for k, v in context.items()])))
            provenance.append(dict(fact_id=fact_ids[n-1], evidence_id=eid, intermediate_document_id=d['document_id'],
                source_url=d['source_url'], document_url=d['document_url'], version_uri=d.get('version_uri'),
                corpus_id=d['corpus_id'], source_block_ids=[b['block_id'] for b in blocks],
                source_locators=[b['source_locator'] for b in blocks],
                acquisition=d['acquisition'], normalized_content_sha256=d['content_sha256']))
        profile_id = 'mvp-profile-' + instance
        profiles.append(dict(coverage_profile_id=profile_id, release_id=RELEASE_ID, catalog_ref=ref('mvp-catalog'),
            knowledge_space_id='hackathon', domain_id='immigration', topic_id='residence', concept_ids=[cid],
            intent=row['intent'], concept_selection_required=True, jurisdiction=jurisdiction,
            context_schema_ref=schema.identity, scope_modes=['exact'], max_descendant_depth=0, max_concepts=1,
            source_ids=sorted({e.citation.source_id for e in row_evidence}),
            source_languages=sorted({e.effective_source_language for e in row_evidence}), temporal_coverage=validity,
            term_routes=[dict(term_language=l, projection_language=l, source_languages=[l], evaluation_ref=evaluation)
                         for l in sorted({e.effective_source_language for e in row_evidence})],
            projection_languages_complete=sorted({e.effective_source_language for e in row_evidence}),
            rule_refs=rule_refs, evaluation_ref=evaluation, approval_status='APPROVED',
            exclusions=[DISCLAIMER, saved_note, *row['notes']],
            freshness_policy=dict(max_age_days=FRESHNESS_DAYS, policy_ref=evaluation)))
        plans.append(dict(coverage_profile_id=profile_id, portions=[dict(portion_id='mvp-portion-' + instance,
            concept_ids=[cid], fact_ids=[] if rule_refs else fact_ids, rule_refs=rule_refs)]))
        request = StructuredGroundingRequest(schema_version='structured-grounding/v1', release_id=RELEASE_ID,
            knowledge_space_id='hackathon', domain_id='immigration', topic_id='residence', concept_ids=[cid],
            intent=row['intent'], jurisdiction=jurisdiction, context=context, as_of=BUILD_DATE,
            scope_mode='exact', max_evidence=5)
        requests.append(dict(name=instance, tool='resolve', arguments=request.model_dump(exclude_none=True),
                             expected_fact_ids=fact_ids, expected_evidence_ids=[e.evidence_id for e in row_evidence]))

    # The declared scope is sealed with the catalog and served verbatim at root discovery.
    catalog = seal_artifact(KnowledgeCatalog(identity=ref('mvp-catalog'), release_id=RELEASE_ID,
        entries=sorted(entries, key=lambda e: e['entry_id']), context_schemas=schemas,
        coverage_profiles=profiles, language_policy_ref=policy.identity,
        scope=dict(statements={'en': SCOPE}, provenance=[curation_ref])))
    graph = seal_artifact(ResolutionGraph(identity=ref('mvp-graph'), release_id=RELEASE_ID, plans=plans))
    documents = list(document_models.values())
    release = seal_artifact(KnowledgeRelease(identity=ref(RELEASE_ID), release_id=RELEASE_ID,
        created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), catalog_ref=catalog.identity,
        context_schema_refs=[s.identity for s in schemas], language_policy_ref=policy.identity,
        snapshot_refs=[d.snapshot_ref for d in documents], normalized_document_refs=[d.identity for d in documents],
        evidence_refs=[e.identity for e in evidence], concept_graph_ref=graph.identity,
        fact_refs=[f.identity for f in facts], rule_refs=[r.identity for r in rules], terminology_refs=[],
        projection_refs=[], index_refs=[], contract_schema_refs=[contract], provider_configuration_ref=provider,
        ranking_configuration_ref=ranking, evaluation_ref=evaluation))
    bundle = ReleaseBundle(release=release, catalog=catalog, language_policy=policy, graph=graph,
        documents=documents, evidence=evidence, facts=facts, rules=rules, external_refs=external)
    validate_release(bundle)
    for request in requests:
        assessment = validate_request(request['arguments'], catalog, policy)
        if assessment.status != 'READY':
            raise ValueError(f"Prepared request {request['name']} is not ready: {assessment}")
        request['validated_preflight_status'] = assessment.status
    # Exercise meaningful scope failures using the pure core validator, not the app.
    zh = next(r for r in requests if r['name'] == 'zh-eu-b')['arguments']
    uk = next(r for r in requests if r['name'] == 'uk-new-employment')['arguments']
    negative_requests = []
    for name, base, changes, expected in [
        ('missing-population', zh, {'context': {}}, 'NEEDS_CONTEXT'),
        ('outside-canton', zh, {'jurisdiction': {'country_code': 'CH', 'canton_code': 'CH-GE'}}, 'OUT_OF_COVERAGE'),
        ('before-source-stated-commencement', uk, {'as_of': '2020-12-31'}, 'OUT_OF_COVERAGE'),
        ('wrong-release', zh, {'release_id': 'unavailable-test-release'}, 'RELEASE_UNAVAILABLE'),
    ]:
        arguments = {**deepcopy(base), **changes}
        assessment = validate_request(arguments, catalog, policy)
        if assessment.status != expected:
            raise ValueError(f'{name}: expected {expected}, got {assessment}')
        negative_requests.append(dict(name=name, tool='resolve', arguments=arguments,
                                      validated_preflight_status=assessment.status))
    # Unbounded validity accepts any applicability date; a stated commencement day is inclusive.
    temporal_checks = []
    for name, base, as_of in [('unbounded-far-past', zh, '1990-01-01'), ('unbounded-far-future', zh, '2099-12-31'),
                              ('commencement-day', uk, '2021-01-01')]:
        assessment = validate_request({**deepcopy(base), 'as_of': as_of}, catalog, policy)
        if assessment.status != 'READY':
            raise ValueError(f'{name}: expected READY, got {assessment}')
        temporal_checks.append(dict(name=name, as_of=as_of, validated_preflight_status=assessment.status))
    # Same-language terms pass preflight; a term in another language is refused
    # by name, and a term against sources in another language is out of coverage.
    term_checks = []
    # Profiles and prepared requests are appended in the same order.
    by_language = {tuple(p['source_languages']): r for p, r in zip(profiles, requests)}
    german, english = by_language[('de',)], by_language[('en',)]
    for name, base, terms, expected, reason in [
        ('german-term-on-german-sources', german['arguments'], [dict(text='Anmeldung Aufenthaltsbewilligung', language='de')], 'READY', None),
        ('english-term-on-english-sources', english['arguments'], [dict(text='residence permit employer', language='en')], 'READY', None),
        ('french-term-not-enabled', german['arguments'], [dict(text='permis de sejour', language='fr')], 'UNSUPPORTED_LANGUAGE', 'unsupported_term_language'),
        ('german-term-on-english-sources', english['arguments'], [dict(text='Aufenthaltsbewilligung', language='de')], 'OUT_OF_COVERAGE', 'unevaluated_language_combination'),
    ]:
        assessment = validate_request({**deepcopy(base), 'retrieval_terms': terms}, catalog, policy)
        if assessment.status != expected or (reason and assessment.issues[0].reason != reason):
            raise ValueError(f'{name}: expected {expected} {reason}, got {assessment}')
        term_checks.append(dict(name=name, tool='resolve', arguments={**deepcopy(base), 'retrieval_terms': terms},
                                validated_preflight_status=assessment.status,
                                **({'reason_code': reason} if reason else {})))
    source_stated = [dict(concept='residence-' + row['key'], **row['validity']) for row in selected if row.get('validity')]
    stated_note = ', '.join(s['concept'] + ' (' + ', '.join(f'{k}={v}' for k, v in s.items() if k != 'concept') + ')'
                            for s in source_stated) or 'none'
    release_path = output / 'release.json'
    release_path.write_text(bundle.model_dump_json(indent=2) + '\n', encoding='utf-8', newline='\n')
    validate_release(ReleaseBundle.model_validate_json(release_path.read_text(encoding='utf-8')))
    for file in external_files:
        if digest((output / file['path']).read_bytes()) != file['identity']['sha256']:
            raise ValueError('Packaged external dependency hash mismatch')
    write_json(output / 'external-artifacts.json', external_files)
    write_json(output / 'provenance.json', provenance)
    write_json(output / 'contacts.json', contacts)
    write_json(output / 'semantic-extraction.json', dict(classification='experimental', disclaimer=DISCLAIMER,
        release_id=RELEASE_ID, operations=selected, facts=[f.model_dump() for f in facts],
        rules=[r.model_dump() for r in rules], evidence=[e.model_dump() for e in evidence]))
    write_json(output / 'source-disposition.json', [dict(document_id=d['document_id'], source_url=d['source_url'],
        disposition='curated' if d['document_id'] in used_ids else 'excluded-response' if not d['eligible_for_processing']
        else 'not-curated-in-this-MVP', intermediate_status=d['status']) for d in records])
    shutil.copyfile(intermediate / 'unavailable.json', output / 'unavailable.json')
    discovery = GetCoverageRequest(release_id=RELEASE_ID, parent_id='residence', limit=100)
    evidence_request = GetEvidenceRequest(release_id=RELEASE_ID, evidence_ids=[evidence[0].evidence_id])
    write_json(output / 'mcp-requests.json', dict(execution_status='Prepared and schema-validated; not sent to an application.',
        discovery=dict(tool='get_coverage', arguments=discovery.model_dump(exclude_none=True)),
        resolve=requests, negative_cases=negative_requests, temporal_checks=temporal_checks, term_checks=term_checks,
        evidence=dict(tool='get_evidence', arguments=evidence_request.model_dump())))
    write_json(output / 'mcp-client.json', {'mcpServers': {'swisstip-residence-mvp': {
        'command': str(ROOT / '.venv/Scripts/python.exe'),
        'args': ['-m', 'swisstip.mcp_server.server', '--release', str(release_path.resolve()), '--active-release-id', RELEASE_ID]}}})
    report = dict(release_id=RELEASE_ID, release_sha256=digest(release_path.read_bytes()),
        classification='experimental', validated=True, checks=['Existing validate_release before and after JSON serialization',
        'Raw snapshot and normalized source hashes', 'Exact evidence spans and block coordinates',
        'All packaged external dependency hashes', 'MCP request Pydantic schemas',
        f'{len(requests)} positive, {len(negative_requests)} negative, {len(temporal_checks)} temporal and {len(term_checks)} retrieval-term core preflight checks'],
        retrieval_term_languages=languages, retrieval_term_routing='same-language lexical overlap only',
        facts=len(facts), evidence=len(evidence), rules=len(rules), concepts=len(seen_concepts),
        coverage_profiles=len(profiles), curated_documents=len(documents), cantonal_contacts=len(contacts),
        prepared_resolve_requests=len(requests), negative_preflight_cases=len(negative_requests),
        app_calls=0, external_model_calls=0,
        runtime_requests_executed=0, human_review=False, prepared_request_as_of=BUILD_DATE,
        source_snapshot_dates=saved, temporal_coverage=dict(default='unbounded', source_stated=source_stated))
    write_json(output / 'validation.json', report)
    (output / 'README.md').write_text(f'''# Experimental residence MCP test data

Release: `{RELEASE_ID}`. Classification: **experimental**.

{len(facts)} assistant-curated facts, {len(evidence)} exact source excerpts, {len(rules)} routing rules,
{len(seen_concepts)} concepts and {len(profiles)} coverage profiles from {len(documents)} saved official pages.
Scope: federal requirements, Zurich canton/city procedures and contacts for all 26 cantons.
Other downloaded pages are accounted for in `source-disposition.json`; they have not all been semantically curated.

`release.json` is the app-ingestible `serving-release/v1` bundle. It contains normalized
source documents, citations, facts, rules, catalog and resolution graph. `semantic-extraction.json`
is a readable semantic export; `provenance.json` maps facts to original blocks and acquisitions.
`sources/` contains the cited raw snapshots. External control files have real content hashes.

Use `mcp-client.json` to configure a local MCP client, or run:

```shell
./.venv/Scripts/python.exe -m swisstip.mcp_server.server --release {release_path.relative_to(ROOT).as_posix() if release_path.is_relative_to(ROOT) else release_path.as_posix()} --active-release-id {RELEASE_ID}
```

`mcp-requests.json` supplies discovery, {len(requests)} resolve examples, {len(negative_requests)} negative cases,
{len(temporal_checks)} temporal checks, {len(term_checks)} retrieval-term checks and an evidence request. Select exactly one concept per resolve and supply the
listed context. `as_of` is the applicability date the caller asks about, normally today; the examples use the
build date {BUILD_DATE}. Validity is unbounded unless the cited source states a commencement or expiry date.
Source-stated limits in this release: {stated_note}.
Each citation records when its page was saved (`accessed_at`; {', '.join(saved)}); the freshness policy reports
results as STALE once that snapshot is older than {FRESHNESS_DAYS} days.
The deterministic concept/fact baseline requires no models. Optional `retrieval_terms` are accepted in
{' and '.join('`' + l + '`' for l in languages)} and rank evidence written in the same language by lexical overlap
with the original excerpt; they never change scope, context or facts. A term in another language is refused
(`UNSUPPORTED_LANGUAGE`), and a term against sources in another language is out of coverage. Semantic retrieval,
embeddings, reranking and cross-language projections are outside this pack.

{DISCLAIMER} Contract `APPROVED`/`CURATED` flags enable this experimental fixture to be
loaded by the existing validator; they do not assert independent review or production approval.
Rules select pre-authored statements by population; they do not compute legal eligibility.
English statements paraphrase the cited original-language text; they are not official translations.

Validation checks contracts, sealed hashes, dependencies and exact source spans. It does not
prove the legal completeness of the statements. No application, database or external model
was called; example MCP requests passed schema and core scope/context checks but have not been executed.
The release has not been imported into the database or activated.
''', encoding='utf-8', newline='\n')
    return report


def main():
    global RELEASE_ID
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intermediate', type=Path, default=ROOT / '.local/intermediate/hackathon-residence-2026-09-11-v1')
    parser.add_argument('--corpus', type=Path, default=ROOT / '.local/corpora/hackathon-residence-2026-09-10')
    parser.add_argument('--output', type=Path, default=ROOT / '.local/mvp/residence-semantic-2026-09-12-v6')
    parser.add_argument('--release-id', default=RELEASE_ID,
                        help='Release identity; choose a new one together with --output when the curated selections change.')
    args = parser.parse_args()
    RELEASE_ID = args.release_id
    print(json.dumps(build(args.intermediate.resolve(), args.corpus.resolve(), args.output.resolve()), indent=2))


if __name__ == '__main__':
    main()
