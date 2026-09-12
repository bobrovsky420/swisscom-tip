# SwissTIP - Swiss Grounding MCP server

SwissTIP is an MCP server that grounds an AI assistant's answers about
residence permits and registration in Switzerland in exact passages of
official pages: the Foreign Nationals and Integration Act on Fedlex, State
Secretariat for Migration (SEM) guidance, the Canton of Zurich migration office
and the City of Zurich. A caller asks for a typed scope (topic, concept,
jurisdiction, applicability date, context) and receives published facts, the
original-language excerpts they rest on, citations with URLs, and an explicit,
named gap when something is not covered. The server never composes an answer;
the calling assistant does.

Built for the Swisscom **Swiss Grounding MCP** challenge at the Swiss {ai} Weeks
hackathon in Zurich, 24 and 25 September 2026. Coverage is one topic done
carefully, designed to be extended.

## Quickstart

Requires Python 3.11 or newer and Git. No database, no model, no credentials.

```shell
git clone https://github.com/bobrovsky420/swisscom-tip.git
cd swisscom-tip
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e packages/core -e packages/runtime -e apps/mcp-server
./.venv/Scripts/swisstip-mcp
```

On macOS or Linux replace `.venv/Scripts/` with `.venv/bin/`. The last command
starts the server on stdio with the release in the top-level `releases/`
folder, verifies its hash, prints which folder it serves, and waits for an MCP
client. Diagnostics go to stderr. Run from any directory; `--releases-dir` or
`SWISSTIP_RELEASES_DIR` point at another folder.

## Connect a client

Print a configuration with the absolute paths of this checkout and paste it
into your client:

```shell
./.venv/Scripts/python.exe scripts/client/print_config.py --client opencode
./.venv/Scripts/python.exe scripts/client/print_config.py --client generic
```

The OpenCode variant raises the client's tool-output cap because topic-level
discovery currently returns about 140 KB; compact discovery is planned. The
generic variant is the `mcpServers` shape used by Claude Desktop and similar
clients. The server advertises three tools:

| Tool | Purpose |
| --- | --- |
| `get_coverage` | Walk the catalog level by level; the root call also returns a `coverage_summary` with the release's scope statement and out-of-scope list, the covered topics and jurisdictions, languages and snapshot dates, so a caller can refuse an outside question after one call; topic and concept levels include coverage profiles and context schemas |
| `resolve` | Return published facts, original excerpts and citations for one concept in a pinned release |
| `get_evidence` | Read up to five original excerpts by evidence ID |

## Try it

Ask the assistant:

> I'm a Czech citizen and starting my work in Zurich next week. By when latest
> should I register my stay on the municipal authority?

A caller discovers the catalog, resolves the federal registration-deadline
concept and the Canton Zurich registration concept with `population: eu_efta`,
the user's canton and today's date, and answers: register with the municipality
within 14 days of arrival and before the first working day, citing the SEM
free-movement FAQ and the Canton Zurich page. Given the arrival date and the
first working day it names the earlier of the two limits. The scripted version
of this test, with a second case asked in Chinese, is
`scripts/test/mock-mcp/run_opencode_test.py --server real --live`.

## Coverage at a glance

| Item | Value |
| --- | --- |
| Topic | Residence permits and registration for foreign nationals in Switzerland |
| Levels | Federal (applies in every canton), Canton Zurich, City of Zurich, and the migration-office contact of all 26 cantons |
| Size | 35 concepts, 84 facts, 84 exact evidence spans, 20 routing rules, 12 official pages |
| Sources | Fedlex (AIG), SEM, Federal Office of Public Health, Canton Zurich, City of Zurich |
| Languages | Evidence in German (one SEM page in English); fact statements in English; catalog labels in English |
| Snapshot | Pages saved on 10 September 2026 |
| Validity | Unbounded unless the source states a date; the UK employment rule applies from 1 January 2021 |
| Freshness | 60 days from the saved copy; results report `STALE` from 9 November 2026 |
| Jurisdictions | A profile serves every place inside its own jurisdiction; the answering level is reported and cantonal specifics are flagged as not covered |

The full list of sources and concepts is generated from the bundled release in
[COVERAGE.md](COVERAGE.md). The limits are in [LIMITATIONS.md](LIMITATIONS.md).

## Limitations, in short

- Curated by an AI assistant from saved official pages with exact spans; no
  independent human or legal review; not legal advice.
- One topic; other cantons' procedures, fees and processing times are not
  covered, and the server says so with the published values that would match.
- Catalog-driven: one concept per call, no free-text search yet. Retrieval
  terms in `de` or `en` rank the evidence of the chosen concept within the
  same language; they never widen scope.
- stdio only; no hosted endpoint yet.
- Facts are English paraphrases; the original excerpt is authoritative.

## Status on 12 September 2026

- **Implemented and tested:** versioned contracts with exported JSON Schema;
  a release reader that fails closed on any hash or span mismatch; discovery,
  resolution and evidence tools over stdio with typed errors; a root coverage
  summary with a scope statement sealed in the release; jurisdiction
  containment with named coverage gaps; unbounded validity with source-stated
  exceptions; a 60-day freshness policy; a bounded crawler with robots
  enforcement per origin; 599 tests across seven suites.
- **Demonstrated:** the Zurich registration question and a Chinese-language
  third-country work-permit question answered correctly through OpenCode with
  citations, recorded under `docs/experiments/`.
- **Remaining before the event:** compact discovery pages, a streamable HTTP
  transport with a hosted endpoint, a concept search tool, broader cantonal
  coverage, refresh and drift checks, and an evaluation table.

## Repository layout

| Path | Contents |
| --- | --- |
| `packages/core` | Contracts, validation, artifact sealing, JSON Schema export |
| `packages/runtime` | Release store, resolution service, scoped retrieval |
| `releases/` | The bundled knowledge release with its hash manifest; what `swisstip-mcp` serves by default |
| `apps/mcp-server` | The stdio MCP server |
| `packages/ingestion`, `apps/knowledge-builder` | Crawler, source catalogue, concept extraction (build side, not needed to serve) |
| `apps/control-api`, `apps/admin-console` | Ingestion studio on PostgreSQL; outside the hackathon MVP |
| `scripts/corpora` | Offline corpus pipeline and the curated release builder |
| `scripts/releases` | `publish_release.py` (bundle a validated release) and `coverage_report.py` (regenerate COVERAGE.md) |
| `scripts/client` | `print_config.py` for client configurations |
| `scripts/test/mock-mcp` | Mock server and the OpenCode caller harness |
| `config/` | Source catalogue, language policy, model profiles |
| `docs/` | Specifications, pitch material, dated pilot and experiment records |

Publishing a new release: build it with `scripts/corpora/build_residence_mvp.py`
into a new directory, then
`./.venv/Scripts/python.exe scripts/releases/publish_release.py --source <dir> --activate`.
Raw source snapshots stay out of Git; they are hash-referenced provenance.

## Tests

```shell
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests
./.venv/Scripts/python.exe -m unittest discover -s packages/ingestion/tests
./.venv/Scripts/python.exe -m unittest discover -s apps/knowledge-builder/tests
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p "test_*.py"
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
```

The PostgreSQL cases in the runtime and control API suites skip unless
`SWISSTIP_TEST_DATABASE_URL` is set. No suite needs the network. Python work
uses the repository-local `.venv`; see `AGENTS.md`.

## Documentation

- [Challenge audit and enhancement proposals - 11 September](docs/hackathon/2026-09-11-challenge-audit-and-enhancements.md)
- [MVP status and plan - 11 September](docs/hackathon/2026-09-11-mvp-status-and-plan.md)
- [One-day team rebuild plan with the existing residence knowledge base](docs/hackathon/one-day-rebuild-plan.md)
- [Hackathon operations, deployment and data transfer](docs/hackathon/hackathon-operations.md)
- [One-minute jury pitch](docs/pitch/one-page-pitch.md)
- [One-slide PowerPoint pitch with speaker notes](docs/pitch/swisstip-one-slide.pptx)
- [Full pitch presentation](docs/pitch/full-presentation.md)
- [Project and pitch review against the jury criteria](docs/pitch/project-review.md)
- [Product specification](docs/product/product-functional-specification.md)
- [Technical specification](docs/architecture/technical-specification.md)
- [Implementation gaps and validation plan](TODO.md)
- [Unbounded validity rule and curated release v3 - 11 September](docs/pilots/2026-09-11-residence-v3-unbounded-validity.md)
- [Freshness policy raised to 60 days and curated release v4 - 12 September](docs/pilots/2026-09-12-residence-v4-freshness-60-days.md)
- [Jurisdiction containment and named coverage gaps - 12 September](docs/pilots/2026-09-12-jurisdiction-containment.md)
- [Residence MCP corpus continuation checkpoint - 11 September](docs/pilots/2026-09-11-residence-mcp-checkpoint.md)
- [Pilot knowledge and lessons](docs/pilots/2026-09-08-retrieval-pilot.md)
- [OpenCode caller test with a mock residence MCP server](docs/experiments/2026-09-11-opencode-mock-mcp-caller-test.md)
- [OpenCode caller test with the real MCP server on the curated pilot release](docs/experiments/2026-09-11-opencode-real-mcp-caller-test.md)
- [OpenCode caller test with a Chinese question on third-country work admission](docs/experiments/2026-09-11-opencode-chinese-work-permit-caller-test.md)
- [Paused extraction experiment and resume checkpoint](docs/experiments/2026-09-10-extraction-pause-checkpoint.md)
- [V3 and DeepSeek Flash switch with the prepared Zurich plan](docs/experiments/2026-09-10-v3-flash-switch.md)
- [zh.ch Apertus 8B/70B experiment results](docs/experiments/2026-09-05-zhch-concept-extraction.md)
- [POC-01 progress, draft findings and resulting requirements](docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md)
- [Prepare and complete the POC-01 review](scripts/test/poc01/README.md)
- [PostgreSQL and pgvector setup, migration and smoke tests](docs/storage.md)
- [Local ingestion GUI: sources, parsing, builds and draft review](apps/admin-console/README.md)
- [Crawler and concept extraction demos](apps/knowledge-builder/README.md)
- [Hackathon residence source catalogue and later crawl/extraction commands](config/catalogs/README.md)
- [Shared model catalog and extraction/retrieval configuration](config/README.md)
- [Semantic-model profiles](config/semantic-models.toml)
- [Core contracts and validation](packages/core/README.md)
- [Structured knowledge runtime](packages/runtime/README.md)
- [MCP server options and client setup](apps/mcp-server/README.md)

## Product vision

The hackathon server is a vertical slice of a larger idea, the Swisscom
Trusted Information Platform: a governed knowledge service that publishes a
versioned catalog of authoritative Swiss information for AI clients. The
calling assistant interprets the question and composes the answer; the
platform owns the published knowledge, its evidence, its applicability and its
limits, and returns them through one structured contract that a form or a
workflow can use as easily as a chat assistant. Five-language retrieval
metadata, reviewed publication, on-demand knowledge builds with human review,
and reuse of the same patterns for regulated enterprise knowledge are the
target-product capabilities described in the
[product specification](docs/product/product-functional-specification.md);
they are not claims about the current implementation. The knowledge builder,
the ingestion studio and the nationwide residence corpus prepared under
`.local/` are the build side of that vision.

## Licence

Code and curated statements are licensed under the Apache License 2.0, see
[LICENSE](LICENSE). Quoted official texts remain the property of their
publishers and are reproduced as cited evidence, see [NOTICE](NOTICE).
