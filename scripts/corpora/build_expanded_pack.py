"""Package all attributed source assertions as experimental serving fixtures.

These are extractive source assertions, not independently curated eligibility
rules. Only pure contracts, hashing and validation are used; no application or
provider is invoked. Identical normalized documents retain an alias ledger.
"""
import argparse
from collections import Counter, defaultdict
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
from audit_source_languages import ROOT, OUT, sha, write
from build_residence_mvp import FRESHNESS_DAYS, ref

INTERMEDIATE = ROOT/'.local/intermediate/hackathon-residence-all-languages-2026-09-11'
SEMANTIC = ROOT/'.local/semantic/hackathon-residence-all-languages-2026-09-11'
DEST = ROOT/'.local/mvp/residence-all-languages-2026-09-11-v1'
# Unbounded validity: source assertions carry no commencement or expiry unless the page states one.
WINDOW = {}
BUILD_DATE = datetime.now(timezone.utc).strftime('%Y-%m-%d')
NOTICE = 'Experimental automatically derived source assertions; no independent semantic or legal review.'
CANTONS = 'AG AI AR BE BL BS FR GE GL GR JU LU NE NW OW SG SH SO SZ TG TI UR VD VS ZG ZH'.split()


def jurisdiction(url):
    host=urlsplit(url).hostname or ''
    special={'jura.ch':'JU','baselland.ch':'BL','bl-api.webcloud7.ch':'BL','hallo-baselland.ch':'BL',
             'bern.ch':'BE','biel-bienne.ch':'BE','stadt-zuerich.ch':'ZH'}
    for domain,code in list(special.items())+[(c.lower()+'.ch',c) for c in CANTONS]:
        if host==domain or host.endswith('.'+domain):
            return dict(country_code='CH',canton_code='CH-'+code)
    return dict(country_code='CH')


def pieces(text,limit=1900):
    """Retain every character; boundaries never remove qualifying language."""
    start=0
    while len(text)-start>limit:
        end=text.rfind('\n',start+limit//2,start+limit)
        if end<=start:
            end=text.rfind(' ',start+limit//2,start+limit)
        if end<=start:
            end=start+limit
        yield text[start:end]
        start=end
    if start<len(text):
        yield text[start:]


def assertion_groups(assertions,limit=50):
    group=[]; cost=0
    for a in assertions:
        n=len(list(pieces(a['original_text'])))
        if group and cost+n>limit:
            yield group; group=[]; cost=0
        group.append(a); cost+=n
    if group: yield group


def merge_profiles(profiles,plans):
    """Keep bounded discovery metadata while retaining exact document selection.

    A profile can serve up to 50 independent document concepts. Each retains its
    own resolution portion, so selecting one never includes its neighbours.
    """
    by_scope=defaultdict(list)
    for profile,plan in zip(profiles,plans):
        by_scope[json.dumps(profile['jurisdiction'],sort_keys=True)].append((profile,plan))
    merged=[]; graphs=[]
    for scoped in by_scope.values():
        for start in range(0,len(scoped),50):
            cohort=scoped[start:start+50]; pid=f'expanded-profile-{len(merged)+1:05d}'
            profile=cohort[0][0]|dict(coverage_profile_id=pid,
                concept_ids=[c for p,_ in cohort for c in p['concept_ids']],
                source_ids=sorted({s for p,_ in cohort for s in p['source_ids']}),
                source_languages=sorted({s for p,_ in cohort for s in p['source_languages']}))
            merged.append(profile)
            graphs.append(dict(coverage_profile_id=pid,portions=[p for _,g in cohort for p in g['portions']]))
    return merged,graphs


def build(output,release_id=None):
    if output.exists():
        raise ValueError('Choose a new output directory; existing releases are immutable')
    # Completion marker prevents packaging a still-being-written assertion stream.
    summary=json.loads((SEMANTIC/'summary.json').read_text(encoding='utf-8'))
    if summary.get('language_detector_accuracy')!='high':
        raise ValueError('Rebuild assertions with the current language-audit implementation first')
    if sha((SEMANTIC/'assertions.jsonl').read_bytes())!=summary['assertions_sha256']:
        raise ValueError('Assertion stream does not match its completed export marker')
    rows=defaultdict(list)
    unresolved=[]
    for line in (SEMANTIC/'assertions.jsonl').open(encoding='utf-8'):
        a=json.loads(line)
        if a.get('source_quality',{}).get('unexpected_control_characters',0)>max(5,len(a['original_text'])//100):
            unresolved.append(dict(assertion_id=a['assertion_id'],reason='unreadable-native-font-mapping',
                document_id=a['document_id'],source_url=a['source_url']))
        elif not a['language']['effective_language']:
            unresolved.append(dict(assertion_id=a['assertion_id'],reason='source-language-undetermined'))
        else:
            rows[a['document_id']].append(a)
    output.mkdir(parents=True)
    alias_ledger=[]
    unique=[]
    seen={}
    for did,assertions in sorted(rows.items()):
        d=json.loads((INTERMEDIATE/'documents'/(did+'.json')).read_text(encoding='utf-8'))
        key=(d['content_sha256'],json.dumps(jurisdiction(d['source_url']),sort_keys=True),
             tuple((a['start_offset'],a['end_offset'],a['language']['effective_language']) for a in assertions))
        if key in seen:
            alias_ledger.append(dict(document_id=did,representative_document_id=seen[key],
                source_url=d['source_url'],document_url=d['document_url'],version_uri=d.get('version_uri'),
                content_sha256=d['content_sha256'],basis='identical normalized text and assertion spans/languages'))
        else:
            seen[key]=did
            unique.append((d,assertions))
    # Contracts have finite cardinalities. Partition only if their actual limits
    # require it, and expose every part in the collection manifest.
    batches=[]; batch=[]; cost=0; concepts=0
    for d,assertions in unique:
        n=sum(len(list(pieces(a['original_text']))) for a in assertions)
        count=sum(1 for _ in assertion_groups(assertions))
        if batch and (cost+n>90000 or concepts+count>8500):
            batches.append(batch); batch=[]; cost=0; concepts=0
        batch.append((d,assertions)); cost+=n; concepts+=count
    if batch:
        batches.append(batch)
    reports=[]
    for number,batch in enumerate(batches,1):
        part=output if len(batches)==1 else output/f'part-{number:03d}'
        part.mkdir(parents=True,exist_ok=True)
        part_report=build_part(part,batch,number,len(batches),release_id=release_id)
        part_report['release_file']=(part/'release.json').relative_to(output).as_posix()
        reports.append(part_report)
    write(output/'document-aliases.json',alias_ledger)
    write(output/'unresolved-assertions.json',unresolved)
    report=dict(schema_version='swisstip.experimental-release-collection/v1',parts=reports,
        unique_documents=len(unique),identical_document_aliases=len(alias_ledger),unresolved_assertions=len(unresolved),
        application_calls=0,llm_calls=0,semantic_review_complete=False,
        scope='All current source assertions with identifiable language, including contextual and archival material.',
        acquisition_completeness='See coverage-report.json; serving validity does not establish corpus completeness.')
    write(output/'collection.json',report)
    server_args=['-m','swisstip.mcp_server.server']
    for part_report in reports:
        server_args.extend(['--release',str(output/part_report['release_file'])])
    if reports:
        server_args.extend(['--active-release-id',reports[0]['release_id']])
        write(output/'mcp-client.json',{'mcpServers':{'residence-expanded':{
            'command':str(ROOT/'.venv/Scripts/python.exe'),'args':server_args}}})
    (output/'README.md').write_text('# Expanded residence source-assertion fixtures\n\n'+NOTICE+'\n\n'
        'This collection preserves original-language source text and citations. It does not provide normalized '
        'eligibility rules or claim that every acquired page concerns residence permits. Archival dates, '
        'conditions and exceptions remain in the original text and semantic JSONL annotations.\n\n'
        '`collection.json` lists every app-ingestible `serving-release/v1` part. Load each listed release '
        'explicitly; parts are not implicitly combined by the MCP server. The root `mcp-client.json` loads '
        'all parts in one server using repeated `--release` arguments. Requests pin the corresponding release ID. '
        '`mcp-requests.json` in each part '
        'lists document concepts and exact evidence IDs. The prepared requests were checked by pure validators, '
        'not sent to a running app. The frozen 2026-09-11 window is test scope, not legal validity.\n\n'
        '`document-aliases.json` retains additional source identities for exactly identical normalized text. '
        '`unresolved-assertions.json` records language gaps. OCR remains a separate unreviewed intermediate '
        'artifact until verified; acquisition and semantic coverage reports record remaining work.\n\n'
        'APPROVED and VERIFIED_AUTOMATIC contract flags enable experimental loading only. They are not '
        'human approval, legal review, or proof of complete extraction. No database import or activation occurred.\n',
        encoding='utf-8',newline='\n')
    return report


def build_part(output,records,number,total,release_id=None):
    # An explicit release identity names a single part exactly; multi-part builds add the part suffix.
    base=release_id or 'hackathon-residence-all-languages-2026-09-11-v1'
    rid=base if (release_id and total==1) else base+(f'-part-{number:03d}' if total>1 else '')
    external=[]; files=[]
    def external_file(identifier,data,relative):
        path=output/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        identity=ref(identifier,sha(data)); external.append(identity)
        files.append(dict(identity=identity.model_dump(),path=relative))
        return identity
    evaluation=external_file('expanded-test-policy',json.dumps(dict(notice=NOTICE,semantic_review=False,
        source_assertions=True,executable_eligibility_rules=False,production_approved=False,
        approval_flags='Experimental fixture loadability only',temporal_window='Snapshot test scope only')).encode(),
        'controls/test-policy.json')
    build_ref=external_file('expanded-build-source',Path(__file__).read_bytes(),'controls/build_expanded_pack.py')
    extractor=external_file('expanded-assertion-source',Path(__file__).with_name('extract_source_assertions.py').read_bytes(),
        'controls/extract_source_assertions.py')
    contract=external_file('expanded-contract-schema',(ROOT/'packages/core/schemas/contracts-v1.schema.json').read_bytes(),
        'controls/contracts-v1.schema.json')
    provider=external_file('expanded-no-providers',b'{"llm_calls":0,"embedding_calls":0}', 'controls/providers.json')
    ranking=external_file('expanded-baseline',b'{"mode":"deterministic-concept-fact-baseline"}', 'controls/ranking.json')
    languages=sorted({a['language']['effective_language'] for _,aa in records for a in aa})
    policy=seal_artifact(LanguagePolicy(identity=ref('expanded-language-policy'),platform_catalog='tip-language-catalog/v4',
        term_languages=[],source_languages=languages,projection_languages=[],routes=[],approval_status='APPROVED',evaluation_ref=evaluation))
    schema=seal_artifact(ContextSchema(identity=ref('expanded-context'),fields=[]))
    documents=[]; evidence=[]; facts=[]; profiles=[]; plans=[]; requests=[]; provenance=[]
    def entry(eid,kind,parent,label,lang='en'):
        return dict(entry_id=eid,kind=kind,parent_ids=[parent] if parent else [],lifecycle='VERIFIED_AUTOMATIC',
            labels={lang:dict(label=(label.strip() or eid)[:500],description=NOTICE,provenance=[extractor,build_ref])})
    entries=[entry('hackathon','knowledge_space',None,'Experimental residence source corpus'),
        entry('immigration','domain','hackathon','Immigration'),entry('residence','topic','immigration','Residence permits in Switzerland')]
    categories=sorted({a['semantic_annotations'].get('topics',['source-context'])[0] for _,aa in records for a in aa})
    entries.extend(entry('category-'+c,'concept','residence',c.replace('-',' ').capitalize()) for c in categories)
    for number,(d,assertions) in enumerate(records,1):
        did=d['document_id']; scope=jurisdiction(d['source_url']); host=urlsplit(d['source_url']).hostname
        source_id='source-'+did
        raw=(OUT/d['acquisition']['path']).read_bytes()
        if sha(raw)!=d['acquisition']['raw_sha256'] or sha(d['content_text'].encode())!=d['content_sha256']:
            raise ValueError('Source hash mismatch: '+did)
        snapshot=external_file('snapshot-'+did,raw,'sources/'+did+Path(d['acquisition']['path']).suffix)
        normalized=seal_artifact(NormalizedEvidenceDocument(identity=ref('normalized-'+did),snapshot_ref=snapshot,
            source_id=source_id,text=d['content_text'],sections=[dict(section_id='full-document',start_offset=0,end_offset=len(d['content_text']))]))
        documents.append(normalized)
        # Each exact document concept is independently resolvable in one portion.
        groups=list(assertion_groups(assertions))
        for g,aa in enumerate(groups,1):
            cid='residence-'+did+(f'-{g}' if len(groups)>1 else '')
            category=Counter(a['semantic_annotations'].get('topics',['source-context'])[0] for a in aa).most_common(1)[0][0]
            entries.append(entry(cid,'concept','category-'+category,d['title']+(f' (part {g})' if len(groups)>1 else ''),
                                 aa[0]['language']['effective_language']))
            row_facts=[]; row_evidence=[]
            for a in aa:
                quote=a['original_text']; lang=a['language']['effective_language']; eid='evidence-'+a['assertion_id']
                if d['content_text'][a['start_offset']:a['end_offset']]!=quote:
                    raise ValueError('Assertion is not an exact source span')
                ev=seal_artifact(EvidenceObject(schema_version='evidence-object/v2',identity=ref(eid),evidence_id=eid,
                    release_id=rid,snapshot_ref=snapshot,normalized_document_ref=normalized.identity,section_id='full-document',
                    start_offset=a['start_offset'],end_offset=a['end_offset'],original_excerpt=quote,
                    citation=dict(source_id=source_id,authority='Kanton Basel-Landschaft' if host=='bl-api.webcloud7.ch' else 'Official publisher: '+str(host),url=d['document_url'],
                        title=d['title'][:500],accessed_at=datetime.fromisoformat(d['acquisition']['retrieved_at']).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
                    declared_language=[d['language_declared'].replace('_','-')] if d.get('language_declared') else [],
                    detected_language=a['language']['detected_language'],effective_source_language=lang,
                    language_detection_method=a['language']['method'],language_confidence=a['language'].get('effective_confidence',a['language']['confidence']),
                    canonical_concept_ids=[cid],jurisdiction=scope,temporal_coverage=WINDOW,provenance_refs=[extractor,evaluation]))
                evidence.append(ev); row_evidence.append(eid)
                for k,text in enumerate(pieces(quote),1):
                    fid='fact-'+a['assertion_id']+f'-{k}'
                    facts.append(seal_artifact(PublishedFact(identity=ref(fid),fact_id=fid,statement=text,language=lang,
                        evidence_ids=[eid],applicability_conditions=[NOTICE,'Interpret this fragment with the complete cited section and source document.'])))
                    row_facts.append(fid)
                provenance.append(dict(assertion_id=a['assertion_id'],evidence_id=eid,document_id=did,
                    source_url=d['source_url'],version_uri=d.get('version_uri'),source_locator=a['source_locator'],
                    source_block_ids=a['source_block_ids'],language=a['language'],semantic_annotations=a['semantic_annotations']))
                provenance[-1]['source_quality']=a.get('source_quality',{})
            pid='profile-'+cid
            profiles.append(dict(coverage_profile_id=pid,release_id=rid,catalog_ref=ref('expanded-catalog'),
                knowledge_space_id='hackathon',domain_id='immigration',topic_id='residence',concept_ids=[cid],
                intent='read-source-assertions',concept_selection_required=True,jurisdiction=scope,
                context_schema_ref=schema.identity,scope_modes=['exact'],max_concepts=1,source_ids=[source_id],
                source_languages=sorted({a['language']['effective_language'] for a in aa}),temporal_coverage=WINDOW,
                evaluation_ref=evaluation,approval_status='APPROVED',exclusions=[NOTICE,'No normalized eligibility decision.'],
                freshness_policy=dict(max_age_days=FRESHNESS_DAYS,policy_ref=evaluation)))
            plans.append(dict(coverage_profile_id=pid,portions=[dict(portion_id=pid+f'-{i//50+1}',concept_ids=[cid],
                fact_ids=row_facts[i:i+50]) for i in range(0,len(row_facts),50)]))
            request=StructuredGroundingRequest(schema_version='structured-grounding/v1',release_id=rid,knowledge_space_id='hackathon',domain_id='immigration',
                topic_id='residence',concept_ids=[cid],intent='read-source-assertions',jurisdiction=scope,context={},
                as_of=BUILD_DATE,scope_mode='exact',max_evidence=5)
            requests.append(dict(tool='resolve',arguments=request.model_dump(exclude_none=True),source_url=d['source_url'],
                evidence_ids=row_evidence,expected_note='Full source evidence is addressable in batches of at most five IDs.'))
        if number%100==0: print(json.dumps(dict(pack=rid,documents=number,total=len(records),facts=len(facts))),flush=True)
    profiles,plans=merge_profiles(profiles,plans)
    catalog=seal_artifact(KnowledgeCatalog(identity=ref('expanded-catalog'),release_id=rid,
        entries=sorted(entries,key=lambda e:e['entry_id']),context_schemas=[schema],coverage_profiles=profiles,language_policy_ref=policy.identity))
    graph=seal_artifact(ResolutionGraph(identity=ref('expanded-graph'),release_id=rid,plans=plans))
    release=seal_artifact(KnowledgeRelease(identity=ref(rid),release_id=rid,created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        catalog_ref=catalog.identity,context_schema_refs=[schema.identity],language_policy_ref=policy.identity,
        snapshot_refs=[d.snapshot_ref for d in documents],normalized_document_refs=[d.identity for d in documents],
        evidence_refs=[e.identity for e in evidence],concept_graph_ref=graph.identity,fact_refs=[f.identity for f in facts],
        rule_refs=[],terminology_refs=[],projection_refs=[],index_refs=[],contract_schema_refs=[contract],
        provider_configuration_ref=provider,ranking_configuration_ref=ranking,evaluation_ref=evaluation))
    bundle=ReleaseBundle(release=release,catalog=catalog,language_policy=policy,graph=graph,documents=documents,
        evidence=evidence,facts=facts,rules=[],external_refs=external)
    validate_release(bundle)
    # One representative request for every jurisdiction and every source language.
    tested=set(); checks=[]
    profiles_by_concept={c:p for p in catalog.coverage_profiles for c in p.concept_ids}
    for request in requests:
        profile=profiles_by_concept[request['arguments']['concept_ids'][0]]
        key=(profile.jurisdiction.canton_code,tuple(profile.source_languages))
        if key not in tested:
            assessment=validate_request(request['arguments'],catalog,policy)
            if assessment.status!='READY': raise ValueError(str(assessment))
            tested.add(key); checks.append(dict(concept_ids=request['arguments']['concept_ids'],status=assessment.status))
    target=output/'release.json'
    target.write_text(bundle.model_dump_json()+'\n',encoding='utf-8',newline='\n')
    validate_release(ReleaseBundle.model_validate_json(target.read_text(encoding='utf-8')))
    write(output/'external-artifacts.json',files); write(output/'provenance.json',provenance)
    write(output/'mcp-requests.json',dict(executed=False,resolve=requests))
    report=dict(release_id=rid,release_file=str(target.relative_to(DEST)) if target.is_relative_to(DEST) else str(target),
        release_sha256=sha(target.read_bytes()),documents=len(documents),facts=len(facts),evidence=len(evidence),
        concepts=len(requests),coverage_profiles=len(profiles),languages=languages,validated=True,
        pure_preflight_checks=len(checks),app_calls=0,llm_calls=0)
    write(output/'validation.json',report)
    write(output/'mcp-client.json',{'mcpServers':{'residence-expanded':{'command':str(ROOT/'.venv/Scripts/python.exe'),
        'args':['-m','swisstip.mcp_server.server','--release',str(target),'--active-release-id',rid]}}})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,default=DEST)
    parser.add_argument('--intermediate',type=Path,default=INTERMEDIATE,help='Intermediate export (default: 2026-09-11 snapshot)')
    parser.add_argument('--semantic',type=Path,default=SEMANTIC,help='Semantic assertion directory (default: 2026-09-11 snapshot)')
    parser.add_argument('--release-id',help='Explicit release identity for a single part, or the base for multi-part builds')
    args=parser.parse_args()
    INTERMEDIATE=args.intermediate.resolve(); SEMANTIC=args.semantic.resolve()
    print(json.dumps(build(args.output.resolve(),args.release_id),indent=2))
