"""Render textless PDF pages for local Windows OCR; preserve raw PDFs unchanged."""
import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image
from audit_source_languages import ROOT, OUT, write, sha


def main():
    intermediate=ROOT/'.local/intermediate/hackathon-residence-all-languages-2026-09-11'
    output=ROOT/'.local/ocr/hackathon-residence-all-languages-2026-09-11'
    (output/'images').mkdir(parents=True,exist_ok=True)
    (output/'results').mkdir(exist_ok=True)
    jobs={}
    for index_file in intermediate.glob('index-part-*.json'):
        for item in json.loads(index_file.read_text(encoding='utf-8')):
            if item.get('representation')=='image':
                doc=json.loads((intermediate/item['file']).read_text(encoding='utf-8'))
                key=doc['acquisition']['raw_sha256']+'-image'
                if key in jobs:
                    jobs[key]['document_ids'].append(doc['document_id'])
                    continue
                original=OUT/doc['acquisition']['path']
                if sha(original.read_bytes())!=doc['acquisition']['raw_sha256']:
                    raise ValueError('Raw image changed')
                image=output/'images'/(key+'.png'); result=output/'results'/(key+'.json')
                with Image.open(original) as bitmap:
                    scale=min(1,3500/max(bitmap.size))
                    if not image.exists():
                        bitmap.thumbnail((3500,3500));bitmap.convert('RGB').save(image)
                jobs[key]=dict(key=key,image=str(image),output=str(result),document_ids=[doc['document_id']],
                    raw_sha256=doc['acquisition']['raw_sha256'],page_number=1,source_type='image',scale=scale,
                    source_language_hint=doc.get('language_hint'),recognizer_language='de-DE',
                    exact_language_recognizer_available=False)
                continue
            pages=item.get('pdf_pages_without_text') or []
            if not pages:
                continue
            doc=json.loads((intermediate/item['file']).read_text(encoding='utf-8'))
            raw=(OUT/doc['acquisition']['path']).read_bytes()
            if sha(raw)!=doc['acquisition']['raw_sha256']:
                raise ValueError('Raw PDF changed')
            with pdfium.PdfDocument(raw) as pdf:
                for page_number in pages:
                    key=doc['acquisition']['raw_sha256']+f'-p{page_number:05d}'
                    if key in jobs:
                        jobs[key]['document_ids'].append(doc['document_id'])
                        continue
                    image=output/'images'/(key+'.png')
                    result=output/'results'/(key+'.json')
                    page=pdf[page_number-1]
                    try:
                        scale=min(2.5,3500/max(page.get_size()))
                        if not image.exists() and not result.exists():
                            bitmap=page.render(scale=scale)
                            try:
                                bitmap.to_pil().save(image)
                            finally:
                                bitmap.close()
                    finally:
                        page.close()
                    hint=(doc.get('language_declared') or doc.get('language_hint') or '').lower().split('-')[0]
                    engine='ru' if hint=='ru' else 'de-DE' if hint=='de' else 'en-GB'
                    jobs[key]=dict(key=key,image=str(image),output=str(result),document_ids=[doc['document_id']],
                        raw_sha256=sha(raw),page_number=page_number,scale=scale,source_language_hint=hint,
                        recognizer_language=engine,exact_language_recognizer_available=hint in {'de','en','ru'})
    write(output/'jobs.json',list(jobs.values()))
    print(json.dumps(dict(unique_pages=len(jobs),pending=sum(not Path(j['output']).exists() for j in jobs.values()))),flush=True)


if __name__=='__main__':
    main()
