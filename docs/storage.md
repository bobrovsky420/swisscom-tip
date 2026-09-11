# Local PostgreSQL and pgvector storage

The [pilot handover](pilots/2026-09-08-retrieval-pilot.md) records model decisions,
corpora, hashes, failures and interpretation limits. Storage does not promote
the experimental pilot into approved knowledge.

## Implemented layout

One Compose service runs PostgreSQL 17 with pgvector 0.8.2, using a named Docker
volume and host binding `127.0.0.1:55432`. Ollama remains in WSL and Groq remains
an independent ranking service. No separate vector database is needed.

| Table | Contents |
| --- | --- |
| `swisstip.releases` | Original JSON bytes, file/canonical hashes, queryable JSONB, explicit test classification |
| `swisstip.artifacts` | Catalog entries, normalized documents, projections, policies and other sealed components |
| `swisstip.evidence` | Release-scoped IDs, revision hashes, original text, citations and complete evidence JSON |
| `swisstip.embeddings` | pgvector values with release/evidence/index/model/dimension bindings |
| `swisstip.attachments` | Exact archived crawl pages, manifests, selected reports/transcripts and replay controls |
| `swisstip.active_release` | Operational slot selection; not approval |
| `swisstip.schema_migrations` | Applied migration names and checksums |
| `swisstip.corpora` | Immutable acquisition run IDs, catalogue/inventory hashes and import counts |
| `swisstip.corpus_files` | Every original file in an acquisition run, including failed-attempt manifests |
| `swisstip.admin_assets` | Saved-page inventory, optional corpus ID, acquisition metadata and extraction eligibility |

Imports validate the existing release contract before writes, then insert all
components in one transaction. An identical import is idempotent. Different bytes
under the same release ID are rejected; UPDATE/DELETE/TRUNCATE triggers protect
stored corpus rows. New attachment names may be appended; existing ones cannot
be replaced. Concurrent importers are serialized. The active slot is mutable,
while existing server instances keep their explicitly selected release ID.

MCP loads release data from PostgreSQL and performs exact pgvector scoring over
only IDs already admitted by the runtime's scope rules. Lexical/concept matching,
fusion and final evidence assembly retain their existing Python implementations.
The complete sealed release is still parsed for each read; this is a storage
foundation, not a large-corpus query optimization. No approximate vector index
is enabled. File storage remains supported for portability and parity checks.

Original bytes preserve file hashes. JSONB and pgvector are derived query
representations: pgvector stores float32 components, so small score differences
are expected and measured. Model/index dimensions cannot be silently mixed.
The importer currently accepts only explicit `experimental`/`synthetic`
classifications; genuine publication remains future work.

## Setup and import

Run from the repository root with Docker Desktop's Linux engine available. The
commands below use the Windows repository interpreter; on Unix replace it with
`./.venv/bin/python`.

```shell
./.venv/Scripts/python.exe -m pip install -e "packages/runtime[postgres]"
./.venv/Scripts/python.exe scripts/storage/init_local.py
docker compose --env-file .local/postgres.env up -d --wait db
./.venv/Scripts/python.exe scripts/storage/migrate_pilot.py --dsn-file .local/postgres-dsn.txt
./.venv/Scripts/python.exe scripts/storage/smoke_pilot.py --dsn-file .local/postgres-dsn.txt
```

On Windows, explicitly select `docker --context desktop-linux` if the current
Docker context is different. Setup generates random credentials under `.local/`
without printing or replacing them. Compose interpolates `.local/postgres.env`;
the host client reads `.local/postgres-dsn.txt`. Both are Git ignored. The initial
local account owns the database; separate least-privilege deployment roles,
remote TLS and automated off-machine backups are not configured here.

The migration script imports the frozen SEM and Zurich releases (18 excerpts,
18 vectors, 90 projections total). It archives all eight raw crawl pages, their
manifests, selected pilot results and the handover. Extra crawled pages remain
archive material, not new serving evidence. Reruns append new immutable handover
revisions by content hash. The script verifies original raw snapshot hashes and
reports any unmatched external snapshot references rather than inventing them.
The source pilot files remain untouched. A fresh clone needs those ignored local
artifacts or a database backup; documentation alone does not recreate the corpus.

Migration and smoke reports are written under `.local/database/`. The smoke reads
corpus, archived controls and vectors from the database, verifies all attachment
hashes and both byte-identical release exports, and exercises ten real-database
runtime cases with recorded provider replay. It also starts an actual stdio MCP
server backed by PostgreSQL for discovery/evidence/unknown-release checks.
No live model calls occur. The notification vector predates the shortened query,
and partial-answer ranking comes from an earlier ranking-only run; these are
explicit storage-parity controls, not fresh semantic evaluations.

## Import downloaded source corpora

Raw acquisition runs can be loaded independently of serving releases:

```shell
./.venv/Scripts/python.exe scripts/storage/import_corpus.py --corpus .local/corpora/hackathon-residence-2026-09-10 --corpus-id hackathon-residence-2026-09-10 --title "Hackathon MVP - Residence permit in Switzerland" --report .local/database/corpus-hackathon-residence-2026-09-10.json
```

The importer verifies catalogue and snapshot hashes/sizes before writing. It
archives all local files and creates saved-page entries for every manifest-backed
download, in one transaction. All stored bytes are read back and verified. Same-ID,
same-content imports are idempotent; changed input requires a new corpus ID.
Existing assets, model jobs and serving releases remain separate historical records.
Keep the import report outside the source directory so reruns see identical input.

In **Saved pages**, use the **Corpus** selector to choose the new run or
**Earlier attempts / ungrouped pages**. Cards show the corpus ID. New extraction
jobs record their corpus IDs and restore the archived acquisition manifests so
source/version/hash provenance and the corpus ID reach the standard extractor.
PDFs, shells and other unsupported inputs remain visible as **Archive only** and
cannot be submitted for extraction. Eligibility only checks format, size,
encoding and acquisition flags; it does not certify substantive source content.

The 2026-09-10 MVP import contains **121 snapshots** (111 HTML, 2 text, 8 PDF)
and **415 archived files** totaling 23,032,644 bytes. There are 105 inputs eligible
for extraction and 16 archive-only inputs (8 PDFs, 8 shells). Failure records for
the 8 unavailable catalogue URLs are retained. The earlier 8 assets, 33 jobs,
2 releases, 18 evidence records and 239 release attachments are preserved. No
models ran and no evidence, embeddings or serving release was created.

Example database filter:

```sql
SELECT source_id, filename, processing_eligible, processing_reason
FROM swisstip.admin_assets
WHERE corpus_id = 'hackathon-residence-2026-09-10';
```

`GET /api/corpora` lists runs and their counts. `GET /api/assets?corpus_id=...`
filters before the 500-row display limit; `corpus_id=__legacy__` selects ungrouped
assets. As with the existing launcher, restart the API/worker after installing
updated code and build the frontend to expose new controls.

## Run MCP against the database

PowerShell:

```powershell
$env:SWISSTIP_DATABASE_URL = (Get-Content -LiteralPath .local/postgres-dsn.txt -Raw).Trim()
./.venv/Scripts/python.exe -m swisstip.mcp_server.server `
  --database-dsn-env SWISSTIP_DATABASE_URL `
  --active-release-id zh-runtime-harness-20260908-190309-949650 `
  --provider-config .local/live-retrieval-20260907-161418/zh-runtime-harness-20260908-190309-949650/providers.toml
```

This is stdio transport for an MCP client, not an HTTP endpoint. Live resolve
also needs reachable Ollama and `GROQ_API_KEY` in the process environment. Omitting
provider configuration allows database discovery/evidence reads, while hybrid
resolve fails with its normal typed operational error. The existing OpenCode
configuration is unchanged; explicitly configure a database-backed server when
ready. `--release` and `--database-dsn-env` are mutually exclusive.

## Backups, restart and restore

```shell
./.venv/Scripts/python.exe scripts/storage/backup_local.py --verify-restore
docker compose --env-file .local/postgres.env restart db
docker compose --env-file .local/postgres.env up -d --wait db
./.venv/Scripts/python.exe scripts/storage/smoke_pilot.py --dsn-file .local/postgres-dsn.txt
```

Backup uses binary-safe `pg_dump -Fc` and writes `.local/database/backups/*.dump`
plus a checksum report. Verification restores into a newly created disposable
database, runs the full database smoke, then removes only that temporary database.
The pilot database is not dropped. To restore on a different
machine, install this Compose image, create an empty target database and use
`pg_restore --exit-on-error -U swisstip -d TARGET` with the dump as binary input.
Restore the local configuration separately; credentials are not in the dump.
Copy backups outside this machine for disaster recovery.

Ordinary container stop/restart/recreation retains the named volume. Removing
the Compose volume deletes the database; preserve a verified backup first.
Docker's volume is managed by the Linux engine, outside the OneDrive checkout.

## Automated database checks

```powershell
$env:SWISSTIP_TEST_DATABASE_URL = (Get-Content -LiteralPath .local/postgres-dsn.txt -Raw).Trim()
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v
```

PostgreSQL tests create a UUID-named disposable database; the connection must
have create/drop-database privileges. They verify transaction rollback,
immutability, concurrent/idempotent import, historical selection and vector
scope/revision binding. With no test URL, only the optional database tests skip.

## Verified local result - 2026-09-08

The running Docker database contains two experimental releases, 18 excerpts,
18 vectors, 90 draft projections and 239 archived attachment records. All eight
raw HTML snapshot hashes matched the retained crawl manifests.

- 73 runtime tests passed, including six tests against a disposable PostgreSQL
  database; four MCP tests passed.
- All ten database replay cases passed, including after a container restart.
  Both release exports and all 239 attachment hashes matched. The maximum
  pgvector/Python cosine difference was `9.1483e-8`.
- A binary backup was restored into a disposable database and passed the same
  ten-case smoke, including database-backed MCP discovery and evidence reads.

Local verification artifacts (Git ignored):

- Import: `.local/database/migration-20260908-195529-446716.json`.
- After restart: `.local/database/smoke-20260908-200605-044508.json`.
- Restore smoke: `.local/database/smoke-20260908-200206-645148.json`.
- Verified backup: `.local/database/backups/swisstip-20260908-200154-492678.dump`,
  SHA-256 `6b9066f38ce6dd4fd772c4c35720c7c02a885cdbc910151cae9f1482fba25580`.

These checks used the real database with recorded provider responses and made
zero new model calls. The corpus remains experimental and OpenCode still uses
its existing configuration.

Implementation references: [pgvector](https://github.com/pgvector/pgvector),
[Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html),
[PostgreSQL JSON representation](https://www.postgresql.org/docs/current/datatype-json.html).
