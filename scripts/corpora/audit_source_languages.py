"""Offline link/language inventory and resumable public-source downloads.

No SwissTIP application or model calls. Discovery decisions retain their originating
page, label and reason. A candidate is not evidence of a working translation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import posixpath
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote, parse_qs, quote

from lxml import html
from extract_intermediate import encoding

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / '.local/corpora/hackathon-residence-2026-09-10'
OUT = ROOT / '.local/corpora/hackathon-residence-all-languages-2026-09-11'
INVENTORY = ROOT / 'config/catalogs/hackathon.sources.expanded.json'
TOPIC = re.compile(r'aufenthalt|ausl[aä]nder|einreise|niederlass|familiennachzug|erwerbst[aä]tigkeit|migration|migrations|migranti|immigra|residen|residenc|residenza|residenza|s[eé]jour|sejour|[eé]tranger|etranger|stranier|soggiorno|ricongiung|regroupement|family.reun|work.permit|arbeitsbewill|permis.de.travail|permessi|permesso|meldeverfahren|freiz[uü]gig|libre.circulation|libera.circolazione|visa|visum|visum|visto|sans.papiers|biometri|legitimation|ci.permit|protection.status|schutzstatus|statut.de.protection', re.I)
TOPIC = re.compile(TOPIC.pattern + r'|\bpermits?\b|settlement|permissiun|dimora|grenzg[aä]nger|frontaliers?|kantonswechsel|renouvellement|rinnovo', re.I)
LANG_NAMES = {'deutsch':'de', 'français':'fr', 'francais':'fr', 'italiano':'it', 'english':'en',
              'rumantsch':'rm', 'romansh':'rm', 'español':'es', 'português':'pt', 'shqip':'sq',
              'türkçe':'tr', 'українська':'uk', 'русский':'ru', 'العربية':'ar', '中文':'zh'}
SKIP = re.compile(r'\.(?:css|js|png|jpg|jpeg|gif|svg|ico|mp4|mp3|woff2?|zip)(?:$|\?)|[?&](?:search|query|tx_solr|sword|sort)=|/search(?:/|\?)|/suche(?:/|\?)|/recherche(?:/|\?)', re.I)
LOCK = threading.Lock()
HOST_LOCKS = {}
GOVERNMENT_ROOTS = {c + '.ch' for c in
    'ag ai ar be bl bs fr ge gl gr ju lu ne nw ow sg sh so sz tg ti ur vd vs zg zh'.split()}
GOVERNMENT_ROOTS.update({'jura.ch', 'baselland.ch', 'bern.ch', 'stadt-zuerich.ch'})


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    for attempt in range(8):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def normalize(url):
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        return None
    if p.hostname in ('localhost', '127.0.0.1'):
        return None
    if p.hostname == 'eforms.sh.ch':
        original = parse_qs(p.query).get('wfjs_orig_req', [''])[0]
        if original.startswith('/') and 'generalid=' in original:
            return normalize(urljoin('https://eforms.sh.ch/migrationsamt_passbuero/', original.lstrip('/')))
    path = p.path or '/'
    if '/..' in path or '/./' in path:
        path = posixpath.normpath(path)
    if p.hostname == 'www.sem.admin.ch' and path.startswith('/content/sem/'):
        path = path[len('/content'):]
    if p.hostname == 'www.vs.ch' and '/c/portal/update_language' in path:
        query = parse_qs(p.query)
        destination = query.get('redirect', [''])[0]
        language = query.get('languageId', [''])[0].split('_')[0]
        if destination.startswith('/') and language:
            destination = re.sub(r'^/(?:de|fr|it|en|es|pt|sq|hr|pl|uk)(?=/web/)', '', destination)
            return normalize('https://www.vs.ch/' + language + destination)
    path = quote(path, safe="/%:@!$&'()*+,;=-._~")
    query = p.query
    if '@@news_portlet_listing' in path:
        query = re.sub(r'&(?:amp;)+', '&', query)
    query = quote(query, safe="%=&?/:;+,$@!'()*-._~")
    netloc=p.netloc.lower()
    try:
        port=p.port
    except ValueError:
        return None
    if (p.scheme=='https' and port==443) or (p.scheme=='http' and port==80):
        netloc=p.hostname
    return urlunsplit((p.scheme, netloc, path, query, ''))


def allowed(url, hosts):
    host = urlsplit(url).hostname or ''
    return host in hosts or host.endswith('.admin.ch') or any(
        host == root or host.endswith('.' + root) for root in GOVERNMENT_ROOTS)


def scan(raw, base, hosts):
    try:
        root = html.fromstring(raw.decode(encoding(raw)), parser=html.HTMLParser(no_network=True))
    except Exception:
        return dict(declared_language=None, language_links=[], topic_links=[], deferred_links=[], title=None)
    title = ' '.join(root.xpath('//title/text()')).strip()
    headings = [' '.join(' '.join(n.itertext()).split()) for n in root.xpath('//h1')]
    langs, topics, deferred = {}, {}, {}
    for node in root.xpath('//a[@href] | //link[@href and @hreflang]'):
        url = normalize(urljoin(base, node.get('href')))
        if not url or SKIP.search(url):
            continue
        label = ' '.join(' '.join(node.itertext()).split())
        lang = node.get('hreflang')
        if not lang:
            lang = LANG_NAMES.get(label.lower())
        if not lang and re.fullmatch(r'(?:de|fr|it|en|rm|es|pt|sq|tr|ru|uk|ar|zh)', label.lower()):
            lang = label.lower()
        language_root = re.fullmatch(r'/(de|fr|it|en|rm|es|pt|sq|tr|ru|uk|ar|zh|fa|ja|ta|ti|hr|bs|so|ur)/?',urlsplit(url).path)
        if not lang and language_root and node.get('role')=='menuitem':
            lang=language_root[1]
        item = dict(url=url, label=label[:500], discovered_on=base)
        if lang and lang != 'x-default':
            item.update(advertised_language=lang, reason='published-language-link')
            (langs if allowed(url, hosts) else deferred)[url] = item
            continue
        lineage = ' '.join((a.get('class', '') + ' ' + a.tag) for a in node.iterancestors() if isinstance(a.tag, str))
        text = unquote(url) + ' ' + label
        attachment = bool(re.search(r'\.pdf(?:$|\?)|/download(?:$|\?)|/dam/', url, re.I))
        # Do not silently discard unselected edges: retain them for the coverage audit.
        relevant = bool(TOPIC.search(text))
        local = urlsplit(url).hostname == urlsplit(base).hostname
        page_path = urlsplit(base).path.removesuffix('.html').rstrip('/')
        topic_parent = bool(TOPIC.search(unquote(base) + ' ' + title))
        descendant = bool(topic_parent and page_path and len(page_path.split('/')) >= 4 and urlsplit(url).path.startswith(page_path + '/'))
        content_attachment = topic_parent and attachment and local and not re.search(r'footer|header|nav', lineage, re.I)
        if relevant or descendant or content_attachment:
            item['reason'] = 'topic-link' if relevant else 'topic-descendant' if descendant else 'content-attachment'
            (topics if allowed(url, hosts) else deferred)[url] = item
        elif local and not re.search(r'footer|header', lineage, re.I):
            item['reason'] = 'unselected-local-link-needs-scope-review'
            deferred[url] = item
    # Swiss federal Nuxt pages publish actual translated slugs in their hydration
    # metadata. Read JSON references only; do not execute downloaded JavaScript.
    for script in root.xpath('//script[@id="__NUXT_DATA__" and @type="application/json"]'):
        try:
            values = json.loads(script.text)
            if not isinstance(values, list):
                continue
            for obj in values:
                if not isinstance(obj, dict) or set(obj) != {'lang', 'slug'}:
                    continue
                lang, slug = values[obj['lang']], values[obj['slug']]
                if not isinstance(lang, str) or not isinstance(slug, str):
                    continue
                url = normalize(urljoin(base, '/' + lang.lower() + '/' + slug.lstrip('/')))
                if url and allowed(url, hosts):
                    langs[url] = dict(url=url, label=slug, advertised_language=lang.lower(),
                                      discovered_on=base, reason='published-language-link',
                                      publication_mechanism='nuxt-lang-slug-metadata')
        except (ValueError, IndexError, TypeError):
            pass
    # Hash substantive text separately from translated navigation. Equality is a
    # fallback/duplicate signal for review, not proof of translation equivalence.
    containers = root.xpath('//main') or root.xpath('//body') or [root]
    content = []
    for container in containers:
        for node in container.xpath('.//text()[not(ancestor::script or ancestor::style or ancestor::nav or ancestor::header or ancestor::footer or ancestor::select)]'):
            if node.strip():
                content.append(' '.join(node.split()))
    body_text = ' '.join(content)
    error_page = any(re.fullmatch(r'Error Page\s*\(404\)|404|Page not found|Seite nicht gefunden|Access Denied|Forbidden', h, re.I)
                     for h in [title, *headings])
    return dict(declared_language=root.get('lang'), title=title, main_headings=headings,
                soft_error_page=error_page, substantive_text_sha256=sha(body_text.encode()),
                substantive_text_characters=len(body_text), language_links=list(langs.values()),
                language_menu_options=root.xpath('//select[contains(@id,"language")]/option/@value'),
                topic_links=list(topics.values()), deferred_links=list(deferred.values()))


def save_inventory(state):
    targets = sorted(state['targets'].values(), key=lambda t: t['url'])
    public_inventory = [dict(url=t['url'], url_id=t['url_id'], status=t['status'],
        advertised_languages=sorted({d['advertised_language'] for d in t['discoveries'] if d.get('advertised_language')}),
        discovery_reasons=sorted({d['reason'] for d in t['discoveries'] if d.get('reason')}),
        discovery_count=len(t['discoveries']), last_error=t.get('last_error')) for t in targets]
    write(INVENTORY, dict(schema_version='swisstip.source-expansion/v1', updated_at=now(),
        scope='All residence-permit information and all published source languages; discovery remains open until audited.',
        completeness='in-progress', full_provenance='.local/corpora/' + OUT.name + '/audit-state.json', sources=public_inventory))
    write(OUT / 'audit-state.json', state)
    write(OUT / 'plan.json', dict(schema_version='swisstip.catalogue-download-plan/v1', created_at=state['created_at'],
        catalogue_sha256=sha((OUT / 'catalogue.md').read_bytes()), targets=targets))


def add(state, item, origin=None):
    url = normalize(item['url'])
    if not url:
        return
    if url not in state['targets']:
        state['targets'][url] = dict(url=url, url_id=sha(url.encode()), status='pending',
            references=[], registry_entries=[], discoveries=[])
    target = state['targets'][url]
    record = {k: v for k, v in item.items() if k != 'url'}
    if origin:
        record['origin_seed'] = origin
    if record and record not in target['discoveries']:
        target['discoveries'].append(record)


def initialize():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'audit-state.json').exists():
        return json.loads((OUT / 'audit-state.json').read_text(encoding='utf-8'))
    plan = json.loads((OLD / 'plan.json').read_text(encoding='utf-8'))
    hosts = sorted({urlsplit(t['url']).hostname for t in plan['targets']})
    state = dict(created_at=now(), targets={}, hosts=hosts, audits={})
    (OUT / 'catalogue.md').write_bytes((ROOT / 'config/catalogs/hackathon.sources.md').read_bytes())
    for target in plan['targets']:
        add(state, dict(url=target['url'], reason='existing-catalogue-seed'))
        state['targets'][target['url']].update(references=target['references'], registry_entries=target['registry_entries'])
    for pointer in OLD.rglob('latest.json'):
        manifest = json.loads(pointer.read_text(encoding='utf-8'))
        for snapshot in manifest.get('snapshots', []):
            raw_path = pointer.parents[2] / snapshot['relative_path']
            raw = raw_path.read_bytes()
            if sha(raw) != snapshot['sha256']:
                raise ValueError('Existing snapshot changed')
            if not re.search(br'<(?:!doctype\s+html|html|head|body)', raw[:8192], re.I):
                continue
            result = scan(raw, snapshot['final_url'], hosts)
            state['audits'][snapshot['final_url']] = result | {'basis': 'saved-original-snapshot', 'raw_sha256':sha(raw)}
            for link in result['language_links'] + result['topic_links']:
                add(state, link, manifest.get('source_page_url', manifest['url']))
    save_inventory(state)
    return state


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = normalize(newurl)
        if not target or not allowed(target, self.hosts):
            raise ValueError('Redirect to unreviewed host: ' + newurl)
        return super().redirect_request(req, fp, code, msg, headers, target)


def download(target, hosts):
    url = target['url']
    folder = OUT / 'pages' / target['url_id']
    folder.mkdir(parents=True, exist_ok=True)
    attempt = len(list(folder.glob('attempt-*'))) + 1
    manifest = dict(url=url, references=target['references'], registry_entries=target['registry_entries'],
                    discoveries=target['discoveries'], snapshots=[])
    with LOCK:
        host_lock = HOST_LOCKS.setdefault(urlsplit(url).hostname, threading.Lock())
    try:
        with host_lock:
            time.sleep(0.3)
            opener = urllib.request.build_opener(SafeRedirect(hosts))
            req = urllib.request.Request(url, headers={'User-Agent':'SwissTIP-Hackathon-SourceAudit/1.0', 'Accept':'text/html,application/pdf,*/*;q=0.5'})
            with opener.open(req, timeout=25) as response:
                raw = response.read(40 * 1024 * 1024 + 1)
                if len(raw) > 40 * 1024 * 1024:
                    raise ValueError('Document exceeds 40 MiB; recorded for separate acquisition')
                final = response.geturl()
                content_type = response.headers.get('Content-Type', '')
                status_code = response.status
        suffix = '.pdf' if raw[:1024].lstrip().startswith(b'%PDF-') else '.html' if re.search(br'<(?:!doctype\s+html|html|head|body)', raw[:8192], re.I) else '.bin'
        relative = f"pages/{target['url_id']}/attempt-{attempt:03d}/response{suffix}"
        path = OUT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifest.update(status='saved', http_status=status_code, snapshots=[dict(relative_path=relative,
            requested_url=url, final_url=final, content_type=content_type, sha256=sha(raw),
            bytes_downloaded=len(raw), retrieved_at=now(), review_flags=[])])
        result = scan(raw, final, hosts) if suffix == '.html' else None
        if result:
            manifest['language'] = result['declared_language']
        write(folder / 'latest.json', manifest)
        return manifest, result
    except Exception as exc:
        manifest.update(status='failed', error=f'{type(exc).__name__}: {exc}', attempted_at=now())
        write(folder / 'latest.json', manifest)
        return manifest, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--batch-size', type=int, default=200, help='Resumable batch size, not a corpus completeness limit')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--until-idle', action='store_true', help='Continue discovered-language/detail batches until the current frontier is empty')
    parser.add_argument('--rescan-host',action='append',default=[],help='Re-audit saved HTML on this host with the current discovery rules')
    args = parser.parse_args()
    state = initialize()
    rendered = OUT/'rendered-audits.json'
    if rendered.exists():
        state['audits'].update(json.loads(rendered.read_text(encoding='utf-8')))
    for target in list(state['targets'].values()):
        if urlsplit(target['url']).hostname not in args.rescan_host:
            continue
        pointer=OUT/'pages'/target['url_id']/'latest.json'
        if not pointer.exists():
            continue
        manifest=json.loads(pointer.read_text(encoding='utf-8'))
        for snapshot in manifest.get('snapshots',[]):
            if snapshot['relative_path'].endswith('.html'):
                raw=(OUT/snapshot['relative_path']).read_bytes()
                if sha(raw)!=snapshot['sha256']:
                    raise ValueError('Snapshot hash changed during language rescan')
                result=scan(raw,snapshot['final_url'],state['hosts'])
                state['audits'][target['url']]=result|{'basis':'saved-snapshot-rescan','verified_at':now()}
                for link in result['language_links']+result['topic_links']:
                    add(state,link)
    for audit in state['audits'].values():
        for link in audit.get('deferred_links', []):
            if (link.get('reason') != 'unselected-local-link-needs-scope-review' or
                    TOPIC.search(unquote(link['url'])+' '+link.get('label',''))) and allowed(link['url'], state['hosts']):
                add(state, link)
    additions = OUT / 'additional-seeds.json'
    if additions.exists():
        for item in json.loads(additions.read_text(encoding='utf-8')):
            host = urlsplit(item['url']).hostname
            if host not in state['hosts']:
                state['hosts'].append(host)
            add(state, item)
    # Recover successful downloads if a previous batch was interrupted while
    # checkpointing, including transient Windows/OneDrive file locks.
    known_ids = {t['url_id'] for t in state['targets'].values()}
    pending_ids = {t['url_id'] for t in state['targets'].values() if t['status'] in {'pending','failed'}}
    for pointer in OUT.glob('pages/*/latest.json'):
        if pointer.parent.name in known_ids and pointer.parent.name not in pending_ids:
            continue
        manifest = json.loads(pointer.read_text(encoding='utf-8'))
        if manifest['url'] not in state['targets']:
            add(state, dict(url=manifest['url'], reason='separately-audited-public-document'))
        target = state['targets'].get(manifest['url'])
        if target and target['status'] in {'pending','failed'}:
            target['status'] = manifest['status']
            target['last_error'] = manifest.get('error')
    for target in list(state['targets'].values()):
        canonical = normalize(target['url'])
        if target['status'] in {'pending', 'failed'} and canonical != target['url']:
            add(state, dict(url=canonical, reason='normalized-published-url', discovered_on=target['url']))
            target.update(status='url-normalization-alias', canonical_url=canonical)
    save_inventory(state)
    while True:
        pending_after_batch = download_batch(state,args)
        if not args.until_idle or not pending_after_batch:
            break


def download_batch(state,args):
    pending = [t for t in state['targets'].values() if t['status'] == 'pending']
    # Language variants first, then existing seeds, then linked detail.
    pending.sort(key=lambda t: (0 if any(d.get('reason')=='published-language-link' for d in t['discoveries']) else
                               1 if any(d.get('reason')=='existing-catalogue-seed' for d in t['discoveries']) else 2, t['url']))
    # Interleave hosts so queued tasks do not monopolize workers waiting for one
    # site's rate-limit lock while other government sites are idle.
    by_host = {}
    for target in pending:
        by_host.setdefault(urlsplit(target['url']).hostname, []).append(target)
    pending = []
    while by_host:
        for host in list(by_host):
            pending.append(by_host[host].pop(0))
            if not by_host[host]:
                del by_host[host]
    print(json.dumps(dict(identified=len(state['targets']), pending=len(pending), audited_pages=len(state['audits']))), flush=True)
    if not args.download:
        return False
    batch = pending[:args.batch_size]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, t, state['hosts']):t for t in batch}
        for index, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            manifest, result = future.result()
            target['status'] = manifest['status']
            target['last_error'] = manifest.get('error')
            if result:
                state['audits'][target['url']] = result | {'basis':'live-download', 'verified_at':now()}
                for link in result['language_links'] + result['topic_links']:
                    add(state, link, target['url'])
            if index % 100 == 0:
                save_inventory(state)
            if index % 20 == 0 or target['status'] == 'failed':
                print(json.dumps(dict(done=index, batch=len(batch), status=target['status'], url=target['url'])), flush=True)
    save_inventory(state)
    print(json.dumps(dict(identified=len(state['targets']), pending=sum(t['status']=='pending' for t in state['targets'].values()),
                         saved=sum(t['status']=='saved' for t in state['targets'].values()),
                         failed=sum(t['status']=='failed' for t in state['targets'].values()))), flush=True)
    return any(t['status']=='pending' for t in state['targets'].values())


if __name__ == '__main__':
    main()
