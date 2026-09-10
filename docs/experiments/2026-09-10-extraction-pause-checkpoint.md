# Extraction pause checkpoint - 10 September 2026

Historical checkpoint: the user subsequently chose the simpler V3 extraction
workflow and DeepSeek V4.1 Flash. See the [switch and prepared offline plan](2026-09-10-v3-flash-switch.md)
for the current resume point. The V4 results and review history below are preserved.

Status: paused at the user's request after the latest live-result audit. No new
extraction, prompt correction or review decision is part of saving this checkpoint.
The next discussion should address the extraction approach and evaluation scope
before scheduling another whole-page run.

## Current state

| Item | Checkpoint |
| --- | --- |
| Latest live job | `891e31a32d0f4f09b16a6ab062eaae00`, created 20:37 Zurich time on 10 September |
| GUI | Local console at `http://127.0.0.1:8000`, Builds & review, Concept extraction |
| Page | Aufenthalt für EU/EFTA-Staatsangehörige, Kanton Zürich; asset `6be69747eebc489294932bc1d8d3c770` (`zh-eu-efta`) |
| Model/profile | `deepseek-v4-pro` / `deepseek_v4_pro`; thinking disabled, JSON-object response |
| Prompt profile | `concept_extraction_v4`, ownership clarification active |
| Contracts | `swisstip.structured-claims/v2`, `swisstip.structured-review/v2` |
| Source plan | Four packets, 68 eligible blocks, 37 policy exclusions |
| Limits | 8192 output tokens; 64000 review/repair input characters; 180 seconds; zero automatic retries; 12 calls/page and 30/run configured |
| Latest outcome | 11 calls, 355.874 extraction seconds, seven retained drafts, six warnings, `needs_attention` |
| Latest human reviews | Zero recorded, confirmed through the local API when saving this checkpoint |
| Review recommendations | Three accept draft, four needs changes; recommendations are not saved decisions |
| Previous reviewed run | `b5ec257972d849da9ddceb0cdb975b2c`: 14 decisions saved, six accepted and eight needs changes |

The latest source review recommends accepting the introductory residence summary,
L permit and G permit. FZA, municipal registration, employment admission and the
90-day notification procedure need changes. Exact comments and source findings
are in the [latest result review](2026-09-10-deepseek-concept-ownership.md#source-review-of-the-seven-retained-drafts).
Do not transfer previous decisions to this result, including for a repeated
candidate ID.

The ownership prompt experiment did not meet its contact-extraction target.
Contacts still combined three ownership groups; self-employment, non-employment
and address/onsite-hours content accepted in the previous run was no longer
retained. Family document logic was correctly rejected by the model reviewer.

## Preserved artifacts

- Latest job files: `.local/admin/jobs/891e31a32d0f4f09b16a6ab062eaae00/`.
- Latest audit, exact-quotation findings, packet failures and review notes:
  `.local/admin/zh-ownership-live-891e31a3-20260910/`.
- Previous reviewed result and decision audit:
  `.local/admin/zh-date-live-b5ec2579-20260910/`.
- Prepared ownership plan and input/configuration comparison:
  `.local/admin/zh-concept-ownership-b5ec2579-20260910/`.
- Experimental history:
  [GUI extraction](2026-09-10-deepseek-zh-gui-extraction.md),
  [calendar dates](2026-09-10-deepseek-calendar-dates.md), and
  [concept ownership](2026-09-10-deepseek-concept-ownership.md).

The `.local` artifacts are local and Git-ignored; this checkpoint references them
without claiming they are committed or portable. The source/configuration and
raw report/checkpoints were not edited during the result audit.

| Identity | SHA-256 |
| --- | --- |
| Source HTML | `b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4` |
| Frozen configuration | `ffa3bbdc8018dd5312c2afe621546057ea6196147148431bca4e7a92e1912ac3` |
| Extraction prompt | `caadc95fed4a5736b179e9f9b7a480bd78fbc052b2d718f53a9ea6381c8f84de` |
| Review prompt | `d2478d3ac3c84104941e47293fe315c2cf350f98bf0e81345829ac9aef3f698b` |
| Latest raw report | `5b2caebd29df8dda2052b3829ed8d8110b1056e187423d5fc587d924e52f13c7` |
| Latest canonical GUI result | `6238166d7e7b9e79991db45dcce372ab967025c196331f888f12be5710cb9851` |

## Diagnosis to carry forward

The main engineering assessment is that a broad semantic-authoring task has been
coupled into each model operation: assertion discovery, ownership allocation,
exact quotation, role inference, condition logic, dates and output-schema
compliance. Another call to the same configured model checks semantics and
coverage, but observed false approvals show that this is not a reliable substitute
for source-based validation. Local guards work; packet-wide failures and shared
request budgets make each model mistake expensive.

The GUI iterations have chiefly repaired the latest symptom through whole-page
regeneration. That can lose previously good output and creates repeated human
review. The latest run had no output-token truncation or provider retry, yet the
target failure persisted. The 338 passing ingestion/builder tests establish
implementation behavior, not semantic extraction quality.

Existing [POC-01 references](2026-09-06-poc-01-semantic-ground-truth.md) should
anchor a smaller, repeatable quality evaluation; independent adjudication and
controlled reviewer evaluation remain pending. A recommended next direction is
to curate a small correct pilot, preserve accepted source-backed work, and evaluate
smaller automated stages by useful accepted content, omissions and human time.
This is a proposed direction, not an implemented architecture change. The product
already permits verified excerpts where structured conclusions are unestablished.

Concrete technical leads remain available for later investigation: the 6000-character
invalid-completion prefix given to repair, missing block/concept details in coverage
errors, source ownership allocation and preservation of conditional branches.
These are recorded leads, not an instruction to resume incremental tuning before
the broader approach is reconsidered. Source, quotation and semantic validation
guards should remain enforced.
