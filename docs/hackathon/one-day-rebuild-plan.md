# One-day team rebuild plan - four developers, AI-assisted

Prepared on 2026-09-11 from the current `main` (`4466a1b`). This plan splits
the existing SwissTIP code into four parallel workstreams so that four developers
can reproduce it in one working day with AI-assisted development. It also records
how to reuse the existing residence knowledge base instead of downloading and
processing real data again, which is the slow part of the pipeline.

Scope statement: the repository holds about 12,400 lines of Python source,
12,000 lines of tests, 2,000 lines of hand-written TypeScript and 10,000 lines
of scripts. Reproducing all of it at line-for-line fidelity in one day is not
realistic. The plan therefore reproduces behaviour, not text: the existing test
suites, READMEs, contracts and saved data are the specification, and each
workstream has a must / should / stretch ordering. Whatever is not finished by
the afternoon checkpoint is bridged with the original package so that the
end-to-end chain still runs at the end of the day.

Decision of 2026-09-11: the hackathon MVP has no PostgreSQL. The demo serves
bundled `release.json` files from the file-backed release store. The curated
release covers federal requirements, Zurich canton and city procedures and the
migration contacts of all 26 cantons in one 1.2 MB file; the two small
nationwide parts can be served alongside it. The control API and the studio
exist only on PostgreSQL today, so they leave the MVP as well and appear only
as a stretch item on a file-backed store.

## 1. What exists today

| Area | Location | Source lines | Tests today | Entry points |
| --- | --- | --- | --- | --- |
| Shared contracts | `packages/core` | 1,756 | 85 pass | `python -m swisstip.core.schemas --check` |
| Acquisition and extraction library | `packages/ingestion` | 4,235 | 171 pass | imported by the builder |
| Structured knowledge runtime | `packages/runtime` | 2,155 | 81 pass, 7 skipped without PostgreSQL | `python -m swisstip.runtime.fixture`, `python -m swisstip.runtime.evaluation` |
| Knowledge builder CLIs | `apps/knowledge-builder` | 3,416 | 182 pass | `swisstip-crawl`, `swisstip-concepts`, `swisstip-download`, `python -m swisstip.builder.source_cli` |
| MCP server | `apps/mcp-server` | 169 | 4 pass | `python -m swisstip.mcp_server.server` |
| Control API and worker (needs PostgreSQL; outside the MVP) | `apps/control-api` | 652 | 22 pass, 11 skipped without PostgreSQL | `python scripts/admin/run.py` |
| Knowledge studio (React; needs the control API; outside the MVP) | `apps/admin-console` | about 2,000 hand-written, 2,900 generated | 3 browser smoke scripts | `npm run build`, launcher serves it on port 8000 |
| Offline corpus pipeline | `scripts/corpora` | about 4,300 | 36 standalone tests | see [scripts/corpora/README.md](../../scripts/corpora/README.md) |
| Mock MCP server and OpenCode harness | `scripts/test/mock-mcp` | about 820 | self-check script | `check_mock_mcp.py`, `run_opencode_test.py` |
| Storage scripts (PostgreSQL; outside the MVP) | `scripts/storage`, `compose.yaml` | about 500 | covered by runtime and control-api DB tests | `init_local.py`, `migrate_pilot.py`, `smoke_pilot.py`, `import_corpus.py` |
| Configuration | `config/` | TOML and JSON | freshness check | `scripts/catalogs/refresh_hackathon.py --check` |

Test counts were rerun on 2026-09-11 in the repository `.venv` (Python 3.14.3).
No suite needs the network; the PostgreSQL tests skip without
`SWISSTIP_TEST_DATABASE_URL`.

Verified tool versions on the reference machine: Python 3.14.3 in `.venv`,
Node 24.14.1, npm 11.11.0, Docker 29.2.1, OpenCode 1.18.29, `mcp` SDK 1.29.1,
Pydantic 2.13.5, FastAPI 0.141.1, psycopg 3.3.5.

The dependency direction is fixed and must be kept in the rebuild:

```text
core  <-  runtime  <-  mcp-server                      (MVP serving path, file-backed)
core  <-  ingestion  <-  knowledge-builder             (MVP build path)
scripts/corpora uses core + runtime contracts only (no builder import except assistant_extraction.py)
runtime[postgres]  <-  control-api  <-  admin-console   (outside the MVP)
```

## 2. Ground rules for the day

1. **One rebuild repository, same layout.** Create a fresh Git repository (for
   example `swisstip-rebuild`) on a local, non-OneDrive path with the same tree:
   `packages/core`, `packages/ingestion`, `packages/runtime`, `apps/knowledge-builder`,
   `apps/mcp-server`, `apps/control-api`, `apps/admin-console`, `scripts/`, `config/`.
   Keep the distribution names (`swisstip-core`, `swisstip-ingestion`,
   `swisstip-runtime`, `swisstip-knowledge-builder`, `swisstip-mcp-server`,
   `swisstip-control-api`) and the `swisstip.*` namespace packages so that
   reference and rebuilt packages can be mixed in one virtual environment.
2. **Starter kit copied before work starts** (data, not code):
   `packages/core/schemas/contracts-v1.schema.json`, everything under `config/`,
   `packages/ingestion/src/swisstip/ingestion/prompts/*.md`, every `tests/`
   directory including `packages/ingestion/tests/fixtures`, the standalone test
   files in `scripts/corpora/test_*.py`, `scripts/corpora/residence_mvp_curated.py`
   (a data module), `apps/admin-console/openapi.json`, `package.json` and
   `package-lock.json`, `compose.yaml`, all READMEs and `docs/`. The tests are
   the specification; nobody rewrites them.
3. **Mixed environment per developer.** Each developer installs the reference
   checkout's packages editable for everything they do not own, and their own
   rebuilt package editable for what they own. At each checkpoint a reference
   package is swapped for the rebuilt one. Example for developer A while the
   runtime is still in progress:
   `pip install -e REBUILD/packages/core -e REF/packages/runtime -e REF/apps/mcp-server`.
4. **Closed book with a timebox.** The AI agent gets the README, the relevant
   specification sections, the copied tests and the fixtures, and implements
   until the tests pass. The reference implementation is opened only after 30
   minutes stuck on one test, and the decision is noted in the commit message.
5. **Definition of done per module.** The copied unit tests pass, the listed CLI
   or API command produces the same observable result as the reference
   (counts, statuses, hashes where the reference records them), and the module
   makes no network or model call unless the command explicitly asks for one.
6. **Bridge rule at 15:30.** Any module not done stays on the reference package.
   The end-of-day demo shows the chain, and the retro lists which packages are
   rebuilt and which are bridged.
7. **Conventions from `AGENTS.md`.** Repository-local `.venv`, ASCII hyphens
   only, Python 3.11 or newer, `unittest` as the runner, one-line commit
   subjects in the style of the recent history.
8. **Credentials.** `.env.dev` in the reference checkout contains live
   Hugging Face, Groq and DeepSeek keys and is Git-ignored. Hand keys out through
   a secure channel, set them as environment variables, and never copy the file
   into the rebuild repository. Only developer C needs a key on the day
   (`DEEPSEEK_API_KEY`); every other task runs without one.
9. **No database.** Nothing in the MVP reads or writes PostgreSQL. The server
   is started with one or more `--release` files and `--active-release-id`;
   `--database-dsn-env`, `compose.yaml` and `scripts/storage` stay unused.

## 3. Workstreams

### Developer A - contracts, runtime and MCP server

Mission: a standard MCP client can discover the catalog, submit
`structured-grounding/v1` and read cited evidence from the bundled curated
residence release through the file-backed release store.

| Priority | Module | What to reproduce | Inputs |
| --- | --- | --- | --- |
| Must | `packages/core/src/swisstip/core/contracts.py` | 55 strict Pydantic models; schema versions `structured-grounding/v1`, `get-coverage/v1`, `get-evidence/v1`, `tool-error/v1`, `knowledge-catalog/v1`, `knowledge-release/v1`, `coverage-profile/v1`, `context-schema/v1`, `evidence-object/v1` and `/v2`, `published-fact/v1`, `published-rule/v1`, `resolution-graph/v1`, `normalized-evidence-document/v1`, `tip-language-catalog/v3` and `/v4`, retrieval artifacts | Frozen schema bundle, [core README](../../packages/core/README.md), technical specification sections 9 and 14, `tests/test_contracts.py` |
| Must | `core/identity.py`, `core/validation.py`, `core/schemas.py` | Canonical sealing, `validate_catalog`, `validate_request` with `INVALID_ARGUMENT` / `NEEDS_CONTEXT` / `OUT_OF_COVERAGE` / `RELEASE_UNAVAILABLE`, schema export that passes `--check` against the frozen bundle | `tests/test_validation.py`, `test_identity.py`, `test_seed_catalog.py` |
| Must | `packages/runtime/.../release.py`, `service.py`, `fixture.py` | `ReleaseBundle` and `validate_release` (hash, reference, span and profile checks), `ReleaseStore.from_files`, `KnowledgeService.get_coverage` / `resolve` / `get_evidence` with HMAC cursors, exact jurisdiction matching, rule execution, deterministic lexical baseline, freshness | [runtime README](../../packages/runtime/README.md), `tests/test_service.py`, `test_corpus.py` |
| Must | `apps/mcp-server/.../server.py` | Three tools over stdio, repeatable `--release`, inlined input schemas, the tool descriptions from the 11 September real-server test, typed `isError` for tool errors; the `--database-dsn-env` option is not needed | [MCP README](../../apps/mcp-server/README.md), `tests/test_server.py` |
| Should | `runtime/retrieval.py`, `hybrid_fixture.py`, `evaluation.py` | Scoped hybrid retrieval with reciprocal rank fusion, synthetic semantic provider, gold-case evaluation gates | `tests/test_retrieval.py`, [BUILD-05 record](../experiments/2026-09-07-build05-retrieval.md) |
| Stretch | `runtime/providers.py`, `provider_config.py` | Ollama embedding/ranking, Groq and DeepSeek ranking adapters, named retrieval profiles | `tests/test_retrieval_providers.py`, `config/retrieval-models.toml` |

Definition of done for the day:

- The curated release `hackathon-residence-semantic-2026-09-11-v2` loads and
  validates (83 facts, 83 evidence objects, 20 rules, 35 concepts, 60 coverage
  profiles, SHA-256 `43a50b52...`).
- All 60 prepared resolve requests and the four negative cases in its
  `mcp-requests.json` return the recorded statuses through the rebuilt service.
- The four MCP tests pass against the rebuilt server.
- Developer D's OpenCode run with `--server real` against the rebuilt server
  reaches the expected deadlines in both scenarios (see section 5). This is the
  standing integration test recorded as POC-12 in the backlog.

Handoffs: developer D runs the caller harness against A's server and packages
its release files; developer B validates the rebuilt release with A's
validator; developer C's concept pack and the nationwide parts 003 and 004 are
served as further `--release` files.

### Developer B - source acquisition and offline corpus-to-release pipeline

Mission: from the saved 2026-09-10 corpus, rebuild the intermediate text
dataset and the curated serving release with identical counts, and show that
the bounded crawler and catalogue downloader work on a five-page smoke run.

| Priority | Module | What to reproduce | Inputs |
| --- | --- | --- | --- |
| Must | `packages/ingestion/.../crawler.py` | `SafeCrawler`: breadth-first, robots per origin and before every hop, host/path allowlists, public-IP-only, request/byte/duration budgets, 429/503 stop, `nofollow` | `tests/test_crawler.py`, FIX-01 and FIX-02 in `TODO.md` |
| Must | `apps/knowledge-builder/.../cli.py` | `swisstip-crawl` with `--dry-run` and the JSON scan report | `tests/test_cli.py` |
| Must | `builder/source_catalog.py`, `source_cli.py` | Offline validation and crawl plans for the 59-source catalogue, sets `smoke`, `multilingual`, `zurich`, `federal`, `cantons`, `all`, German-first ordering, parallel-page groups | [catalogue README](../../config/catalogs/README.md), `tests/test_source_catalog.py` |
| Must | `ingestion/acquisition.py`, `source_plugins.py`, `sources/fedlex.py`, `source_snapshots.py`, `builder/download_cli.py`, `plugin_downloads.py` | Catalogue downloader with `pages/<url-sha256>/attempt-NNN/` layout, manifests, hash reuse, Fedlex ELI resolution to dated HTML/PDF | `tests/test_source_plugins.py`, `test_plugin_downloads.py`, `tests/fixtures` |
| Must | `scripts/corpora/extract_intermediate.py` | HTML/PDF to `swisstip.source-intermediate/v1`: blocks with DOM paths, offsets, per-block hashes, `text_integrity`, shells and maintenance pages excluded, PDF pages via pypdf | `scripts/corpora/test_extract_intermediate.py`, README section "Output" |
| Must | `scripts/corpora/build_residence_mvp.py` (+ copied `residence_mvp_curated.py`) | Packages curated claims into `serving-release/v1`, writes `mcp-client.json`, `mcp-requests.json`, `validation.json`, `provenance.json`, `source-disposition.json`; refuses to overwrite | [corpora README](../../scripts/corpora/README.md) "Semantic MVP release" |
| Should | `scripts/catalogs/refresh_hackathon.py`, `scripts/corpora/retry_failed_downloads.py` | Reseal the seed catalogue and language policy; paced host-by-host retry | `test_retry_failed_downloads.py` |
| Stretch | `audit_source_languages.py`, `extract_expanded.py`, `extract_source_assertions.py`, `build_expanded_pack.py`, `finalize_expanded.py` | Nationwide language audit, sharded extraction, Lingua-based assertions, multi-part packs. Reproduce code only; do not run the nationwide download on the day | `test_expanded_pack.py` |

Definition of done for the day:

- `python -m swisstip.builder.source_cli --dry-run` and `--set all --dry-run`
  produce plans with 59 references, 53 eligible and six excluded, no network.
- `extract_intermediate.py` over `.local/corpora/hackathon-residence-2026-09-10`
  yields 121 records, 111 extracted responses, 10 excluded, 26,179 blocks and
  414 PDF pages, and the curated block coordinates still line up (the release
  builder raises "Curated block text or offsets changed" otherwise).
- `build_residence_mvp.py` writes a release that developer A's validator
  accepts with the same counts as the reference `validation.json`.
- One live smoke crawl (five sources, at most 25 requests) saves HTML with
  manifests. This is the only live acquisition of the day.

Handoffs: the intermediate dataset goes to developer C for dry runs; the rebuilt
release goes to developer A for validation and to developer D for bundling.

### Developer C - semantic extraction and model adapters

Mission: the V3 concept extractor plans and runs over saved pages with exact
evidence, model-assisted review, budgets and checkpoints, selectable through the
shared model catalogue.

| Priority | Module | What to reproduce | Inputs |
| --- | --- | --- | --- |
| Must | `packages/ingestion/.../concepts.py` | Normalizer (HTML to sections with contact/navigation/news filters), chunking with overlap, V3 request and response schema, numbered spans with Python-attached exact quotations, candidate rejection on non-exact evidence, `CandidateConcept` contract | `tests/test_concepts.py`, `test_concept_quality.py`, `test_related_navigation.py` |
| Must | `ingestion/concept_review.py`, `prompt_templates.py` (+ copied prompts) | Separate bounded review call with issue vocabulary; packaged prompts and per-run file overrides with hashes | `tests/test_concept_review.py`, `test_prompt_templates.py`, [prompts README](../../packages/ingestion/src/swisstip/ingestion/prompts/README.md) |
| Must | `core/model_profiles.py`, `builder/model_profiles.py`, `provider_factory.py` | Shared TOML catalogue plus role files, `active_profile` switching, identity fields locked, fail-closed selection | `config/*.toml`, `tests/test_model_profiles.py`, `test_provider_factory.py`, `core/tests/test_model_catalog.py` |
| Must | `core/deepseek.py`, `builder/deepseek_provider.py`, `ingestion/ollama.py` | DeepSeek JSON-object chat with thinking off and identity checks; Ollama structured generation | `core/tests/test_deepseek.py`, `builder/tests/test_deepseek_provider.py`, `ingestion/tests/test_ollama.py` |
| Must | `builder/concept_cli.py`, `concept_batch.py`, `concept_recovery.py` | `swisstip-concepts`: paths, directories, wildcards, `--dry-run`, `--config`, `--checkpoint-dir`, `--fresh-inference`, `--compact`; page/request/character budgets checked before the first call; conservative consolidation; checkpoint v2 with identity revalidation and bounded retries | [builder README](../../apps/knowledge-builder/README.md), `tests/test_concept_cli.py`, `test_concept_batch.py`, `test_concept_recovery.py` |
| Should | `builder/huggingface_provider.py`, `groq_provider.py` | Apertus via Hugging Face router with PublicAI fallback disabled and alias policy; Groq strict schema | `tests/test_huggingface_provider.py`, `test_review_fallback.py` |
| Should | `builder/experimental_knowledge.py`, `scripts/corpora/build_concept_pack.py` | Candidate bundle with search, and packaging retained candidates into a `serving-release/v1` part | `tests/test_experimental_knowledge.py`, `scripts/corpora/test_build_concept_pack.py` |
| Stretch | `ingestion/source_structure.py`, `claim_contracts.py`, `structured_extraction.py`, `builder/extraction_review.py`, v4 prompts | V4: logical blocks v3, structured claims v2, coverage audit, bounded repair, offline review packets | `tests/test_structured_extraction.py`, `test_structured_workflow.py`, [V4 record](../experiments/2026-09-06-structured-extraction.md) |

Definition of done for the day:

- `swisstip-concepts <SEM EN page> --config config/semantic-models.toml --dry-run`
  prints a plan with `effective_prompts`, request estimates and zero model calls.
- A live V3 run with `deepseek_v4_1_flash` on one to three saved pages writes a
  `swisstip.concept-proposal-batch/v1` report whose retained candidates all have
  exact quotations and review verdicts, with `model_identities` recorded.
- An over-budget batch fails before the first model call.
- `test_concepts.py` and `test_concept_cli.py` pass against the rebuilt code.

Handoffs: the proposal report goes through `build_concept_pack.py` to a release
part that developer A serves and developer D bundles.

### Developer D - caller demo, release bundle and delivery

Mission: a jury member can start the demo from a clean checkout with one
bundled `release.json`, one MCP client configuration and one command; an
unguided OpenCode caller answers the Zurich registration question against the
file-backed server; and the same bundle runs on a second machine after a
checksum verification. No database anywhere.

| Priority | Module | What to reproduce | Inputs |
| --- | --- | --- | --- |
| Must | `scripts/test/mock-mcp/mock_residence_mcp.py`, `check_mock_mcp.py` | Stdio MCP server with constants only, three tools, `NEEDS_CONTEXT`, `OUT_OF_COVERAGE`, `required_user_facts`; the self-check prints 13 `ok` lines. First hour: smallest surface, gives the harness a target | [mock-mcp README](../../scripts/test/mock-mcp/README.md) |
| Must | `scripts/test/mock-mcp/run_opencode_test.py`, `Start-OpenCodeDesktop.ps1` | OpenCode harness: generated `opencode.json`, `residence-assistant` agent, `--server mock|real`, `--release-file`, `--release-id`, raised tool-output cap, two date scenarios, heuristic assessment; desktop launcher | [real-server test record](../experiments/2026-09-11-opencode-real-mcp-caller-test.md) |
| Must | New: `scripts/demo/` bundle and setup tooling (MVP plan step A4) | Copy one or more validated release directories into `demo-bundle/` with `mcp-client.json` paths rewritten for the target checkout, `checksums.sha256`, a README with the start command and the two demo questions; a setup script that creates `.venv`, installs core, runtime and mcp-server, verifies checksums and runs the mock self-check and a real-server `--check-connection` | [operations guide](hackathon-operations.md) sections 4 and 6, MVP plan step A4 |
| Must | `scripts/corpora/live_mcp_check.py` | Live stdio check over the served parts: `calls.jsonl`, `summary.json`, README digest, jurisdiction-balanced fixture sample, negative and boundary cases; expects the expanded fixture layout, so run it over parts 003 and 004 | `scripts/corpora/test_live_mcp_check.py` |
| Should | New: release-store cache (MVP plan step A1) | Cache validated bundles per release ID inside `ReleaseStore` while preserving immutability, with a regression test; the runtime re-parses a pinned release on every call today, which is why parts 001 and 002 answer in 5 to 9 s | MVP plan section 4, `runtime/tests/test_service.py` |
| Should | `scripts/corpora/assemble_collection.py` | Copies validated parts unchanged into one collection with a root `mcp-client.json` and `collection.json`; re-running adds only new hashes | [corpora README](../../scripts/corpora/README.md) "Extending a collection" |
| Stretch | `apps/control-api` and `apps/admin-console` on a file-backed store | The existing code needs PostgreSQL; a file-backed `store.py` and worker lock would be a deliberate deviation from the reference, only if everything above is done | [studio README](../../apps/admin-console/README.md) |
| Excluded | `runtime/postgres.py`, `runtime/corpus.py`, `runtime/migrations`, `compose.yaml`, `scripts/storage` | Out of the MVP by the 2026-09-11 decision; remain reference material | [storage guide](../storage.md) |

Definition of done for the day:

- The mock self-check prints 13 `ok` lines from the rebuilt mock server.
- The OpenCode run with `--server real` against developer A's rebuilt server
  reaches the expected deadlines in both scenarios (the POC-12 test).
- A second machine, from a clean checkout and the bundle, completes the written
  setup steps, verifies the checksums, starts the server on the bundled
  `release.json` and passes `--check-connection` without touching `.local/` of
  the reference machine.
- `live_mcp_check.py` over parts 003 and 004 records zero contract failures and
  every negative expectation met, as in the 11 September check.

Handoffs: developer A's server and developer B's rebuilt release are the inputs;
developer C's concept part is added to the bundle as a further release file.

## 4. Timeline and checkpoints

Times assume a 09:00 to 18:00 day; shift them as needed.

| Time | All | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| 08:30 | Kickoff: rules, starter kit, data bundle, keys, branches, agent setup | | | | |
| 09:00 | | Contracts | Crawler and `swisstip-crawl` | Normalizer and V3 schema | Mock server and self-check |
| 10:30 | | Validation, sealing, schema `--check` | Catalogue validation and plans | Model catalogue and DeepSeek adapter | OpenCode harness against the mock, then against the reference real server |
| **11:30** | **Checkpoint 1**: A serves the reference curated release over stdio from the rebuilt core; D's harness connects to it; B's dry-run plans match; C's dry run works on the reference corpus | | | | |
| 12:30 | Lunch | | | | |
| 13:00 | | Runtime service and MCP server | Downloader and Fedlex plugin, `extract_intermediate.py` | `swisstip-concepts` CLI, budgets, checkpoints | Bundle and setup tooling, checksums, demo README |
| **14:30** | **Checkpoint 2**: rebuilt release validates through rebuilt core; C runs one live V3 page; D's harness runs against A's rebuilt server | | | | |
| 14:30 | | Hybrid retrieval (should) | `build_residence_mvp.py` | Live V3 run, `build_concept_pack.py` | Release-store cache, multi-release server with parts 003 and 004 |
| **15:30** | **Bridge decision**: swap remaining reference packages in or out, freeze the demo bundle | | | | |
| 15:30 | | Should items | Smoke crawl | Should items | `live_mcp_check.py`, second-machine rehearsal from the bundle |
| 16:30 | **End-to-end run**: saved corpus -> intermediate -> curated release -> bundled `release.json` on the file-backed server -> OpenCode answers the Zurich question; C's concept part and parts 003 and 004 served alongside | | | | |
| 17:15 | Retro: rebuilt versus bridged packages, test counts, what to keep | | | | |

Integration order matters: A's contracts unblock everyone's validation, so A
publishes the rebuilt core package at checkpoint 1 even if the runtime is
unfinished. D starts with the mock server because it is the smallest surface
and gives the harness a target before A's server exists.

## 5. Option: use the existing residence knowledge base

Downloading and processing the real sources is the slow path. The nationwide
audit fetched 12,117 responses over several sessions and its extraction, OCR and
packaging ran in sharded batches. None of that should run on the day. Everything
below is already on the reference machine under `.local/`, which is Git-ignored,
so it must be copied to each developer separately.

### Level 0 - serve the bundled release (seconds; the MVP demo data)

`.local/mvp/residence-semantic-2026-09-11-v2/` (4.5 MB) is the release used by
the successful OpenCode test. Its single `release.json` covers federal
requirements, Zurich canton and city procedures and the migration contacts of
all 26 cantons from 12 saved official pages: 83 facts, 20 rules, 35 concepts
and 60 coverage profiles. Contents: `release.json` (1.2 MB, the
`serving-release/v1` bundle), `mcp-client.json`, `mcp-requests.json` (discovery,
60 resolve examples, four negative cases, one evidence request),
`validation.json`, `provenance.json`, `semantic-extraction.json`,
`source-disposition.json`, `contacts.json`, `sources/` (raw snapshots) and
`controls/`.

```shell
./.venv/Scripts/python.exe -m swisstip.mcp_server.server --release .local/mvp/residence-semantic-2026-09-11-v2/release.json --active-release-id hackathon-residence-semantic-2026-09-11-v2
```

Notes:

- `mcp-client.json` contains absolute Windows paths of the reference machine;
  rewrite `command` and `--release` for each developer's checkout.
- Requests must pin `as_of` inside the frozen window 2026-09-10 to 2026-09-11.
- Jurisdictions match exactly: federal concepts take the country only, Zurich
  concepts need `CH-ZH`, the city concept needs municipality `261`; one concept
  per resolve; `population: eu_efta` for the Zurich EU/EFTA concepts.
- Topic-level `get_coverage` returns 120 to 145 KB; raise OpenCode's tool-output
  cap to 400,000 bytes (the harness does this).
- The v1 release in the sibling directory lacks the SEM free-movement FAQ
  concept and fails the work-first scenario; use v2.

The standing caller integration test:

```shell
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --check-connection
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --live
```

Question sent in turn 1: "I'm a Czech citizen and starting my work in Zurich
next week. By when latest should I register my stay on the municipal
authority?" Expected: both limits stated (within 14 days of arrival and before
starting work), no date computed before the arrival date is known, then in
turn 2 register before 16 September for the `work-first` scenario and by
15 September for `fourteen-days-first`. The model is
`opencode/ling-3.0-flash-fin-free` and needs internet access; without it, use
`check_mock_mcp.py` style calls from the recorded transcript in the
[real-server test record](../experiments/2026-09-11-opencode-real-mcp-caller-test.md).

### Level 1 - rebuild the curated release from the saved corpus (minutes)

- Raw corpus: `.local/corpora/hackathon-residence-2026-09-10/` (23 MB; 121
  snapshots, 107 of 115 catalogue URLs plus 14 Fedlex files; attempt folders
  with manifests). It is read directly from disk; no import step exists in the MVP.
- Intermediate dataset: `.local/intermediate/hackathon-residence-2026-09-11-v1/`
  (61 MB; 121 records, 26,179 blocks, `documents.jsonl`, `validation.json`).
- Release builder: `scripts/corpora/build_residence_mvp.py --output NEW_DIR --release-id NEW_ID`.
  The curated block coordinates are pinned to the intermediate export hash, so
  keep the intermediate directory unchanged or regenerate it with the same
  extractor before building.

```shell
./.venv/Scripts/python.exe -m pip install -r scripts/corpora/requirements.txt
./.venv/Scripts/python.exe scripts/corpora/extract_intermediate.py --corpus .local/corpora/hackathon-residence-2026-09-10 --output .local/intermediate/rebuild-check
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/rebuild-check --release-id hackathon-residence-semantic-rebuild-check
```

Refreshing the corpus itself (`swisstip.builder.download_cli --download`, 115
URLs, robots-paced, plus Fedlex resolution) takes minutes and is the only
acquisition worth running live; it changes hashes, so the curated coordinates
would then need a review.

### Level 2 - nationwide collection (do not rebuild on the day)

`.local/mvp/residence-all-languages-2026-09-11-v2/` holds four parts with a root
`mcp-client.json` and `collection.json`:

| Part | Release ID | `release.json` | Content | Call latency |
| --- | --- | --- | --- | --- |
| 001 | `hackathon-residence-all-languages-2026-09-11-v1-part-001` | 520 MB | Source assertions, first half | 5 to 9 s; startup about 100 s |
| 002 | `...-v1-part-002` | 283 MB | Source assertions, second half | 5 to 9 s |
| 003 | `...-v2-part-003` | 15 MB | 333 recovered documents | under 1 s |
| 004 | `...-v2-part-004` | 3.5 MB | 377 assistant-authored V3 concept candidates on 81 pages | under 1 s |

For a fast "nationwide" flavour add parts 003 and 004 as further `--release`
arguments next to the curated release; the active release stays the curated
one and callers pin the part IDs explicitly. Parts 001 and 002 exist only to
show scale; the runtime
re-parses the pinned release on every call, so they are slow until the
release-store cache from the MVP plan (step A1) exists. The raw nationwide corpus
(`.local/corpora/hackathon-residence-all-languages-2026-09-11/`), the
intermediate and semantic directories, OCR jobs and the live-check results under
`.local/evaluations/` are reference material, not day inputs.

### Not used - PostgreSQL pilot

`.local/database/backups/*.dump` and `scripts/storage/migrate_pilot.py` belong
to the 8 September database pilot. They stay on the reference machine as
reference material and are not part of the MVP bundle.

### Transfer bundle

Copy these directories to a USB drive or share with a `checksums.sha256` file.
The minimum demo bundle is the 4.5 MB curated release; the rebuild inputs bring
the total to about 90 MB, and the optional collection parts add about 135 MB
because their `sources/` folders carry the raw snapshots (only their
`release.json` files, 15 MB and 3.5 MB, are needed to serve them):

```text
.local/mvp/residence-semantic-2026-09-11-v2/                    4.5 MB (release.json 1.2 MB)
.local/corpora/hackathon-residence-2026-09-10/                  23 MB
.local/intermediate/hackathon-residence-2026-09-11-v1/          61 MB
.local/mvp/residence-all-languages-2026-09-11-v2/part-003/      117 MB (optional)
.local/mvp/residence-all-languages-2026-09-11-v2/part-004/      18 MB (optional)
```

Do not put the rebuild checkout or the bundle inside OneDrive; the operations
guide records why.

## 6. Prerequisites checklist

| Developer | Needs |
| --- | --- |
| All | Git, Python 3.11 or newer with a fresh `.venv`, the starter kit, the transfer bundle, an AI coding agent with the reference checkout readable |
| A | `mcp` SDK 1.28 or newer; Pydantic 2 |
| B | `scripts/corpora/requirements.txt` (lxml, pypdf, pypdfium2, lingua, striprtf); internet for the single smoke crawl |
| C | `DEEPSEEK_API_KEY` for the live V3 run; optional `HF_TOKEN` and `GROQ_API_KEY`; Ollama only if the local profile is exercised |
| D | OpenCode 1.18.29 or newer with the free `opencode/ling-3.0-flash-fin-free` model reachable; a second machine or clean directory for the checkout rehearsal; no Docker, no Node |

## 7. Risks and fallbacks

- **Volume.** The test suites total about 12,000 lines; reusing them unchanged is
  what makes one day possible. Any developer who starts editing tests to fit an
  implementation is off plan.
- **Model access.** DeepSeek quota or outage blocks developer C's live run only;
  dry runs and checkpoint replay tests cover everything else. Extraction has no
  automatic provider fallback by design.
- **Caller model reachability.** The OpenCode run needs internet access to the
  free Ling model. Offline, developer D replays the recorded transcript through
  a standalone MCP client; the mock self-check and the live check need no model.
- **Slow releases.** Never serve parts 001 or 002 in a demo or test loop. The
  curated release and parts 003 and 004 answer in under a second.
- **No persistence layer.** Without PostgreSQL there is no job queue, saved-page
  inventory or review history; extraction runs from the CLI and its reports
  live under `.local/`. This is accepted for the MVP.
- **Absolute paths.** Every `mcp-client.json` and the `.local/opencode.json`
  pin the reference machine's paths. Rewrite them before use.
- **Ambiguity of "done".** A module counts as reproduced when the copied tests
  pass and the listed command matches the reference output. It does not need to
  match the reference source text.

## 8. Reference commands from the current repository

```shell
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests -v
./.venv/Scripts/python.exe -m unittest discover -s packages/ingestion/tests -v
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/knowledge-builder/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p "test_*.py"
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
./.venv/Scripts/python.exe scripts/catalogs/refresh_hackathon.py --check
./.venv/Scripts/python.exe scripts/test/mock-mcp/check_mock_mcp.py
```

On Unix substitute `./.venv/bin/python`. These are the baselines each rebuilt
package must reach before it replaces the reference package in a checkpoint.
