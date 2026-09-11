# Residence corpus download recovery - 11 September 2026

Status: completed for the recoverable causes. This is the acquisition part of
step 3 in the [continuation checkpoint](2026-09-11-residence-mcp-checkpoint.md).
It retried the 475 failed downloads recorded in the nationwide corpus with
deliberate pacing, followed the links found on recovered pages until the
frontier was empty again, and recorded every outcome. The recovered responses
are raw snapshots only: no intermediate, semantic or serving artifact includes
them yet, and the v1 release, its statistics and the pure validation results are
unchanged.

## What was done

- Ledgers of the raw corpus were copied to
  `.local/corpora/hackathon-residence-all-languages-2026-09-11/pre-recovery-2026-09-11/`
  before any change (audit state, plan, coverage and language ledgers, seeds,
  rendered audits and the checked-in inventory).
- [retry_failed_downloads.py](../../scripts/corpora/retry_failed_downloads.py)
  retried 442 of the 475 failed targets host by host with a 2 s delay between
  requests, 45 s backoff after HTTP 429 and up to three attempts for transient
  causes; 404, 403, DNS and certificate failures got one fresh attempt. Mailto
  redirects (12), the defunct `www.bfm.admin.ch` host (18) and three documents
  over 40 MiB were listed as skipped. Ledger: `recovery-2026-09-11-results.json`.
- A second pass with a 5 s delay and 90 s backoff covered the two hosts that
  still answered 429 (`www.sz.ch`, `www.gl.ch`). Ledger:
  `recovery-2026-09-11-pass2-results.json`.
- The crawler, now with a `--host-delay` option, downloaded the links discovered
  on recovered pages in two bounded batches (239, then 19) without `--until-idle`.
  The frontier is empty again; an empty frontier is still not proof of exhaustive
  discovery.
- The checked-in inventory
  [hackathon.sources.expanded.json](../../config/catalogs/hackathon.sources.expanded.json)
  was rewritten by the crawler's own inventory function. No extraction
  application, model or database call was made. TLS verification was never
  disabled; no login, form or non-government host was fetched.

## Recorded results

| Measure | Before | After |
| --- | ---: | ---: |
| Identified URLs | 12,384 | 12,642 |
| Saved responses | 11,728 | 12,117 |
| Failed downloads | 475 | 344 |
| URL normalization aliases | 181 | 181 |
| Pending frontier | 0 | 0 |
| Snapshots retrieved during recovery | | 389 |
| Previously failed targets recovered | | 176 of 442 retried |
| Newly discovered links saved | | 213 of 258 |

Recovered previously failed targets by cause: rate limited 127 of 128, connect
timeouts 17 of 17, read timeouts 2 of 2, redirects to now-allowed government
subdomains 11 of 14, server errors 4 of 5, dead links 13 of 232, forbidden 2 of 15.
By host: `migrationsamt.tg.ch` 55, `www.sz.ch` 31, `www.biel-bienne.ch` 24,
`www.eda.admin.ch` 13, `www.gl.ch` 11, `www.sg.ch` 10, `awa.tg.ch` 8,
`www.ge.ch` 7, `zg.ch` 6, and smaller counts on Bern, Basel-Stadt, SEM, Jura
and Aargau hosts.

## What remains failed and why

| Cause | Count | Assessment |
| --- | ---: | --- |
| HTTP 404 dead links (vs.ch 77, ag.ch 28, sem.admin.ch 26, gl.ch 17) | 233 | Stale references on other pages; replacements need rediscovery, not retries |
| Redirects to mailto addresses (migrationsamt.tg.ch 40) | 42 | Contact links, not documents |
| DNS failures (bfm.admin.ch 18, meweb.admin.ch 5, wira.lu.ch 2, gef.be.ch 2) | 29 | Defunct hosts; successor content is on sem.admin.ch and wira.was-luzern.ch |
| Connection refused (vd.ch) | 18 | Host refuses this client; needs a rendered or manual acquisition route |
| HTTP 403 (baselland.ch 12, zh.ch 1) | 13 | Bot protection; Basel-Landschaft content was already recovered through its document host and Hallo Baselland |
| Oversized over 40 MiB (one SEM consultation PDF in de, fr, it) | 3 | Contextual archival material; `--oversized-limit` can fetch it deliberately |
| TLS certificate failures (bdm.bs.ch, www.migrationsamt.tg.ch) | 2 | Not bypassed; the Thurgau host is served under `migrationsamt.tg.ch` |
| Server errors, one blocked redirect to easygov.swiss, one HTTP 406 | 4 | Individually reviewable |

## Consequences for the next version

- Coverage ledgers in the raw corpus (`coverage-report.json`,
  `source-coverage.json`, `deferred-scope-review.json`,
  `language-version-audit.json`) and the checked-in coverage summary still
  describe the pre-recovery snapshot. The finalizer also rewrites the v1
  intermediate's index and validation files, so it was deliberately not run.
- The 389 new raw responses need extraction, language assignment, assertion
  export, packaging and finalization as a new intermediate, semantic and serving
  version with new release IDs, as step 5 of the checkpoint requires. Several
  script paths are fixed to the 2026-09-11 snapshot and must be parameterized
  first.
- Newly saved pages include print views, share links, event archives and
  integration programme pages whose relevance to residence permits is
  unreviewed; scope review remains part of step 3.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/retry_failed_downloads.py --dry-run
./.venv/Scripts/python.exe scripts/corpora/retry_failed_downloads.py --host-delay 2 --backoff 45 --workers 6 --label recovery-<date>
./.venv/Scripts/python.exe scripts/corpora/audit_source_languages.py --download --batch-size 300 --workers 4 --host-delay 2
```
