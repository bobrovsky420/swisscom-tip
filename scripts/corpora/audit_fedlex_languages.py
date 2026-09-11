"""Resolve every published language/HTML/PDF expression of identified Fedlex laws.

Standalone public metadata GET requests only; no application or model invocation.
"""
import json
import re
from urllib.parse import urlencode, urlsplit
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy

from audit_source_languages import OLD, OUT, write, now, sha, download


def main():
    plan = json.loads((OLD / 'plan.json').read_text(encoding='utf-8'))
    expanded = json.loads((OUT/'audit-state.json').read_text(encoding='utf-8'))
    redirects=[]
    for t in expanded['targets'].values():
        if urlsplit(t['url']).hostname=='www.admin.ch' and ('/opc/' in t['url'] or '/ch/' in t['url']):
            pointer=OUT/'pages'/t['url_id']/'latest.json'
            if pointer.exists():
                manifest=json.loads(pointer.read_text(encoding='utf-8'))
                for snapshot in manifest.get('snapshots',[]):
                    if 'www.fedlex.admin.ch/eli/cc/' in snapshot['final_url']:
                        redirects.append(t|{'url':snapshot['final_url']})
    targets = [t for t in [*plan['targets'], *expanded['targets'].values(), *redirects]
               if urlsplit(t['url']).hostname == 'www.fedlex.admin.ch' and '/eli/cc/' in t['url']]
    cached = {r['work']:r for r in json.loads((OUT/'fedlex-language-audit.json').read_text(encoding='utf-8'))} if (OUT/'fedlex-language-audit.json').exists() else {}
    records = []
    seen = set()
    for target in targets:
        path = re.split(r'/(?:de|fr|it|en|rm)(?:/|$)', urlsplit(target['url']).path)[0].rstrip('/')
        path = re.sub(r'/[0-9]{8}$','',path)
        work = 'https://fedlex.data.admin.ch' + path
        if work in seen:
            continue
        seen.add(work)
        if work in cached and cached[work]['status'] == 'resolved':
            records.append(cached[work])
            continue
        query = f'''PREFIX j: <http://data.legilux.public.lu/resource/ontology/jolux#>
SELECT DISTINCT ?version ?expression ?manifestation ?file WHERE {{
 ?version j:isMemberOf <{work}> .
 FILTER(REGEX(STR(?version), "/[0-9]{{8}}$"))
 FILTER(STR(?version) <= "{work}/20260911")
 ?version j:isRealizedBy ?expression .
 ?expression j:isEmbodiedBy ?manifestation .
 FILTER(STRENDS(STR(?manifestation), "/html") || STRENDS(STR(?manifestation), "/pdf-a"))
 ?manifestation j:isExemplifiedBy ?file .
}}'''
        endpoint = 'https://fedlex.data.admin.ch/sparqlendpoint?' + urlencode({'query':query, 'format':'application/sparql-results+json'})
        record = dict(source_url=target['url'], work=work, checked_at=now(), query=query, references=target.get('references',[]),
                      registry_entries=target.get('registry_entries',[]))
        try:
            with urllib.request.urlopen(endpoint, timeout=60) as response:
                data = json.load(response)
            record['metadata'] = data
            candidates = [dict(url=row['file']['value'], version_uri=row['version']['value'],
                language=row['expression']['value'].rsplit('/',1)[-1],
                representation=row['manifestation']['value'].rsplit('/',1)[-1]) for row in data['results']['bindings']]
            latest = {language:max(d['version_uri'] for d in candidates if d['language']==language)
                      for language in {d['language'] for d in candidates}}
            record['latest_version_by_language'] = latest
            record['documents'] = [d for d in candidates if d['version_uri']==latest[d['language']]]
            record['selection_policy'] = 'Latest available version per published language as of 2026-09-11; translations can lag.'
            record['status'] = 'resolved' if record['documents'] else 'no-expression-found'
        except Exception as exc:
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        records.append(record)
        write(OUT / 'fedlex-language-audit.json', records)
        print(json.dumps(dict(work=work, status=record['status'], documents=len(record.get('documents',[])))), flush=True)
    tasks = []
    for record in records:
        for document in record.get('documents', []):
            registry = deepcopy(record['registry_entries'])
            for entry in registry:
                entry['definition']['language'] = document['language']
                entry['definition']['source_id'] += '-' + document['language']
            target = dict(url=document['url'], url_id=sha(document['url'].encode()),
                          references=record['references'], registry_entries=registry,
                          discoveries=[dict(reason='fedlex-published-expression', source_url=record['source_url'],
                                            version_uri=document['version_uri'], advertised_language=document['language'])])
            tasks.append((target, document, record))
    write(OUT / 'fedlex-language-audit.json', records)
    pending=[]
    for target,document,record in tasks:
        pointer=OUT/'pages'/target['url_id']/'latest.json'
        if pointer.exists() and json.loads(pointer.read_text(encoding='utf-8')).get('status')=='saved':
            continue
        pending.append((target,document,record))
    print(json.dumps(dict(works=len(records),representations=len(tasks),pending=len(pending))),flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download,t,['fedlex.data.admin.ch']):(t,d,r) for t,d,r in pending}
        for future in as_completed(futures):
            target, document, record = futures[future]
            manifest, _ = future.result()
            manifest.update(language=document['language'], version_uri=document['version_uri'],
                            source_page_url=record['work'].replace('fedlex.data.admin.ch','www.fedlex.admin.ch') + '/' + document['language'])
            write(OUT/'pages'/target['url_id']/'latest.json', manifest)
            print(json.dumps(dict(document=document['language']+' '+document['representation'],status=manifest['status'])), flush=True)


if __name__ == '__main__':
    main()
