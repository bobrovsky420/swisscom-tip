# POC-01 source-only review

This worksheet is prepared, not evaluated. All historical zh.ch pages are
development examples. You are the primary reviewer and the same person doing a
second pass. That re-review does not provide independent adjudication or holdout
evidence. Do not open the neighboring archive's proposals, model reports, logs or
checkpoints until the source labels have been frozen.

1. Open `index.html`. Read each normalized source and its full escaped original
   HTML. The original is inert text, including scripts as text; it makes no
   network requests. The normalizer has not passed its fidelity experiment.
   Check conditions, exceptions, dates, numbers and population boundaries in the
   original; record suspected normalization loss in `notes`.
2. Edit `gold.csv` in a CSV-aware editor. Ten blank rows are supplied per page.
   Derive 5-10 expected answerable concepts per page from sources yourself.
   Start with 10-15 concepts across pages that you judge highest risk; mark
   `first_batch=yes` and explain `risk_reason`. No concepts or risk labels were
   supplied by a model. Leave unused rows blank.
3. Fill label, description, scope, conditions, exceptions, domain/topic,
   proposed supported operation, required context and typed applicability.
   Write `none stated` where the source has no condition or exception, and
   explain uncertainty explicitly. Proposed catalog/context fields remain
   authoring proposals and do not establish supported product coverage.
4. Enter `evidence_refs_json` as a JSON array. Copy exact text from a section's
   `evidence_text` in `sources/source-NN/normalized.json`. Include its section ID
   and exact quote; the freeze command derives offsets when the quote occurs
   exactly once. Include multiple references for separate conditions or
   exceptions. For a synthetic section containing `Heading\nExample`, use
   `[{"section_id":"section-0001","quote":"Heading"}]`.
   This is a format example, not a claim from the corpus. CSV editors handle
   quotation escaping; a hand-edited CSV must double internal quotes.
   If the quote occurs more than once, include a longer unique quote or add
   explicit `start` and `end` offsets. These count zero-based Unicode characters
   in `evidence_text`, with an exclusive end. Derived exact references are saved
   separately in `validated-gold.json`; your CSV is never rewritten.
5. Record actual primary `review_minutes`. In the second pass, fill
   `rereview_decision`, `rereview_notes` and `rereview_minutes` yourself.
   Keep independent-adjudicator fields empty. A source-only second pass can
   improve these labels but cannot count as an independent reviewer.
6. Ask the operator to freeze the initial batch, then freeze full gold after
   completing 5-10 concepts per page. Freezing validates completeness and exact
   spans, and snapshots the worksheet without publishing or passing the POC.
   Preserve each snapshot; revisions require another freeze.

If a claim is present only in the full original and is missing from normalized
sections, record the loss and pause that concept's normalized evidence labeling.
Do not invent a section reference or remove the condition to make validation pass.

Later comparison work must freeze one common proposal set and record outcomes
for never proposed, rejected, represented elsewhere and truly missing concepts.
Structural validation, same-model review, an independent reviewer configuration,
and structured condition/exception checking then use that same set. Provider
selection, whole-run elapsed/currency budgets, independent second review and an
unseen natural holdout remain pending. No live comparison has been run.

Keep this entire packet internal under the ignored `.local` directory. It
contains restricted source text, quotes and human annotations. Do not commit it.
