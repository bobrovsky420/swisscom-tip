# Root coverage summary with a sealed scope statement - 12 September 2026

Status: applied and verified; release rebuilt and bundled as v5. Resolves
proposal E7 of the
[challenge audit](../hackathon/2026-09-11-challenge-audit-and-enhancements.md):
a caller can decide from the first `get_coverage` call, with no arguments,
whether a question lies inside the served scope, and answer "not covered"
without walking the catalog.

## What changed

- **Scope statement in the release.** `KnowledgeCatalog` gains an optional
  `scope` (`scope-statement/v1`): per language, one in-scope paragraph and an
  out-of-scope list, with provenance. The curator writes it next to the
  concepts (`SCOPE` in `scripts/corpora/residence_mvp_curated.py`); the
  builder seals it into the catalog, so it is covered by the catalog hash and
  the release validator like every other served fact.
- **Hash compatibility.** A null `scope` is omitted from the canonical
  document that the artifact hash covers, so every release sealed before the
  field existed (v4, the nationwide parts) still verifies unchanged; a
  published statement is always hashed. The rule is a named list of extension
  fields in `swisstip.core.identity`, tested in `test_identity.py`.
- **Summary shape.** The root `get_coverage` result carries
  `coverage_summary` (`coverage-summary/v1`): `scope` and `out_of_scope` per
  language, copied verbatim from the release; `out_of_scope_response`, the
  instruction to say that the server does not cover the question and stop;
  `topics`; `jurisdictions` grouped by level, intent and concept count, so the
  26 cantonal contact profiles are one row; `jurisdiction_rule`; `languages`
  (evidence, labels, retrieval terms); snapshot dates; the concept count; and
  `derived_limits`, the statements the data alone implies (retrieval terms
  unsupported, source-stated validity windows). A release without a scope
  statement, such as the synthetic fixture, gets the complement of its topics,
  intents and places in `derived_limits` instead. Child pages are unchanged.
- **Tool description.** `get_coverage` says that the first call returns the
  scope statement and the out-of-scope list, and that a question matching
  `out_of_scope` or outside `scope` is to be answered from
  `out_of_scope_response` with no further calls.
- **Coverage page.** `scripts/releases/coverage_report.py` prints the sealed
  statement, the derived limits and the grouped jurisdiction table; the
  hand-written list it used to carry is gone, the release is the only source.
- **Release v5.** `hackathon-residence-semantic-2026-09-12-v5` is built from
  the same snapshots and spans as v4 with the scope statement added; it is the
  only bundled release. v4 stays reproducible from the builder at commit
  `3a64507`.

## Measured on release v5

| Call | Bytes |
| --- | --- |
| Root `get_coverage` on v4 before this change | 1,207 |
| Root `get_coverage` on v5 | 5,739 |
| of which `coverage_summary` | 4,532 |
| Child pages | unchanged |

A default OpenCode output cap of 51,200 bytes is not approached.

The served statement (English) is reproduced in [COVERAGE.md](../../COVERAGE.md)
under "Scope". Its out-of-scope list names taxes, driving licences, voting,
schooling, naturalisation, asylum, entry visas, social insurance beyond the
health-insurance enrolment deadline, fees and processing times, the procedures
of other cantons beyond the contact, municipal procedures outside the City of
Zurich, individual eligibility decisions, and any country other than
Switzerland.

## What it does not do

- German, French and Italian versions of the statement are not written yet;
  the contract accepts them per language and they belong with the E10 label
  work.
- It does not shrink topic-level discovery (proposal E5).
- The release's `controls/contracts-v1.schema.json` records the contract as
  exported at build time, which now includes the scope and summary models.

## Verification

- `packages/core/tests/test_identity.py`: a catalog without a scope hashes as
  it did before the field existed; a published scope is part of the hash and
  editing it breaks verification.
- `packages/core/tests/test_contracts.py`: a scope statement needs text,
  at least one out-of-scope item, provenance and distinct language keys.
- `packages/runtime/tests/test_service.py`: the fixture without a statement
  serves derived limits; a sealed statement is served verbatim and replaces
  the derived complement; jurisdiction rows group places by level, intent and
  count; child pages carry no summary; the root page stays under 8 KB.
- `apps/mcp-server/tests`: stdio parity of the root result; the bundled
  release test calls root discovery over stdio against v5.
- `swisstip.core.schemas --check` passes after regeneration; the corpora
  script suite passes after the builder change.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/residence-semantic-2026-09-12-v5 --release-id hackathon-residence-semantic-2026-09-12-v5
./.venv/Scripts/python.exe scripts/releases/publish_release.py --source .local/mvp/residence-semantic-2026-09-12-v5 --activate
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -p "test_service.py"
```
