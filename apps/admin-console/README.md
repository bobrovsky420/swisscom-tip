# SwissTIP knowledge studio

A local browser GUI for ingestion, parsing and pilot demonstrations. The console
uses React, TypeScript, Vite, Mantine and TanStack Query with a generated Hey API
client. FastAPI delegates jobs to a separate Python worker and stores operational
state in the existing PostgreSQL database.

## Start

From the repository root, with the [local database](../../docs/storage.md) running:

```shell
./.venv/Scripts/python.exe -m pip install -e "packages/runtime[postgres]" -e apps/control-api
npm --prefix apps/admin-console ci
npm --prefix apps/admin-console run build
./.venv/Scripts/python.exe scripts/admin/run.py
```

On Windows PowerShell use `npm.cmd` if script execution policy blocks `npm.ps1`.
On Unix replace the Python path with `./.venv/bin/python`. Node 24 was used for the
build. Open **http://127.0.0.1:8000**. Keep the launcher terminal open; Ctrl+C stops
the API and asks the worker to stop its active child process. The browser can be
closed while a job continues. The launcher applies checked SQL migrations before
starting the services. It does not start Docker automatically.

The server reads `SWISSTIP_DATABASE_URL` or `.local/postgres-dsn.txt`. API keys stay
in the server environment. Set the configured profile's token variable before
starting the launcher when using a hosted extraction service. The GUI displays
credential presence, never values. Ollama still runs in WSL.

## Suggested demo, with no new model calls

1. In **Sources**, SEM residence DE/EN and Zurich EU/EFTA are preselected from
   the 59-source catalog. Click **Load saved pilot pages**. This copies the eight
   archived pages from database attachments into the immutable page inventory;
   loading again reuses identical snapshots. Three demo pages are preselected.
2. In **Saved pages**, inspect the SEM English card's **parsed text**. The preview
   uses the configured extraction profile's normalization and content filters.
   The current V3 profile excludes generic contact, navigation, feedback and news.
3. Keep SEM English selected and deselect the other two demo pages. Click
   **Preview extraction plan**. The worker runs the real CLI in dry-run mode.
4. In **Builds & review**, inspect the page and request estimates. The plan sends
   zero model requests. Download its full report. V4 plans also show a block inventory.
5. In **Stored knowledge**, browse Zurich and SEM excerpts and original citations.
   These are the existing experimental releases, not published facts.

## Crawl and extract new material

Downloaded corpora can be imported with the [corpus importer](../../docs/storage.md#import-downloaded-source-corpora).
In **Saved pages**, choose **Corpus -> Hackathon MVP - Residence permit in Switzerland**
(`hackathon-residence-2026-09-10`) to show its 121 downloaded files. Choose
**Earlier attempts / ungrouped pages** to return to older assets. The 8 PDFs and
8 application shells are marked **Archive only**; 105 HTML/text inputs pass the
basic acquisition checks. New jobs and their extraction reports retain the corpus
ID. Importing pages stores source material; processing and publication are later
operations.

- **Sources -> Review crawl -> Confirm crawl** fetches the selected allowlisted
  sources with the existing `smoke` crawl profile and robots enforcement. At most
  ten sources can be selected per job. Downloaded UTF-8 pages and crawl provenance
  are retained; partial/failed crawls remain visible. Review needed/manual sources
  cannot be started from this console. Edit the existing source catalog to add
  new approved source definitions; arbitrary URL crawling is not exposed.
- **Upload a page** accepts UTF-8 HTML, text and Markdown up to 2 MB, associated
  with a source chosen from the catalog. That association is an operator
  declaration, not verified crawl provenance. PDF and JavaScript rendering are
  not supported by this increment.
- **Saved pages -> Preview extraction plan** checks selected content and request
  budgets without contacting a model. A maximum of ten pages is supported; the
  existing semantic config may impose stricter input and request limits.
- **Run extraction -> Confirm extraction** runs the configured extractor and
  model-assisted review using a selected named model profile. The current
  extraction profile is `concept_extraction_v3`, independently of the selected
  DeepSeek V4.1 Flash model. Change `extraction.prompt_profile` in
  `config/semantic-models.toml` to select another extraction workflow.
  Profiles in `config/semantic-models.toml` refer to Ollama/Hugging Face/Groq/DeepSeek definitions
  in the shared `config/model-profiles.toml` catalog.
  For GPT-OSS 120B extraction and review, set `GROQ_API_KEY` before launching
  and select `groq_gpt_oss_120b`. Ranking remains an independent selection.
  For the default DeepSeek V4.1 Flash model, set `DEEPSEEK_API_KEY` before
  launching and select `deepseek_v4_1_flash`; Pro remains available as
  `deepseek_v4_pro`. See the [setup details](../../config/README.md#deepseek-v41-flash).
- Each job freezes its source catalog or fully resolved model configuration;
  queued extraction jobs do not depend on later shared model catalog edits. Automatic
  provider retries are disabled; V4 extraction repairs remain bounded by the
  displayed attempt ceiling. V3 has no structured repair loop. A run over its plan
  budget fails before inference.
- V3 candidates show scope, questions and source quotes; saved V4 candidates
  retain their structured claims. Record **accept draft**,
  **needs changes** or **reject**, with a reviewer name and notes. Each press of
  **needs changes** or **reject** opens a dialog for that candidate with a fresh
  comment field and the reviewer name. Enter a comment and choose **Save review**,
  or **Cancel** to leave the decision unchanged. Saving confirms the review beside
  the candidate without scrolling to the top; a failed save keeps the dialog and
  comment available to retry. Acceptance uses the separate optional acceptance note.
  Decisions append to a history bound to the exact result hash and candidate ID.
  They are local authoring annotations, not independent semantic verification or
  release approval.

`Needs attention` includes extraction reports with zero candidates, warnings or
rejections even if the CLI returned exit code 0. A completed job is not a semantic
quality pass. Original reports remain downloadable. No action replaces an existing
serving release or creates embeddings/publication automatically. A full validated
build-to-release pipeline remains future work.

## Persistence and operation

Migration `002_admin.sql` adds `admin_assets`, `admin_jobs` and `admin_reviews` to
the existing `swisstip` schema. Raw page bytes and review records are immutable;
job lifecycle rows are mutable. The queue is serialized by a worker advisory lock.
The API returns a job ID immediately and the browser polls status. Queued jobs
survive a restart; previously running jobs become `interrupted` when the worker
restarts and are never automatically retried.

The worker creates `.local/admin/jobs/<job-id>/` for input copies, frozen config,
stdout reports, progress logs and model checkpoints. Results and bounded logs are
also saved in PostgreSQL. DB backups include page bytes, job results and draft
decisions; back up `.local/admin/` separately to retain every checkpoint and full
local log. Provider credentials are excluded from browser payloads and redacted
from displayed progress. Jobs have a one-hour execution and 20 MB output/log cap.

This is a single-operator localhost tool. Host/origin checks and a custom request
header protect mutations from ordinary cross-site browser requests; there is no
shared-user login or remote deployment authorization. The launcher binds only to
`127.0.0.1`. Do not expose it on the LAN without implementing that control plane.

## Development and checks

To regenerate API types/SDK after API changes, then build:

```shell
./.venv/Scripts/python.exe scripts/admin/export_openapi.py
npm --prefix apps/admin-console run generate
npm --prefix apps/admin-console run build
```

For frontend hot reload, run `npm --prefix apps/admin-console run dev` alongside
the launcher and open http://127.0.0.1:5173. Vite proxies `/api` to port 8000.

PowerShell database integration tests create and remove a new disposable database:

```powershell
$env:SWISSTIP_TEST_DATABASE_URL = (Get-Content -LiteralPath .local/postgres-dsn.txt -Raw).Trim()
./.venv/Scripts/python.exe -m unittest discover -s apps/control-api/tests -v
```

With the console running and pilot corpus imported:

```shell
node apps/admin-console/browser-smoke.mjs
```

The browser smoke uses installed Edge on Windows (headless) or Playwright Chromium
on Unix. It loads saved pages, inspects parsed text, completes a real offline plan,
browses stored evidence and checks mobile overflow. It creates one plan job in the
pilot database and sends no crawl/model requests. Results and screenshots are
saved under `.local/admin/`.

To check candidate review dialogs against the running console:

```shell
node apps/admin-console/review-dialog-smoke.mjs
node apps/admin-console/v3-extraction-smoke.mjs
```

This focused browser check intercepts all API requests with synthetic data. It
checks comments, cancellation, submission and retry, scroll position, and mobile
layout without creating jobs or changing saved review decisions.
The V3 check also covers Flash selection, parsed-source preview, request plans,
scope/questions/evidence and historical V4 plans and claims, with all API requests
mocked. Screenshots and reports are saved under `.local/admin/v3-extraction-smoke/`.

Dependency versions are pinned in `package-lock.json`. TypeScript 5.9.3 is used
for compatibility with the generator; the `js-yaml` override selects its patched
4.3.1 release. Implementation follows the [repository GUI design](../../docs/architecture/technical-specification.md#161-recommended-implementation-stack)
and [Mantine Vite setup](https://mantine.dev/guides/vite/).

Verified on 2026-09-08: the production frontend build, ten Control API/worker
database tests, 73 runtime tests and four MCP tests passed. The real-browser
smoke passed desktop and mobile checks with the saved pilot and a real worker;
it sent zero crawl/model requests. Live extraction and crawling reuse existing
adapters but were not rerun against external services for this GUI change.
