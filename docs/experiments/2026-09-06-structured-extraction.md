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
