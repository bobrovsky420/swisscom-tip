# DeepSeek V4 Pro GUI review-format failure

GUI job `f6c0078579204723af48065b59557fa0` ran the saved English SEM Residence
page through `deepseek_v4_pro` and `concept_extraction_v4`. Four model calls took
about 47 seconds and retained zero candidates. Reported usage was 17739 input
tokens and 5573 output tokens, with no provider retries.

Both extraction revisions contained the same structurally valid Residence
concept: a permit requirement with connected work OR duration conditions, the
Cantonal Migration Offices' issuing role, and the complete permit taxonomy.
Assistant inspection found all six source assertions represented, exact condition
excerpts, the strict three-month threshold and source-answerable questions.

Both reviews failed because `scope_fields` was nested inside `condition_logic`
on every claim-support entry. The schema requires these objects to be siblings.
The validator correctly rejected both reviews, removed their checkpoints and
retained no candidate. The repeated checkpoint filename identifies an identical
request, not an identical response: the saved raw review texts differ.

The previous three comparison runs all retained a candidate, with two needing
review-format repair. Including this later GUI run gives three retained results
in four DeepSeek runs on this known page. The earlier 3/3 result did not establish
reliable repair or general model accuracy. No comparison result was rewritten.

## Correction prepared offline

Previously the validation error was supplied only to the extraction repair.
Because that repair returned the same valid proposals, the next reviewer received
the same source and proposals with no indication that its prior review was
malformed. The extractor cannot fix the nesting of the reviewer's next response.

The v4 pipeline now includes `review_validation_feedback` on the next review
request after a review-validation failure. It contains the previous revision,
the local error and a truncation indicator. The error is capped at 2000 characters
within the existing source/proposal input allowance; full raw responses remain
in history. The diagnostic changes that review's checkpoint key and is explicitly
treated as a diagnostic, never as evidence or an instruction to approve claims.

The review prompt now includes a JSON shape example that closes `condition_logic`
before opening `scope_fields`. Example decisions are placeholders marked uncertain;
actual claims still require individual source-based assessments. It asks the model
to correct the reported contract error in a complete review of the current
proposals. No fields are moved or invented automatically in production.

This keeps the existing one-repair/four-call ceiling, schemas, evidence validation,
negative-review rejection and human promotion requirements. It adds no provider
retry or automatic live model call. New GUI jobs start a fresh builder subprocess
and load the updated prompt; the running GUI does not need a restart for this fix.

| Artifact | SHA-256 |
| --- | --- |
| Original live report | `e340c50debb595e16ecc0b5a1c4fe6bb3f9c418841846bee5e69a60e6d63c106` |
| Original source | `4e24815fa1ac301c1d0e3c4cd7c4f63eec1802e3af00529526774c7515d578bb` |
| Extraction prompt, unchanged | `4b870022420a0be39e16b8d993a8b1a44ee122375088807835d3d1c4efc5290e` |
| Previous review prompt | `19412842e494e320b666a084c9c97da89d0204dd60e64465ac67ff14762ce284` |
| Updated review prompt | `854222e23c4209f5786f2e09cd1ad97f7d9f9f314fe3340eb8a881a4c616ed9b` |

## Offline evidence and limits

The fixture `packages/ingestion/tests/fixtures/deepseek_v4_residence_f6c00785.json`
preserves the exact live proposals, both raw failed reviews, source evidence and
provenance hashes. The original GUI job's files have unchanged hashes.

- Replaying both saved malformed reviews still makes four simulated calls,
  rejects both reviews and retains zero candidates. The second reviewer receives
  the correct validation error, while source, proposals and schema match the first.
- An assistant-authored format-only control moves the existing `scope_fields`
  assessments to the required sibling position and retains one candidate.
  Adding a negative assessment to that control again blocks retention. Neither
  control is a newly observed DeepSeek response or an independent quality label.
- Disabled repair and an odd page budget allow no additional review call. A
  model-controlled long field name does not expand the bounded diagnostic;
  its original full response remains in history.
- The prompt's JSON example passes the actual claim-assessment schema. All 115
  ingestion tests passed, including these replay and contract checks.
- All 158 knowledge-builder tests passed, including the existing CLI, prompt
  override, checkpoint and structured workflow checks (273 tests in total).
- A real CLI dry-run with provider construction blocked loads the updated prompt
  and still plans four calls for one page, with zero network calls.

The dry-run plan, replay reports, second review request, original file hashes and
audit are under `.local/admin/deepseek-review-f6c00785-20260909/`. These checks
establish request construction and validation behavior, not whether the model
will correct its next live response.

## Resume GUI, one step at a time

Next: in **Saved pages**, keep only **SEM residence overview (en)** selected with
`deepseek_v4_pro`, and click **Preview extraction plan**. Confirm one page, four
planned requests, zero sent and the updated review prompt hash before proceeding
to **Run extraction** / **Confirm extraction** in a separate confirmed step.

After a live run, inspect candidate count and review history as well as status.
The GUI can label a run **Needs attention** when a candidate exists because model
coverage assessments still require human review. Zero candidates with the schema
errors above was an actual failure to retain a usable draft.
