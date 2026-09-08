# Structured extraction and assisted review

The opt-in `concept_extraction_v4` path implements the extraction controls motivated
by the POC-01 source review. The default v3 configuration and its checkpoint
identities remain available for historical comparisons. This is an authoring
pipeline, not a published knowledge release or an automatic eligibility engine.

## Run locally

From the repository root, first inspect the source inventory and request ceiling:

```shell
.venv/bin/python -m swisstip.builder.concept_cli downloaded/page.html --structured --dry-run > plan.json
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
Dry-run does not instantiate a provider, access credentials or send model requests.
It reports every source block, including exclusions, unresolved structure and
groups withheld by size or request limits. It is not a tokenizer or a semantic
quality check. Under the original logical-blocks/v1 normalizer, the six archived
POC-01 pages passed individual offline preflight,
with 679 inventoried blocks and per-page request ceilings of 12, 12, 12, 8, 12 and 8.
Their combined ceiling exceeds the default 30-request run budget; use separate
bounded runs or explicitly configure a larger run budget.

Generate a fresh comparison outside the frozen POC packet:

```shell
.venv/bin/python -m swisstip.builder.concept_cli downloaded/page.html --structured --checkpoint-dir .local/experiments/structured-v4/checkpoints --verbose > .local/experiments/structured-v4/proposals.json
.venv/bin/python -m swisstip.builder.extraction_review export .local/experiments/structured-v4/proposals.json --output-dir .local/experiments/structured-v4/review-001
```

Create the output parent directory before redirecting JSON. The CLI uses the
selected provider/model from `config/semantic-models.toml`; `--structured` overrides
only the prompt profile. Alternatively set `extraction.prompt_profile` to
`concept_extraction_v4` in a separate configuration. `max_repair_attempts` accepts
0 or 1 and defaults to 1. Generation output/context settings still need measurement
on the selected model: the larger schema and review payload may require smaller
source packets or a larger context/output allowance. Failed or truncated responses
never produce automatically approved knowledge.

Open `review-001/index.html` and edit only `decision` and `notes` in `decisions.csv`:

- For a candidate, judge the proposed output against its source evidence.
- For a source block, judge the recorded gap or disposition. Accepting its
  disposition does not certify complete extraction.
- Use `accept`, `correction`, `reject`, `defer` or leave `pending`. Corrections,
  rejections and deferrals require notes. A correction requests a new revision;
  it does not silently rewrite the report or its model assessment.

```shell
.venv/bin/python -m swisstip.builder.extraction_review import .local/experiments/structured-v4/review-001/report.json --decisions .local/experiments/structured-v4/review-001/decisions.csv --reviewer reviewer-name > .local/experiments/structured-v4/decisions-001.json
```

Import requires every original item exactly once, a reviewer identity and matching
report bytes, item identities, source hashes and output revisions. A fresh export
directory prevents overwriting existing annotations. Imported decisions are
authoring annotations: they neither mutate candidates nor publish a release.

## Implemented controls

- `swisstip.logical-blocks/v2` preserves whole lists, tables and heading/body
  relationships. An infobox heading stays local while a resumed outer list keeps
  its enclosing ownership. Distinct panels have separate ownership. Contact prose
  and `mailto:`/`tel:` targets remain in scope. Explicit navigation and standalone
  headings are excluded under a versioned content policy, with inventory records.
- Raw-byte SHA-256, normalization version and normalized input hash bind evidence
  to its source revision. Evidence IDs and exact offsets refer to normalized block
  text, not raw HTML byte offsets. Complex table spans, unresolved HTML structure
  and oversized ownership groups are queued for human review rather than split
  into apparently complete rules. Site adapters are still needed for layouts this
  conservative parser cannot interpret.
- Navigation classification includes exact SEM/Zurich component classes for
  menus, breadcrumbs, skip links, table-of-contents controls and footer menus,
  plus page-level banner headers and standalone SEM navigation controls.
  Excluded subtrees remain in `source_inventory` as `navigation` with status
  `excluded_policy`; their headings cannot relabel later substantive blocks.
  Article headers, the Zurich wrapper around the table of contents and page body,
  whole condition lists, substantive links and authority contacts remain eligible.
  Matching uses structural markers, not translated labels or class substrings.
- `swisstip.structured-claims/v1` represents claims, populations, jurisdiction,
  permit status, actors, recipients, procedure branches, conditions, exceptions,
  limitations and explicit AND/OR/UNRESOLVED logic. Conditions retain exact source
  excerpts separately from proposed operators, values, units and time windows.
  Strict validation rejects unknown citations, evidence borrowed across ownership
  groups, duplicate IDs, cyclic/repeated logic and unattached predicates.
- A separate model call reviews claim support, scope, completeness and every
  generated question, and audits every supplied substantive block even when the
  extractor proposed nothing. Coverage claims must link to candidates citing the
  block. Rejected candidates cannot count as retained coverage. The same configured
  model performs both calls; this is not independent human or model adjudication.
- At most one repair uses the same evidence and recorded feedback. Initial
  extraction/audit calls for later packets take priority over repair slots. Failed
  revisions, structural rejections, assessments and final gaps remain visible.
  Provider retries consume the existing hard network request budgets and can leave
  later work unresolved. Invalid response checkpoints are discarded; valid earlier
  work remains reusable. Legacy checkpoint keys are preserved and v4 is isolated.
- Descriptions are rendered from the reviewed claims. Batch consolidation includes
  structured predicates and limitations, so matching prose cannot merge differing
  operators or scope facts. Every retained candidate enters the human queue.

Reports use `swisstip.concept-proposal-report/v2` inside the existing batch envelope.
`source_inventory`, `semantic_reviews[].history` and `human_review_queue` expose
the complete disposition. `covered` means model-assessed representation only.
`coverage_complete`, `publication_eligible` and imported `verified_coverage` remain
false. The legacy confidence field is zero with an explicit `not_scored` explanation;
it is not a calibrated probability. The report's request count includes cached
completions; batch execution statistics distinguish actual network attempts.

## Navigation correction validated on 2026-09-07

The live-test dry-run exposed menus and breadcrumbs classified as pending on
four SEM residence language pages and four Zurich residence pages. The v2
normalizer was checked against all eight saved HTML snapshots without downloading
pages or calling models. Eligible previews now begin with residence content.
Pending block counts changed from 443 to 261; excluded containers can combine
multiple former blocks, so raw exclusion counts are not comparable across versions.
All source byte hashes remained unchanged. No blocks in the new plans were
withheld for structure, size or budget, though pending does not certify relevance
or successful semantic extraction.

The request ceiling remains 64 across separate page runs: four calls per SEM
page and twelve per Zurich page. Use bounded batches within the existing
30-request run limit. Filtering did not justify increasing that limit.

Regenerate normalization and extraction plans after this update. Version v2 is
included in normalized content identities and structured extraction provenance,
so previous normalized references and model checkpoints are not silently reused.
Historical v1 reports and raw snapshots remain intact. This correction is scoped
to explicit navigation markers; it is not a universal website-content classifier.

## Structural repair feedback correction

A local Apertus 8B run on the saved English SEM residence page made four model
calls and retained zero candidates. Both generation responses created condition
groups but selected a single condition as the root, leaving the other nodes
unconnected. Both review responses then marked blocks covered despite receiving
an empty list of valid concepts. The validators correctly rejected both errors,
but the failed-review branch discarded the earlier structural rejection from
repair feedback and report history.

Each failed revision now retains its stage, decoded proposals, structural
rejections and available raw completion. A repair receives the validation error,
the earlier structural reasons with proposal indices, and each proposal once;
raw invalid review text remains in history rather than being copied into repair
input. Existing source/feedback size limits and request budgets still apply.
Review transport failures retain structural diagnostics too. Progress and report
warnings expose failed stages; a zero CLI exit still means a report was written,
not that candidates passed validation or coverage was established.

The extraction prompt explains connected condition roots and comparative
operators. The review prompt requires nonempty valid concept references for
covered/partial blocks and explicitly handles empty proposal lists. These prompt
changes have new recorded hashes and therefore new model checkpoint keys.
Regression tests cover successful repair, repeated rejection, review outage and
a malformed repair without stale proposal data. Offline replay can verify error
retention; live improvement requires another run on the same source.

## PublicAI 70B response identity correction

The English SEM live run with Apertus 70B first returned HTTP 504, then returned
the model identity `swiss-ai/apertus-70b-instruct`. The adapter rejected this
response because its explicit PublicAI alias list only included the 8B model.
On 2026-09-07, the public Hugging Face model API confirmed this exact 70B alias
as PublicAI's `providerId` for `swiss-ai/Apertus-70B-Instruct-2509`:
<https://huggingface.co/api/models/swiss-ai/Apertus-70B-Instruct-2509?expand=inferenceProviderMapping>.

The adapter now accepts that explicit alias only for that provider and configured
revision, retaining both requested and observed identities in completions and
checkpoints. Offline regressions cover acceptance, checkpoint reuse and rejection
of other providers, model sizes, revisions and unlisted spellings. This fixes
response compatibility; it does not establish extraction quality or prevent
upstream 504 errors. The failed run produced no retained candidates.

## Validation and remaining evidence

### Live reviewer false positive: issuing authority role

On 2026-09-08, an assistant-guided Groq GPT-OSS 20B repair produced one concept
with three claims covering the English SEM paragraph. It passed schema, reference,
excerpt and condition-graph validation. The issuing-authority claim nevertheless
placed `Cantonal Migration Offices` in `scope.recipient` while leaving
`scope.actor` unspecified. The source says the offices issue the permits.

Groq GPT-OSS 120B then returned a structurally valid audit approving the concept.
Its scope reason incorrectly described the fields as unspecified, missing the
populated recipient. This is a semantic review false positive, not a successful
quality gate. The candidate response SHA-256 is
`df210894493879cb3d8622a93d1281947a84a511a320d004175b9226ecbf511a`;
the review prompt SHA-256 is
`d7bd5eb88a4a0b2850c0daf6e4925e37189c09ba3d4733d9299db72ccbfbf611`.
Raw local artifacts are `groq-extraction-diagnostic-ap4n0fuu` and
`groq-review-z32icqim` under the frozen live-retrieval run directory.

The authoring correction proposed by the assistant moves the issuing authority
to the claim's actor and leaves its recipient unspecified. It is a separate draft,
not an alteration of the model response or audit. Jurisdiction omissions and the
extractor's `saturated=true` remain review items. The model's approval does not
transfer to the edited draft. This observed failure must be retained when assessing
whether model review is sufficient for unattended authoring; no such sufficiency
has been demonstrated by this pilot.

### German reviewer repeat and targeted prompt revision

The German SEM snapshot repeated the failure on 2026-09-08. Groq GPT-OSS 20B
returned one structurally valid requirement claim in 1.154 seconds, preserving
the work OR stay-over-three-months logic. It omitted claims about the issuing
authority and permit categories, added an applicant role, and placed the issuing
authority in the requirement's recipient field. GPT-OSS 120B approved the concept
and marked the entire source block covered in 2.457 seconds, without identifying
these issues. A structurally valid review is therefore another semantic false
positive, not evidence of complete extraction.

Artifacts are `groq-extraction-diagnostic-6linbcsb` and `groq-review-2ttpt9nv`.
The source SHA-256 is
`955efe8bafc4ff4ad22166b12470993899b5b9b01d7f19911e7ba495672b0a20`;
the candidate response SHA-256 is
`dc248b50726c121fc68983988db0b0ea1c61aad4005d6727fcb101c810e7e98e`.
The failed review used the same review prompt hash recorded above for English.

The revised v4 review prompt requires statement-to-claim mappings in coverage
reasons and inspection of each populated scope field for its specific relationship.
It distinguishes complete conditions in one claim from complete block coverage,
and an issuing authority from an application recipient. The response schema is
unchanged. The next diagnostic reuses the unchanged German candidate with the
revised prompt. This is a targeted comparison on a known failure, not an unseen
quality evaluation.

The comparison in `groq-review-sxyaao_3` completed in 2.590 seconds with review
prompt SHA-256 `60c90403561caa628b409a4d4f2b639d3b2ae5e9eec692b707a8d98486945a87`.
It withheld approval because it considered the population uncertain, but again
marked the source block covered and missed the issuing-authority and category
omissions and incorrect roles. Withholding approval is a limited improvement;
coverage and role checking remain unsuccessful on this known case. No new prompt
revision follows this result. The next diagnostic compares a fresh GPT-OSS 120B
extraction with the existing 20B extraction using the same German input, extraction
prompt, schema and generation settings. It does not change the configured default.

The fresh 120B extraction in `groq-extraction-diagnostic-kig7noel` completed in
1.870 seconds with 725 completion tokens. Its schema was valid, but local
validation rejected a reordered condition excerpt. It again omitted separate
issuance and category claims, mixed issuance roles into the requirement, and
narrowed the source's generic `Bewilligung` to `Aufenthaltsbewilligung`, which the
source lists as one category. This single comparison gives no basis for adopting
120B as a successful extractor. The failed output is retained without semantic
review because it did not pass the structural gate.

An assistant-authored German draft now restores the exact source requirement,
verbatim condition excerpts, the OR and strict duration comparison, and separate
issuance and category claims. The authority is the actor only in the issuance
claim; unsupported applicant and recipient roles are unspecified. The draft's
three statements are mapped to exact source excerpts, with an explicit note about
resolving the issuer sentence's pronoun. It passed schema, excerpt and condition
graph checks; user confirmation is pending. Originals remain unchanged. This
allows a separately labelled assisted-authoring test to proceed after confirmation;
it does not qualify unattended extraction or constitute a serving release.

The user subsequently confirmed the German draft for testing. The confirmation
is bound to the draft hash in a separate sidecar, as for English. Both original
model responses and the pre-confirmation drafts remain unchanged.

The next provider pilot uses these six confirmed claims (three per language)
with six preselected questions about the requirement, issuer and categories.
For each question, the target is the corresponding claim in the other language;
it must strictly outrank the other two claims in that language by cosine score.
One Ollama batch embeds all twelve texts using the active embedding profile.
An offline preparation validated draft confirmation hashes, source excerpt
references and claim structure without sending inference requests. The packet
records the assistant-authored origin and saves source/draft hashes for later
ranking checks. This small cross-language provider test does not exercise runtime
scope filtering, abstention, release loading or MCP, and is not a serving release.

The live embedding batch in `sem-retrieval-20260908-071453-532732` passed all six
cross-language checks using `qwen_embedding_0_6b` (`qwen3-embedding:0.6b`), with
1024-dimensional vectors. Total batch time for six claims plus six queries was
16.719 seconds; this diagnostic does not separate model loading from inference.
Margins over the strongest opposite-language alternative ranged from 0.169603
to 0.405053. This is a successful small provider pilot, not general retrieval
qualification or a per-query latency measurement.

The follow-up Groq ranking pilot uses the same saved packet, whose SHA-256 is
`9524b0640339086a2bce42aace2c2cdc5be0e37a608fec255a89525f657b86b8`.
It calls the configured runtime ranking adapter once per question (six maximum),
without retries, and stops on provider or response-validation failure. Inputs
contain opposite-language original excerpts with opaque IDs and no projections;
topic labels, expected answers and corrected claim wording are withheld from
the ranker. The expected excerpt must strictly outrank both alternatives.
No embeddings are recomputed. Offline preparation passed, including packet-to-
confirmed-draft comparison; live ranking results remain pending.

The live ranking run `sem-ranking-20260908-173136-472479` passed all six
cross-language order checks with `groq_gpt_oss_20b` (`openai/gpt-oss-20b`). It
made six requests in 2.703 seconds total, with per-request times of 0.258 to
0.706 seconds and no embedding calls. Responses used different score scales
(0-1 and 0-10), which the current provider contract permits. The result verifies
relative order within each candidate set only. It does not calibrate the runtime's
absolute `minimum_semantic_score` cutoff or establish abstention behavior.

Before a real hybrid serving test, the runtime requires projections in five
languages (`en`, `de`, `fr`, `it`, `rm`). An offline review packet now proposes 30
search projections over the six confirmed claims, preserving the original
evidence and its language. Non-source-language rows are assistant translations,
not new source evidence. The English source's annual-permit wording and German
source's time-limited wording are kept distinct; no equivalence mappings are
proposed. Romansh drafts target Rumantsch Grischun but remain language-unvalidated.
Projection review, release assembly and release-specific evaluation remain pending;
neither provider pilot alone qualifies the data for hybrid MCP serving.

The user confirmed the projection drafts for a local test. A hash-bound sidecar
records that limited confirmation without changing the drafts' language validation
status. To test runtime integration before governed release tooling exists, an
isolated harness was built at
`sem-runtime-harness-20260908-174216-188972`. It combines two real captured source
documents, six exact source excerpts, 30 draft search projections and six cached
1024-dimensional document vectors with explicitly synthetic catalog, scope,
approval/evaluation and temporal test metadata. The approval fields are fixture
values, not an assertion that translations or legal coverage passed validation.
`test-scaffolding.json` records that distinction and hashes the input artifacts.

The harness enables English and German query routes only, has no published facts,
rules, equivalence groups or fallback, and fixes the evidence cap to one. The date
scope is the capture date, 2026-09-07, as a test restriction rather than a legal
validity assertion. No semantic cutoff is declared. Every result carries explicit
test limitations. The default MCP configuration is unchanged.

Release schema, artifact hash, source snapshot hash, exact span and retrieval-asset
validation passed offline. All six cases then passed an explicitly labelled replay
through `KnowledgeService`, exercising language filtering, lexical/concept/vector
fusion, reranking, top-one selection and exact citation round-trips. The replay
uses saved provider vectors and scores, not fresh semantic decisions under the
runtime's richer ranking inputs. Each case returned `INSUFFICIENT_VERIFIED_EVIDENCE`
with `EXCERPTS_ONLY` and no supported facts, as intended. A missing-provider control
returned `OPERATIONAL_ERROR` with no silent fallback. Live runtime execution and
MCP transport verification remain pending; this harness is not a governed release.

Live runtime execution in `check-20260908-174505-199199` passed all six cases
through `KnowledgeService`, making six Ollama embedding calls and six Groq ranking
calls with no replay. Total time was 13.811 seconds: the first case took 10.424
seconds and the remaining cases 0.613-0.718 seconds. The log does not isolate model
loading, so the first-case delay cannot be attributed conclusively. All results
retained the four hybrid channels, exact expected opposite-language excerpts,
`EXCERPTS_ONLY` trust and no published facts. The missing-provider control passed.

The next test uses an actual MCP SDK client and a separately launched stdio server
on this same harness. Offline execution in `mcp-check-20260908-174710-022923` passed
initialization, advertised input/output schemas, release-pinned discovery,
structured/text response parity, typed missing-provider error transport and exact
evidence lookup. No providers were configured during that check. The prepared live
case asks in English for the issuing authority and expects German `sem-e005`, then
checks `get_evidence` parity. Its ceiling is one embedding call and one ranking
call, without retries. The subprocess receives the ranking credential through its
environment; it is not written to configuration. OpenCode and its existing MCP
configuration remain unchanged. Live MCP and caller-model behavior remain pending.

Live MCP execution in `mcp-check-20260908-174808-062188` passed in 3.574 seconds:
initialization, schemas, pinned discovery, one hybrid resolution and exact
`get_evidence` parity. The returned German issuer excerpt was `sem-e005`, with
`INSUFFICIENT_VERIFIED_EVIDENCE`, `EXCERPTS_ONLY` and all four retrieval channels.
The MCP test did not invoke a caller model.

The prepared next step is a guided OpenCode caller test using the existing
`opencode/ling-3.0-flash-fin-free` model. A separate child-process configuration
points at the harness; the normal `.local/opencode.json` is preserved. The prompt
supplies exact scope JSON and asks for coverage discovery, one resolution, then
an evidence round-trip, stopping on tool error. The expected answer and evidence
ID are not supplied to Ling. Output is saved for checking actual tool calls and
faithful reporting; a successful process exit alone does not establish caller
quality or a fixed model-call count. OpenCode 1.18.29 command help was inspected,
and a connection-only run in `opencode-check-20260908-175146-195015` confirmed the
`swisstip` server connected to the harness without running inference.

The live caller run `opencode-check-20260908-175324-468329` passed the guided
integration test, with one minor reporting issue. An offline audit of the original
transcript verified exactly three completed MCP tool calls, exactly one resolve,
exact prescribed arguments, release hashes, typed outputs and full evidence-object
parity. Ling preserved `sem-e005`, its original German excerpt and URL, all four
channels, the empty supported portions, `INSUFFICIENT_VERIFIED_EVIDENCE` and
`EXCERPTS_ONLY`. The report explicitly described real saved excerpts with synthetic
catalog/coverage metadata and no published facts. No unsupported legal answer was
observed; the original OpenCode configuration was preserved.

The report placed `max_evidence: 1` under the coverage profile, although that value
comes from the supplied request and catalog cap. Coverage and resolve were requested
in the same model turn; the exact scope was already supplied, so this does not
demonstrate autonomous discovery or intent/context grounding. The original transcript
SHA-256 is `8bc863194aca824639422750035ffd78fbc495d1ca299163e264e9272ba510d3`.
The separate caller audit records both the authored prompt text hash and the actual
file hash because Windows converted the prompt's line endings when writing it.

This completes the guided end-to-end smoke test from Ling through MCP, runtime,
Qwen embeddings and Groq ranking to original SEM evidence. It does not resolve
automatic extraction/review failures, multilingual projection validation, relevance
cutoff/abstention calibration or governed release publication. Further qualification
requires broader and negative cases, rather than repeating this successful lookup.

### MCP boundary rejection checks

The four planned boundary cases passed in
`mcp-boundaries-20260908-180210-976526` under the SEM runtime harness. The test
launched the actual MCP stdio server and configured its production provider
adapters against observed loopback HTTP endpoints, with a synthetic test key.
No real inference services or caller models were contacted.

| Request change | Result | Provider requests | Returned evidence |
| --- | --- | --- | --- |
| Unknown release ID | `RELEASE_UNAVAILABLE` / `release_unavailable` | 0 | None |
| French retrieval term | `UNSUPPORTED_LANGUAGE` / `unsupported_term_language` | 0 | None |
| Date 2026-09-08, outside the capture-date scope | `OUT_OF_COVERAGE` / `unsupported_combination` | 0 | None |
| Undeclared context field | `INVALID_ARGUMENT` / `unknown_field` | 0 | None |

The date rejection is a structured grounding result (`isError=false`) with no
executed scope, no retrieval trace and `fact_support=NONE`. The other three are
typed MCP tool errors. Advertised input/output schemas and structured/text parity
were checked for every call.

A valid-scope control on the same connection reached both loopback endpoints:
one fabricated embedding response enabled ranking, whose deliberate HTTP 503
produced `OPERATIONAL_ERROR` without retry or fallback. This confirms the zero-call
measurements were not caused by disconnected providers. Total local control
traffic was two HTTP requests; real model calls were zero. The test completed in
2.280 seconds. All normal provider and OpenCode configurations remain unchanged.
This verifies scope rejection, not relevance-based abstention for a valid scope.

Reproduce without inference credentials or running Ollama:

```shell
./.venv/Scripts/python.exe .local/test_sem_mcp_boundaries.py --harness .local/live-retrieval-20260907-161418/sem-runtime-harness-20260908-174216-188972
```

The helper and its frozen inputs are local experiment artifacts, not portable
repository fixtures. Its `summary.json`, individual MCP responses and
`provider-observations.json` retain the observed results.

### Valid-scope irrelevant-evidence diagnostic

Four assistant-labelled cases retain the valid harness scope and supported query
languages while asking about chocolate-cake baking (English), Wi-Fi password
changes (German), permit application fees (English), and processing time (German).
The six supplied excerpts contain none of those answers. The last two cases check
missing details within the topic, including the distinction between processing
time and permit validity. The diagnostic target is no evidence with `fact_support`
`NONE`; this answer-relevance target is stricter than broad concept association.

All four requests passed offline scope validation. In
`abstention-20260908-180602-232366`, deterministic providers then returned a
fabricated valid vector and zero scores for every candidate. All four cases still
returned one excerpt and `EXCERPTS_ONLY`, because the harness deliberately has
`minimum_semantic_score=null`. The control therefore completed with
`abstention_passed=false` and exit code 1. It made eight stub calls and zero real
model calls. The original release and configurations were not changed.

The prepared live diagnostic records each full runtime result and actual ranking
scores, making at most four embedding and four ranking calls without retries.
It continues across relevance failures to collect the four cases, but stops on
operational or response-integrity failure. Such an error cannot count as successful
abstention.

The live run `abstention-20260908-180722-622748` completed all four cases in
10.564 seconds, using four embedding and four ranking requests. All four failed
the abstention target: the first three assigned every candidate score 0, and the
processing-time question assigned every candidate score 0.1, yet each returned
one excerpt with `EXCERPTS_ONLY`. No provider failure explains these results.

A separate local trial, `sem-cutoff-trial-20260908-181157-420008`, sets
`minimum_semantic_score=0.5`. This is a provisional midpoint between the observed
negative maximum (0.1) and the smallest positive target score (0.9), not a
calibrated provider threshold. Groq's observed scores vary between 0-1 and 0-10
scales. The positive scores also came from the earlier excerpt-only ranking
diagnostic; runtime ranking includes projections. The original release and normal
configurations remain unchanged.

Offline selection checks with saved scores retained all six positive targets and
rejected all four negative cases. Negative query vectors were not saved, so those
checks use fabricated unit vectors with the observed ranking scores; they verify
selection behavior rather than replaying actual embedding retrieval. The trial's
`cutoff-trial.json` and `saved-score-checks.json` record these limits and provenance.

Before further inference, `new-cases.json` freezes six newly phrased positive
questions about requirements, issuers and categories, plus four negative questions
about email passwords, apple cake, application documents and booking appointments.
Offline preparation validated all ten request scopes with zero model calls. The
case-file SHA-256 is
`5ad4a8f9b0095a760bfdf49f0342e397bb6a4b6f9168ee041d49657acd0fba0e`.
The pending live check permits at most ten embedding and ten ranking calls without
retries, and reports positive retrieval and negative abstention separately. These
are assistant-labelled new phrasings against the same pages, not an independent
corpus evaluation or qualification of a governed release.

The live ten-case run `abstention-20260908-181829-032597` finished in 24.813
seconds with ten embedding and ten ranking calls. All six positives passed, as
did three negatives. The German appointment-booking question returned the English
issuing-authority excerpt (`sem-e002`) with score 3, although the excerpt contains
no booking instructions. Thus `positive_retrieval_passed=true`,
`abstention_passed=false` and `quality_gate_passed=false`. Positive target scores
included 0.9, 1 and 5; increasing the old cutoff above 3 would discard several
valid targets. The trial does not establish a usable absolute v1 cutoff.

### Opt-in answer relevance rubric regression

The new inactive profile `groq_answer_relevance_20b` selects
`scoring_contract="answer_relevance_v2"` and adapter identity `groq-ranking/v2`.
Existing profiles default to `relevance_v1`, preserving their prompt and request
schema. Model choice remains `openai/gpt-oss-20b`; the profile changes the scoring
contract rather than the model. The rubric uses fixed ordinal categories:

| Grade | Meaning |
| --- | --- |
| 0 | Unrelated |
| 1 | Shared topic or entity, without requested information |
| 2 | Partial requested information, with a material gap or uncertainty |
| 3 | Requested information explicitly supplied by the original excerpt |

The prompt distinguishes question types and prevents projections from supplying
facts absent from the original excerpt. It allows all candidates to receive low
grades and prohibits relative rescaling. The request uses an integer enum in the
strict JSON schema, following the [Groq structured-output protocol](https://console.groq.com/docs/structured-outputs).
Local validation independently rejects missing/foreign IDs, booleans, fractions,
nonfinite values and grades outside 0-3. It does not clamp or normalize responses.
Schema compliance alone cannot verify the model's semantic judgement.

The separate test harness `sem-answer-relevance-20260908-182238-130324` pins v2
and sets its minimum score to 3, selecting only the direct-support category.
This number is not comparable with the earlier v1 score of 3. The harness retains
explicitly synthetic qualification metadata and contains no published facts or
rules. Root active profiles, original harnesses and OpenCode configuration remain
unchanged. Its local `providers.toml` selects the experimental profile.

`regression-cases.json` preserves the same ten question texts and expected
evidence IDs, rebinding only their release IDs. These are known regression cases
after a rubric change, not unseen evaluation. Offline preparation validates every
scope and release/provider binding without model calls. All 63 runtime tests pass,
including malformed-grade rejection and an optional-excerpt selection control
that rejects grades 0-2 and retains grade 3 without creating published facts.
The live run `abstention-20260908-182544-139279` passed all ten cases in 16.920
seconds with ten embedding and ten ranking requests. All six positive targets
received grade 3 and were returned as `EXCERPTS_ONLY`. All four negative cases,
including appointment booking, returned no evidence and `fact_support=NONE`;
their candidates all received grade 0. Both positive retrieval and abstention
gates passed. This demonstrates the desired selection on these known cases,
not independently measured generalization or exact discrimination of grades 0
versus 1 for related-but-unanswerable questions.

The result pins release-file SHA-256
`c5b8ece8a347ad75cf06f27f37045a0c7a71dbee5ab745c3226750f23e242046`,
case-file SHA-256
`8e6814436af3bcba65e56b971fa5246354d56cfe51144fd7b7f64d4990e6fa17`,
and provider-config SHA-256
`59864b84d0d3a51712ecb35cf53faa304eecdb9e0c427ba9ae12454ae04cfc2e`.

The next prepared caller check uses Ling with the same v2 harness and the German
appointment question. `.local/run_sem_opencode.py` now accepts explicit harness,
provider configuration, case file and case selection, validating release and
provider identities before preparing its isolated child configuration. Offline
preparation `opencode-check-20260908-182735-826648` passed without inference and
left the original OpenCode configuration unchanged.

The caller receives the exact scoped request and conditional reporting
instructions, but not the case's expected evidence IDs or the prior result.
It is asked to call coverage, then resolve once, and fetch evidence only when
resolve returns IDs. With an empty result it should report the source limitation
without inventing appointment instructions or claiming the information does not
exist elsewhere. This is a guided abstention-reporting test; its prompt requests
one resolve without retries, but actual caller compliance must be inspected in
the saved transcript. Live caller behaviour on this case remains pending.

The live caller run `opencode-check-20260908-182905-607970` now passes the guided
abstention-reporting check. Its saved transcript has SHA-256
`d101b5314907a7846bfb26eb91caec376813afd287408acbcc6f30af238de888`.
An offline hash-bound audit verified both tool inputs exactly against the frozen
request, typed outputs, release/catalog/provider references, and the original
OpenCode configuration hash. There were exactly two completed calls: coverage
and one resolve. No `get_evidence`, retries or other tool calls appeared.

Resolve returned `INSUFFICIENT_VERIFIED_EVIDENCE`, `fact_support=NONE`, no evidence
and no supported portions. All four retrieval channels executed, with three
candidates and no provider degradation. Ling preserved these fields, skipped
evidence lookup and did not invent booking instructions or citations. It bounded
the conclusion to this local result and explicitly described catalog, approval
and temporal metadata as synthetic. Process exit code was 0. Provider network
attempts are not independently metered by this caller transcript.

Ling announced parallel coverage and resolve calls. Recorded coverage completion
precedes resolve start, but both calls belong to the same model turn and all scope
values were supplied in advance; this does not demonstrate autonomous discovery.
The final report also repeats the frozen harness's earlier top-one-only limitation.
The actual release now has the experimental grade-3 cutoff; general abstention
quality remains unqualified. This inherited wording was not rewritten in the
recorded release or transcript.

`.local/audit_sem_abstention_caller.py` saved
`caller-audit-20260908-183123-637535.json` alongside the transcript with outcome
`guided_abstention_reporting_passed`. Semantic observations are explicitly the
assistant's review of that exact transcript, rather than conclusions from keyword
checks. No further inference was used for the audit. The current local pilot now
has positive retrieval, negative retrieval and guided caller-abstention evidence;
broader evaluation should next use the saved Zurich EU/EFTA page with labels fixed
before inference. These results do not qualify unattended extraction or publication.

### Frozen Zurich passage-ranking evaluation

The next packet, `zh-ranking-packet-20260908-183716-424632`, uses the previously
saved Zurich EU/EFTA page, captured on 2026-09-07. The HTML content SHA-256 is
`b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4`.
Twelve assistant-selected, contiguous normalized passages retain their source
headings and nearby scope. Exact text offsets, the full normalized text hash,
source URL and capture timestamp are retained. This is a new page for the ranking
experiment, not a claim about model pretraining exposure or independent gold data.

Six positive questions cover moving-registration deadlines, notification-only
work, L permits, B permits, cross-border commuters and the evidence required for
self-employment. Four negative questions ask about an exact L-permit fee,
B-permit processing time, appointment-booking steps, and a combined L-contract
duration plus fee question. The last case has partial support, which must not
qualify as direct support under the unchanged grade-3 acceptance rule. Labels
refer only to the twelve supplied passages, not the entire site or current law.

`.local/test_zh_answer_relevance.py` freezes labels before inference and validates
source and prompt hashes on reuse. It uses `groq_answer_relevance_20b`, with the
existing v2 rubric and no prompt change. Each query ranks all twelve passages;
candidate order rotates and opaque IDs replace source identifiers. Expected IDs,
label reasons and provenance are not included in the model request. No generated
claims or translation projections are supplied.

Offline preparation passed with zero model calls. The pending live run permits
at most ten Groq requests, no retries, and stops on provider or integrity failure.
It continues across quality failures to collect all cases. No Ollama, runtime,
MCP or caller model is used in this step, so it measures passage-ranking selection
and rejection rather than embedding recall or end-to-end operation. The packet's
`review.md` contains every question, expected result and exact source passage.

The initial live run `ranking-20260908-183819-204531` made three requests in
1.468 seconds. Moving-registration and notification-only work both passed with
only their expected passage graded 3. The L-permit case stopped on
`provider_http_error` before returning scores. The remaining seven cases were
not attempted, and all aggregate gates remain null. The old exception discarded
the HTTP status, so neither rate limiting nor a schema failure can be inferred
from this run.

The shared adapter now raises a `ProviderHttpFailure` retaining the numeric
HTTP status and a numeric `Retry-After` delay when present. Its public exception
text remains `provider_http_error`; arbitrary headers, response bodies and
credentials are not exposed. HTTP-date delays are not parsed and remain null.
Requests, model options and retry behaviour are unchanged. Fourteen provider
tests pass, including a loopback check for status/delay retention without body
exposure.

The local diagnostic now supports `--resume-from` and `--max-new-requests`.
It validates the prior packet/model/rubric identity, contiguous completed-case
prefix, exact saved requests, complete grade maps and recomputed acceptance
before reusing completed checks (including any quality failures). A new output
folder links the prior summary hash and records new versus cumulative attempts;
existing reports are not overwritten. Aggregate gates remain null until all ten
cases have results. Offline validation confirmed that a one-request resume starts
at `en-short-stay`, retaining the first two checks and sending no model calls.

The manual one-request resume `ranking-20260908-184242-044851` passed the
L-permit case in 0.501 seconds. Only `zh-e004` received grade 3; the other eleven
passages received grade 0. Two earlier checks were reused, bringing the completed
prefix to three cases and cumulative network attempts to four (including the
earlier failed request). The original HTTP failure's cause remains unknown.
All aggregate gates remain null because seven cases are pending. Offline resume
validation checked the three saved requests and grade maps against the unchanged
packet, and confirmed that the next run starts with `de-residence` and can finish
the remaining seven cases without repeating completed inference.

The next resume, `ranking-20260908-184345-059186`, passed the B-permit and
cross-border commuter cases, then stopped on the self-employment request with
HTTP 429 and a numeric `Retry-After` of 1 second. Five cases are complete and
passing, with seven cumulative attempts; all four negative cases remain untested.
This failure is a rate-limit response, but its specific request/token quota is
not recorded. It does not establish the cause of the earlier status-less error.

The local helper now accepts `--request-interval-seconds` (0-60), recording the
interval and waiting between request starts without automatically retrying any
failed request. Offline validation verified the five-check resume prefix and the
unchanged packet. The next prepared run requests at most five new calls with
five-second spacing. This conservative pacing is an experiment, not a guarantee
against the provider's account-specific limits; any further failure still stops
the run and preserves completed checks.

The paced resume `ranking-20260908-184536-022195` failed on its first request
(`de-self-employed`) with HTTP 400 and no numeric Retry-After, after 0.699 seconds.
No inter-request pacing was exercised because this was the first request. Five
completed checks remain preserved, with eight cumulative attempts. The 400 reason
cannot be identified from status alone and must not be conflated with the prior
429 response.

Error-detail capture is now opt-in at the adapter level and enabled only by this
local diagnostic. It reads at most 16 KiB (also respecting the provider byte limit
and request deadline), retains only code/type/message/failed-generation fields,
redacts supplied authentication values and leaves the ordinary exception text
unchanged. Oversized or malformed error bodies produce a capture diagnostic
without replacing the HTTP failure. Runtime profiles do not enable capture.
The local helper saves `provider-error.json`, printing the bounded error message
and code but leaving failed generation in the file. Failed generation is never
accepted as scores or used to revise labels automatically. All 65 runtime tests
pass. Offline resume verification selects only `de-self-employed` for the next
single-request diagnostic, with unchanged packet, model and prompt.

The diagnostic `ranking-20260908-184835-632727` returned HTTP 400 with
`json_validate_failed`: `/d012` was a string where an integer was required. The
saved failed generation has eleven integer grades and `"d012":"0"`. This is a
response-format failure; the failed generation is not accepted or coerced into
scores. Five baseline cases remain completed, all passing, with nine cumulative
requests including failed attempts. The four negative cases are still pending.

`.local/repair_zh_ranking_format.py` prepares a separate one-request formatting
repair for the self-employment case. It verifies the source packet, original
request and captured error, then appends an explicit instruction requiring
unquoted JSON integer values. The question, twelve passages, schema, rubric,
model and expected labels are unchanged. Neither expected labels nor the failed
grade map is sent to the model. The prompt variant is recorded as
`assistant_format_repair/v1`, not an unchanged-v2 result, and is not automatically
merged into the baseline evaluation. Local strict validation remains in place.

Offline preparation `format-repair-20260908-185023-118858` passed with zero
model calls. The base instruction hash is
`b41919669a75d1e061f4c4315269594687da993869e90a2020debb6d90d81723`;
the repair instruction hash is
`3a2d52140ae0ce9533feb344acfd8ce530de0fa7ae98f21aab10974fcd94ea10`.
Live repair success remains unverified. This experiment neither changes the
active runtime profile nor silently weakens the integer score contract.

The live formatting repair `format-repair-20260908-185106-094688` succeeded in
1.065 seconds with one request. All twelve grades passed strict validation; only
the expected self-employment passage (`zh-e007`) received grade 3, with the others
graded 0. `schema_valid` and `case_passed` are true. This remains an assisted
format-repair result, separate from the unchanged-v2 baseline's five completed
cases; no failed generation was accepted and no automatic merge occurred.

The local ranking helper now supports `--case-group negative`, selecting the four
original frozen negative questions without changing their original candidate
rotation or labels. It runs them under the original v2 prompt. Subset reports
record selected case IDs, a four-case count and the ten-case packet count; a
passing subset does not claim that all ten baseline cases passed. Positive
retrieval remains null when no positive cases are selected. Resumption validates
the same selected-case sequence and prevents mixing subset and full-run results.
Offline preparation verified the four-case selection and backwards-compatible
five-case baseline resume with zero inference. The next live step requests at
most four calls, spaced five seconds apart, with no automatic retries.

The negative-only run `ranking-20260908-185305-510020` passed fee, processing-time
and appointment questions: every candidate received grade 0, and none qualified
as direct support. The fourth request (`de-partial`) stopped on HTTP 429 after
15.152 seconds. The provider identified a tokens-per-minute limit of 8,000, with
6,078 used and 2,775 requested, and returned a numeric Retry-After of 7 seconds.
Thus five-second request spacing was insufficient for this workload and account
at that time. No failed generation was returned. Three negative checks are saved;
the subset aggregate gates remain null until the partial-support case completes.
Offline resume validation confirmed that only `de-partial` will be submitted next,
with the original v2 prompt and all twelve passages. The planned manual retry
waits at least the indicated delay and makes one new request without automatic
retries or repetition of successful cases.

The final negative-case resume `ranking-20260908-185439-703627` passed
`de-partial` in 1.495 seconds with one new request. The L-permit passage
(`zh-e004`) received grade 2 because it supplies contract duration but no fee;
all other passages received grade 0. No passage reached the direct-support
cutoff of 3. The four-case subset is now complete with `abstention_passed=true`
and `quality_gate_passed=true`; `positive_retrieval_passed=null` correctly reflects
that this subset has no positive cases. Offline validation verified all four
saved requests and grade maps and found no pending subset cases.

Across the Zurich experiment, the unchanged v2 prompt produced five passing
positive cases and four passing negative cases. The sixth positive case passed
only in the separately recorded assisted formatting repair after schema-invalid
responses. This is not a clean ten-case pass for unchanged v2. The original
five-case prefix and four-case negative subset remain separate records, with the
repair explicitly labelled. Together these branches used fifteen requests:
fourteen unchanged-v2 attempts (nine valid results and five HTTP failures) and
one successful repair request. The causes of two early status-only failures
remain undetermined; subsequent captures identified rate limiting and a string
grade where an integer was required.

This stage demonstrates useful passage selection and rejection of partial
answers on the assistant-labelled Zurich packet, while exposing response-format
reliability and throughput limits. It does not yet evaluate Qwen candidate recall
or the Zurich passages through the runtime/MCP pipeline. Those are the next
integration checks; no active model configuration or governed release was changed
by the result audit.

### Zurich embedding candidate recall preparation

`.local/test_zh_embeddings.py` prepares the same twelve exact source passages
and ten frozen questions for `qwen_embedding_0_6b` (`qwen3-embedding:0.6b`).
The six positive targets must rank within the top three of twelve candidates by
cosine similarity. Top-one recall is reported separately; ties are counted
pessimistically so evidence-ID ordering cannot manufacture a pass. Negative
queries retain similarity diagnostics but do not receive an embedding abstention
pass/fail judgement. The ranker's direct-support gate remains a separate check.

The input transform is unchanged raw question text and exact normalized source
passages, with no generated claims, translations or query-prefix additions.
Twenty-two texts are split into six sequential batches of at most four. This
local test sets a 120-second timeout without changing the normal deployment
profile, sends no Groq requests and performs no automatic retries. Each completed
batch is saved with plan/input hashes; resume validates model identity, count,
1024-dimensional finite nonzero vectors and batch order before reusing it.
All completed vectors are retained for subsequent runtime harness construction,
even if a candidate-recall quality check fails.

Offline preparation `embeddings-20260908-185815-304466` passed with plan hash
`bc93ac0f73f3ed4e1d7739cc78b8217c030a6c0334f0779d3ab159452600501e`.
Synthetic offline controls checked correct target recall, tied-score rejection,
negative-case exclusion from the recall gate, and invalid-vector rejection.
No model calls were made; live embedding recall and latency remain pending.

The live embedding run `embeddings-20260908-185929-413480` completed all six
batches in 11.064 seconds, with 22 vectors of 1024 dimensions and no ranking
requests. All six positive targets ranked within the top three (recall 1.0).
Top-one recall was 0.5: all three German questions ranked their target first,
while the three English questions ranked theirs second. This small matrix
supports retaining multiple candidates for ranking, not replacing ranking with
the nearest vector. Negative-query similarity remains diagnostic only.
The vector-file SHA-256 is
`03dc9aefda06cf9b550185fdcda32bcdcda4457ba8f3f73b1e50a7c6610a1c54`.

### Zurich runtime harness preparation

`.local/build_zh_runtime_harness.py` created
`zh-runtime-harness-20260908-190309-949650`, reusing the twelve saved document
vectors. It validates packet/source/vector hashes, recomputes the recall result,
and binds exact contiguous normalized windows to the saved Zurich citation.
The release contains no published facts, rules or equivalences. Catalog, approval
and evaluation declarations, capture-date scope and freshness policy remain
explicitly synthetic test metadata.

The runtime requires projections in EN/DE/FR/IT/RM and a candidate limit of at
least 20. This harness therefore supplies 60 draft topic projections (the German
source headings plus short assistant translations) and considers all twelve
passages. These are topic labels, not full claim translations; translation
accuracy is unvalidated. Query routes are enabled only for English and German,
with German source evidence and test jurisdiction CH-ZH. It pins the unchanged
`groq-ranking/v2` rubric and grade-3 cutoff. Existing deployments are unchanged.

Release validation and an offline first-case replay passed, including exact
source-evidence and citation round-trip checks. Replayed ranking scores came from
the earlier passage-only request, so this checks runtime plumbing with the new
projections, not live semantic quality. The first prepared live case is the
English moving-registration question (`en-move`), expected to return `zh-e002`
as `EXCERPTS_ONLY` with no supported facts. It permits one live query embedding
and one ranking call, without retries. Release-file SHA-256:
`e822e48737c661cf87ddd2a910c4ad79b5a52addd3e9f2b1c4b3bcc0af40ac6c`.
Offline preparation `abstention-20260908-190401-098318` validated the exact request
scope and provider identities with zero model calls.

The first live runtime run `abstention-20260908-190516-356899` passed `en-move`
in 9.769 seconds, with one query embedding and one ranking request. It returned
exactly `zh-e002` as `EXCERPTS_ONLY`; that passage scored 3 and the other eleven
scored 0. This establishes the single positive runtime case, not the full Zurich
matrix or runtime abstention.

The next prepared step uses `.local/test_sem_mcp.py` with explicit case,
provider-config and expected-candidate-count arguments. The German `de-partial`
question requests both permit duration and a fee, so acceptance requires empty
evidence and `NONE` through MCP. The helper validates release, case-file and
provider bindings, checks advertised schemas and structured/text response parity,
and skips evidence reads when none are expected. Its live ceiling is one embedding
and one ranking request, without retries or a caller model.

Offline check `mcp-check-20260908-191014-790753` passed MCP initialization,
discovery and explicit provider-error transport with no model calls. Because the
server had no providers, this is not a live abstention result. Default MCP and
OpenCode configurations remain unchanged.

Live MCP check `mcp-check-20260908-191113-166695` passed `de-partial` in 10.531
seconds. One resolve returned `INSUFFICIENT_VERIFIED_EVIDENCE`, `NONE`, empty
evidence and all four retrieval channels, with no degradations. Initialization,
schemas and pinned discovery passed; no evidence read was needed. This verifies
the partly answerable case through MCP, without a caller model.

Offline caller preparation `opencode-check-20260908-191152-476796` selected the
same case and pinned harness/providers for Ling 3.0 Flash Fin Free. The guided
prompt requests coverage discovery followed by one resolve and, when evidence is
empty, no evidence lookup or invented answer. Expected labels are kept outside
the prompt. No model was invoked; the original OpenCode configuration hash
remained unchanged. Live caller compliance and answer quality await transcript
review; the requested tool sequence is not an enforced request ceiling.

The live Ling run `opencode-check-20260908-191241-251004` preserved abstention.
Offline transcript audit verified exactly two completed calls, coverage before
resolve, the exact frozen request, twelve candidates, empty evidence and supported
portions, `NONE`, all four retrieval channels and no degradations. Release,
provider, case-file, prompt-text and original configuration hashes matched.
Transcript SHA-256:
`a06d1e9873c4100d04ac89ad1cbde6f85b0065c08a2344d7e49975d8a4628802`.
The separate `assistant-audit.json` preserves this assessment without rewriting
the original run summary.

Manual answer review is a qualified pass: Ling invented no fee, duration or
citation, but overstated empty evidence as meaning the source cannot support any
factual claim about the question. A combined-question rejection does not establish
that every individual part lacks source support. It also listed `APPROVED`
without immediate synthetic qualification, although its final limits correctly
identified the test metadata. The guided caller prompt now explicitly distinguishes
an empty lookup from source-wide absence and identifies approval fields as
synthetic. This changes the test prompt only; revised live behavior is unverified.

The revised caller run `opencode-check-20260908-191533-249998` corrected the
source-scope explanation and explicitly labelled approval metadata as synthetic.
However, report accuracy failed: Ling labelled the request question as an original
source excerpt and claimed an evidence comparison succeeded despite skipping the
lookup. It also attributed request `max_evidence` to the coverage profile. These
are caller reporting errors; the MCP response still had empty evidence, `NONE`,
twelve candidates and no degradations. Exactly two completed calls preserved the
frozen inputs. Both were requested in one model turn; timestamps show coverage
finished before resolve started, so overlapping execution was not observed.

Offline audit preserved the original summary and wrote `assistant-audit.json`,
bound to transcript SHA-256
`7db3b8cc18d4b07faecf5a89a58d9680227135cabca65da3919f410c3991c4d8`.
The guided prompt now requires a separate model turn after discovery, restricts
source excerpts to evidence-array objects, and specifies None/Not applicable for
empty evidence and skipped comparisons. This is a test-prompt revision, not a
production enforcement mechanism or evidence that the model will comply.

Caller regression `opencode-check-20260908-191822-333507` passed the targeted
checks with prompt SHA-256
`095b05c8adc78f12651a91357bcbc0a8f906010c2c5da16fd6725bcfe67ffd70`.
Exactly two completed calls used separate model turns, with coverage completed
before the unchanged resolve request. The empty evidence result remained `NONE`
with twelve candidates and no degradations. Manual review confirmed that the
answer reported no excerpt or citation, marked the skipped comparison as not
applicable, and preserved the narrow lookup limitation and synthetic approval
qualification. Original configuration and all input bindings matched.
The separate audit binds transcript SHA-256
`f4c2458f6a115a23c42cab169ad7fac7a77261b2f1d47fa7e768aea8c6fa26ec`.
This closes the targeted negative caller regression; earlier failed reports remain
part of the record and this guided pass does not establish general reliability.

Offline preparation `opencode-check-20260908-192009-834198` selected `en-move`
for the positive caller check. Expected evidence is `zh-e002`; the intended calls
are coverage, one resolve, then a pinned evidence read. Acceptance requires the
original German excerpt and citation to match the tool results, with
`EXCERPTS_ONLY` and no published support. No new model calls were made during
preparation; the positive caller result remains pending.

Positive caller run `opencode-check-20260908-192057-083269` passed tool-contract
and exact evidence round-trip checks. Three completed calls used separate model
turns in coverage/resolve/evidence order, with one unchanged resolve request.
Both tools returned the full `zh-e002` object exactly as stored in the release,
including original German text and citation. The result retained
`INSUFFICIENT_VERIFIED_EVIDENCE`, `EXCERPTS_ONLY`, no supported portions, twelve
candidates, all four channels and no degradations. Input and original configuration
hashes matched. Transcript SHA-256:
`6e439f902849e755e7d64c119b6d6c11291ab701417c1b0ffbfa7251c1b969c2`.

Ling shortened the displayed quote using an ellipsis. Offline comparison verified
each retained German fragment against the original excerpt and confirmed the
exact citation URL. This is a correct abridged display, not a full verbatim display;
the complete evidence remains available in both tool responses. The separate
`assistant-audit.json` records that distinction. No additional live rerun of this
case is needed.

The targeted Zurich caller smoke checks now cover one positive evidence lookup
and one partly answerable abstention, using the revised guided prompt. This closes
that integration checkpoint only. The complete ten-case Zurich runtime matrix
has not passed as a whole; ranking-only self-employment required separate format
repair, and source/projection quality and release governance remain outside these
caller checks. Earlier failures are retained rather than counted as clean passes.

### Remaining Zurich runtime cases

The next prepared runtime subset excludes the completed `en-move` and
`de-partial` cases. It contains five positive cases (notification, short stay,
residence, frontier commuter and self-employment) and three negative cases
(fee, processing time and appointment). The local runtime tester now supports a
finite 0-60 second interval between live case starts, reports the current/pending
cases, and saves completed checks and provider counts after each result. It
retains stop-on-provider-failure behavior and performs no automatic retries.

Offline validation found that the original German notification query has 137
characters, exceeding the runtime's 120-character term limit. The shortened
`de-notification-short` variant preserves both requested details: annual workday
allowance and reporting authority. The old packet and subset are preserved;
`remaining-runtime-cases-v2-provenance.json` records the change. This variant must
not be presented as an unchanged replay of the original ranking query.

Frozen `remaining-runtime-cases-v2.json` SHA-256:
`c1774725ce670723b4d57d1c1ebdf5d2b3bf3309c2fa09841f1fa8970dd216dc`.
Preparation `abstention-20260908-192513-514369` passed scope, model and provider
validation for all eight cases with zero model calls. The prepared live run uses
a 35-second start interval and at most eight query embeddings plus eight ranking
requests, with no caller model. Pacing reduces request pressure but does not
guarantee rate-limit avoidance. Live quality results remain pending.

Runtime run `abstention-20260908-192559-938021` completed the notification-short,
short-stay and residence cases successfully, then stopped at `en-frontier` with
`OPERATIONAL_ERROR`. It attempted four embeddings and four rankings in 106.391
seconds, using 35-second pacing. The frontier embedding completed; no successful
ranking response was recorded. The original observations did not retain the
failure cause, so neither rate limiting nor schema failure can be concluded.
Five cases remain pending; aggregate quality gates remain unset.

Offline audit verified the three completed results against the frozen subset,
saved release evidence and provider score observations. It preserved the previous
summary, bound by SHA-256
`6a36e0036498fee31ef284d2b2eb20fd046cba0047b46f3876fd5122c95df0c5`.
The separate `frontier-runtime-diagnostic-case.json` contains only the unchanged
frontier request, SHA-256
`a3a40f7f03e0e00628c76c104007c0db900698c52f12b413c3a27d44ed96c4f5`.
The five pending cases are also saved separately; previous passes are not rerun.

The local tester now records provider failures before the service converts them
to its public error contract. Optional `--capture-provider-errors` enables the
existing bounded HTTP diagnostic capture; details stay in the case provider file,
while the summary includes status, numeric Retry-After and error codes. Rejected
generations remain diagnostic data and are never accepted or automatically
repaired. Offline controls exercised HTTP 429/400, invalid ranking grades and a
timeout, confirming preserved observations, `OPERATIONAL_ERROR` and no retries.
Single-case preparation `abstention-20260908-193023-329870` passed with zero network
calls. Its live ceiling is one embedding and one ranking request.

Frontier rerun `abstention-20260908-193114-257142` passed in 1.590 seconds with
one embedding and one ranking request. `zh-e006` scored 3 and all other eleven
passages scored 0; its exact saved evidence was returned as `EXCERPTS_ONLY`.
Offline audit verified the input bindings, provider observations and full evidence
object. The summary SHA-256 is
`a7e51d09e91f57839ce7b12132f8d2994e23e756102db68d1b9a4ec0a16c21ce`.
The successful rerun does not identify the earlier provider failure's cause or
erase that failed attempt.

The four remaining runtime cases are self-employment, fee, processing time and
appointment. Their requests and labels are unchanged from the frozen revised
subset. `remaining-runtime-final-four.json` has SHA-256
`8a1d4a47978d2e4e3eadf1d52d5168d643085519b0235301c79e128cfcec42e8`.
Offline preparation `abstention-20260908-193222-940025` passed with no model calls.
The prepared live run keeps 35-second pacing and diagnostic capture, with a
ceiling of four embeddings and four rankings, no retries, and no caller model.
Expected outcomes are `zh-e007` for self-employment and empty evidence for the
other three cases. These live results remain pending.

### Zurich runtime checkpoint completed

Final subset `abstention-20260908-193315-943134` passed all four cases in 107.251
seconds, with four embeddings and four rankings. Self-employment returned the
exact `zh-e007` excerpt at grade 3 without format repair; the remaining eleven
passages scored 0. Fee, processing-time and appointment questions returned no
evidence and `NONE`, with all grades 0. This successful runtime attempt does not
replace the earlier ranking-only self-employment format failure in the record.

`runtime-checkpoint-audit.json` in the Zurich harness now consolidates ten unique
passing observations across the preserved runs: six positive evidence lookups
and four abstentions. Nine cases were checked through the direct runtime and the
partly answerable case through MCP. Offline verification checked release and
provider hashes, frozen case files, trace queries, exact evidence objects, support
status, twelve candidates and no degradations. Direct-runtime observations also
matched the configured models and categorical ranking scores. The consolidated
audit references each result and summary by hash; it made no model calls.

| Case | Expected and observed evidence | Check transport |
| --- | --- | --- |
| en-move | zh-e002 | Direct runtime |
| de-notification-short | zh-e003 | Direct runtime |
| en-short-stay | zh-e004 | Direct runtime |
| de-residence | zh-e005 | Direct runtime |
| en-frontier | zh-e006 | Direct runtime, successful rerun |
| de-self-employed | zh-e007 | Direct runtime |
| en-fee | None | Direct runtime |
| de-processing | None | Direct runtime |
| en-appointment | None | Direct runtime |
| de-partial | None | MCP stdio |

This closes the selected local runtime checkpoint across runs, not a single clean
ten-case execution or a general reliability claim. The earlier frontier provider
failure remains explicitly recorded with unknown cause. The notification query
variant and earlier caller-report failures also remain documented. Revised guided
caller checks cover one positive and one negative case separately. The harness
still contains no published facts or genuine release approvals; independent source,
projection and applicability review has not been established by these checks.
No further live calls are needed to complete this checkpoint.

### Earlier live diagnostics

The subsequent prompt-only Apertus run completed two responses but repeated the
same top-level field placement errors after repair; no proposal reached review.
A Groq GPT-OSS 20B comparison of the frozen request returned HTTP 400 with
`json_validate_failed`, missing concept-level `questions` and `limitations`,
despite requesting strict schema mode. Its failed generation also used an evidence
identifier as `primary_section_id`. This was not an authentication failure or
evidence of valid extraction. The v4 extraction prompt now explicitly lists the
required keys at each nesting level and distinguishes section, scope and evidence
identifiers. Optional question content still requires a `questions` array. The
prompt's recorded hash changes; schema and acceptance checks remain unchanged.

During the English SEM live diagnostic, PublicAI's schema-constrained Apertus
70B response emitted whitespace until its token limit. A prompt-only comparison
completed in 6.7 seconds with 370 output tokens, but failed the local schema:
`scope_evidence_ids` was on the concept instead of its claim, required fields
were missing, and `primary_section_id` contained a scope identifier. Its predicate
also omitted the work branch of the source's OR condition. This is evidence of
completion in the alternative mode, not extraction quality or a proven upstream
root cause. Schema-in-prompt instructions and formatting instructions changed
along with the API response mode, so this was not an isolated causal test.

`response_mode = "prompt_only"` is now an explicit Hugging Face profile option,
with strict local validation retained and no automatic mode fallback. The default
remains `json_schema`. Schema-error repair feedback now names missing and unknown
fields and includes up to 6,000 characters of the invalid completion, marked when
truncated. This text is diagnostic model output, never accepted evidence. Existing
request and combined input limits still apply. Offline regressions verify that a
malformed proposal is withheld from review and can be repaired within the budget;
live repair success remains unverified.

Offline regressions cover source structure, contact retention, exact evidence,
logic integrity, scope mixing, incomplete assessments, empty extraction, repair
limits, saturation, provider failures, CLI planning, checkpoint isolation/reuse,
structured consolidation and stale/duplicate/missing review decisions. Positive
controls retain supported candidates. These deterministic fixtures validate the
controls; they do not prove that a model recognizes every semantic failure.

The immutable POC packet still verifies all 87 artifacts and six sources. The live
v4 diagnostics above have not established a usable extraction or quality comparison.
Next, run fresh v4 outputs
against the same frozen reference set, measure unsupported retention, scope and
logic errors, omissions, review minutes, tokens and cost, then evaluate unseen
pages with independent adjudication. Automatic publication remains blocked on
release-bound provenance, validated language/scope, operation-specific acceptance
gates and measured quality; increasing model size alone does not establish them.
