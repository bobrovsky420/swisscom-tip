"""Extract attributed, original-language assertions with semantic annotations.

This preserves source assertions and their complete section context. It does not
infer executable eligibility decisions or silently translate the source text.
Language identification uses a local statistical classifier, never an LLM.
"""
from collections import Counter
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata

from lingua import LanguageDetectorBuilder
from audit_source_languages import ROOT, sha, write

SOURCE = ROOT/'.local/intermediate/hackathon-residence-all-languages-2026-09-11'
OUTPUT = ROOT/'.local/semantic/hackathon-residence-all-languages-2026-09-11'
TOPICS = {
    'family':r'famil|nachzug|regroupement|ricongiung|reunif|separat|scheidung|divorc',
    'settlement':r'niederlass|etablissement|settlement|domicilio|permissiun da domicil',
    'employment':r'erwerb|arbeitsbewill|work.permit|gainful|emploi|travail|lavor|lavur',
    'study-and-nonworking':r'stud|etudi|rentner|retire|pension|sans.activite|ohne.erwerb',
    'entry-and-visas':r'einreise|entry|entree|entrata|visa|visum|visto',
    'registration-and-mobility':r'anmeld|einwohner|register|registration|registraz|annonce|kantonswechsel|changement.de.canton',
    'integration-and-language':r'integrat|sprach|langue|language|lingu|lingua',
    'fees-and-financial-evidence':r'gebuhr|emolument|\bfees?\b|taxe|tassa|finanziell|moyens.financi|financial.means',
    'protection-and-provisional-admission':r'asyl|schutzstatus|vorlaufig|provisoire|provisional|protection|protezione',
    'renewal-loss-and-departure':r'verlanger|renew|rinnovo|renouvel|abmeld|ausreise|depart|widerruf|revoc|verlust|perte|perd[iu]',
    'permit-types-and-procedures':r'aufenthalt|bewilligung|ausweis|permis|permesso|permissiun|residen|sejour|soggiorno|dimora',
    'forms-and-documents':r'formular|formulaire|modul|checklist|merkblatt|application.form|document',
}
LANGUAGE_NAMES = {
    'arabisch':'ar','arabic':'ar','arabe':'ar','shqip':'sq','albanisch':'sq','albanais':'sq',
    'russisch':'ru','russian':'ru','russe':'ru','ukrainisch':'uk','ukrainian':'uk','ukrayina':'uk',
    'portugues':'pt','portugais':'pt','portugiesisch':'pt','espanol':'es','espagnol':'es','spanisch':'es',
    'turkce':'tr','turc':'tr','tuerkisch':'tr','turkisch':'tr','somali':'so','somalisch':'so',
    'tamil':'ta','tamoul':'ta','tigrinya':'ti','tigrigna':'ti','kurdi':'ku','kurdish':'ku',
    'serbo-croate':'hbs','serbokroatisch':'hbs','griechisch':'el','grec':'el',
    'rumantsch':'rm','romansh':'rm','rumanisch':'ro','roumain':'ro',
    'vietnamesisch':'vi','vietnamese':'vi','tschechisch':'cs','slowakisch':'sk',
    'slowenisch':'sl','kroatisch':'hr','bosnisch':'bs','serbisch':'sr',
    'ungarisch':'hu','finnisch':'fi','niederlandisch':'nl','polnisch':'pl',
    'persisch':'fa','farsi':'fa','chinesisch':'zh','japanisch':'ja',
    'kurdisch':'ku','tamilisch':'ta','serbocroate':'hbs',
    'anglais':'en','english':'en','francais':'fr','deutsch':'de','italiano':'it',
}
CONDITIONAL = re.compile(r'\b(?:wenn|falls|sofern|ausser|außer|ausgenommen|soweit|si|sauf|exception|unless|if|provided|except|se|salvo|eccetto|qualora|sche|если|кроме)\b',re.I)
PERMIT = re.compile(r'\b(?:Ausweis|Bewilligung|permit|permis|permesso|permissiun)\s*[-:]?\s*(Ci|[LBCGFNS])\b',re.I)
NUMBER_UNIT = re.compile(r'\b\d+(?:[.,]\d+)?\s*(?:Tage?n?|Wochen?|Monate?n?|Jahre?n?|jours?|semaines?|mois|ans?|days?|weeks?|months?|years?|giorni|settimane|mesi|anni|Stunden?|heures?|hours?|ore|%|CHF|Fr\.)\b',re.I)
DATE = re.compile(r'\b(?:\d{1,2}[./]\d{1,2}[./](?:19|20)\d{2}|(?:19|20)\d{2}-\d{2}-\d{2})\b')


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))


def substantive_blocks(document):
    blocks=document['blocks']
    has_main=any(b.get('source_locator',{}).get('in_main') for b in blocks)
    for block in blocks:
        loc=block.get('source_locator',{})
        contact=block['kind']=='address' or any(l.get('href','').startswith(('mailto:','tel:')) for l in block.get('links',[]))
        if block['kind']=='control':
            continue
        if not contact and (loc.get('region') in {'nav','header','footer'} or
                            set(loc.get('aria_roles',[])) & {'navigation','banner','contentinfo'}):
            continue
        if has_main and not loc.get('in_main') and not contact:
            continue
        # Link-only navigation is recorded in the acquisition graph, not turned
        # into a legal assertion. Short unlinked checklist items remain intact.
        if block['kind']=='list_item' and block.get('links'):
            labels=' '.join(l.get('text','') for l in block['links'])
            if fold(labels).strip()==fold(block['text']).strip():
                continue
        yield block


def sections(document,limit=10000):
    group=[]
    key=None
    def emit(items):
        if not items or all(b['kind']=='heading' for b in items):
            return []
        start,end=items[0]['start'],items[-1]['end']
        ranges=[]
        while end-start>limit:
            stop=document['content_text'].rfind('\n',start+limit//2,start+limit)
            if stop<=start:
                stop=document['content_text'].rfind(' ',start+limit//2,start+limit)
            if stop<=start:
                stop=start+limit
            ranges.append((start,stop,items))
            start=stop
        if end>start:
            ranges.append((start,end,items))
        return ranges
    for block in substantive_blocks(document):
        loc=block.get('source_locator',{})
        next_key=(loc.get('article_id') or tuple(block.get('heading_path',[])),
                  loc.get('page'),bool(loc.get('is_footnote')),loc.get('part'))
        if group and (next_key!=key or block['end']-group[0]['start']>limit):
            yield from emit(group)
            group=[]
        group.append(block)
        key=next_key
    yield from emit(group)


def identify_language(document,sample,detector,cached=None):
    declared=document.get('language_declared')
    hint=(declared or document.get('language_hint') or '').replace('_','-').lower().split('-')[0]
    published_path=fold(document['source_url'])
    named=next((tag for name,tag in LANGUAGE_NAMES.items()
                if re.search(r'(?<![a-z])'+re.escape(name)+r'(?![a-z])',published_path)),None)
    if named:
        hint=named
    if cached is not None:
        detected,confidence=cached['detected_language'],cached['confidence']
    else:
        values=detector.compute_language_confidence_values(sample[:3500]) if sample.strip() else []
        detected=values[0].language.iso_code_639_1.name.lower() if values else None
        confidence=values[0].value if values else 0.0
    flags=[]
    if hint and detected and hint!=detected:
        flags.append('declared_or_path_language_differs_from_statistical_detection')
    # Publisher metadata takes precedence over unreviewed statistical guesses.
    if hint:
        effective,method=hint,'published-language-metadata'
    elif detected and confidence>=0.90 and len(sample)>100:
        effective,method=detected,'local-lingua-statistical-detection'
    else:
        effective,method=hint or None,'source-language-metadata' if hint else 'undetermined'
    if method=='local-lingua-statistical-detection':
        flags.append('inferred_language_requires_review')
    return dict(declared_language=declared,published_path_language=named,detected_language=detected,
                confidence=confidence,effective_confidence=confidence if method=='local-lingua-statistical-detection' else 0.0,
                effective_language=effective,method=method,review_flags=flags)


def annotate(text,heading,source_url):
    context=fold(heading)
    body=fold(text)
    scored=[(3*len(re.findall(pattern,context))+len(re.findall(pattern,body)),name)
            for name,pattern in TOPICS.items()]
    scored.sort(reverse=True)
    topics=[name for count,name in scored if count][:4]
    if '/eli/cc/' in source_url:
        topics=['legal-basis',*topics]
    sentences=re.split(r'(?<=[.!?;])\s+|\n\n',text)
    return dict(topics=topics or ['source-context'],
        permit_mentions=[dict(text=m.group(),permit_code=m.group(1).upper(),start=m.start(),end=m.end()) for m in PERMIT.finditer(text)],
        duration_or_amount_mentions=[dict(text=m.group(),start=m.start(),end=m.end()) for m in NUMBER_UNIT.finditer(text)],
        date_mentions=[dict(text=m.group(),start=m.start(),end=m.end()) for m in DATE.finditer(text)],
        condition_or_exception_sentences=[s for s in sentences if CONDITIONAL.search(s)],
        logical_conditions_normalized=False,eligibility_decision_computed=False)


def main(shard_index=0,shard_count=1,reuse_detection=False):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    indexes={i['document_id']:i for path in SOURCE.glob('index-part-*.json')
             for i in json.loads(path.read_text(encoding='utf-8'))}
    indexes={k:v for k,v in indexes.items() if int(k[4:12],16)%shard_count==shard_index}
    suffix=f'-part-{shard_index}' if shard_count>1 else ''
    cached_assertions={}; cached_documents={}
    if reuse_detection:
        with (OUTPUT/('assertions'+suffix+'.jsonl')).open(encoding='utf-8') as old:
            for line in old:
                item=json.loads(line)
                cached_assertions[item['assertion_id']]=item['language']
        cached_documents={d['document_id']:d.get('language') for d in
            json.loads((OUTPUT/('source-disposition'+suffix+'.json')).read_text(encoding='utf-8'))}
    detector=LanguageDetectorBuilder.from_all_languages().build()
    counts=Counter()
    dispositions=[]
    seen={}
    with (OUTPUT/('assertions'+suffix+'.jsonl')).open('w',encoding='utf-8',newline='\n') as stream:
        for number,item in enumerate(sorted(indexes.values(),key=lambda i:i['document_id']),1):
            document=json.loads((SOURCE/item['file']).read_text(encoding='utf-8'))
            if not document['eligible_for_processing']:
                dispositions.append(dict(document_id=document['document_id'],source_url=document['source_url'],
                    status=document['status'],assertions=0))
                continue
            if sha(document['content_text'].encode())!=document['content_sha256']:
                raise ValueError('Normalized source text changed')
            sample='\n'.join(b['text'] for b in substantive_blocks(document))
            language=identify_language(document,sample,detector,
                cached_documents.get(document['document_id']) if document['representation']!='rtf' else None)
            units=0
            for start,end,blocks in sections(document):
                quote=document['content_text'][start:end]
                if not quote.strip():
                    continue
                loc=blocks[0].get('source_locator',{})
                heading=' / '.join(blocks[0].get('heading_path',[])) or document['title']
                identifier='assertion-'+sha((document['document_id']+':'+str(start)+':'+str(end)).encode())[:24]
                semantic=annotate(quote,heading,document['source_url'])
                section_language=language
                if len(quote)>100:
                    section_language=identify_language(document,quote,detector,
                        cached_assertions.get(identifier) if document['representation']!='rtf' else None)
                duplicate_key=(document['content_sha256'],start,end,document['source_url'])
                record=dict(schema_version='swisstip.source-assertion/v1',assertion_id=identifier,
                    semantic_relation='source-section-states',document_id=document['document_id'],
                    source_url=document['source_url'],document_url=document['document_url'],
                    title=document['title'],heading=heading,version_uri=document.get('version_uri'),
                    language=section_language,original_text=quote,start_offset=start,end_offset=end,
                    source_block_ids=[b['block_id'] for b in blocks],source_locator=loc,
                    assertion_kind='publication-history' if loc.get('is_footnote') else 'source-statement',
                    semantic_annotations=semantic,identical_source_assertion=seen.get(duplicate_key),
                    source_quality=dict(extraction_warnings=document.get('warnings',[]),
                        unexpected_control_characters=sum(ord(c)<32 and c not in '\t\n\r' for c in quote),
                        private_use_characters=sum(0xE000<=ord(c)<=0xF8FF or 0xF0000<=ord(c)<=0xFFFFD or 0x100000<=ord(c)<=0x10FFFD for c in quote)),
                    review_status='automatically-derived-unreviewed',independent_legal_review=False)
                seen.setdefault(duplicate_key,identifier)
                stream.write(json.dumps(record,ensure_ascii=False)+'\n')
                counts['assertions']+=1
                counts['language:'+str(section_language['effective_language'])]+=1
                units+=1
            dispositions.append(dict(document_id=document['document_id'],source_url=document['source_url'],
                status='assertions-extracted',assertions=units,language=language))
            if number%100==0:
                print(json.dumps(dict(documents=number,total=len(indexes),assertions=counts['assertions'])),flush=True)
    write(OUTPUT/('source-disposition'+suffix+'.json'),dispositions)
    write(OUTPUT/('summary'+suffix+'.json'),dict(generated_at=datetime.now(timezone.utc).isoformat(),counts=dict(counts),
        documents=len(indexes),method='Original-language source assertions with structural and rule-based semantic annotations',
        llm_calls=0,application_invoked=False,local_statistical_language_detector='lingua-language-detector 2.2.0',
        language_detector_accuracy='high',shard_index=shard_index,shard_count=shard_count,
        language_assignment_policy='publisher-metadata-first; statistical inference unreviewed',
        assertions_sha256=sha((OUTPUT/('assertions'+suffix+'.jsonl')).read_bytes()),
        executable_eligibility_rules=False,semantic_quality_independently_reviewed=False,
        completeness='Acquired native-text records only; acquisition frontier and OCR review remain separate.'))
    print(json.dumps(dict(counts),indent=2),flush=True)


def merge(shard_count):
    counts=Counter(); dispositions=[]; reports=[]
    with (OUTPUT/'assertions.jsonl.tmp').open('wb') as stream:
        for n in range(shard_count):
            report=json.loads((OUTPUT/f'summary-part-{n}.json').read_text(encoding='utf-8'))
            raw=(OUTPUT/f'assertions-part-{n}.jsonl').read_bytes()
            if report.get('shard_count')!=shard_count or sha(raw)!=report['assertions_sha256']:
                raise ValueError('Incomplete or mismatched assertion shard')
            stream.write(raw); counts.update(report['counts']); reports.append(report)
            dispositions.extend(json.loads((OUTPUT/f'source-disposition-part-{n}.json').read_text(encoding='utf-8')))
    if len({d['document_id'] for d in dispositions})!=len(dispositions):
        raise ValueError('Duplicate source documents across assertion shards')
    expected={i['document_id'] for path in SOURCE.glob('index-part-*.json')
              for i in json.loads(path.read_text(encoding='utf-8'))}
    if {d['document_id'] for d in dispositions}!=expected:
        raise ValueError('Assertion shard dispositions do not cover the complete current intermediate index')
    (OUTPUT/'assertions.jsonl.tmp').replace(OUTPUT/'assertions.jsonl')
    write(OUTPUT/'source-disposition.json',dispositions)
    report=reports[0]|dict(generated_at=datetime.now(timezone.utc).isoformat(),counts=dict(counts),
        documents=sum(r['documents'] for r in reports),shard_index=None,
        assertions_sha256=sha((OUTPUT/'assertions.jsonl').read_bytes()))
    write(OUTPUT/'summary.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard-index',type=int,default=0); parser.add_argument('--shard-count',type=int,default=1)
    parser.add_argument('--reuse-detection',action='store_true')
    parser.add_argument('--merge',action='store_true'); args=parser.parse_args()
    if not 0<=args.shard_index<args.shard_count: parser.error('Invalid shard index/count')
    merge(args.shard_count) if args.merge else main(args.shard_index,args.shard_count,args.reuse_detection)
