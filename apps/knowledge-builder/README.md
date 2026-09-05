# SwissTIP knowledge-builder demos

These CLIs are small proofs of the acquisition and concept proposal stages
described in the product and technical specifications:

```text
Source Registry -> scan / crawl / fetch -> snapshot metadata
Downloaded page -> normalize -> model-assisted extraction -> candidate concepts
```

They run only as operator-triggered knowledge-builder commands. They are not
imported by, or suitable for, request-time MCP handling.

## Install

Python 3.11 or newer is required. From the repository root:

```shell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e packages/ingestion -e apps/knowledge-builder
```

On macOS or Linux, use `.venv/bin/python` instead. The examples below use the
Windows executable path; activation is not required.

## Propose concepts from downloaded pages

`swisstip-concepts` accepts one or more local file paths, directory paths, or
wildcard patterns. Eligible files have an `.html`, `.htm`, `.txt`, `.md`, or
`.markdown` extension. Directory scanning recursively includes supported files
in nested subfolders. It does not descend into symlinked or junction child
directories encountered beneath the supplied root. A link in the explicitly
supplied root path is treated as deliberate. The command does not download
URLs. From the repository root, run:

```powershell
.venv\Scripts\swisstip-concepts.exe downloaded\permit-page.html `
  downloaded\arrival-checklist.md `
  --config config\semantic-models.toml
```

Pass a directory to process supported files throughout its directory tree:

```powershell
.venv\Scripts\swisstip-concepts.exe downloaded `
  --config config\semantic-models.toml
```

Wildcard patterns are expanded by the CLI. Quote them so the shell passes the
pattern unchanged, particularly when using a shell that expands wildcards
itself:

```powershell
.venv\Scripts\swisstip-concepts.exe "downloaded\permit-*.html" `
  --config config\semantic-models.toml
```

Recursive `**` patterns are also supported. Keep the pattern quoted:

```powershell
.venv\Scripts\swisstip-concepts.exe "downloaded/**/*.html" `
  --config config\semantic-models.toml
```

Wildcard syntax takes precedence even when a literal path containing `*`, `?`,
or `[` exists. Escape a literal opening bracket with a bracket expression; for
example, use `page[[]1].html` to select the literal file `page[1].html`.

Resolved files are ordered deterministically. If multiple inputs resolve to the
same canonical path, it is processed only once. A wildcard that matches no
eligible files, or a directory tree with no supported files, is reported as an
input error rather than producing an empty result. Files discovered through a
directory or wildcard cannot be symlinks; an explicit file symlink remains an
intentional input. Recursive wildcard matching skips hidden path components
unless the pattern names them explicitly.

Input discovery is capped at 100,000 filesystem entries by default, including
directories and unsupported files. Use `--max-discovery-entries` to choose a
different positive ceiling. The configured `max_pages_per_run` limit is applied
to the de-duplicated eligible files before they are read or sent to a model.

The command emits one JSON wrapper to stdout, with a separate proposal report
for every input file. Use `--compact` for unindented JSON or redirect stdout to
a file when a stored proposal is useful:

```powershell
.venv\Scripts\swisstip-concepts.exe downloaded\permit-page.html `
  --config config\semantic-models.toml `
  --compact > concept-proposals.json
```

The output is a proposal report, not a published taxonomy. Every extracted item
remains a candidate concept and includes exact page evidence. The report also
records the selected profile, provider and model identity, input and output
hashes, semantic operation, prompt profile, request identifiers when available,
token usage when available, and validation warnings. A candidate with
unsupported or non-exact evidence is rejected instead of being silently
accepted; other valid candidates in the same response remain available.

### Select one of the three model profiles

All non-secret model settings are in
[`config/semantic-models.toml`](../../config/semantic-models.toml). Change only
this value to select a complete preconfigured provider and model:

```toml
[semantic_model]
active_profile = "ollama_local"
```

The available values are:

| Profile | Runtime | Configured model | Intended use |
| --- | --- | --- | --- |
| `ollama_local` | Local Ollama API | `MichelRosselli/apertus:8b-instruct-2509-q4_k_m` | Offline/local testing with an unofficial community package |
| `apertus_8b` | Hugging Face router | `swiss-ai/Apertus-8B-Instruct-2509` | Free-account testing |
| `apertus_70b` | Hugging Face router | `swiss-ai/Apertus-70B-Instruct-2509` | Paid demo account |

For example, switching to the 70B demo model requires only:

```toml
[semantic_model]
active_profile = "apertus_70b"
```

The profile owns its adapter, URL, model, provider, timeout, and optional billing
configuration. The Ollama profile also owns its context and keep-alive settings.
Generation and extraction limits are shared settings. To add another model
using the implemented Ollama or Hugging Face adapter, define it once under
`[profiles.<name>]`; future switches then change only `active_profile`. A new
provider API requires a corresponding adapter implementation.

Selection is explicit and fail-closed. The command does not fall back to another
profile or model after an authentication, quota, availability, transport, or
response-validation failure.

The extraction section also places hard limits on pages, normalized input
characters, requests per page, and requests per run. Every page is chunked and
the complete batch is checked before the first model call. An over-budget batch
fails instead of partially running or incurring unbounded paid requests.

### Run with local Ollama

Install and start Ollama, then make sure the model named by `ollama_local` is
available locally:

```powershell
ollama pull MichelRosselli/apertus:8b-instruct-2509-q4_k_m
```

Keep `active_profile = "ollama_local"`. This profile calls
`http://127.0.0.1:11434` and does not require a token. The configured quantized
8B model is the practical local option; actual GPU residency and speed depend on
available VRAM, context size, and Ollama's CPU offloading.

The configured Ollama artifact is an unofficial community packaging of the
official Apertus weights. Use the Hugging Face profiles when the canonical model
deployment and chat template are required.

### Run with Hugging Face

Both Hugging Face profiles call the configured Inference Providers router. The
only secret read from the environment is `HF_TOKEN`; tokens in the TOML file are
rejected. Create a fine-grained token with permission to make calls to Inference
Providers. In the same PowerShell session that runs the command:

```powershell
$env:HF_TOKEN = "hf_your_token_here"
.venv\Scripts\swisstip-concepts.exe downloaded\permit-page.html `
  --config config\semantic-models.toml
```

Set `active_profile` to `apertus_8b` for the configured 8B testing model or
`apertus_70b` for the configured 70B demo model. The Python command and token
mechanism are identical; only the profile selector and the Hugging Face account
behind the token differ. Account quota and provider/model availability still
apply.

Hugging Face mode transmits the normalized page text, title, language, and
derived document identifier to the `base_url` and provider selected by the
trusted configuration file. Changing `base_url` changes where the bearer token
and page data are sent. Do not use it for content that is not approved for that
external processing. Reports include the supplied local source path. For an
organization-paid account, set the optional `bill_to` value once in the
`apertus_70b` profile; selecting the profile remains a one-line change.

Do not commit a real token or place one in `semantic-models.toml`. The process
environment is used directly; the application does not load `.env` files.

## Bounded crawler

### Inspect the safety policy without making a request

```powershell
.venv\Scripts\swisstip-crawl.exe https://www.example.org/ --dry-run
```

### Run a deliberately small official-source scan

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

### Controls that prevent runaway crawling

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

The crawler is intentionally not the full ingestion pipeline: it does not
persist raw snapshots, perform conditional revalidation, parse PDFs, normalize
documents, or publish a release. The reported hashes and cache headers provide
the hand-off to those later components. Save or otherwise supply downloaded page
files separately before invoking the concept extractor.

## Tests

The tests use deterministic fake HTTP responses and make no network requests:

```shell
.venv\Scripts\python.exe -m unittest discover -s packages/ingestion/tests -v
.venv\Scripts\python.exe -m unittest discover -s apps/knowledge-builder/tests -v
```
