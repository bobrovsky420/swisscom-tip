# Implementation alignment and validation plan

Assessment date: 2026-09-06. Baseline: [Product Specification V20](docs/product/product-functional-specification.md),
[Technical Specification V11](docs/architecture/technical-specification.md), current
source code and tests, and the recorded zh.ch experiment.

This is an implementation and validation backlog. Parent items stay unchecked
until their full acceptance boundary is met; completed steps are checked separately.
Existing build proofs remain useful; there is
no implemented MCP runtime or conversational server to migrate. The new work is
the governed publication and structured serving layer around reviewed knowledge.

## Product boundary to preserve

- The caller discovers available topics/concepts, interprets the user question,
  selects explicit scope, obtains missing facts and composes the final answer.
- TIP publishes versioned catalog entries, supported operations, context schemas,
  evidence and rules, and serves `structured-grounding/v1` requests pinned to a
  release. A form can submit the same contract directly.
- Original-language `retrieval_terms` are optional scoped relevance signals. They
  never establish or override intent, jurisdiction, date or applicability facts.
- German is preferred for a single-version MVP seed; multilingual selections
  retain all chosen official versions. Reviewed concepts may share language-neutral
  IDs and multilingual terms, while source/evidence identities remain separate.
  Evidence eligibility and claim support precede a German tie-breaker among
  verified equivalent versions; explicit source filters and caller answer language
  remain independent.
- Five compact metadata projections (`en`, `de`, `fr`, `it`, `rm`)
  and scoped multilingual lexical/concept/vector retrieval with semantic ranking
  remain P0. No common-language or source-language translation is required from
  callers for evaluated profiles.
- Search and vector retrieval are components of the governed knowledge service.
  A collection of candidate chunks or embeddings is not a published release.
- Whole-question language detection, mixed-span planning, server answer rendering
  and a separate natural-language MCP path are outside the server scope. Source
  language validation and per-term retrieval routes remain server responsibilities.

## What the code currently proves

| Area | Observed implementation | Alignment and next boundary |
|---|---|---|
| Acquisition | [Crawler](packages/ingestion/src/swisstip/ingestion/crawler.py) emits bounded metadata and enforces robots per origin/hop; the [source catalogue runner](config/catalogs/README.md) can retain exact HTML bytes and source manifests on explicit runs | Bind experimental snapshots into immutable release contracts; add PDF/JavaScript adapters and governed language discovery |
| Source planning | The `hackathon` residence catalogue has 59 official source references covering all 26 cantons; multilingual sets retain chosen versions, schedule German first and carry unevaluated parallel-page groups; no pages or extracted concepts are included | Run selected test crawls, review discovered scope and source-first topic/concept proposals; catalogue grouping does not prove content equivalence |
| Normalization and evidence spans | [Normalizer and extractor](packages/ingestion/src/swisstip/ingestion/concepts.py) read local files, record local paths and verify normalized offsets | Add authoritative URL/source identity, immutable snapshot binding, persisted normalized sections and release-associated evidence |
| Candidate semantics | `CandidateConcept` contains prose scope, proposed relationships and `user_questions`; validation state remains `CANDIDATE` | Retain authoring/review aids. Add reviewed promotion into typed applicability, operations and context schemas; do not expose candidates as supported coverage |
| Candidate identity | Candidate IDs hash page content/label/scope; [batch group IDs](apps/knowledge-builder/src/swisstip/builder/concept_batch.py) also depend on description/language | Keep those identities for traceability; introduce stable language-neutral public IDs and reviewed candidate-to-catalog mappings |
| Review workflow | Model review, rejected proposals, 30 frozen reference labels and an assistant draft comparison exist | Implement separate support/scope/completeness/question assessments, validated human-review import and promotion gates; structural/model approval alone does not publish knowledge |
| Source languages | HTML `lang` is a hint; plain-text inputs have no inferred language | Add governed source-language validation/segmentation, `tip-language-catalog/v3`, five projections and published term routes |
| Provider/recovery | Explicit profiles, request budgets, retries, validated requested/observed model identity and v2 generation/review checkpoints exist; legacy caches are not reused | Include retained identity in published provenance; historical HF observed identity remains unverifiable |
| Runtime/product | Crawler/concept CLIs plus shared versioned contracts and offline catalog/request validation are implemented | Reviewed seed coverage, catalog publisher/reader, immutable releases, scoped retrieval/rules and the three MCP tools remain unimplemented |

The proposed workspace tree in the technical specification is not the implemented
tree. Reuse the existing modules as build components; do not manufacture runtime
completeness by renaming proposal reports or their IDs.

The [zh.ch experiment](docs/experiments/2026-09-05-zhch-concept-extraction.md)
retained 47/55 candidates from six German pages with 8B/70B. Retained citation
offset checks passed, but both models and reviewers accepted a material omission.
That historical report predates the source-first review. POC-01 now has 30 frozen
reference concepts and an assistant draft comparison against both final runs;
the user's second pass remains pending. These results establish neither semantic
completeness nor superiority of either model.

Original offline baseline, rerun for this review before FIX-01/02:

- 47 ingestion tests passed.
- 75 builder tests passed, including the PowerShell workflow with loopback fake
  Ollama. The repository uses `unittest`; pytest is not a required test runner.
- Two additional crawler probes reproduced robots-policy gaps; one in-memory HF
  decoder probe reproduced incorrect model attribution. No live source or model
  calls were used. The passing existing suites do not cover these failures.

Reproduce the existing suites using the repository environment. On Windows:

```powershell
./.venv/Scripts/python.exe -m unittest discover -s packages/ingestion/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/knowledge-builder/tests -v
```

On Unix use `./.venv/bin/python` for the same commands.

The BUILD-01 update adds the core suite. Install and test it in the same environment:

```shell
./.venv/Scripts/python.exe -m pip install -e packages/core
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests -v
```

Current verification (rerun 2026-09-06): 71 core, 63 ingestion
and 110 builder tests pass, including source catalogue planning/snapshot fixtures,
POC-01 preparation and the loopback workflow.
These counts do not establish semantic review or complete a POC.
The schema export and source catalogue freshness checks also pass. POC-01 packet
preservation verification passes for six sources and 87 historical artifacts.

## Immediate fixes supported by the review

These are demonstrated defects, not open hypotheses requiring another POC.

- [x] **FIX-01: enforce robots per origin and before every content hop.**
  Previously, [crawler.py](packages/ingestion/src/swisstip/ingestion/crawler.py)
  checked a single robots parser before `_fetch()`, while redirected requests
  rechecked scope/DNS only. A redirect from an allowed path to an expressly
  disallowed path was fetched. A linked page on a configured secondary host was
  also fetched without requesting that host's robots file. Policies are now
  cached by origin and enforced before every content hop. Policy acquisition
  shares the declared budgets; per-origin status is reported. Offline regressions
  cover both defects plus scope/DNS, loops, timeout, request/byte limits, policy
  ownership, cache reset and crawl delays.
- [x] **FIX-02: preserve and validate requested versus observed model identity.**
  [huggingface_provider.py](apps/knowledge-builder/src/swisstip/builder/huggingface_provider.py)
  previously checked response `model` only for a nonempty string and reported the configured
  model. A payload naming `completely-different/model` was attributed to the
  configured Apertus model. Requested and raw observed names are now retained in
  completions, reports and [checkpoints](apps/knowledge-builder/src/swisstip/builder/concept_recovery.py).
  Exact identities and explicitly approved provider aliases are accepted; the
  existing shortened lowercase name is scoped to PublicAI's configured 8B model.
  Unexplained mismatches fail. Checkpoint v2 isolates unverifiable v1 files and
  revalidates identity on every hit. Regressions cover exact names, aliases,
  mismatches, legacy reuse, valid-checksum invalid identities and split reviews.

Both fixes are implemented with offline regressions. Historical artifacts remain
unchanged; these fixes do not establish their missing observed model identities
or validate historical model-quality comparisons.

## Implementation queue

These are delivery tasks with explicit outputs. The POCs below validate their
assumptions; POCs do not replace the implementation backlog.
Numbered substeps show completed work directly in the queue; parent rows remain
open until their remaining acceptance requirements are met.

| Done | Order | Work item | Acceptance boundary |
|---|---|---|---|
| [ ] | BUILD-01 | Define versioned catalog, context, evidence and `structured-grounding/v1` contracts; curate a small seed catalog | Stable public domain/topic/concept IDs, supported finite intents, canonical jurisdictions, conditional context schemas, strict unknown-field/ID handling and explicit outcomes |
| [x] | BUILD-01.1 | Define shared versioned contracts and export JSON Schema | Catalog, context, release, evidence, discovery and structured request/result shapes implemented in `packages/core` |
| [x] | BUILD-01.2 | Implement offline catalog/request validation and artifact sealing | Hierarchy, IDs, intents, jurisdictions, conditional context, bounded scope, release identity, typed validation outcomes and content/dependency hashes covered by offline tests |
| [x] | BUILD-01.3 | Prepare the draft residence catalogue and source registry | 59 official references across all 26 cantons, exclusions, scan sets and budgets; candidate seed scaffold only, with reviewed concepts and supported coverage still pending |
| [ ] | BUILD-02 | Add root-seeded source-language discovery, persist raw/normalized evidence and implement reviewed promotion | Logical source blocks, bounded cross-section evidence, declared content policy, separate semantic assessments, validated review import, URL/authority/snapshot/evidence chain and immutable publication identities |
| [x] | BUILD-02.1 | Implement explicit test-crawl planning and raw snapshot capture | Offline planning by default; explicit crawls retain exact HTML bytes and URL/time/hash manifests; fixtures verify language retention, German ordering, separate snapshots and failures |
| [ ] | BUILD-03 | Implement `get_coverage`, `resolve` and `get_evidence` over that release | Bounded hierarchical discovery with inline context schemas, release-bound cursors, typed context validation, exact/descendant scope, published facts/rules and evidence round-trips |
| [ ] | BUILD-04 | Add source-language validation, closed v3 policy, reviewed cross-language concept/section alignment, terminology and all five compact projections | Stable concept IDs with separate source/evidence identities; revision-bound alignment, per-field provenance/completeness and evaluated term/projection/source routes; required failures block promotion |
| [x] | BUILD-04.1 | Define and validate the closed v3 language policy | Language-only role sets, tagged term routes, independent source filters and policy closure implemented and tested offline; source-language validation and evaluated retrieval/projections remain pending |
| [ ] | BUILD-05 | Integrate scoped lexical/concept/vector retrieval and semantic ranking | Hard eligibility constraints survive every channel; multilingual recall/relevance gates, explicit source filters, verified equivalent evidence grouping, conditional German tie-breaker and evaluated provider fallback |
| [ ] | BUILD-06 | Complete on-demand release publication, retention, observability and client qualification | Atomic promotion, historical reads, no silent release substitution, fresh/stale reporting, external-client setup and separate caller evaluation |

Completed steps within the open implementation items:

- [x] **BUILD-01: define shared versioned contracts and export JSON Schema.**
  [Core contracts](packages/core/src/swisstip/core/contracts.py) cover catalog,
  context, release, evidence, discovery and structured request/result shapes.
- [x] **BUILD-01: implement offline catalog and request validation.**
  [Validators](packages/core/src/swisstip/core/validation.py) enforce hierarchy,
  explicit IDs, finite intents, jurisdictions, conditional context, bounded scope,
  release identity and typed validation outcomes. Artifact sealing binds content
  and dependency hashes; it does not publish or approve artifacts.
- [x] **BUILD-01/02: prepare the draft residence source catalogue.**
  The [catalogue](config/catalogs/README.md) records 59 official references across
  all 26 cantons, explicit exclusions, scan sets and budgets. The seed remains
  `CANDIDATE`, with no concepts, context schemas or supported coverage profiles.
- [x] **BUILD-02: implement explicit test-crawl planning and raw snapshot capture.**
  The [source CLI](apps/knowledge-builder/src/swisstip/builder/source_cli.py)
  defaults to offline planning; explicit crawls save exact HTML bytes and
  URL/time/hash manifests. Fixtures verify selected-language retention, German
  ordering, separate snapshots and failure reporting. Live catalogue crawl
  validation, normalized evidence binding and reviewed promotion remain pending.
- [x] **BUILD-04/POC-06: define and validate the closed v3 language policy.**
  Core contracts and offline regressions enforce language-only role sets, tagged
  term routes, independent source filters and policy closure. Actual source-language
  validation, evaluated retrieval routes and five-language projections remain pending.

BUILD-01 is in progress: shared contracts and offline boundary validation are
implemented in [packages/core](packages/core/README.md). The seed catalog remains
a draft pending reviewed promotion. POC-01 has 30 frozen reference concepts,
five per source, with 101 reported primary-review minutes. The fixed comparison
contains 116 historical proposals and 60 assistant draft alignments. The
[experiment record](docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md)
preserves scope limitations and assistance provenance. The user's same-person
second pass, independent adjudication, controlled reviewer comparison and unseen
holdout remain pending. Neither BUILD-01 nor POC-01 is complete.

BUILD-02 has acquisition scaffolding; reviewed evidence/promotion work still needs
the first accepted fixture. FIX-01/02 are complete.
BUILD-04 can progress in parallel with BUILD-03; BUILD-05 integrates both.
The early identifier/lexical fixture in BUILD-03 proves contracts, not completion
of the multilingual P0 service.

Remaining BUILD-02 work includes parsers for supported language selectors, HTML/HTTP `hreflang`
and sitemap alternates, reviewed source-language hint mappings, explicitly scoped
adapters where needed, shared-budget scheduling and reports for discovered,
fetched, validated, excluded, failed and unresolved variants. POC-09 validates
these implementation outputs; fixed German seeds are only an early fixture.

The source catalogue now offers a four-language SEM `multilingual` set. `all`
retains 59 references with 53 eligible sources and six explicit exclusions;
`smoke` selects five seeds, including the German SEM version. Offline fixtures
cover exact selection retention, German ordering, group validation, independent
snapshot capture and a failed German version alongside selected English content.
They do not establish live availability, translation fidelity or concept alignment.

BUILD-04 must distinguish reviewed concept equivalence from revision-bound claim
equivalence, including unequal conditions across official translations. BUILD-05
must avoid counting equivalent translations as independent corroboration, keep
alternate evidence references and expose conflicts. Add runtime regressions for
explicit English-only filters, multilingual terms matching the same concept,
equally suitable German evidence, better or newer non-German evidence, missing
German content, partial translations and a caller answer language different from
its citations. These gates remain pending; the current extractor groups proposals
using language-dependent candidate metadata and does not create shared public IDs.

The source review sets the following BUILD-02 implementation priorities. These
are requirements from V20/V11, not capabilities already delivered by the worksheet:

1. Add versioned, separate claim-support, scope, completeness and per-example-
   question assessments, bound to candidate and evidence revisions. Preserve
   conditions, exceptions, AND/OR, population, units, time windows and deadline
   triggers. Source ambiguity must remain unresolved rather than becoming a
   guessed rule or a repeated request for facts already supplied.
2. Preserve logical source blocks through normalization and chunking: tables,
   conditional lists, resumed lists after infoboxes and body/heading relationships.
   Retain raw/normalized identities and record loss, ambiguity and truncation.
3. Allow necessary evidence from explicitly linked sections under validated scope.
   A primary section is an anchor; neither arbitrary sibling mixing nor blanket
   rejection of all multi-section evidence satisfies the acceptance boundary.
4. Freeze content/operation expectations before extraction and comparison. Keep
   actionable authority contacts and procedures when included in that policy;
   a contact heading alone is not a reason to drop included substantive content.
   Report filtered, skipped, budget-limited, unproposed, rejected and differently
   represented content separately. Do not retroactively exclude gaps to raise scores.
5. Import the user's second review with explicit decisions and actual time,
   turn confirmed failures and correct controls into regression fixtures, and
   enforce affected-claim/operation promotion gates. Complete text representation
   in a rejected or partly unsupported proposal is not verified retained coverage.

Keep comparison work outside the immutable packet inventory, under
`.local/experiments/poc-01-comparisons/`. Preserve existing gold/proposal snapshots
when implementing these changes; fresh outputs and corrected labels need new
versioned artifacts. Prioritize these controls before scaling the corpus or
treating model size as the primary improvement.

## Validation queue

Effort is a proposed experiment timebox in focused engineer-days, excluding
reviewer availability and provider queues. It is not a delivery estimate. At each
timebox, record a decision or an inconclusive result instead of silently expanding
the experiment. Dependencies require only the relevant fixture or prototype.
Existing POC identifiers are retained so previous references remain meaningful.

| Done | Rank | POC and decision | Dependencies | Timebox |
|---|---|---|---|---|
| [ ] | 01 | Independent semantic ground truth and reviewer value | Existing experiment artifacts | 0.5-1 day + review |
| [ ] | 02 | Smallest catalog-to-structured-MCP evidence path | Reviewed subset from 01; BUILD-01/02 | 1-2 days |
| [ ] | 03 | Applicability, factual support and typed status precedence | 01, 02 | 0.5-1 day + review |
| [ ] | 04 | Acquisition and evidence trust boundaries | FIX-01; repeat runtime cases after 02 | 0.5-1 day |
| [ ] | 05 | Meaning preservation through normalization/chunking | 01 | 0.5-1 day |
| [ ] | 06 | V3 per-term routing and source-language validation | 01; fluent reviewers for claimed profiles | 0.5-1 day + review |
| [ ] | 07 | Scoped retrieval channels, catalog value and evidence budget | 01-03, 06, 10; curated projection fixtures can unblock early work | 1-2 days |
| [ ] | 08 | Immutable catalog/release promotion, pinning and freshness | 02, 03 | 0.5-1 day |
| [ ] | 09 | Root-based source-language discovery and crawl coverage | FIX-01, 04; controlled website fixture | 0.5-1 day |
| [ ] | 10 | Five-language projection and catalog-metadata fidelity | 01, 06; results feed 07 | 0.5-1 day + review |
| [ ] | 11 | Provider identity, quality-qualified cost and reliability | FIX-02, 01; 05/10 for full build cost | 0.5-1 day plus runs |
| [ ] | 12 | Clean deployment, catalog usability and separate caller behavior | 02, 03, 05-10 plus focused 04/11 | 0.5-1 day |
| [ ] | 13 | Typed Arrival Checklist/MCP/REST contract reuse | Passing core service; P1 only | 0.5 day |

Continue 01 alongside BUILD-01 and acquisition validation. Feed a small reviewed fixture
into 02 immediately, then develop typed applicability handling in 03. Develop 06
and 10 in parallel with the MCP path, followed by the full multilingual comparison
in 07. Validate release lifecycle and source discovery independently. Finish with
the full-cost and client checks in 11/12. Keep 13 behind the P0 server.

This entire backlog is not a credible two-day commitment from the current
baseline. A smaller corpus and fewer supported operations can limit work while
preserving the five-language projection and scoped-ranking requirements. A
partial prototype remains incomplete P0; reviewer or time shortages do not
silently make those capabilities optional. Any product-scope change needs a
separate explicit decision. Admin UI, REST/Arrival and Hike remain P1/P2.

- [x] **P1 Admin GUI design: document the stack, build execution and initial screens.**
  [Technical specification section 16](docs/architecture/technical-specification.md#161-recommended-implementation-stack)
  defines React/TypeScript/Vite/Mantine, the FastAPI Control API, generated SDK,
  build polling and Sources/Builds/Concept review screens. The applications remain
  unimplemented; this completes the design step only.

## Evaluation rules and evidence

- Freeze source manifests, normalized hashes, code revision, model/configuration,
  prompt, schema, language policy and evaluation-suite versions for each comparison.
  Preserve existing temporary experiment artifacts in durable internal storage
  before rerunning or refreshing the fixture. Keep permitted test fixtures and
  sanitized summaries in the repository; preserve source material under the
  existing experiment's reuse restrictions.
- Define gold concepts, claims, required conditions, evidence spans and expected
  statuses before inspecting a model's output. Have a second reviewer adjudicate
  high-impact claims and disputed labels. Fluent review is required for each
  language/variant being claimed. Reviewer absence means an unvalidated profile.
- Separate development examples, synthetic adversarial cases and held-out natural
  examples. Existing zh.ch failures are development cases. Do not tune against the
  holdout; a changed system needs a new independent holdout for a fresh claim.
- Report numerators and denominators per scenario/language, reviewer disagreement,
  precision, recall and abstention. A system that rejects every supported structured request cannot
  pass. Zero observed critical errors in a small suite is a release gate for that
  finite slice, not proof of zero real-world risk. Report uncertainty for broader
  accuracy estimates and mark small samples inconclusive.
- Numerical gates below are **proposed experiment criteria**, unless labelled
  **existing specification gate**. Freeze them before comparison. Performance and
  monetary budgets must be set from the actual deployment and team constraints;
  this plan does not invent a latency SLA or provider price.
- Write each result to `docs/experiments/YYYY-MM-DD-poc-NN-<topic>.md`, with artifact
  locations/hashes, reproducible commands, measurements, failures and a decision:
  `CONFIRMED_FOR_TESTED_SLICE`, `REJECTED` or `INCONCLUSIVE`. Record resulting
  changes to product, technical and pitch claims together. Run Python through
  `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on Unix.

## POC-01 - Independent semantic quality and reviewer value

Recorded progress in the
[experiment report](docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md):

- [x] Preserve six source pages and 87 historical artifacts with a verified manifest.
- [x] Prepare source-only review views and freeze 30 human-led, assistant-assisted
  reference concepts, five per source, with 101 reported primary-review minutes.
- [x] Prepare the fixed historical comparison: 116 proposals and 60 assistant draft
  alignments, with a separate second-review worksheet.
- [ ] Complete the user's same-person second pass and select an accepted seed subset.
- [ ] Complete independent adjudication, controlled reviewer comparisons and unseen
  holdout evaluation. Reviewer value and model selection remain `INCONCLUSIVE`.

**Assumption:** exact evidence plus model review can identify publication-quality
concepts and reduce human effort. The existing experiment already disproves the
strong version that all retained claims are correct and complete.

**Experiment:**

1. Preserve the six-page fixture and existing 8B/70B outputs. Independently label
   5-10 expected answerable concepts per page. Begin with 10-15 matched high-risk
   concepts, then include model-specific concepts and rejected proposals.
2. Annotate label, description, scope, candidate example questions, necessary
   conditions, exceptions and evidence separately. Also label domain/topic,
   supported operation, typed applicability and required context for promotion.
   Assess every example question against the saved candidate and cited evidence;
   uncited source text may identify a correction but cannot silently repair the
   original proposal. Keep proposal history separate from retained complete,
   partial, missing or unresolved representation, including representation in
   another concept. Record filter/skip/budget causes and actual human time.
3. Freeze a common proposal set and compare structural validation alone, current
   same-model review, an independent reviewer configuration and structured
   condition/exception checking. Change one factor at a time; do not rerun
   generation for each reviewer comparison.
4. Include correct claims and controlled mutations: omitted care/support condition,
   changed population, quota exemption changed to permit exemption, altered date
   or number, changed time-window unit, misleading label and an unanswerable
   proposed question. Include valid cross-section evidence and invalid sibling-
   population mixing, missing registration/sector exceptions, and source ambiguity
   with all relevant user facts supplied. Evaluate natural failures on held-out
   pages separately from synthetic mutations.

**Measure/gate:** every known critical mutation must be caught; no unresolved
material error may be promoted in the reviewed acceptance set. Report material
false-acceptance rate, valid-proposal false-rejection rate, gold-topic recall and
review cost. A reviewer is useful only if it reduces missed material errors on
the holdout without excessive valid-content loss or human review cost.
Declare required versus optional coverage and valid-content-loss/cost criteria
before running each comparison. Report draft representation counts separately
from adjudicated quality metrics; same-person review or assistant assessments do
not satisfy independent-review requirements. The 101 primary-review minutes are
not minutes per usable concept until the usable subset has been accepted.

**Decision:** keep curated promotion as the baseline. If review still shares the
generator's errors, use it for triage and leave output `CANDIDATE`; do not map it
to `VERIFIED_AUTOMATIC`. A larger model or lower rejection count is not a pass.
This challenges product section 9.1 and technical sections 9.1/10.1.

## POC-02 - Minimal catalog-to-structured-MCP vertical slice

**Assumption:** a caller can discover supported knowledge and construct a valid
scoped request without inventing IDs or loading the whole catalog. Neither
existing CLI currently tests that assumption.

**Experiment:** use 5-10 independently reviewed concepts and frozen SEM/zh.ch
sections. Publish stable IDs, multilingual labels/aliases, supported intents,
canonical jurisdictions, context schemas and scope combinations alongside raw
snapshot identity, source authority/URL, normalized sections, exact evidence and
reviewed facts/rules. Candidate IDs and `proposal-group-*` IDs remain provenance
references, not public concept IDs.

Implement the three tools with a persisted fixture release and curated/lexical
lookup first. `get_coverage` exposes bounded root/child pages and complete inline
context schemas. Pin the returned release for child calls, continuation cursors,
`resolve` and `get_evidence`. Test pagination/filter changes, stale cursors, active
release changes and unknown IDs. Discovery lists must not imply a cross-product of
supported combinations.

The `structured-grounding/v1` request requires `schema_version`, `release_id`,
`knowledge_space_id`, `domain_id`, `topic_id`, `intent`, `jurisdiction`, `context`,
`as_of` and `scope_mode`. `concept_ids` is required only by operations that need
it. Optional `retrieval_terms` contain bounded `text` and required `language`.
`source_languages` and `max_evidence` retain the specification's constraints.
Unknown fields, a missing required concept selector and malformed inputs are
`INVALID_ARGUMENT`; conditional facts absent from a valid context envelope are
`NEEDS_CONTEXT`. There is no raw question or generated-answer language field.

Begin with tagged English and German terms over reviewed German evidence and
curated metadata. This is an early plumbing fixture, not a new language baseline
or completion of P0. All five projections and scoped semantic ranking remain
required and are validated through 06/10/07.

**Measure/gate:** initial supported, missing-context and out-of-coverage fixtures
produce the agreed schemas/statuses; every fact maps to original evidence, source
URL/authority, snapshot and release; every evidence ID round-trips. A fresh client
can discover the fields and IDs needed to call the tools. A warm client with known
catalog and sufficient context completes one resolution call. Run the fixture
with source-network access unavailable; model-free lexical behavior validates
that fixture only, while semantic-provider behavior is tested in 07/11.

**Decision:** fix missing schemas, discovery affordances or provenance before
expanding the corpus. Do not turn report JSON into a public catalog merely by
renaming fields. See product section 12 and technical sections 9, 13 and 14.

## POC-03 - Applicability, claim support and status precedence

**Assumption:** published evidence and declared rules can support the requested
operation under explicit client-supplied context. Source relevance alone cannot
establish an individualized conclusion.

**Experiment:** extend the gold set to at least 30 structured requests. Pair
positive cases with one changed selector or fact: nationality, purpose, duration,
canton/municipality, date or existing foreign permit. Include missing conditional
inputs, unknown IDs, known unsupported combinations, required concepts omitted,
exceptions, non-entailing citations, unsupported local detail and separately
supported/unresolved portions of one declared operation.

Include source-defined gaps such as an unassigned exact-age boundary and an
unstated deadline trigger, with all applicable client facts already present.
These must preserve an evidence limitation, not produce a guessed predicate or
misleading `NEEDS_CONTEXT` for the same known facts. A permission to reside alone
does not establish employment rights unless a reviewed rule supplies that link.

Put conflicting place names, dates and personal facts in `retrieval_terms` and
verify they cannot populate missing fields or override typed values. Compare
`exact` with explicitly bounded `descendants`. Evaluate published curated
facts/rules and reviewed build-time fact proposals; do not generate new factual
conclusions through runtime model assembly.

Pre-adjudicate per-fact and aggregate outcomes for stale AND conflicting evidence,
partial support AND missing context, and federal/cantonal specialization. Freeze
the precedence/aggregation table before implementing it. Use controlled evidence
fixtures, separate from claims about live legal requirements.

**Measure/gate:** zero unsupported, wrongly scoped or incorrectly dated asserted
facts in the finite acceptance suite; all negatives have the agreed status and
reason; at least 90% of supported held-out cases return the required supported
facts. Measure missing conditions and false abstention separately from citation
validity. If only excerpts are verified, return those with limitations rather
than inventing a structured conclusion.

**Decision:** implement explicit fact/rule, applicability, temporal and status
contracts from product sections 10-11 and technical section 13. Preserve typed
validation as distinct from confirming the truth of client assertions.

## POC-04 - Acquisition and evidence trust boundaries

**Assumption:** scope, per-origin robots handling and typed acceptance boundaries
keep network/source/model input from changing platform policy.

**Prerequisite:** FIX-01 closes the reproduced redirect-path and secondary-origin
robots gaps. Keep both as regression cases before evaluating wider acquisition.

**Experiment:** use a controlled local HTTP/DNS/transport harness for forbidden
redirect paths, multiple allowed origins with distinct robots rules, loops, proxy
routing, changed DNS answers, encoded paths, oversized/slow responses, 429/503 and
exhausted budgets. Exercise actual transport as well as fakes. Do not infer a
demonstrated DNS exploit merely from separate validation/connection code paths.

Inject instructions into HTML, model proposals, catalog/projection metadata,
evidence and retrieval terms: override authority, change scope, invent citations,
add languages, alter deadlines or expose a synthetic secret. Exercise available
build boundaries now, then published catalog, projection, embedding/ranking,
rule-input and result-assembly boundaries as implemented. User-answer fidelity
belongs to the separate caller track in 12.

**Measure/gate:** zero requests to disallowed paths/origins; shared request,
byte/time and redirect limits hold for every hop and auxiliary request. No source
or term instruction changes scope/policy, creates an accepted fact/evidence ID
or leaks a sentinel. Model scores cannot bypass eligibility. Untrusted output
remains data and is escaped in later displays.

**Decision:** enforce constraints at actual fetch and acceptance boundaries.
Failures block the affected live crawl or publication path. Existing fake-HTTP
tests alone do not prove all advertised source-policy behavior.

## POC-05 - Meaning preservation through normalization and chunking

**Assumption:** filtered sections and bounded chunks retain enough context for
complete, correctly scoped concepts. The current review receives only current
chunk fragments of primary sections, sometimes marked `context_may_be_partial`.

**Experiment:** build annotated fixtures with nested headings, lists, table
headers/rows, footnotes, adjacent population rules, mixed-language sections,
encoding damage and relevant text resembling navigation/news. Include unseen
SEM layouts. Add PDF samples only if needed by intended coverage; otherwise
explicitly exclude their content and measure the resulting coverage gap.
Include a condition list resumed after a deadline infobox, a general procedure
under a misleading inherited heading, and substantive in-scope authority contact
details under a contact/footer heading. Freeze the inclusion policy before the
run so intentional exclusions are distinguishable from extraction failures.

Trace required clauses from raw bytes through normalization, filtering, chunking,
evidence selection and review. Compare current chunks with bounded full-section
context, then explicitly linked parent/table/footnote context. Separately vary the
six-concepts-per-chunk cap, overlap and output constraints. The review prompt
already forbids omitted conditions; adding that instruction again is not a new
test. Preserve exact citations while testing scoped context composition.

**Measure/gate:** preserve 100% of annotated essential clauses and their population
relationships in recoverable fixture content; damaged/ambiguous required content
must trigger explicit quarantine and prevent the affected coverage from being
published. No silent loss, sibling-scope leakage or accepted claim with missing
required context. Report lost clauses, exclusions, cap saturation, gold-topic
recall, truncation and requests per useful reviewed concept. Check source
declared/detected language mismatches; HTML `lang` alone is not verified regional
source-language coverage. This evaluates builder-owned source detection, not
whole-question language interpretation. Review annotations must become explicit
publication decisions before candidate content is served.

**Decision:** adopt scoped context links, narrower claims or explicit manual
assembly when primary-section fragments cannot support completeness. If a format
cannot be normalized reliably, remove it from claimed coverage instead of silently
dropping its conditions. See [concepts.py](packages/ingestion/src/swisstip/ingestion/concepts.py)
and technical sections 10.1/10.3.

## POC-06 - V3 term routes and source-language validation

**Assumption:** closed, explicitly tagged term routes support multilingual
retrieval while independently validated source languages preserve provenance.

**Experiment:** implement `tip-language-catalog/v3` roles and test canonical tag
casing, language-only identifiers, reviewed German/Swiss German routes to `de`, declared
Romansh forms, and referential closure. The permitted term tags are `en`, `de`,
`fr`, `it`, `rm` and `gsw`; enabled profiles
remain release-specific. Source/projection roles use the five exact standard
tags. Jurisdiction and evaluated dialect/idiom forms remain separate metadata;
raw website tags are preserved with explicit reviewed source mappings.

Test malformed tags as `INVALID_ARGUMENT`, unsupported tags as
`UNSUPPORTED_LANGUAGE`, and recognized but unevaluated combinations as
`OUT_OF_COVERAGE`. Cover multiple separately tagged terms, no-term requests,
empty/oversized terms and independent source filters (omitted, `null`, empty,
deduplicated, unsupported or with no covered sources). Unsupported entries are
reported, never dropped. A German term must not implicitly select German sources.

Separately benchmark actual **source-language** validation over annotated
documents/sections, including misleading HTML hints, missing declarations, mixed
sections, encoding damage, regional ambiguity and official parallel revisions.
Compare declared/detected identity and quarantine behavior; an HTML `lang`
attribute alone is not verified evidence language.

Mutate policies with dangling aliases/routes, disabled-role references and
provider-proposed additions. Each invalid policy must fail publication.
Whole-question carrier confidence, protected-span offsets, detector thresholds,
English-response baselines and fixed answer-language rules are removed from the
server plan. Caller question interpretation is evaluated in 12.

**Measure/gate:** all deterministic contract/route fixtures pass; no unsupported
language or combination is silently admitted. Use independently authored,
fluent-reviewed terms per claimed profile and source-language labels, reporting
route correctness, source misclassification and false rejection. Retrieval
quality of routed terms is measured with 07/10; language validation alone does
not establish recall or semantic fidelity.

**Decision:** keep each unvalidated profile explicitly incomplete. Five compact
projections and scoped multilingual ranking remain P0 requirements; no reviewer
or provider capability claim substitutes for passing evaluation.

## POC-07 - Scoped retrieval, catalog value and evidence sufficiency

**Assumption:** the required multilingual retrieval channels and reviewed catalog
can supply relevant, sufficient evidence within the caller's explicit scope.

**Experiment:** hold snapshots, scope and applicability rules fixed while varying
tagged retrieval terms across supported languages. Compare original/expanded
lexical, curated concept lookup, localized metadata, multilingual vectors and
semantic ranking through controlled additions/ablations. Include exact scope,
bounded descendants, topic-level operations without optional concept selectors,
sibling leakage, foreign jurisdictions, rare terms and wrong/missing assignments.

Ablating the concept lookup channel must retain validated selectors and published
scope assignments. Other channels may recover evidence only inside that scope.
Unknown IDs or missing mandatory selectors never enable unrestricted search.

For aggregation, label equivalent terminology and hard negatives: with/without
employment, identity document/permit, different populations/jurisdictions and
foreign/Swiss permits. Compare conservative review-group consolidation with a
curated public catalog and proposed automated aggregation. Change labels,
descriptions, source sections and applicability to test stable public concept IDs,
version-specific evidence and audited mappings.

**Measure/gate:** **existing specification gate:** every required gold document
appears in the top 20 candidates, every required fact has support in the final
top 5 evidence objects, and citations resolve to original evidence. Also measure
fact completeness, in-scope relevance, leakage, harmful merges, review time,
latency and response size. No incorrect P0 scope merge is acceptable.

Hard eligibility and published rules remain deterministic. Record projection,
index, embedding/ranker and configuration versions; do not require identical
ranking across languages or nondeterministic model calls. Include outage tests
for only evaluated lexical/concept fallbacks; report degradation or a typed
operational error, never broaden scope or turn provider failure into a coverage
claim.

**Decision:** choose implementations/configurations through measured relevance,
cost and reliability. Ablations do not make five-language projections or scoped
semantic ranking optional. If supported operations require more evidence, use
explicit partial coverage or propose a reviewed budget change; do not hide
conditions or inflate evidence objects to satisfy a cap. Keep curated publication
when automatic aggregation cannot meet quality gates.

## POC-08 - Release promotion, catalog pinning and temporal truth

**Assumption:** every discoverable identifier, schema and result belongs to one
immutable release, while freshness accurately describes what was checked and when.

**Experiment:** publish release A, then candidate B with updated rules, renamed
labels, changed context schemas, a deleted page and different official-language
revision dates. Pin raw snapshots, normalized content, evidence, catalog/graph,
assignments, context schemas, rules, terminology, v3 language policy, projections,
indexes and model/ranking configuration.

Change the active release between discovery pages and before resolution. Exercise
pinned continuations, unknown/selector-mismatched cursors, unavailable releases,
old evidence lookups and incompatible context changes. Omitted release is allowed
only for initial discovery; child/continuation/resolution calls pin its identity.

Inject 304 responses, changed validators, fetch failure, corrupt checkpoints,
missing required projections, failed evaluation and termination around promotion.
Serve reads during promotion, restart and roll back. Separate content/dependency
hashes from operational timestamps.

**Measure/gate:** no request mixes A/B catalogs, schemas or evidence; failures
leave A available; old citations remain resolvable while their release is retained.
Unavailable requested releases yield `RELEASE_UNAVAILABLE`, never substitution.
Cursors bind release and selector scope. Unchanged artifacts reuse work only with
matching dependencies; legacy unverifiable model provenance follows FIX-02's
explicit invalidation policy.

Record attempted/successful refresh, source revision, effective date, release
publication and evaluation time separately. Freshness changes with evaluation
time even for immutable evidence; a successful fetch does not prove a rule current.
Scope/rule replay is distinguished from variable semantic ranking.

**Decision:** implement atomic publication, retention, provenance and freshness
contracts before claiming the service reproducible. This remains on-demand
full-build validation; it does not require a scheduler or incremental Knowledge CI/CD.

## POC-09 - Root language discovery and honest crawl coverage

**Assumption:** a root-seeded bounded crawl can discover the required eligible
language variants without separate language seeds. Six fixed German fixture URLs
do not test this requirement.

**Experiment:** create a multilingual website fixture with default-language
redirects, HTML/HTTP `hreflang`, selector links/options, sitemap alternates,
`x-default`, HTML base URLs, canonical links and language-bearing query strings.
Include a separately allowed host, unsupported language branches, a selector
requiring an adapter and same-URL content varying by an explicit request profile.
Test sufficient and exhausted budgets, misleading hints and divergent parallel
versions. After POC-04 passes, validate selected behavior with a small permitted
live root crawl and compare to a manually enumerated in-scope reference set.

**Measure/gate:** **existing specification gate:** the controlled root redirect
fixture discovers/fetches all enabled German, French and Italian variants without
separate seeds when budget allows. All cases report advertised, fetched, validated,
excluded, failed and unresolved variants with provenance. Meaningful language
parameters survive deduplication, while robots/scope/request/byte/time limits hold.
Missing required variants prevent candidate promotion; optional gaps reduce coverage.
Source-language discovery is independent of retrieval-term and projection profiles;
five metadata languages do not imply authoritative sources exist in all five.

**Decision:** retain static discovery plus explicit adapters/entry URLs where
necessary. Do not infer a monolingual site from an empty discovery result or claim
site-wide completeness from a bounded crawl. Resolve the current default query
exclusion with reviewed language-parameter handling, rather than enabling arbitrary
query crawling. See product section 9 and technical section 10.

## POC-10 - Five-language projection and catalog-metadata fidelity

**Assumption:** compact localized metadata preserves source meaning well enough
to improve retrieval, while reviewed multilingual catalog labels help callers
select the correct stable identifiers.

**Experiment:** select at least 20 condition/exception/number-rich sections from
the gold set. For all five P0 projection languages, compare curated fields,
eligible official parallel fields and model projections. Include stale/divergent
official parallels, near-synonyms with different legal scope and ambiguous catalog
labels. Record original hashes, method/provider/model/reviewer and completeness
for each field.

Review labels, aliases, descriptions and compact section metadata with independent
fluent reviewers. Evaluate equivalent typed requests with original-language terms,
preserving independent source filters. Include omitted conditions, altered dates
or numbers, wrong-language fields, swapped source references, missing required
fields, provider outages and source prompt injection. Language detection and
number matching alone cannot establish fidelity.

**Measure/gate:** all required P0 projections are complete, provenance-linked and
correctly scoped in the reviewed set; derivative metadata never becomes cited
evidence. Unsupported generated languages cannot expand the policy. Required
projection failure blocks publication and preserves the preceding release.
Equivalent terms retrieve relevant eligible originals without caller translation.

**Decision:** use reviewed official/curated metadata where model fields fail;
limit corpus or supported operations if needed while retaining all five target
projection languages. Unfinished evaluation remains an unmet requirement, not a
deferred language by default. Server answer rendering, answer-language routing
and runtime excerpt translation are not part of this POC; caller answer fidelity
is a separate integration assessment in 12.

## POC-11 - Provider identity, quality-qualified cost and reliability

**Assumption:** provider switching preserves the contract, selected model identity
is auditable, and recovery makes an affordable build likely to finish.

**Completed prerequisite (FIX-02):** in
[huggingface_provider.py](apps/knowledge-builder/src/swisstip/builder/huggingface_provider.py),
response identity is now validated against the requested model and explicit
provider aliases. `ModelCompletion` retains requested and observed names;
checkpoint v2 prevents reuse of unverifiable legacy completions. Historical
attribution remains uncertain, and new model-comparison claims still need the
experiment below.

**Experiment:** after semantic labels exist, run at least three paired builds per
eligible configuration on identical inputs/settings and comparable operational
limits. Set experiment-wide elapsed-time and monetary budgets first; existing
request caps are not a whole-run deadline or a currency limit. Separate fresh
local inference, warm cache, interrupted resume and
controlled failure injection. Use isolated artifact/checkpoint roots. The wrapper's
`-FreshInference` bypasses local checkpoint reads; it does not establish absence
of upstream caching or statistically independent samples.

Record every attempt, request ID, requested/observed model, timeout, truncation,
retry wait, fallback review, known usage, missing usage and full elapsed time.
Exercise truncation-to-small-review recovery and budget exhaustion. A full P0
build-cost assessment includes all five projection languages; extraction-only
runs are labelled as partial-stage measurements. Measure runtime embeddings and
ranking separately from build work and caller interpretation/answer generation.
Estimate growth by pages/chunks/projection languages and check a second bounded
corpus size. Runtime outages use only evaluated fallback profiles, identify omitted
channels and return a typed operational error when no permitted path can complete.

**Measure/gate:** declared attempt/time/byte limits hold in all injected cases,
and every attempt has an outcome and explicit usage-known/unknown state. Select
only configurations passing POC-01's quality gate within a recorded team budget.
Report build completion rate, median/tail observations, cost per reviewed useful
concept and human review effort; three runs are a pilot, not a reliable tail SLA.
Token totals for successful/reused responses must not be presented as billing.

**Decision:** choose the least costly configuration meeting quality/reliability
needs, or shrink the corpus/automation. Mark availability, price and identity
uncertainty explicitly. The existing 41.849s/117.944s resumed invocations are not
a valid 8B/70B speed comparison. See the experiment and
[model configuration](config/semantic-models.toml).

## POC-12 - Clean deployment, discovery usability and caller behavior

**Assumption:** another person can start the server, discover valid scope and use
its structured contract efficiently. A client can faithfully interpret questions
and explain results without transferring those jobs to the MCP.

**Experiment:** use a clean checkout/environment and an evaluated fixture
release. Test the documented transport with two independent standard MCP clients,
including OpenCode where available. Separate two tracks:

1. **Server:** submit catalog-derived typed requests; test schema/errors, paginated
   discovery with inline context schemas, release pinning, scope enforcement,
   supported/partial/stale/conflicting outcomes and retrieval degradation.
2. **Caller integration:** start fresh agent sessions with user questions,
   including `How to get Aufenthaltsbewilligung in Zurich?`. Verify discovery of
   published IDs, city/canton clarification when needed, accurate intent/context,
   preserved original-language terms, handling of `NEEDS_CONTEXT` and faithful
   final answers with citations and limitations. Never send the user question as
   `resolve` input.

Use at least 20 fully specified supported scenarios and separately labelled
missing-context/coverage/failure cases. Count cold discovery, pagination, evidence
inspection, resubmissions and warm resolution calls separately. Measure bytes,
tokens, provider calls, latency and concurrency, distinguishing server embedding/
ranking cost from caller interpretation/answer inference. Simulate source and
semantic-provider unavailability. No live calls are required for deterministic
contract fixtures.

**Measure/gate:** both clients validate the tools and all boundary fixtures; at
least 90% of warm, fully specified supported tasks with a known catalog complete
with one `resolve` call. Cold and clarification paths have separate denominators.
No negative fixture becomes an unconditional positive client answer. Report
measured size/latency budgets rather than inventing SLAs. Semantic-provider
failure uses a declared fallback with degradation or a typed operational error.

**Decision:** improve discovery labels, schema descriptions and context
requirements where clients select incorrectly; do not add a hidden question
interpreter to compensate. Verify the actual Swisscom harness when accessible;
standard-client success is not evidence of compatibility with an unavailable
harness. Any conversational harness adapter stays outside MCP.

## POC-13 - Typed Information Product reuse, after core validation

**Assumption:** Arrival Checklist and AI clients can consume the same governed
knowledge contract without duplicating domain rules. This remains P1 validation.

**Experiment:** construct typed nationality/purpose/duration, canton/municipality,
arrival and work-start context from the published schemas. Submit the same
release-pinned scope and context through MCP and the optional REST adapter,
replaying 10 cases from 03. Include missing fields and unsupported municipalities.
A minimal form or script is sufficient; no chat prompt or backend answer-language
field exists in either path.

**Measure/gate:** equivalent requests use the same scope, published facts/rules,
evidence, statuses and limitations across adapters. Pin a deterministic or recorded
ranking fixture for exact parity checks; variable ranking must still preserve
eligibility and fact support. The application owns labels and explanation.

**Decision:** fix duplicated runtime logic before adding more clients. The form
is an ordinary structured consumer, not a special queryless exception. This POC
does not validate enterprise governance, marketplace economics or production
regulatory use.

## Assumptions and implementation claims to track

The current specifications define the intended product boundary. The assessments
below distinguish missing implementation and experimental evidence from approved
requirements; they do not silently amend those requirements.

| Expectation | Assessment | Next evidence or action |
|---|---|---|
| The existing code implements the governed MCP service | False; current entry points crawl and extract candidate proposals | BUILD-01 through BUILD-06; retain accurate README/status wording |
| Candidate IDs or proposal groups are stable selectable catalog concepts | False; IDs depend on content and editorial fields | Reviewed mappings into stable public IDs and release-associated evidence |
| Quotes and model review establish semantic completeness | Rejected by the recorded experiment | POC-01/05; independent reviewed promotion |
| More retained concepts or larger models prove higher accuracy or speed | Unproven by counts and resumed timings | POC-01/11 with independent labels and full accounting |
| Existing robots/model checks cover their advertised behavior | FIX-01/02 repair the two demonstrated defect classes with offline regressions | Validate affected live scenarios and new provider comparisons using the repaired code |
| Typed requests eliminate multilingual retrieval needs | Incorrect for retained original-language terms | Five P0 projections and scoped hybrid ranking, POC-06/07/10 |
| The five-language P0 service is already demonstrated | Not implemented or evaluated | Build required capabilities and narrow corpus/operations as needed; mark incomplete gates honestly |
| Whole-question detectors or server answer rendering are next runtime tasks | Outside the accepted server boundary | Per-term routing/source validation in 06; caller interpretation/fidelity in 12 |
| Source authority or semantic relevance proves individual applicability | Unsupported inference | Published facts/rules, typed context and adjudicated outcomes in 03 |
| Explicit IDs always reflect the user's actual intent | Not guaranteed by server validation | Discoverable labels/schemas and separate caller selection tests in 12 |
| Pinned versions guarantee identical model ranking | Incorrect for nondeterministic rankers | Record provenance and evaluate relevance/stability while enforcing invariant scope |
| Every operation fits five evidence objects and one call | Unproven outside the finite accepted slice | Preserve top-20/top-5 gates; measure evidence sufficiency and warm/cold call budgets |
| Root scanning or HTML language hints prove source coverage | Not demonstrated by six fixed German seeds | Governed source validation and discovery in 06/09 |
| Successful checkpoint reuse proves publication-quality provenance | Unproven and affected by discarded HF observed identity | FIX-02, immutable dependency records and release checks in 08/11 |

Autonomous refresh, marketplace/billing, real hiking providers and production
enterprise/regulatory readiness remain outside P0. A candidate build, a partial
fixture or a successful CLI run cannot substitute for publication and runtime gates.

## Completion checklist for each POC

- [ ] Freeze the hypothesis, baseline, fixture/holdout, metrics and decision gate.
- [ ] Execute within the timebox and preserve reproducible, source-linked evidence.
- [ ] Record negative cases, uncertainty, failed attempts and human review effort.
- [ ] Decide confirmed for the tested slice, rejected or inconclusive.
- [ ] Add regressions for demonstrated defects or durable trust/contract invariants.
- [ ] Update implementation status and affected specification/pitch claims; keep
      caller capabilities separate from server guarantees and record the next decision.
