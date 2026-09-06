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
quality check. The six archived POC-01 pages pass individual offline preflight,
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

- `swisstip.logical-blocks/v1` preserves whole lists, tables and heading/body
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

## Validation and remaining evidence

Offline regressions cover source structure, contact retention, exact evidence,
logic integrity, scope mixing, incomplete assessments, empty extraction, repair
limits, saturation, provider failures, CLI planning, checkpoint isolation/reuse,
structured consolidation and stale/duplicate/missing review decisions. Positive
controls retain supported candidates. These deterministic fixtures validate the
controls; they do not prove that a model recognizes every semantic failure.

The immutable POC packet still verifies all 87 artifacts and six sources. No live
v4 inference or quality comparison has been performed. Next, run fresh v4 outputs
against the same frozen reference set, measure unsupported retention, scope and
logic errors, omissions, review minutes, tokens and cost, then evaluate unseen
pages with independent adjudication. Automatic publication remains blocked on
release-bound provenance, validated language/scope, operation-specific acceptance
gates and measured quality; increasing model size alone does not establish them.
