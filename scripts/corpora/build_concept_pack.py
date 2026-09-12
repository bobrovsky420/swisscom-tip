"""Package V3 concept candidates from knowledge-builder batch results as a serving part.

Reads ``swisstip.concept-proposal-batch/v1`` results (for example the
assistant-authored runs under ``.local/extraction/...``), re-normalizes each page
with the app's own normalizer to recover section texts, and emits one
``serving-release/v1`` part: a catalog concept and a published fact per retained
candidate, evidence objects for the cited quotations with exact offsets, and
exact-scope coverage profiles grouped by jurisdiction. Only pure contracts,
hashing and validation are used; no application, provider, database or network
call is made. Candidates keep the CANDIDATE lifecycle: they are model or
assistant proposals after an automated review, not human-approved knowledge.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

from swisstip.core.contracts import (ContextSchema, EvidenceObject, KnowledgeCatalog,
    KnowledgeRelease, LanguagePolicy, NormalizedEvidenceDocument, PublishedFact,
    ResolutionGraph, StructuredGroundingRequest)
from swisstip.core.identity import seal_artifact
from swisstip.core.validation import validate_request
from swisstip.runtime.release import ReleaseBundle, validate_release
from audit_source_languages import ROOT, sha, write
from build_residence_mvp import FRESHNESS_DAYS, ref
from build_expanded_pack import BUILD_DATE, jurisdiction, merge_profiles, WINDOW
from extract_expanded import language_hint

DEFAULT_WORKDIR = ROOT / '.local/extraction/assistant-v3-2026-09-11'
NOTICE = ('Assistant-authored V3 concept candidates after the app\'s automated review; '
          'no human review, legal review or eligibility decision.')
INTENT = 'read-concept-candidates'
TYPE_LABELS = dict(PROCESS='Procedures', RULE='Rules and conditions', SERVICE='Services',
                   DOCUMENT='Documents and forms', ENTITY='Organizations and entities', OTHER='Other concepts')


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def reports(workdir):
    for result_path in sorted((workdir / 'runs').glob('*/result.json')):
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result.get('schema_version') != 'swisstip.concept-proposal-batch/v1':
            raise ValueError('Unexpected result schema: ' + str(result_path))
        for report in result['reports']:
            yield result_path, result, report


def page_text(page):
    """Concatenate section evidence texts; candidate offsets are relative to each section."""
    sections, offset, parts = [], 0, []
    for section in page.sections:
        text = section.evidence_text
        sections.append(dict(section_id=section.section_id, start_offset=offset, end_offset=offset + len(text)))
        parts.append(text)
        offset += len(text) + 2
    return '\n\n'.join(parts), sections


def build(workdir, output, release_id):
    from swisstip.ingestion.source_snapshots import normalize_source_snapshot
    if output.exists():
        raise ValueError('Choose a new output directory; existing releases are immutable')
    output.mkdir(parents=True)
    rid = release_id
    external, files = [], []

    def external_file(identifier, data, relative):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        identity = ref(identifier, sha(data))
        external.append(identity)
        files.append(dict(identity=identity.model_dump(), path=relative))
        return identity

    evaluation = external_file('concept-test-policy', json.dumps(dict(
        notice=NOTICE, assistant_authored=True, model_provider_calls=0, prompt_profile='concept_extraction_v3',
        human_review=False, production_approved=False, approval_flags='Experimental fixture loadability only',
        temporal_window='Snapshot test scope only')).encode(), 'controls/test-policy.json')
    build_ref = external_file('concept-build-source', Path(__file__).read_bytes(), 'controls/build_concept_pack.py')
    contract = external_file('concept-contract-schema', (ROOT / 'packages/core/schemas/contracts-v1.schema.json').read_bytes(),
                             'controls/contracts-v1.schema.json')
    provider = external_file('concept-no-providers', b'{"llm_calls":0,"embedding_calls":0,"completions":"assistant-authored"}',
                             'controls/providers.json')
    ranking = external_file('concept-baseline', b'{"mode":"deterministic-concept-fact-baseline"}', 'controls/ranking.json')
    schema = seal_artifact(ContextSchema(identity=ref('concept-context'), fields=[]))

    def entry(eid, kind, parent, label, lang, description=NOTICE, aliases=(), lifecycle='VERIFIED_AUTOMATIC', refs=()):
        return dict(entry_id=eid, kind=kind, parent_ids=[parent] if parent else [], lifecycle=lifecycle,
                    labels={lang: dict(label=(label.strip() or eid)[:500], aliases=[a[:500] for a in aliases][:30],
                                       description=(description.strip() or NOTICE)[:2000], provenance=[build_ref, *refs])})

    entries = [entry('hackathon', 'knowledge_space', None, 'Experimental residence source corpus', 'en'),
               entry('immigration', 'domain', 'hackathon', 'Immigration', 'en'),
               entry('residence', 'topic', 'immigration', 'Residence permits in Switzerland', 'en')]
    documents, evidence, facts, profiles, plans, requests, provenance = [], [], [], [], [], [], []
    languages, types_used, batch_refs, prompt_hashes, identities = set(), set(), {}, set(), Counter()
    pages_with_candidates, skipped = 0, []
    for result_path, result, report in reports(workdir):
        if not report['candidates']:
            continue
        batch_id = result_path.parent.name
        if batch_id not in batch_refs:
            batch_refs[batch_id] = external_file('concept-batch-' + batch_id, result_path.read_bytes(),
                                                 f'controls/{batch_id}-result.json')
        batch_ref = batch_refs[batch_id]
        prompt_hashes.add(report['effective_prompts']['extraction']['sha256'])
        for identity in report['model_identities']:
            identities[(identity['provider'], identity['model'])] += 1
        page = normalize_source_snapshot(Path(report['source']), preserve_structure=True)
        if page.content_hash != report['input_hash']:
            raise ValueError('Normalized page no longer matches the report input hash: ' + report['source'])
        text, sections = page_text(page)
        offsets = {s['section_id']: s['start_offset'] for s in sections}
        did = report['document_id']
        # Evidence must name a language: prefer the page's declared language, then the
        # publisher's URL language segment; pages with neither are listed, not guessed.
        lang, method, confidence = page.language, 'html-lang-attribute', 1.0
        if not lang:
            lang, method, confidence = language_hint(report['provenance']['source_url']), 'url-language-hint', 0.5
        if not lang:
            skipped.append(dict(document_id=did, source_url=report['provenance']['source_url'],
                                candidates=len(report['candidates']), reason='no-declared-or-url-language'))
            continue
        raw = Path(report['source']).read_bytes()
        if sha(raw) != report['provenance']['sha256']:
            raise ValueError('Raw snapshot hash mismatch: ' + report['source'])
        snapshot = external_file('snapshot-' + did, raw, f'sources/{did}.html')
        source_id = 'source-' + did
        normalized = seal_artifact(NormalizedEvidenceDocument(identity=ref('normalized-' + did), snapshot_ref=snapshot,
                                                                source_id=source_id, text=text, sections=sections))
        documents.append(normalized)
        pages_with_candidates += 1
        scope = jurisdiction(report['provenance']['source_url'])
        host = urlsplit(report['provenance']['final_url']).hostname
        accessed = utc(report['provenance']['retrieved_at'])
        reviews = {(r['chunk_index'], r['candidate_index']): r for r in report.get('semantic_reviews', [])}
        for candidate in report['candidates']:
            cid = candidate['candidate_id']
            ctype = candidate['concept_type']
            types_used.add(ctype)
            # Serving contracts only load CURATED or VERIFIED_AUTOMATIC entries; the
            # candidate status is carried by the notice, the evaluation policy and provenance.
            entries.append(entry(cid, 'concept', 'candidate-type-' + ctype.lower(), candidate['preferred_label'], lang,
                                 description=candidate['description'], aliases=candidate['alternative_labels'],
                                 lifecycle='VERIFIED_AUTOMATIC', refs=[batch_ref]))
            evidence_ids = []
            for number, span in enumerate(candidate['evidence'][:5], 1):
                start = offsets[span['section_id']] + span['start']
                end = offsets[span['section_id']] + span['end']
                if text[start:end] != span['quote']:
                    raise ValueError(f'Candidate {cid} quotation is not an exact span of the normalized page')
                eid = f'evidence-{cid}-{number}'
                evidence.append(seal_artifact(EvidenceObject(
                    schema_version='evidence-object/v2', identity=ref(eid), evidence_id=eid, release_id=rid,
                    snapshot_ref=snapshot, normalized_document_ref=normalized.identity, section_id=span['section_id'],
                    start_offset=start, end_offset=end, original_excerpt=span['quote'],
                    citation=dict(source_id=source_id, authority='Official publisher: ' + str(host),
                                  url=report['provenance']['final_url'], title=(page.title or did)[:500], accessed_at=accessed),
                    declared_language=[page.language] if page.language else [], detected_language=None,
                    effective_source_language=lang, language_detection_method=method,
                    language_confidence=confidence, canonical_concept_ids=[cid],
                    jurisdiction=scope, temporal_coverage=WINDOW, provenance_refs=[build_ref, batch_ref])))
                evidence_ids.append(eid)
            languages.add(lang)
            fid = 'fact-' + cid
            facts.append(seal_artifact(PublishedFact(
                identity=ref(fid), fact_id=fid, statement=candidate['description'][:2000], language=lang,
                evidence_ids=evidence_ids,
                applicability_conditions=[('Scope: ' + candidate['scope'])[:500], NOTICE])))
            provenance.append(dict(candidate_id=cid, document_id=did, batch_id=batch_id,
                                   source_url=report['provenance']['source_url'], final_url=report['provenance']['final_url'],
                                   candidate=candidate, evidence_ids=evidence_ids,
                                   semantic_review=reviews.get((None, None)), reviews=[r for r in report.get('semantic_reviews', [])
                                                                                        if r.get('preferred_label') == candidate['preferred_label']]))
            pid = 'profile-' + cid
            profiles.append(dict(coverage_profile_id=pid, release_id=rid, catalog_ref=ref('concept-catalog'),
                                 knowledge_space_id='hackathon', domain_id='immigration', topic_id='residence',
                                 concept_ids=[cid], intent=INTENT, concept_selection_required=True, jurisdiction=scope,
                                 context_schema_ref=schema.identity, scope_modes=['exact'], max_concepts=1,
                                 source_ids=[source_id], source_languages=[lang], temporal_coverage=WINDOW,
                                 evaluation_ref=evaluation, approval_status='APPROVED',
                                 exclusions=[NOTICE, 'No normalized eligibility decision.'],
                                 freshness_policy=dict(max_age_days=FRESHNESS_DAYS, policy_ref=evaluation)))
            plans.append(dict(coverage_profile_id=pid, portions=[dict(portion_id=pid + '-1', concept_ids=[cid], fact_ids=[fid])]))
            request = StructuredGroundingRequest(schema_version='structured-grounding/v1', release_id=rid,
                                                 knowledge_space_id='hackathon', domain_id='immigration', topic_id='residence',
                                                 concept_ids=[cid], intent=INTENT, jurisdiction=scope, context={},
                                                 as_of=BUILD_DATE, scope_mode='exact', max_evidence=5)
            requests.append(dict(tool='resolve', arguments=request.model_dump(exclude_none=True),
                                 source_url=report['provenance']['source_url'], evidence_ids=evidence_ids,
                                 expected_note='One assistant-authored candidate with its cited evidence.'))
    if not facts:
        raise ValueError('No retained candidates found in the batch results')
    for ctype in sorted(types_used):
        entries.append(entry('candidate-type-' + ctype.lower(), 'concept', 'residence', TYPE_LABELS[ctype], 'en'))
    profiles, plans = merge_profiles(profiles, plans)
    policy = seal_artifact(LanguagePolicy(identity=ref('concept-language-policy'), platform_catalog='tip-language-catalog/v4',
                                          term_languages=[], source_languages=sorted(languages), projection_languages=[],
                                          routes=[], approval_status='APPROVED', evaluation_ref=evaluation))
    catalog = seal_artifact(KnowledgeCatalog(identity=ref('concept-catalog'), release_id=rid,
                                             entries=sorted(entries, key=lambda e: e['entry_id']), context_schemas=[schema],
                                             coverage_profiles=profiles, language_policy_ref=policy.identity))
    graph = seal_artifact(ResolutionGraph(identity=ref('concept-graph'), release_id=rid, plans=plans))
    release = seal_artifact(KnowledgeRelease(
        identity=ref(rid), release_id=rid, created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        catalog_ref=catalog.identity, context_schema_refs=[schema.identity], language_policy_ref=policy.identity,
        snapshot_refs=[d.snapshot_ref for d in documents], normalized_document_refs=[d.identity for d in documents],
        evidence_refs=[e.identity for e in evidence], concept_graph_ref=graph.identity, fact_refs=[f.identity for f in facts],
        rule_refs=[], terminology_refs=[], projection_refs=[], index_refs=[], contract_schema_refs=[contract],
        provider_configuration_ref=provider, ranking_configuration_ref=ranking, evaluation_ref=evaluation))
    bundle = ReleaseBundle(release=release, catalog=catalog, language_policy=policy, graph=graph, documents=documents,
                           evidence=evidence, facts=facts, rules=[], external_refs=external)
    validate_release(bundle)
    tested, checks = set(), []
    by_concept = {c: p for p in catalog.coverage_profiles for c in p.concept_ids}
    for request in requests:
        profile = by_concept[request['arguments']['concept_ids'][0]]
        key = (profile.jurisdiction.canton_code, tuple(profile.source_languages))
        if key not in tested:
            assessment = validate_request(request['arguments'], catalog, policy)
            tested.add(key)
            checks.append(dict(concept_ids=request['arguments']['concept_ids'], status=assessment.status))
    target = output / 'release.json'
    target.write_text(bundle.model_dump_json() + '\n', encoding='utf-8', newline='\n')
    validate_release(ReleaseBundle.model_validate_json(target.read_text(encoding='utf-8')))
    write(output / 'external-artifacts.json', files)
    write(output / 'provenance.json', provenance)
    write(output / 'mcp-requests.json', dict(executed=False, resolve=requests))
    report = dict(release_id=rid, release_file='release.json', release_sha256=sha(target.read_bytes()),
                  documents=len(documents), facts=len(facts), evidence=len(evidence), concepts=len(requests),
                  coverage_profiles=len(profiles), languages=sorted(languages), validated=True,
                  pure_preflight_checks=len(checks), preflight_statuses=dict(Counter(c['status'] for c in checks)),
                  app_calls=0, llm_calls=0, batches=sorted(batch_refs), pages_with_candidates=pages_with_candidates,
                  skipped_pages=skipped,
                  extraction_prompt_sha256=sorted(prompt_hashes),
                  completion_identities={f'{p}/{m}': n for (p, m), n in identities.items()},
                  lifecycle='VERIFIED_AUTOMATIC', candidate_status='assistant-authored proposals after the app review; not human-reviewed',
                  notice=NOTICE)
    write(output / 'validation.json', report)
    write(output / 'mcp-client.json', {'mcpServers': {'residence-concepts': {'command': str(ROOT / '.venv/Scripts/python.exe'),
                                                                             'args': ['-m', 'swisstip.mcp_server.server', '--release', str(target),
                                                                                      '--active-release-id', rid]}}})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release-id', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.workdir.resolve(), args.output.resolve(), args.release_id), indent=2))
