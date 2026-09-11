"""Capture public JavaScript page content with an isolated headless Edge profile.

No SwissTIP application, existing browser profile, login, form submission or LLM
is used. Saved bytes are explicitly labelled rendered DOM, not an HTTP body.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from audit_source_languages import OUT, download, now, scan, sha, write
from urllib.parse import urlsplit


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--url',action='append',required=True)
    args=parser.parse_args()
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.exists(): raise ValueError('Microsoft Edge is unavailable')
    hosts=json.loads((OUT/'audit-state.json').read_text(encoding='utf-8'))['hosts']
    hosts=sorted(set(hosts)|{urlsplit(u).hostname for u in args.url})
    additions=json.loads((OUT/'additional-seeds.json').read_text(encoding='utf-8'))
    audits=json.loads((OUT/'rendered-audits.json').read_text(encoding='utf-8')) if (OUT/'rendered-audits.json').exists() else {}
    for url in args.url:
        uid=sha(url.encode()); folder=OUT/'pages'/uid; folder.mkdir(parents=True,exist_ok=True)
        attempts=[int(p.name.split('-')[-1]) for p in folder.glob('attempt-*')]
        attempt=max(attempts,default=0)+1
        with tempfile.TemporaryDirectory(prefix='residence-public-browser-') as profile:
            result=subprocess.run([str(edge),'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
                '--disable-background-networking','--disable-extensions','--user-data-dir='+profile,
                '--virtual-time-budget=15000','--dump-dom',url],capture_output=True,timeout=90,
                creationflags=subprocess.CREATE_NO_WINDOW)
        raw=result.stdout
        if result.returncode or b'<html' not in raw.lower():
            print(json.dumps(dict(url=url,status='rendering-failed',error=result.stderr.decode(errors='replace')[-1000:])),flush=True)
            continue
        relative=f'pages/{uid}/attempt-{attempt:03d}/rendered.html'
        path=OUT/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        audit=scan(raw,url,hosts); audits[url]=audit|{'basis':'headless-browser-rendered-dom','verified_at':now(),'raw_sha256':sha(raw)}
        manifest=dict(url=url,status='saved',attempt=attempt,references=[],registry_entries=[],
            discoveries=[dict(reason='public-javascript-content-recovery')],language=audit.get('declared_language'),
            snapshots=[dict(relative_path=relative,requested_url=url,final_url=url,content_type='text/html; charset=utf-8',
                sha256=sha(raw),bytes_downloaded=len(raw),retrieved_at=now(),
                review_flags=['browser-rendered-dom-not-raw-http-response'])],
            rendering=dict(engine='Microsoft Edge headless',isolated_profile=True,virtual_time_budget_ms=15000,
                           authenticated=False,form_submissions=0,llm_calls=0))
        write(folder/'latest.json',manifest)
        additions.append(dict(url=url,reason='public-javascript-content-recovery'))
        for link in audit['topic_links']+audit['language_links']:
            if link not in additions: additions.append(link)
        print(json.dumps(dict(url=url,bytes=len(raw),text_characters=audit.get('substantive_text_characters'),
            language_links=len(audit['language_links']),topic_links=len(audit['topic_links']))),flush=True)
    write(OUT/'additional-seeds.json',additions);write(OUT/'rendered-audits.json',audits)


if __name__=='__main__':main()
