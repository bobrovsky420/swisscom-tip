# Apertus 70B v4 GUI extraction diagnostic

Date: 2026-09-09. Three live runs retained zero candidates. Prompt refinements and
explicit claim checks have not produced usable output on this page. The latest
run repeated a broken condition tree and altered quotation during repair. A
further pipeline change collects independent structural errors together and
repairs proposals before review; this change has been tested offline only. This
is a known-case diagnostic, not an independent comparison or a qualified extractor.

## Preserved live result

GUI job `bf0585b3892a49bc9aa64fc814b79b41` processed one saved SEM English
residence page using `concept_extraction_v4`, `apertus_70b`, PublicAI through the
Hugging Face router, and `response_mode=json_schema`. The requested model was
`swiss-ai/Apertus-70B-Instruct-2509:publicai`; all four responses reported the
explicitly accepted alias `swiss-ai/apertus-70b-instruct`.

The report records four requests, 60.821 seconds, 9559 input tokens and 3731
output tokens. Two proposals were generated in each revision; zero candidates
were retained. CLI exit 0 means the report was written, while the GUI correctly
marked the job `needs_attention`.

| Call | Observation |
| --- | --- |
| Extraction | Two schema-valid concepts, including a duration-only requirement represented as a fact with empty condition fields. |
| Review | Scope, completeness and questions were uncertain; source coverage was partial. This triggered the single permitted repair. |
| Repair | Two revised proposals repeated the work-branch omission, incorrect authority role and unanswerable questions. |
| Review | Concept 0 had two questions but only question index 0 was assessed. `parse_review` rejected the incomplete review. |

The raw failed review is preserved in `semantic_reviews[].history` even though
its checkpoint was removed. Three earlier checkpoints remain. Original files
are under `.local/admin/jobs/bf0585b3892a49bc9aa64fc814b79b41/` and are Git ignored.

| Artifact | SHA-256 |
| --- | --- |
| `result.json` | `1131f24784b72d2985d4e1e52fdb7d82a022d901fe707e354e13fd074eee5e76` |
| Original source bytes | `4e24815fa1ac301c1d0e3c4cd7c4f63eec1802e3af00529526774c7515d578bb` |

Assistant inspection found additional semantic failures: the work alternative
was absent; the issuing office was placed in a requirement's recipient field;
questions requested unsupported exception and renewal information; the first
review swapped the reasons for concept 0's two questions. Coverage review also
treated definitions and procedures absent from the source as extraction omissions,
while missing actual source assertions. Fixing question count alone would not
make these proposals acceptable.

## First prompt revision

The first extraction prompt revision explicitly inventories source assertions, preserves
conditional rules in typed claims and connected logic, separates issuing roles
from recipients, and checks that each proposed question has a source-backed
answer. Repairs must restore actual omissions and remove unsupported assertions
or questions, without inventing details requested by an incorrect review.

The review prompt specifies exact per-concept question counts and zero-based
indices, including unsupported/uncertain questions. Reasons must match their
question. Concept completeness and block coverage are assessed against what the
source actually states; a bounded category list need not include absent renewal
procedures. Actual omitted conditions, unsupported roles, precision and inferred
logic must still fail the corresponding review dimensions.

| Prompt | Previous SHA-256 | Revised SHA-256 |
| --- | --- | --- |
| Extraction | `63bc1325d82bac92cac88f406811daa49195385d2ba2f4a3040cac727e654fe2` | `95ee33096b7d70f40ecab5b75fd00b7b3f905fc7f0d98048607958196ecef545` |
| Review | `60c90403561caa628b409a4d4f2b639d3b2ae5e9eec692b707a8d98486945a87` | `e3bdcfecd5b7e1329d9b1c66d8fc764524079d692b94d95c257a185e613a6694` |

In this first revision, model/provider selection, response schemas, validation,
repair count, token limits and acceptance gates were unchanged. New CLI invocations load the revised
packaged prompts and record their text/hashes; existing reports retain the old
text and identities. A newly started GUI job invokes a fresh CLI subprocess.

## First revision offline verification and live comparison

Offline verification passed 92 ingestion tests and 10 structured builder workflow
tests. Replaying the original review still withholds approval, and the incomplete
final review still fails with the same question-assessment error. The original
report and source bytes are unchanged. A dry-run using the same saved source and
job configuration loads both revised prompt hashes and plans four requests with
zero model calls; provider construction is explicitly blocked during the check.
Its plan and audit are saved under
`.local/admin/prompt-revision-bf0585b3-20260909/`. These checks establish loading,
provenance and validator behavior, not improved model judgment.

The GUI preview `9addfe65e3044c2ab568fb8fb10617c5` subsequently confirmed those
hashes and four planned calls with zero inference. After user confirmation, live
job `d1b9c10eb3674b289a96693b84d68379` loaded the same revised prompts and source.
Its `result.json` SHA-256 is
`f75e12feec79b114b23b78d794dbe571f3121539d1673a843bd09645b1e0c886`.

| Call | Observation |
| --- | --- |
| Extraction | Two concepts. The work alternative returned in prose, the rule became a requirement, and questions were empty. Conditions and groups remained empty. Authority roles, population and permit status were still misassigned. |
| Review | Structurally valid, but approved unsupported scope and claimed complete block coverage without an actual issuance claim. Completeness still demanded exceptions and renewal details absent from the source. |
| Repair | Two concepts retained these errors; changes were minor. |
| Review | Response metadata reported `aisingapore/Qwen-SEA-LION-v4-32B-IT` for an Apertus 70B request. Identity validation rejected it before accepting completion content. |

The run attempted four network calls in 113.211 seconds. Three accepted completions
reported the approved `swiss-ai/apertus-70b-instruct` alias; their usage totals were
8197 prompt tokens and 1928 output tokens. Zero candidates were retained. Failed
call billing is unknown. Empty questions do not establish that indexed reviews
of nonempty question lists improved.

A separately authorized, single-request diagnostic used the same route and
`json_schema` mode, with a 64-token output limit and no retries. It returned the
approved alias and the requested tiny JSON object in 2.161 seconds (37 input,
6 output tokens). Metadata is saved at
`.local/admin/provider-diagnostics/apertus-70b-identity-20260909T171849711384Z.json`.
One successful probe does not establish consistently correct routing or explain
whether the earlier mismatch was routing or response metadata.

## Follow-up: explicit claim checks and a worked example

The extraction contract remains `swisstip.structured-claims/v1`. A new appended
synthetic visitor-badge example demonstrates two connected OR alternatives, a
strict numeric threshold, and a separate issuing-action claim. The issuer is
the actor of the issuing fact; it is not copied into the requirement's actor or
application recipient fields. The example does not contain SEM source facts.

V4 review responses now use `swisstip.structured-review/v2`:

- Every claim-support entry requires `condition_logic` and `scope_fields` in
  addition to its statement decision. Each of the six scope fields gets its own
  decision and reason, including fields whose value is `unspecified`.
- Condition logic first classifies source applicability as `conditional`,
  `unconditional` or `uncertain`. This is a model assessment, not inferred by a
  keyword rule in Python.
- A supported conditional assessment with no conditions is rejected as internally
  inconsistent. Supported added conditions on an unconditional assertion, and
  supported logic with uncertain applicability, are also rejected.
- A failed detail assessment blocks retention even if the statement and broad
  concept summaries are supported. Valid negative reviews remain in the repair
  feedback. Missing detail fields fail validation rather than defaulting to approval.

This enforces more explicit and internally consistent review; it does not prove
that the reviewer correctly recognizes conditional language or authority roles.
A model can still misclassify a source or approve an unsupported scope field.
Source coverage, additional assertions and final human approval remain necessary.
Unconditional obligations and descriptive facts can still have empty conditions.
The unchanged 4096-token completion limit also means verbose detailed reviews can
still be truncated; no automatic fallback or extra calls were added.

| Current prompt | SHA-256 |
| --- | --- |
| Extraction, including worked example | `4b870022420a0be39e16b8d993a8b1a44ee122375088807835d3d1c4efc5290e` |
| Detailed review | `19412842e494e320b666a084c9c97da89d0204dd60e64465ac67ff14762ce284` |

Model selection, response mode, request budgets and repair count are unchanged.
Reports record the new review contract version. Original reports remain readable;
the old review shape is intentionally not accepted as a new detailed review.
Changed prompts and response schemas already produce distinct checkpoint keys.
Custom v4 review-prompt overrides must request the new schema.

## Follow-up offline verification

The repository test fixture location is
`packages/ingestion/tests/fixtures/apertus_v4_residence_d1b9c10e.json`. It preserves
both exact saved proposal revisions, the first review, source evidence and hashes.
No final review content is fabricated. Tests that supply new detail assessments
label them as assistant-authored controls, not fresh Apertus output.

- 101 ingestion tests passed, including replay of both saved proposal revisions,
  all seven detailed rejection dimensions, missing fields, contradictory condition
  assessments, repair feedback preservation, and unconditional positive controls.
  The worked example also passes the real schema, source-quote and tree validators.
- The broader 143-test builder run passed 142 tests and exposed one old empty-review
  fixture lacking the new version field. After updating that fixture, all 10 tests
  in its structured-workflow module passed, including CLI/checkpoint reuse.
- An offline dry-run on the exact saved source and frozen GUI configuration loads
  the current prompt hashes and plans four calls with zero requests sent. Provider
  construction is blocked. All original job files, including checkpoints, have
  unchanged hashes. The saved proposal shapes still validate; the original broad
  review does not satisfy the new detailed contract.

The dry-run plan and audit are under
`.local/admin/review-v2-d1b9c10e-20260909/`. No new live extraction was performed
while preparing that follow-up. These results establish contract behavior and
prompt loading, not an improvement in Apertus extraction accuracy.

## Latest live result: the repair repeated the invalid proposal

GUI preview `c527ae6ab4ed4a4ab82ad15b1309569e` verified the current prompt hashes,
the same source and four planned calls with zero inference. The subsequently
confirmed live job `8d0e464828e74e2bbc024ec4f8d0702d` used those prompts and retained
zero candidates. Its report SHA-256 is
`5835d256e03e4c2b17b5c6e033810fa93b78f5323426164499bdc2ee8f6ac4d7`.

All four responses reported the approved Apertus 70B alias. The run took 42.313
seconds and recorded 11577 prompt tokens and 2198 output tokens, with no retries.
Both extraction responses contained exactly the same single concept and two
claims; both review responses were also identical.

The requirement now had separate work and duration conditions, including `gt`,
value `3` and unit `months`. However, `condition_root` was the operator string
`OR` and `condition_groups` was empty. The first condition also quoted "works
during their stay in Switzerland" instead of the source's "works during his/her
stay in Switzerland". The root error stopped validation before the quotation
error was reported. An in-memory correction of only the root/group exposed the
quotation error; it did not change any saved files.

The second claim now asserted the issuing action as well as permit categories.
The requirement still assigned the issuing office as recipient, and unsupported
population/procedure fields remained. Because structural validation rejected the
whole proposal, both reviews received an empty concept list. Both marked the
substantive block `partial` with no concept reference, which fails coverage
validation. No per-claim review was exercised, so the detailed review changes
have not yet been evaluated on a live valid proposal.

## Pipeline repair: collect independent errors before review

The new structural validator gathers independently checkable errors across a
schema-valid proposal instead of returning immediately after its first bad root.
Each structural rejection retains its first-error `reason` and adds an `errors`
array with paths, reasons and an optional repair hint. Graph checks still reject
unknown roots, cycles, dangling nodes, duplicate IDs/operands, shared subtrees,
unconnected nodes and unresolved logic without limitations. Numeric values and
exact quotations are checked independently, including in later claims. JSON
shape failures still stop before these field checks, rather than inspecting an
unsafe or incomplete object shape.

When structural errors exist and a repair plus review fit the budget, the flow
now sends the complete error list directly to the repair call. Each proposal
appears only once in that payload. Semantic review follows only after repair
validation. If no valid proposal remains, review is skipped and source coverage
stays unresolved. If repair is exhausted but a mixed result contains valid
proposals, only that valid subset is reviewed. A genuinely empty extraction,
with no invalid proposals, still needs a source coverage audit.

Schema-valid extraction checkpoints remain saved and are revalidated on replay.
Changed repair feedback naturally selects a different checkpoint key. The one
repair limit, later packets' audit reservations, existing input-size bound and
the preview's request ceiling remain enforced. In particular, an odd page budget
does not authorize an early repair beyond the preview's lower even ceiling.
No model, prompt, response schema, quotation or semantic acceptance rule was
changed in this pipeline repair. It supplies better feedback; it does not
construct a missing OR group or replace quoted words automatically.

## Pipeline repair offline verification

`packages/ingestion/tests/fixtures/apertus_v4_residence_8d0e4648.json` preserves the
exact saved proposals, raw reviews, source evidence and provenance hashes.

- 110 ingestion tests passed. The saved failure now yields both root and quotation
  errors in a single repair payload. Replaying its identical bad repair makes
  two simulated extraction calls, zero review calls and retains zero candidates.
- A separate assistant-authored control fixes only the tree and quotation. It
  reaches review on call three, where a supplied negative authority-role decision
  still blocks retention. This is not a newly observed Apertus correction.
- Positive controls retain valid repaired proposals. Further controls preserve
  empty-extraction coverage review, mixed valid/invalid results, later packet
  budgets, disabled repair and odd page limits. Error collection still rejects
  cycles, dangling references, repeated nodes and errors in later claims.
- The existing 143-test builder suite passed. The updated 11-test structured
  workflow suite also passed, including a new CLI/checkpoint regression: two
  invalid extraction checkpoints are retained, then reused on the second run
  without new provider calls or any semantic review.
- A dry-run using the actual saved HTML and frozen GUI configuration still plans
  four calls with zero inference. Both prompt hashes are unchanged. Replaying the
  original proposals through the new extraction flow produces a 4704-character
  repair payload containing both errors. The original invalid coverage response
  is still rejected by the unchanged coverage validator. All original job files,
  including reports and checkpoints, retain their hashes.

The plan, replay report, exact repair request and audit are saved under
`.local/admin/structural-repair-8d0e4648-20260909/`. Their replay provider is labeled
`offline-replay`; no live provider was invoked. No improvement in Apertus repair
accuracy is claimed. A new live run requires the user's next step confirmation.
