"""Validate text retention and write source/language coverage ledgers locally."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

from audit_source_languages import ROOT, OUT, sha, write
from build_expanded_pack import jurisdiction, CANTONS

DEST=ROOT/'.local/intermediate/hackathon-residence-all-languages-2026-09-11'
SEMANTIC=ROOT/'.local/semantic/hackathon-residence-all-languages-2026-09-11'


def main():
    state=json.loads((OUT/'audit-state.json').read_text(encoding='utf-8'))
    index={i['document_id']:i for p in DEST.glob('index-part-*.json') for i in json.loads(p.read_text(encoding='utf-8'))}
    statuses=Counter(); languages=Counter(); cantons=defaultdict(Counter); warnings=[]; validated=0
    by_url=defaultdict(list)
    for i in index.values():
        d=json.loads((DEST/i['file']).read_text(encoding='utf-8'))
        if sha(d['content_text'].encode())!=d['content_sha256']:
            raise ValueError('Normalized hash mismatch: '+d['document_id'])
        for b in d['blocks']:
            if d['content_text'][b['start']:b['end']]!=b['text']:
                raise ValueError('Block span mismatch: '+b['block_id'])
        validated+=1; statuses[d['status']]+=1
        lang=d.get('language_declared') or d.get('language_hint') or 'undeclared'
        languages[lang]+=1
        code=jurisdiction(d['source_url']).get('canton_code','CH')
        cantons[code][d['status']]+=1
        by_url[d['acquisition']['requested_url']].append(d['document_id'])
        if d.get('warnings') or d.get('pages_without_text'):
            warnings.append(dict(document_id=d['document_id'],source_url=d['source_url'],status=d['status'],
                warnings=d.get('warnings',[]),pdf_pages_without_native_text=d.get('pages_without_text',[])))
    write(DEST/'index.json',sorted(index.values(),key=lambda i:i['document_id']))
    write(DEST/'text-quality-review.json',warnings)
    write(DEST/'validation.json',dict(validated_at=datetime.now(timezone.utc).isoformat(),documents=validated,
        checks=['Every normalized document hash','Every block codepoint span'],statuses=dict(statuses),
        characters=sum(i['text_characters'] for i in index.values()),blocks=sum(i['blocks'] for i in index.values()),
        source_metadata_languages=dict(languages),app_calls=0,llm_calls=0))
    versions=[]; deferred={}; rows=[]
    for url,target in sorted(state['targets'].items()):
        a=state['audits'].get(url,{})
        advertised=sorted({d['advertised_language'] for d in target['discoveries'] if d.get('advertised_language')})
        rows.append(dict(url=url,download_status=target['status'],download_error=target.get('last_error'),
            advertised_languages=advertised,declared_language=a.get('declared_language'),
            soft_error_page=a.get('soft_error_page'),document_ids=by_url.get(url,[]),
            acquisition_without_intermediate=target['status']=='saved' and not by_url.get(url),
            jurisdiction=jurisdiction(url),body_fingerprint=a.get('substantive_text_sha256')))
        for link in a.get('language_links',[]):
            other=state['audits'].get(link['url'],{})
            fingerprint=a.get('substantive_text_sha256')
            versions.append(dict(source_url=url,published_language_url=link['url'],
                advertised_language=link.get('advertised_language'),
                download_status=state['targets'].get(link['url'],{}).get('status','not-identified'),
                target_declared_language=other.get('declared_language'),target_soft_error_page=other.get('soft_error_page'),
                same_substantive_text=bool(fingerprint and fingerprint==other.get('substantive_text_sha256')),
                translation_equivalence_reviewed=False))
        for link in a.get('deferred_links',[]):
            if link['url'] not in state['targets']:
                deferred.setdefault(link['url'],link)
    ocr_dir=ROOT/'.local/ocr'/OUT.name
    ocr=[]
    for p in (ocr_dir/'results').glob('*.json'):
        r=json.loads(p.read_text(encoding='utf-8'))
        ocr.append(dict(result=p.relative_to(ROOT).as_posix(),status=r['status'],
            has_recognized_text=bool(r.get('text','').strip()),document_ids=r['job']['document_ids'],
            page=r['job']['page_number'],exact_language_recognizer_available=r['job']['exact_language_recognizer_available'],
            quality_reviewed=r.get('quality_reviewed',False)))
    write(DEST/'ocr-disposition.json',ocr)
    write(OUT/'source-coverage.json',rows)
    write(OUT/'language-version-audit.json',versions)
    write(OUT/'deferred-scope-review.json',list(deferred.values()))
    counts=Counter(t['status'] for t in state['targets'].values())
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),scope='Residence permits in Switzerland, all published source languages',
        acquisition=dict(identified=len(rows),statuses=dict(counts),intermediate_documents=len(index),
            saved_without_intermediate=sum(r['acquisition_without_intermediate'] for r in rows),
            deferred_unique_links_needing_scope_disposition=len(deferred)),
        canton_source_responses={c:dict(cantons.get('CH-'+c,{})) for c in CANTONS},
        language_links_checked=len(versions),language_links_with_identical_body=sum(v['same_substantive_text'] for v in versions),
        language_translation_equivalence_reviewed=False,ocr=dict(results=len(ocr),with_recognized_text=sum(r['has_recognized_text'] for r in ocr),quality_reviewed=False),
        semantic_method='Extractive original-language source assertions with structural and keyword annotations',
        semantic_interpretation_complete=False,exhaustive_corpus_verified=False,
        application_calls=0,llm_calls=0,
        limitations=['Discovery includes contextual and historical material needing domain relevance review.',
            'HTTP failures, soft error pages and application shells are not usable source evidence.',
            'Published language links do not prove substantive translations; identical bodies and declarations are audit signals.',
            'OCR, mixed-language sections, source layout and legal qualification require review.',
            'Source assertions are not independently curated executable eligibility rules.'])
    semantic_summary=SEMANTIC/'summary.json'
    if semantic_summary.exists():
        summary=json.loads(semantic_summary.read_text(encoding='utf-8'))
        if summary.get('language_detector_accuracy')=='high' and summary.get('assertions_sha256')==sha((SEMANTIC/'assertions.jsonl').read_bytes()):
            report['source_assertion_export']=summary
            methods=defaultdict(Counter); flags=Counter(); quality=[]
            with (SEMANTIC/'assertions.jsonl').open(encoding='utf-8') as stream:
                for line in stream:
                    a=json.loads(line); lang=a['language']
                    methods[lang['method']][str(lang['effective_language'])]+=1
                    flags.update(lang['review_flags'])
                    q=a.get('source_quality',{})
                    if q.get('private_use_characters') or q.get('unexpected_control_characters'):
                        quality.append(dict(assertion_id=a['assertion_id'],source_url=a['source_url'],quality=q))
            report['assertion_language_audit']=dict(assignments_by_method=dict(methods),review_flags=dict(flags),
                independently_verified=False)
            write(SEMANTIC/'language-assignment-audit.json',report['assertion_language_audit'])
            write(SEMANTIC/'text-quality-review.json',quality)
    collection=ROOT/'.local/mvp/residence-all-languages-2026-09-11-v1/collection.json'
    if collection.exists():
        report['serving_fixture_collection']=json.loads(collection.read_text(encoding='utf-8'))
    write(OUT/'coverage-report.json',report)
    detail=''
    if 'source_assertion_export' in report:
        detail+=f"Source assertion sections: {report['source_assertion_export']['counts']['assertions']}. These retain source statements, not normalized eligibility decisions.\n\n"
        tags=sorted(report['assertion_language_audit']['assignments_by_method'].get('published-language-metadata',{}))
        detail+='Publisher language hints in the assertion export: '+', '.join(tags)+'. Classifier-only assignments are separately flagged; translation equivalence is unverified.\n\n'
    detail+=f"Published language links checked: {len(versions)}. Deferred links needing scope review: {len(deferred)}. OCR jobs: {len(ocr)}, with recognized text: {sum(r['has_recognized_text'] for r in ocr)}; OCR quality remains unreviewed.\n\n"
    if 'serving_fixture_collection' in report:
        c=report['serving_fixture_collection']
        detail+=f"Serving collection: {len(c['parts'])} validated parts, {sum(p['facts'] for p in c['parts'])} quotation fragments, {c['unresolved_assertions']} unresolved/excluded assertions retained in the intermediate ledger.\n\n"
    table='\n'.join('| '+c+' | '+str(cantons.get('CH-'+c,{}).get('extracted',0))+' |' for c in CANTONS)
    (ROOT/'config/catalogs/hackathon.sources.coverage.md').write_text('# Expanded corpus coverage checkpoint\n\n'
        'Status: incomplete. This report does not certify exhaustive discovery or complete semantic interpretation.\n\n'
        f"Identified URLs: {len(rows)}. Download states: {dict(counts)}. Intermediate documents: {len(index)}.\n\n"
        +detail+
        'Cantonal counts include contextual material and are not counts of reviewed residence-permit rules.\n\n'
        '| Canton | Responses with extracted native text |\n| --- | ---: |\n'+table+'\n\n'
        'Detailed local ledgers: `.local/corpora/'+OUT.name+'/coverage-report.json`, `source-coverage.json`, '
        '`language-version-audit.json`, and `deferred-scope-review.json`. The expanded JSON catalogue lists every identified URL.\n',
        encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
