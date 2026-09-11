"""Stream every acquired response into lossless intermediate records for review.

This is source-text preparation, not completed semantic interpretation. No app,
network, database or model is invoked. Existing records are reused only when their
raw hash and extractor version still match the acquired snapshot.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import warnings
import io
import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader
from office_text import extract_openxml, extract_ole_word
from striprtf.striprtf import rtf_to_text

from audit_source_languages import OUT, ROOT, sha, write
from extract_intermediate import extract_html, attach_offsets, encoding, FORMAT

EXTRACTOR_VERSION = 'expanded-1.2.0'

DEST = ROOT / '.local/intermediate/hackathon-residence-all-languages-2026-09-11'


def extract_rtf(raw):
    text = rtf_to_text(raw.decode('latin-1'))
    return dict(blocks=[dict(kind='paragraph', text=p, heading_path=[],
                source_locator={'paragraph': n}, links=[])
                for n, p in enumerate(text.splitlines(), 1) if p.strip()],
                representation='rtf', decoding='striprtf 0.0.33', html_title=None,
                main_headings=[], language_declared=None, page_kind='rtf_document',
                warnings=['rtf_layout_and_embedded_objects_unverified'])


def language_hint(url):
    match = re.search(r'/(de|fr|it|en|rm|ar|sq|tr|uk|ru|es|pt)(?:/|[-_])', url, re.I)
    suffix = re.search(r'[-_](de|fr|it|en|rm|ar|sq|tr|uk|ru|es|pt|so|ta|ti|sr|hr|bs|pl|el)(?:\.pdf|[-_])', url, re.I)
    return suffix[1].lower() if suffix else match[1].lower() if match else None


def extract_pdf(raw):
    blocks, blank = [], []
    with pdfium.PdfDocument(raw) as pdf:
        page_count = len(pdf)
        for number in range(page_count):
            page = pdf[number]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_bounded().replace('\r\n','\n').strip()
                finally:
                    textpage.close()
            finally:
                page.close()
            if text:
                blocks.append(dict(kind='pdf_page',text=text,heading_path=[],source_locator={'page':number+1},links=[]))
            else:
                blank.append(number+1)
    # Retain native AcroForm metadata separately; do not pretend blank fields are answers.
    fields = []
    reader = PdfReader(io.BytesIO(raw))
    for name, field in (reader.get_fields() or {}).items():
        fields.append(dict(name=name,field_type=str(field.get('/FT','')),label=str(field.get('/TU','')),
                           value=str(field.get('/V','')),options=[str(x) for x in field.get('/Opt',[])]))
    return dict(blocks=blocks,pdf_page_count=page_count,pages_without_text=blank,form_fields=fields,
                html_title=None,main_headings=[],language_declared=None,page_kind='pdf_document',
                decoding='PDFium native embedded text',warnings=['pdf_layout_and_reading_order_unverified'] +
                (['some_pdf_pages_have_no_text_no_ocr_performed'] if blank else []))


def run(corpus, output, shard_index=0, shard_count=1, retry_failures=False, refresh_rtf=False, retrieved_after=None):
    output.mkdir(parents=True, exist_ok=True)
    (output/'documents').mkdir(exist_ok=True)
    pointers = sorted(corpus.glob('pages/*/latest.json'))
    index, unavailable, errors = [], [], []
    if retry_failures or refresh_rtf:
        previous_index=json.loads((output/f'index-part-{shard_index}.json').read_text(encoding='utf-8'))
        failed=[i for i in previous_index if i['status']=='extraction_failed' or
                (refresh_rtf and '.rtf' in i['source_url'].lower())]
        if not failed:
            print('No failed records to retry',flush=True)
            return
        pointers=sorted({corpus/json.loads((output/i['file']).read_text(encoding='utf-8'))['acquisition']['manifest_path'] for i in failed})
        selected={i['document_id'] for i in failed}
        index=[i for i in previous_index if i['document_id'] not in selected]
        unavailable=json.loads((output/f'unavailable-part-{shard_index}.json').read_text(encoding='utf-8'))
    groups, hashes = defaultdict(list), defaultdict(list)
    todo = []
    for pointer in pointers:
        manifest = json.loads(pointer.read_text(encoding='utf-8'))
        if not manifest.get('snapshots') and retrieved_after is None:
            unavailable.append(dict(source_url=manifest['url'],status=manifest['status'],error=manifest.get('error')))
        for snapshot in manifest.get('snapshots', []):
            # A subset export keeps only snapshots acquired at or after the given time.
            if retrieved_after is not None and snapshot.get('retrieved_at','') < retrieved_after:
                continue
            relative = snapshot['relative_path']
            identifier = 'doc-' + sha(relative.encode())[:20]
            if int(identifier[4:12],16) % shard_count != shard_index:
                continue
            todo.append((pointer, manifest, snapshot, identifier))
            hashes[snapshot['sha256']].append(identifier)
            groups[manifest.get('source_page_url', manifest['url'])].append(identifier)
    for number, (pointer, manifest, snapshot, identifier) in enumerate(todo, 1):
        target = output/'documents'/(identifier+'.json')
        relative = snapshot['relative_path']
        raw_path = (corpus/relative).resolve()
        if not raw_path.is_relative_to(corpus.resolve()):
            raise ValueError('Snapshot escapes acquisition directory')
        raw = raw_path.read_bytes()
        if sha(raw)!=snapshot['sha256'] or len(raw)!=snapshot['bytes_downloaded']:
            raise ValueError('Raw snapshot hash or size mismatch')
        document = None
        if target.exists():
            previous = json.loads(target.read_text(encoding='utf-8'))
            if (previous['acquisition']['raw_sha256']==snapshot['sha256'] and previous['extractor_version']==EXTRACTOR_VERSION
                    and previous['status']!='extraction_failed'
                    and not (raw.lstrip().startswith(b'{\\rtf') and previous['representation']!='rtf')
                    and not (b'window.CONTENT_ID' in raw and len(previous['content_text'])<300)):
                document = previous
        if document is None:
            source_url = manifest.get('source_page_url', manifest['url'])
            document = dict(schema_version=FORMAT, document_id=identifier, corpus_id=corpus.name,
                source_url=source_url, document_url=snapshot['final_url'], version_uri=manifest.get('version_uri'),
                source_registry=manifest.get('registry_entries',[]), catalogue_references=manifest.get('references',[]),
                discovery_provenance=manifest.get('discoveries',[]), extractor_version=EXTRACTOR_VERSION,
                acquisition=dict(path=relative,manifest_path=pointer.relative_to(corpus).as_posix(),
                    manifest_sha256=sha(pointer.read_bytes()),raw_sha256=sha(raw),bytes=len(raw),
                    retrieved_at=snapshot['retrieved_at'],requested_url=snapshot['requested_url'],
                    declared_content_type=snapshot['content_type'],review_flags=snapshot.get('review_flags',[])),
                representation_group='source-'+sha(source_url.encode())[:20],
                language_hint=manifest.get('language') or language_hint(snapshot['final_url']))
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    if raw[:1024].lstrip().startswith(b'%PDF-'):
                        document.update(extract_pdf(raw),representation='pdf')
                    elif raw.startswith(b'PK\x03\x04'):
                        document.update(extract_openxml(raw))
                    elif raw.lstrip().startswith(b'{\\rtf'):
                        document.update(extract_rtf(raw))
                    elif raw.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                        document.update(extract_ole_word(raw))
                    elif raw.startswith((b'\xff\xd8\xff',b'\x89PNG\r\n\x1a\n')):
                        with Image.open(io.BytesIO(raw)) as bitmap:
                            dimensions=list(bitmap.size)
                        document.update(blocks=[],representation='image',image_dimensions=dimensions,
                            html_title=None,main_headings=[],language_declared=None,page_kind='image_document',
                            decoding='Image metadata only; pixels retained in raw source',warnings=['image_requires_ocr'])
                    elif re.search(br'<(?:!doctype\s+html|html|head|body)\b',raw[:8192],re.I):
                        document.update(extract_html(raw,snapshot['final_url']),representation='html')
                    elif 'text/' in snapshot['content_type'] or 'json' in snapshot['content_type'] or 'xml' in snapshot['content_type']:
                        codec = encoding(raw)
                        document.update(blocks=[dict(kind='plain_text',text=raw.decode(codec),heading_path=[],
                            source_locator={'file':relative},links=[])],representation='text',decoding=codec,
                            html_title=None,main_headings=[],language_declared=None,page_kind='text_document',warnings=[])
                    else:
                        raise ValueError('Unsupported binary format; retained raw for format-specific extraction')
                document.setdefault('warnings',[]).extend(str(w.message) for w in caught)
                excluded = document['page_kind'] in {'application_shell','maintenance_page','error_page'}
                document.update(eligible_for_processing=bool(document['blocks']) and not excluded,
                    status='excluded_source_response' if excluded else 'extracted' if document['blocks'] else 'no_extractable_text',
                    exclusion_reasons=[document['page_kind']] if excluded else [])
            except Exception as exc:
                document.update(blocks=[],representation='unknown',warnings=[f'{type(exc).__name__}: {exc}'],
                    status='extraction_failed',eligible_for_processing=False,html_title=None,main_headings=[],language_declared=None)
            refs = document['catalogue_references']
            title=document.get('html_title')
            document['title'] = title if title and not title.startswith('input-') else (
                refs[0]['label'] if refs else next(iter(document['main_headings']),source_url))
            attach_offsets(document)
            document.update(identical_raw_snapshots=[x for x in hashes[snapshot['sha256']] if x!=identifier],
                html_counterparts=[], preferred_representation=document['eligible_for_processing'],
                semantic_status='pending-semantic-review')
            write(target,document)
        if document['title'].startswith('input-'):
            document['title']=next(iter(document.get('main_headings',[])),document['source_url'])
            write(target,document)
        index.append({k:document.get(k) for k in ['document_id','source_url','document_url','version_uri','title',
                     'representation','language_declared','language_hint','status','eligible_for_processing','semantic_status']} |
                     dict(file='documents/'+identifier+'.json',blocks=len(document['blocks']),
                          text_characters=len(document['content_text']),content_sha256=document['content_sha256'],
                          pdf_pages_without_text=document.get('pages_without_text',[])))
        if document['status']=='extraction_failed':
            errors.append(dict(document_id=identifier,source_url=document['source_url'],warnings=document['warnings']))
        if number%100==0:
            write(output/f'index-part-{shard_index}.json',index)
            print(json.dumps(dict(processed=number,total=len(todo),failures=len(errors))),flush=True)
    # Stream JSONL instead of accumulating all source texts in memory.
    with (output/f'documents-part-{shard_index}.jsonl').open('w',encoding='utf-8',newline='\n') as stream:
        for item in index:
            document=json.loads((output/item['file']).read_text(encoding='utf-8'))
            stream.write(json.dumps(document,ensure_ascii=False)+'\n')
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),acquisition_corpus=corpus.name,
        acquisition_manifest_count=len(pointers),documents=len(index),shard_index=shard_index,shard_count=shard_count,
        statuses=dict(Counter(i['status'] for i in index)),
        declared_languages=dict(Counter(i['language_declared'] or 'undeclared' for i in index)),
        blocks=sum(i['blocks'] for i in index),text_characters=sum(i['text_characters'] for i in index),
        documents_with_pdf_pages_without_text=sum(bool(i['pdf_pages_without_text']) for i in index),
        unavailable=len(unavailable),semantic_status='not-yet-semantically-curated',
        retrieved_after=retrieved_after,
        application_invoked=False,model_calls=0,network_calls=0,ocr_performed=False)
    for name,value in [('index',index),('summary',report),('unavailable',unavailable),('errors',errors)]:
        write(output/f'{name}-part-{shard_index}.json',value)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,default=OUT)
    parser.add_argument('--output',type=Path,default=DEST)
    parser.add_argument('--shard-index',type=int,default=0)
    parser.add_argument('--shard-count',type=int,default=1)
    parser.add_argument('--retry-failures',action='store_true')
    parser.add_argument('--refresh-rtf',action='store_true')
    parser.add_argument('--retrieved-after',help='Only snapshots retrieved at or after this ISO timestamp (subset export)')
    args=parser.parse_args()
    if not 0 <= args.shard_index < args.shard_count:
        parser.error('shard-index must be in [0, shard-count)')
    run(args.corpus.resolve(),args.output.resolve(),args.shard_index,args.shard_count,args.retry_failures,args.refresh_rtf,
        args.retrieved_after)
