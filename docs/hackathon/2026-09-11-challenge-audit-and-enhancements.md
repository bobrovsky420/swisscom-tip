# Challenge audit and enhancement proposals - 11 September 2026

Prepared against `main` (`ce1e5db`) with every test suite rerun today and the
curated release exercised over a real stdio session. Section 1 reproduces the
published challenge, which the [project review](../pitch/project-review.md)
could not retrieve on 9 September. Sections 2 and 3 record what was verified
and where the current app falls short of the five jury criteria. Section 4
proposes the work that still fits before the Zurich hackathon on 24 and 25
September 2026 (Kraftwerk Zurich, per zh.ai-weeks.ch), ordered by expected
effect on the score per day of effort. Effort figures are working estimates
for one developer with an assistant, not commitments.

Status, 12 September 2026: the date-window blocker (section 3.1, E1) is
resolved in commit `fdd57a5`, the 30-day freshness finding is mitigated by the
60-day policy of release v4, the jurisdiction finding (E6) is resolved by
containment matching, and the repository blockers E2 and E3 are resolved by the
bundled release, the quickstart README, the coverage and limitation pages and
the licence, and the root coverage statement (E7) is served since the same
day from release v5; findings and proposals carry their status inline. Discovery size
(E5) and the missing HTTP transport (E4) remain the open blockers.

## 1. The published challenge

Source: <https://zh.ai-weeks.ch/challenges/swiss-grounding-mcp>, retrieved
11 September 2026. Challenge partner: Swisscom. Title: **Swiss Grounding MCP**.

**Problem statement.** "Large language models can search the web, but they
still struggle to answer questions about Switzerland reliably." Public Swiss
information is scattered across federal, cantonal, municipal and institutional
sources in several languages, across websites, APIs, datasets, PDFs,
regulations and service calendars. Generic search retrieves wrong
jurisdictions, outdated pages, commercial summaries, or information from
neighbouring countries that does not apply to Switzerland.

**Objective.** Build an MCP server, hosted in a GitHub repository, that gives
AI assistants efficient access to authoritative Swiss public information. The
primary deliverable is a functional server that Swisscom can access and
evaluate during the hackathon. Teams choose their Swiss sources, coverage
scope, tool design and implementation. Nationwide coverage in two days is not
expected; a focused, credible foundation that can be extended is a valid
submission.

**Repository and documentation requirements.** Public or private GitHub
repository with clear setup instructions; coverage and limitations must be
documented; private repositories need Swisscom evaluation access; secrets must
never be committed; test credentials are exchanged through a secure channel.

**Testing approach.** "All MCP servers connect to the same MCP-compatible AI
client and LLM configuration (potentially using OpenCode as an open-source
client)." The server is the variable under test, not the caller.

**Evaluation criteria.**

| # | Criterion | Published definition |
| --- | --- | --- |
| 1 | Grounding quality | Correctness, authoritative sources, jurisdiction, freshness, citation support, and honest handling of unsupported questions |
| 2 | Useful Swiss coverage | Breadth and practical value of accessible Swiss public information and declared coverage scope |
| 3 | Agent efficiency | Tool selection quality, call quantity, response size, token usage, latency, and minimisation of unnecessary live requests |
| 4 | Operability | Reproducible setup, refresh and caching strategies, resilience, monitoring, source etiquette, and long-term maintainability |
| 5 | Integration readiness | Coherent MCP contract, clear documentation, extensibility, and seamless operation through standard MCP clients and Swisscom's test harness |

**Evaluation method.** Automated testing (factual grounding, citations,
unsupported queries, tool calls, response size, latency, freshness checks)
plus manual review (architecture, coverage, operability, artifact quality).

**Support.** Swisscom experts attend the hackathon. Virtual Q&A on Wednesday
16 September 2026 at 15:00; signup at <https://luma.com/qa-swisscom2-16Sep26>.

**Other conditions.** No confidential data, production user prompts, myAI
system prompts or myAI sandbox access are needed. Publishing the repository
under an open-source licence is encouraged but not required.

## 2. What was verified today

| Check | Result |
| --- | --- |
| Test suites (`unittest`, repository `.venv`, Python 3.14.3) | 581 ran, all pass: 85 core, 81 runtime (7 PostgreSQL cases skipped), 4 MCP, 22 control API (11 skipped), 171 ingestion, 182 builder, 36 corpora scripts |
| `swisstip.core.schemas --check` and `refresh_hackathon.py --check` | Pass; 59 source references current |
| GitHub remote `bobrovsky420/swisscom-tip` | Public; 280 tracked files; no tracked secrets; `.env.*` ignored; no `LICENSE` file |
| Curated release `hackathon-residence-semantic-2026-09-11-v2` | 1.18 MB; 35 concepts, 83 facts, 83 evidence spans, 20 rules, 60 coverage profiles, 12 documents; evidence languages `de` and `en`; labels `en` only; zero term routes |
| Real stdio session on that release (`mcp` SDK 1.29.1) | initialize 2.7 s; root discovery 0.10 s and 1.2 KB; topic discovery 0.18 s and 137.7 KB; `resolve` 0.11 s and 9.4 KB, `SUPPORTED` |
| All 60 prepared resolves in process | All `SUPPORTED`; 5.1 / 5.5 / 10.9 KB min / median / max; slowest 58 ms |
| Standing caller test (Czech citizen, Zurich) | Passes with Ling 3.0 Flash on v2 with the guided tool descriptions: 6 and 8 calls in turn 1, both deadlines correct. Unguided first attempt: 17 and 27 calls, one wrong deadline |
| Nationwide collection parts 001 and 002 (520 MB and 283 MB) | 5 to 9 s per call, 100 s startup, about 5.8 GB resident; parts 003 and 004 answer in under 1 s |
| Crawler etiquette | robots.txt per origin before every hop, user agent `SwissTIPDemoCrawler/0.1`, 2 s host delay, stop on 429 and 503, request and byte budgets |

## 3. Findings against the five criteria

Severity: **blocker** can zero an automated test or stop Swisscom from running
the server; **major** costs points on a criterion; **minor** is polish.

### 3.1 Grounding quality

Strength: every fact returned by the curated release is tied to an exact
original-language span with URL, authority, access time and hashes; missing
context and out-of-coverage outcomes are typed; the deadline question is
answered correctly with SEM and Canton Zurich citations.

| Sev. | Finding | Evidence |
| --- | --- | --- |
| Resolved (was blocker) | The curated release froze `temporal_coverage` to 2026-09-10 through 2026-09-11, so any `resolve` with a later `as_of` returned `OUT_OF_COVERAGE`. Resolved 11 September in release v3: validity is unbounded unless the cited source states a date; the UK employment concept keeps its source-stated 2021-01-01 commencement. Verified over stdio for 2026-09-11, 2026-09-25, 2099 and 1990. | Commit `fdd57a5`; [v3 validity record](../pilots/2026-09-11-residence-v3-unbounded-validity.md) |
| Resolved (was major) | Federal profiles required the jurisdiction to equal `{country_code: CH}`, so a caller that added the user's canton received `OUT_OF_COVERAGE` with a message that named neither the field nor the fix. Resolved 12 September: a profile serves every place inside its own jurisdiction (federal for any canton or municipality, cantonal for its municipalities, never upward or sideways), the answering level is reported in `executed_scope` with a caveat, the narrowest matching profile wins, and every coverage gap names its dimension with the published values. | Commit pending; [containment record](../pilots/2026-09-12-jurisdiction-containment.md); probed on v4 |
| Mitigated (was major) | Snapshots were accessed on 2026-09-10 with a 30-day freshness policy, so results would have flipped to `STALE` on 10 October. On 12 September the default became 60 days and the release was rebuilt as v4 (same snapshots and spans): `STALE` now starts on the evening of 9 November 2026. The demo release should still be rebuilt from fresh snapshots the week before the event. | Commit pending; [v4 freshness record](../pilots/2026-09-12-residence-v4-freshness-60-days.md); `citation.accessed_at` 2026-09-10 |
| Major | No human review of any served fact; every entry is assistant-authored and the release calls itself a test fixture with `APPROVED` flags "for the serving test-fixture contract only". The jury's manual review will read that wording. | Curated release README and `validation.json` |
| Minor | `retrieval_terms` in any language return `UNSUPPORTED_LANGUAGE` on every real release because no term routes are published, while the pitch leads with five-language retrieval. | Probed today; live check record |

### 3.2 Useful Swiss coverage

Strength: 12,117 saved official responses from all 26 cantons and the
federal level exist locally, with a validated assertion layer of 96,197
sections; the source catalogue and crawl plans are reproducible.

| Sev. | Finding | Evidence |
| --- | --- | --- |
| Major | Served, agent-usable coverage is one topic: residence permits (federal AIG and SEM pages, Canton and City of Zurich procedures), 26 cantonal migration-office contacts and one health-insurance deadline. The automated tests will ask across Swiss public information; almost every question outside residence will be out of coverage. | Concept list of the curated release |
| Major | The nationwide corpus is not reachable through an agent: parts 001 and 002 are too slow to serve, and no release offers search, so a caller must guess among thousands of document-level concept IDs. | Live check record; discovery shape "14 category concepts, 7,033 and 3,850 document concepts beneath" |
| Minor | Coverage and limitations are spread over more than thirty documents; the challenge asks for them to be documented, and a reviewer will look for one page. | `docs/` tree |

### 3.3 Agent efficiency

| Sev. | Finding | Evidence |
| --- | --- | --- |
| Blocker | Topic-level `get_coverage` returns 121 to 138 KB (60 profiles and 60 context schemas inline, roughly 30,000 tokens) on every cold path. The team's harness raises OpenCode's tool-output cap from 51,200 to 400,000 bytes; Swisscom's harness will not, so the discovery result is truncated and the caller never sees the concept it needs. | `service.py` lines 129 to 143; harness note; measured 137,690 bytes today |
| Major | The best guided run needs 6 to 8 calls for one question (root, space, domain, topic, two to four resolves); the unguided run needed 17 to 27. One concept per resolve (`max_concepts=1`) forces federal, cantonal and city facts into separate calls; two concepts in one call is `OUT_OF_COVERAGE`. | Real-server caller test; probed today |
| Major | Catalog entries carry no usable description or aliases: every entry's `description` is the disclaimer sentence and `aliases` is empty, so concept selection depends on 35 short English labels. | Curated release catalog |
| Minor | Every profile repeats the same three exclusions, evaluation and policy references; the payload is mostly repetition. | Discovery output |

### 3.4 Operability

Strength: fail-closed release validation with content hashes, per-origin
robots enforcement, request budgets, deterministic builds, and a corpus
pipeline with checksums and ledgers.

| Sev. | Finding | Evidence |
| --- | --- | --- |
| Resolved (was blocker) | No real release was in the repository; a clean clone served only the synthetic fixture. Resolved 12 September: release v4 is bundled in the top-level `releases/` folder with a hash-verified manifest, `swisstip-mcp` serves it with no arguments, `publish_release.py` is the only way to change it, and `print_config.py` prints client configurations with the checkout's own paths. | [README](../../README.md) quickstart; `releases/MANIFEST.json` |
| Major | No refresh or drift procedure for a served release: re-downloading the 12 curated pages changes hashes, and the builder's intermediate-hash guard then refuses to build. Nothing reports that a source page changed. | `build_residence_mvp.py` line 63 |
| Major | No monitoring or health surface: the server logs only exceptions; no per-call record of tool, status, bytes and latency; no health endpoint. | `server.py` |
| Major | Release re-parsing per call makes large parts unusable (5 to 9 s per call); the MVP plan's step A1 is still open. | `release.py` lines 272 to 296 |
| Minor | No CI; no Dockerfile for the server (`compose.yaml` only starts PostgreSQL, which the MVP no longer uses). | Repository root |

### 3.5 Integration readiness

Strength: strict, versioned contracts with exported JSON Schema; typed
`isError` tool errors; structured plus text content on every result; inline
input schemas that survive weak tool parsers; SDK-level stdio tests.

| Sev. | Finding | Evidence |
| --- | --- | --- |
| Blocker | stdio only. The SDK in use ships streamable HTTP, Starlette and uvicorn are installed, but there is no `--transport` option, no authentication and no hosted endpoint. "A server Swisscom can access" during the event most plausibly means a URL. | `server.py`; `mcp.server.streamable_http_manager` importable today |
| Resolved (was major) | The README opened with the target product; no licence, coverage page or portable client configuration existed. Resolved 12 September: quickstart-first README, generated [COVERAGE.md](../../COVERAGE.md), hand-written [LIMITATIONS.md](../../LIMITATIONS.md), Apache-2.0 `LICENSE` with a `NOTICE` on quoted official texts, and the decks now use the advertised tool names. | Repository root |
| Major | The contract is unforgiving for an unknown caller LLM: `release_id` required on every child discovery call, `schema_version` required, `as_of` required, exact jurisdiction, one concept per call. Only the guided descriptions made Ling pass; Swisscom's model is unknown. | Caller test attempt 1 versus 2 |
| Minor | Decks and rationale name the tools `swiss_information.get_coverage`; the server advertises `get_coverage`. | Project review table |

## 4. Enhancement proposals

Ordered within each tier by score effect per day. Tier 1 is the minimum for
the submission to be evaluable at all; without it the other tiers do not
matter.

### Tier 1 - make the submission evaluable (about two developer-days in total)

| ID | Change | Why it moves the score | Where | Effort |
| --- | --- | --- | --- | --- |
| E1 | **Resolved 11 September** (commit `fdd57a5`, [validity record](../pilots/2026-09-11-residence-v3-unbounded-validity.md)): both `DateRange` bounds optional with a shared `covers()` check; per-concept validity in the curated data, unbounded by default; release rebuilt as v3 with 84 facts and three temporal preflight checks. Still to do before the event: rebuild from fresh snapshots in the final week (the intermediate-hash guard must be updated deliberately). | Removed the `OUT_OF_COVERAGE` result for every request dated after 11 September; grounding tests can pass. | `contracts.py`, `validation.py`, `service.py`, `build_residence_mvp.py`, `residence_mvp_curated.py` | Done |
| E2 | **Resolved 12 September.** Ship the knowledge in Git: commit the curated `release.json` (1.2 MB) under `releases/`, optionally parts 003 and 004 (18.5 MB); make `swisstip-mcp` default to the bundled release when `--release` is omitted; regenerate `mcp-client.json` and `opencode.json` examples without machine-specific paths. | A clean clone answers real questions; this is the deliverable the challenge names. | `releases/`, `apps/mcp-server/bundled.py`, `scripts/releases/`, `scripts/client/` | Done |
| E3 | **Resolved 12 September.** Quickstart-first README, `LICENSE`, `COVERAGE.md`, `LIMITATIONS.md`: what it is in two sentences, one install and one start command, an OpenCode and a generic MCP client snippet, one worked question, the coverage table (topics, jurisdictions, sources, languages, snapshot date), and the limits. Move the product vision below the fold. | Required by the challenge text; the first thing manual review reads. | `README.md`, `COVERAGE.md`, `LIMITATIONS.md`, `LICENSE`, `NOTICE` | Done |
| E4 | Streamable HTTP transport and a hosted endpoint: `--transport streamable-http --host --port --token-env` using the SDK's `StreamableHTTPSessionManager` behind Starlette and uvicorn; bearer token; `Dockerfile` (slim Python image, editable installs of core, runtime and mcp-server, `COPY releases/`); deploy to one small host and record the URL and token exchange in the setup notes. Keep stdio unchanged. | The harness and Swisscom experts can connect without cloning; standard clients support `type: remote`. | `server.py`, new `Dockerfile` | 1 day |
| E5 | Compact discovery: at topic level return a profile summary (profile ID, concept IDs, intent, jurisdiction, required context fields with allowed values, temporal coverage, source IDs) and no inline context schemas; full profiles and schemas only at concept level (3.4 KB today) or on `detail: "full"`. Deduplicate exclusions and references into one block per result. Target under 25 KB. | Removes the truncation risk under a default client and cuts about 30,000 tokens from every cold path. | `packages/runtime/service.py` `get_coverage`, `contracts.py` `GetCoverageResult` | 1 day |
| E6 | **Resolved 12 September** ([containment record](../pilots/2026-09-12-jurisdiction-containment.md)). Jurisdiction compatibility and diagnostics: accept a request jurisdiction that is more specific than the profile's (country profile accepts canton and municipality; canton profile accepts municipality), report the profile jurisdiction in `executed_scope` with a limitation note; when nothing matches, name the field that failed (date window, jurisdiction, concept set, scope mode) and the nearest profile IDs in `allowed_values`. | Unguided callers stop losing calls to trial and error; federal facts appear alongside cantonal ones. | `contracts.py`, `validation.py`, `service.py`, `server.py` | Done |

### Tier 2 - raise the criterion scores (pick by team size; each 0.5 to 3 days)

| ID | Change | Why it moves the score | Where | Effort |
| --- | --- | --- | --- | --- |
| E7 | **Resolved 12 September** ([record](../pilots/2026-09-12-root-coverage-summary.md)). The catalog seals a curated scope statement (`KnowledgeCatalog.scope`: in-scope text and out-of-scope list), and the root `get_coverage` result serves it verbatim in `coverage_summary` together with an out-of-scope response instruction, the topics, the profile jurisdictions grouped by level and intent, languages, snapshot dates and derived limits. Release rebuilt and bundled as v5 (same snapshots and spans); the nationwide collection is rebuilt as v3 with a statement in every part. Root discovery is 5.7 KB; child pages are unchanged. COVERAGE.md prints the served statement. | Honest unsupported handling with one call instead of a five-call walk; both are scored. | `contracts.py`, `identity.py`, `service.py`, `server.py`, `residence_mvp_curated.py`, `build_residence_mvp.py`, `coverage_report.py` | Done |
| E8 | A `find_concepts` tool: lexical search (the existing `tokens()` scorer or a small BM25) over concept labels, aliases, fact statements and excerpts of every loaded release, taking `query`, optional `language` and `jurisdiction`, returning candidate concept IDs with their profile scope and a snippet, never facts or evidence. The caller still resolves. | Cold path becomes search plus resolve; also the only practical way to expose the nationwide parts. | new method in `service.py`, `server.py` | 1 day |
| E9 | One-call journeys: publish a topic-level profile per journey (`concept_selection_required=False`, `max_concepts` 5, one portion per concept) so "register after arriving in Zurich" resolves federal deadline, cantonal registration and city appointment together. Requires the validator to prefer the narrowest matching profile instead of returning `ambiguous_coverage_profiles` when a single-concept request also matches the topic profile. | Warm one-call target from the specification becomes true for the demo questions. | `residence_mvp_curated.py`, `build_residence_mvp.py`, `validation.py` | 1 day |
| E10 | Coverage sprint through the existing curation path: (a) the arrival journey beyond permits from ch.ch and federal offices (municipal registration, AHV number, driving-licence exchange, tax at source, health insurance already present); (b) EU/EFTA registration and permit pages of the six to eight largest other cantons from the pages already saved; (c) label every concept with `de`, `fr` and `it` labels and aliases. Target 80 to 120 concepts, three to four topics, eight to ten cantons. Parallelisable per person; every claim keeps an exact span. | Directly scored breadth; multilingual labels let callers select concepts from German or French questions without translation. | `residence_mvp_curated.py` (data), saved corpus | 2 to 3 days |
| E11 | Release-store cache: keep the validated bundle per release ID and return it without re-parsing (the service never mutates it; freeze the models or deep-copy only the returned result). Regression test and a repeated live check. | Makes parts 003 and 004 and any future larger release cheap; required before serving anything beyond the curated file. | `packages/runtime/release.py` `ReleaseStore` | 3 h |
| E12 | Enable `retrieval_terms` for `en`, `de` and `fr` on the curated release: publish term routes with lexical projections (the label and alias text) so a tagged term ranks evidence instead of erroring. | Removes `UNSUPPORTED_LANGUAGE` from a Swiss server; a small, honest multilingual claim replaces the unproven five-language one. | language policy in `build_residence_mvp.py` | 1 day |

### Tier 3 - operability and evidence for the manual review (0.5 to 1 day each)

| ID | Change | Why it moves the score | Where | Effort |
| --- | --- | --- | --- | --- |
| E13 | Refresh and drift check: a script that re-downloads the curated pages with conditional requests, the 2 s host delay and robots checks, compares hashes with the release's snapshots, reports changed blocks against curated spans, and rebuilds only on operator confirmation. Document the cadence. | Operability lists refresh, caching, source etiquette and maintainability by name. | new `scripts/refresh_release.py` | 1 day |
| E14 | Per-call structured log line (tool, status, bytes, milliseconds, release) to stderr, an optional `--metrics` JSON summary, and a `/health` route on the HTTP transport reporting release IDs, hashes and snapshot dates. | Monitoring and resilience evidence. | `server.py` | 3 h |
| E15 | Evaluation suite mirroring Swisscom's automated tests: 30 to 40 questions (in scope, out of scope, German and French, jurisdiction traps such as a German or Austrian rule, a date-sensitive case) with expected status and citation URLs; run through OpenCode with default settings and no raised output cap; record calls, bytes, latency, citation presence; publish the table in the README. | Gives the jury measured efficiency and grounding numbers and catches regressions from E5 to E10. | extend `run_opencode_test.py` and `live_mcp_check.py` | 1 day |
| E16 | GitHub Actions: the six suites, the schema check, and a stdio smoke test against the bundled release on every push. | Reproducibility evidence for reviewers. | `.github/workflows/` | 2 h |
| E17 | Documentation and pitch alignment: fix the status drift (README opener, operations guide, tool names), add a dated "implemented / demonstrated / remaining" note, lead the deck with the caller journey, and replace "test fixture" wording with "curated from official pages on <date>; not independently reviewed". | Artifact quality is an explicit manual-review item; drift undermines the careful work. | `README.md`, `docs/` | 4 h |

### Not recommended before the event

- Serving parts 001 and 002, or any PostgreSQL-backed path: slow, large and
  outside the 11 September no-database decision.
- Building five-language projections, vector indexes or live semantic ranking
  for real data: the hybrid path exists only for synthetic releases and would
  need evaluated assets that cannot be produced and qualified in time.
- Adding a question-answering or translation tool to the server: it moves the
  boundary the architecture is built on and makes the harness comparison
  about the caller model again.

## 5. Suggested sequence to 24 September

| Days | Work | Exit condition |
| --- | --- | --- |
| 12 Sep | E7 (done; E1, E2, E3 done) | A stranger clones, installs, starts, and asks the Zurich question with today's date through OpenCode default settings |
| 13 to 15 Sep | E5, E4, E11 (E6 done) | Cold path under 25 KB per call; hosted URL answers the same question; federal plus canton request succeeds |
| 16 Sep | Swisscom Q&A (section 6); adjust the plan | Open questions answered |
| 16 to 20 Sep | E8, E9, E10, E12 in parallel | Search plus resolve in two calls; 80 or more concepts across three topics; German and French labels |
| 21 to 22 Sep | E13, E14, E15, E16 | Evaluation table in the README; CI green; refresh procedure rehearsed |
| 23 Sep | E17, fresh snapshots and final rebuild, release freeze, rehearsal on a second machine and on the hosted endpoint | Frozen release hashes recorded; fallback recording saved |

## 6. Questions for the Swisscom Q&A on 16 September

1. Will the harness connect over stdio to a locally started server, or over
   HTTP to a URL the team provides? Which is preferred?
2. Which client and model will the harness use, and are the client's
   tool-output size limits left at their defaults?
3. Does the harness supply the current date to the model, and are
   date-sensitive answers judged against the snapshot date or the test date?
4. How are unsupported questions scored: is a fast, explicit "not covered"
   with the declared scope the intended best answer?
5. Are questions asked in German, French and Italian as well as English?
6. Is a narrow, deep topic scored differently from a broad, shallow one?
7. What does "access during the hackathon" require for a private repository
   or a hosted endpoint: GitHub handles, an allowlisted IP, a token?

## 7. Claims to keep and claims to drop

Keep: exact-span citations from official sources; typed missing-context and
out-of-coverage outcomes; release-pinned, hash-verified knowledge; robots and
budget-enforced acquisition; a nationwide corpus prepared for future
coverage; the standing caller test with its recorded transcripts.

Drop or rephrase until implemented: "five languages", "hallucination-free",
"production-ready", "answers any Swiss question", "test fixture" as a
description of the served release, and the `swiss_information.` tool prefix.
