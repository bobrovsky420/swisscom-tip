# SwissTIP bounded crawler demo

This CLI is a small proof of the acquisition stage described in the product and
technical specifications:

```text
Source Registry -> scan / crawl / fetch -> snapshot metadata
```

It runs only as an operator-triggered knowledge-builder command. It is not
imported by, or suitable for, request-time MCP handling.

## Install

Python 3.11 or newer is required. From the repository root:

```shell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e packages/ingestion -e apps/knowledge-builder
```

On macOS or Linux, use `.venv/bin/python` instead. The examples below use the
Windows executable path; activation is not required.

## Inspect the safety policy without making a request

```powershell
.venv\Scripts\swisstip-crawl.exe https://www.example.org/ --dry-run
```

## Run a deliberately small official-source scan

The seed below is one of the SEM pages relevant to the Arrival Checklist. Depth
zero fetches only the seed page (plus `robots.txt`); increase it explicitly when
link discovery is required.

```powershell
.venv\Scripts\swisstip-crawl.exe "https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html" `
  --source-id sem-eu-efta-faq-en `
  --authority "State Secretariat for Migration (SEM)" `
  --jurisdiction CH `
  --language en `
  --allow-path-prefix /sem/en/home/themen/fza_schweiz-eu-efta/ `
  --max-depth 0 `
  --max-pages 1 `
  --max-requests 3 `
  --max-total-bytes 1000000 `
  --max-response-bytes 750000 `
  --max-duration 30 `
  --delay 2
```

The command emits JSON to stdout. It includes the effective source scope and
limits, each response's URL/status/media type/size/hash/title, `ETag` and
`Last-Modified` values when supplied, skipped URLs with reasons, and aggregate
request/payload-byte counts. Redirects and the `robots.txt` lookup are included
in the request budget.

## Controls that prevent runaway crawling

- Breadth-first traversal with explicit `--max-depth` and `--max-pages`.
- A separate hard request budget, including redirects and `robots.txt`.
- Per-response and whole-run payload-byte caps. Compressed transfer is disabled
  so the accounting remains understandable.
- Sequential requests only, with a configurable minimum delay. A larger
  `Crawl-delay` or `Request-rate` from `robots.txt` takes precedence.
- Total-duration, request-timeout, redirect, failure, per-page-link and queued-URL
  limits.
- Exact host and path-prefix allowlists; every redirect is checked before it is
  requested.
- Query strings are skipped by default to avoid calendars, searches and other
  crawler traps.
- Public IP addresses only by default, which blocks loopback/private targets and
  reduces SSRF risk. `--allow-private-networks` exists solely for local testing.
- `robots.txt` is mandatory and failures are fail-closed. `rel=nofollow` and page
  `nofollow` directives are honored.
- HTTP 429 and 503 responses stop the run immediately; there are no automatic
  retries.
- Non-HTML response bodies are not downloaded by this discovery proof.

This is intentionally not the full ingestion pipeline: it does not persist raw
snapshots, perform conditional revalidation, parse PDFs, normalize documents, or
publish a release. The reported hashes and cache headers provide the hand-off to
those later components.

## Tests

The tests use deterministic fake HTTP responses and make no network requests:

```shell
.venv\Scripts\python.exe -m unittest discover -s packages/ingestion/tests -v
.venv\Scripts\python.exe -m unittest discover -s apps/knowledge-builder/tests -v
```
