"""Save manually verified public source links without mutating a running crawl."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from urllib.parse import urlsplit
from audit_source_languages import OUT, write, download, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=Path,required=True)
    args=parser.parse_args()
    seeds=json.loads(args.seeds.read_text(encoding='utf-8'))
    hosts=sorted({urlsplit(s['url']).hostname for s in seeds})
    additions=json.loads((OUT/'additional-seeds.json').read_text(encoding='utf-8')) if (OUT/'additional-seeds.json').exists() else []
    targets=[]
    for seed in seeds:
        if seed not in additions: additions.append(seed)
        target=dict(url=seed['url'],url_id=sha(seed['url'].encode()),references=[],registry_entries=[],discoveries=[seed])
        pointer=OUT/'pages'/target['url_id']/'latest.json'
        if pointer.exists() and json.loads(pointer.read_text(encoding='utf-8')).get('status')=='saved': continue
        targets.append(target)
    write(OUT/'additional-seeds.json',additions)
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(download,t,hosts):t for t in targets}
        for future in as_completed(futures):
            manifest,audit=future.result()
            results.append(dict(url=manifest['url'],status=manifest['status'],audit=audit,error=manifest.get('error')))
            if audit:
                for link in audit['topic_links']+audit['language_links']:
                    if link not in additions: additions.append(link)
            print(json.dumps(dict(url=manifest['url'],status=manifest['status'])),flush=True)
    write(OUT/'additional-seeds.json',additions)
    write(OUT/(args.seeds.stem+'-results.json'),results)


if __name__=='__main__': main()
