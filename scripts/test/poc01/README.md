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
same-person re-review, not an independent reviewer. Independent adjudication,
new held-out pages, a frozen common proposal set, comparison providers and
whole-run budgets remain open prerequisites for the full POC-01 comparison.

Offline tests use synthetic source data only:

```shell
./.venv/bin/python -m unittest discover -s apps/knowledge-builder/tests -p test_poc01_packet.py -v
```
