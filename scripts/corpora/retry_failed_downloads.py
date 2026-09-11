"""Paced retry of failed public-source downloads in the resumable audit state.

The normal crawler batch processes pending targets only. This script selects
targets whose last attempt failed for a recoverable reason, retries them one
host at a time with a configurable delay, backs off on HTTP 429, and records
every outcome in a dated recovery ledger. Saved responses become new attempt
folders; the discovery graph and the checked-in inventory are updated through
the crawler's own functions. Skipped causes (mailto redirects, defunct or
authentication hosts, oversized documents unless a larger limit is allowed) are
listed in the ledger rather than silently dropped. No SwissTIP application,
model or database call is made. TLS verification is never disabled.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re
import threading
import time
from urllib.parse import urlsplit

import audit_source_languages as audit
from audit_source_languages import OUT, add, now, save_inventory, write

DEFUNCT_HOSTS = {'www.bfm.admin.ch'}
SKIP_HOSTS = {'auth.ag.ch'}
CATEGORIES = [
    ('mailto-redirect', re.compile(r'mailto:', re.I), 'skip'),
    ('oversized', re.compile(r'exceeds \d+ MiB'), 'oversized'),
    ('rate-limited', re.compile(r'HTTP Error 429'), 'retry'),
    ('not-found', re.compile(r'HTTP Error 404'), 'retry-once'),
    ('forbidden', re.compile(r'HTTP Error 403'), 'retry-once'),
    ('server-error', re.compile(r'HTTP Error 50[0-9]'), 'retry'),
    ('other-http', re.compile(r'HTTPError'), 'retry-once'),
    ('dns-failure', re.compile(r'getaddrinfo failed'), 'retry-once'),
    ('connection-refused', re.compile(r'10061'), 'retry'),
    ('connect-timeout', re.compile(r'10060'), 'retry'),
    ('read-timeout', re.compile(r'timed out', re.I), 'retry'),
    ('tls-certificate', re.compile(r'CERTIFICATE_VERIFY_FAILED'), 'retry-once'),
    ('redirect-unreviewed-host', re.compile(r'Redirect to unreviewed host'), 'retry'),
]


def classify(target):
    error = target.get('last_error') or ''
    host = urlsplit(target['url']).hostname or ''
    for name, pattern, action in CATEGORIES:
        if pattern.search(error):
            if host in DEFUNCT_HOSTS:
                return name, 'skip-defunct-host'
            if host in SKIP_HOSTS:
                return name, 'skip-authentication-host'
            return name, action
    return 'unclassified', 'retry-once'


def plan(state, *, oversized_limit=None):
    """Split failed targets into (target, category, attempts or None) and skipped ledger rows."""
    selected, skipped = [], []
    for target in sorted(state['targets'].values(), key=lambda t: t['url']):
        if target['status'] != 'failed':
            continue
        category, action = classify(target)
        entry = dict(url=target['url'], category=category, last_error=target.get('last_error'))
        if action == 'oversized' and oversized_limit is None:
            skipped.append(entry | dict(action='skip-oversized'))
        elif action.startswith('skip'):
            skipped.append(entry | dict(action=action))
        else:
            selected.append((target, category, 1 if action == 'retry-once' else None))
    return selected, skipped


def retry_host(host, items, hosts, args, results, lock, state, download=None):
    download = download or audit.download
    consecutive_429 = 0
    for position, (target, category, max_attempts) in enumerate(items):
        attempts = max_attempts or args.max_attempts
        previous_error = target.get('last_error')
        outcome, attempt = dict(status='dry-run', error=None), 0
        for attempt in range(1, attempts + 1):
            if args.dry_run:
                break
            if category == 'oversized' and args.oversized_limit:
                manifest, audit_result = download(target, hosts, args.oversized_limit)
            else:
                manifest, audit_result = download(target, hosts)
            outcome = dict(status=manifest['status'], error=manifest.get('error'))
            if manifest['status'] == 'saved':
                consecutive_429 = 0
                with lock:
                    target['status'] = 'saved'
                    target['last_error'] = None
                    if audit_result:
                        state['audits'][target['url']] = audit_result | {
                            'basis': 'live-download-recovery', 'verified_at': now()}
                        for link in audit_result['language_links'] + audit_result['topic_links']:
                            add(state, link, target['url'])
                break
            with lock:
                target['last_error'] = manifest.get('error')
            if 'HTTP Error 429' in (manifest.get('error') or ''):
                consecutive_429 += 1
                if consecutive_429 >= args.max_consecutive_429:
                    outcome['host_paused'] = True
                    break
                time.sleep(args.backoff * attempt)
            elif attempt < attempts:
                time.sleep(args.host_delay)
        row = dict(url=target['url'], host=host, category=category, attempts=attempt,
                   previous_error=previous_error, **outcome)
        with lock:
            results.append(row)
        print(json.dumps(dict(host=host, status=outcome['status'], category=category, url=target['url'])), flush=True)
        if outcome.get('host_paused'):
            with lock:
                for remaining, remaining_category, _ in items[position + 1:]:
                    results.append(dict(url=remaining['url'], host=host, category=remaining_category, attempts=0,
                                        previous_error=remaining.get('last_error'),
                                        status='not-attempted-host-paused', error=None))
            return
        if not args.dry_run:
            time.sleep(args.host_delay)


def summarize(results, skipped, state, args, started):
    return dict(
        schema_version='swisstip.download-recovery/v1', label=args.label, started_at=started, finished_at=now(),
        parameters=dict(host_delay=args.host_delay, backoff=args.backoff, max_attempts=args.max_attempts,
                        max_consecutive_429=args.max_consecutive_429, workers=args.workers,
                        oversized_limit=args.oversized_limit, only_host=args.only_host, dry_run=args.dry_run),
        outcomes=dict(Counter(r['status'] for r in results)),
        outcomes_by_category={c: dict(Counter(r['status'] for r in results if r['category'] == c))
                              for c in sorted({r['category'] for r in results})},
        saved_by_host=dict(Counter(r['host'] for r in results if r['status'] == 'saved')),
        remaining_errors=dict(Counter(re.sub(r'https?://\S+', 'URL', (r['error'] or ''))[:80]
                                      for r in results if r['status'] == 'failed')),
        statuses_after=dict(Counter(t['status'] for t in state['targets'].values())),
        results=sorted(results, key=lambda r: r['url']), skipped=sorted(skipped, key=lambda r: r['url']),
        note='Recovered responses are saved raw attempts. Intermediate extraction, semantic assertions and '
             'serving releases must be rebuilt as a new version before any published statistic changes.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-delay', type=float, default=2.0, help='Seconds between requests to one host')
    parser.add_argument('--backoff', type=float, default=45.0, help='Base seconds to wait after HTTP 429')
    parser.add_argument('--max-attempts', type=int, default=3)
    parser.add_argument('--max-consecutive-429', type=int, default=3)
    parser.add_argument('--workers', type=int, default=6, help='Hosts processed concurrently')
    parser.add_argument('--oversized-limit', type=int, help='Bytes allowed for documents previously over the cap')
    parser.add_argument('--only-host', action='append', default=[])
    parser.add_argument('--dry-run', action='store_true', help='Plan and ledger only; no request, no state change')
    parser.add_argument('--label', default=datetime.now(timezone.utc).strftime('recovery-%Y-%m-%d'))
    args = parser.parse_args(argv)
    state = json.loads((OUT / 'audit-state.json').read_text(encoding='utf-8'))
    selected, skipped = plan(state, oversized_limit=args.oversized_limit)
    by_host = {}
    for target, category, max_attempts in selected:
        host = urlsplit(target['url']).hostname
        if args.only_host and host not in args.only_host:
            continue
        by_host.setdefault(host, []).append((target, category, max_attempts))
    print(json.dumps(dict(failed_targets=sum(t['status'] == 'failed' for t in state['targets'].values()),
                          selected=sum(len(v) for v in by_host.values()), hosts=len(by_host),
                          skipped=len(skipped), dry_run=args.dry_run)), flush=True)
    results, lock, started = [], threading.Lock(), now()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(retry_host, host, items, state['hosts'], args, results, lock, state)
                   for host, items in sorted(by_host.items())]
        for future in as_completed(futures):
            future.result()
    summary = summarize(results, skipped, state, args, started)
    if not args.dry_run:
        save_inventory(state)
        write(OUT / f'{args.label}-results.json', summary)
    print(json.dumps({k: summary[k] for k in ('outcomes', 'outcomes_by_category', 'saved_by_host',
                                              'remaining_errors', 'statuses_after')}, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
