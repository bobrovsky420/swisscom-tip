# POC-01 preparation and gold freeze

Run from the repository root using the repository environment. No model or
network calls occur. On Unix, use `.venv/bin/python`; on Windows use
`.venv/Scripts/python.exe` in these commands.

```shell
./.venv/bin/python scripts/test/poc01/prepare_packet.py prepare
./.venv/bin/python scripts/test/poc01/prepare_packet.py verify
./.venv/bin/python scripts/test/poc01/prepare_packet.py freeze-review --stage initial-batch
./.venv/bin/python scripts/test/poc01/prepare_packet.py freeze-review --stage full-gold
```

`prepare` defaults to the system temporary directory's `swisstip-zhch-poc` and
the repository's `.local/experiments/poc-01`. `--source` and `--destination`
override them, but the destination must remain under the ignored `.local`
directory. A nonempty destination is refused, including previously annotated
packets. `verify` is read-only and permits changes only to `reviewer/gold.csv`
and separately versioned `review-freezes/`. Keep original temporary artifacts
untouched until independently satisfied with the preserved archive.
The packet inventory is fixed: comparison worksheets, scripts, previews and
scratch files belong in a separate sibling directory, such as
`.local/experiments/poc-01-comparisons/`, not inside the preserved packet.

The packet contains:

- `archive/`: every original artifact, including failed logs and checkpoints,
  copied byte-for-byte. Original manifests and embedded historical paths remain
  unchanged. Model proposal contents are copied and hashed, never parsed or
  used to create gold labels.
- `metadata/source-map.json`: original paths/URLs and portable archived and
  reviewer paths. `metadata/frozen/` preserves current script, schema, suite,
  source code, specification and TOML configuration snapshots. These are current
  preparation inputs; they do not retroactively identify historical HF models.
- `preservation-manifest.json` and its SHA-256 sidecar: all immutable file hashes
  and initial worksheet hash. Verification detects accidental corruption and
  inventory changes; checksums are not a signature or filesystem write lock.
- `reviewer/`: source-only index, normalized evidence sections, full escaped raw
  HTML with restrictive CSP, instructions and ten blank gold rows per page.
- `review-freezes/`: new, uniquely named snapshots after human labeling. Every
  freeze binds the worksheet to the preservation manifest and records its hash.
  `validated-gold.json` records exact checked evidence references, deriving
  offsets from each unique quote without modifying the original worksheet.
  A freeze is not a POC pass, adjudication, publication or holdout assessment.

The existing normalizer is called with `preserve_structure=True`, matching the
current v3 profile's normalization mode. Its code/configuration hashes are
frozen. Its semantic fidelity remains unvalidated, so reviewers must compare
normalized sections against the escaped full original. Source language remains
an unvalidated hint. The raw HTML is escaped text, so active HTML/scripts are
not rendered; original scripts remain readable as text for preservation.

The source-only worksheet asks the user to select 10-15 high-risk concepts for
the first batch and then 5-10 per page. The user supplies both passes; this is
same-person re-review, not an independent reviewer. Assistant-structured fields,
scope corrections and draft assessments must retain their provenance; assistant
checks or a primary-review confirmation cannot populate second-review decisions
or minutes. Independent adjudication, new held-out pages, a frozen common proposal
set, comparison providers and whole-run budgets are prerequisites for the full
POC-01 reviewer comparison; the current record below identifies what is ready.

## Current internal review artifacts

The [experiment record](../../../docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md)
documents 30 frozen source concepts and 101 primary-review minutes, with an
assistant-authored comparison of the two final historical runs. The common set
contains all 116 retained/rejected proposals; no fresh configured extraction or
reviewer calls were made. The user's same-person second pass is complete: 30
references accepted, 60 comparison assessments agreed, and 42 reported review
minutes. Independent evaluation remains pending.

The original pre-comparison full-gold freeze is
`.local/experiments/poc-01/review-freezes/20260906T133038-b99b9023/`.
The comparison browser view, CSVs, fixed inputs and hash manifests are under
`.local/experiments/poc-01-comparisons/20260906-full-gold-01/`.
Open its `index.html` directly in a browser; it displays one concept and both
models at a time without a server. It does not save answers. Record feedback
through the guided review or the CSV worksheets, with time recorded once per
reference concept. The local `assemble.py` records how the view was generated
and refuses to overwrite outputs; corrected drafts require a preserved revision.

The completed second-pass gold freeze is
`.local/experiments/poc-01/review-freezes/20260906T165716-1a187305/`.
The comparison directory's `second-pass-001/` contains frozen review CSVs,
`completion.json`, `seed-selection.json` and a hash manifest. Eight accepted
references were selected for internal seed authoring; catalog mapping and
publication remain pending. Per-response changes are preserved in `review-revisions/`.
The working gold worksheet now contains second-pass decisions and actual minutes;
old freezes, comparison inputs and the historical browser view remain unchanged.
Use the completion records for current status rather than the viewer's draft banner.
The per-question worksheet was not independently completed by these comparison-level
agreements. No independent adjudication or POC pass is implied.

These internal artifacts and their original source text must remain ignored.
Only sanitized findings and specification/backlog changes belong in tracked docs.
New specification versions do not alter metadata already frozen in the packet.

Offline tests use synthetic source data only:

```shell
./.venv/bin/python -m unittest discover -s apps/knowledge-builder/tests -p test_poc01_packet.py -v
```
