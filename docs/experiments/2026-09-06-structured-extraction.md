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
