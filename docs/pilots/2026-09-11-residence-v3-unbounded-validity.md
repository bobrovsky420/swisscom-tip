# Unbounded validity rule and curated release v3 - 11 September 2026

Status: applied and verified. This fixes the date-window blocker recorded in
the [challenge audit](../hackathon/2026-09-11-challenge-audit-and-enhancements.md)
(section 3.1, proposal E1). Before this change every coverage profile and
evidence object of the curated release carried the frozen window 2026-09-10
through 2026-09-11, so any `resolve` with a later `as_of`, which is what a
caller using today's date sends, returned `OUT_OF_COVERAGE`.

## The rule

- A knowledge entry carries no commencement or expiry date unless the cited
  source page states one. A missing bound is unbounded, in both directions.
- Source-stated limits are recorded per concept. Examples: rules that apply
  only after an official date such as the end of the Brexit transition period,
  a law published with a future commencement date, an agreement with a stated
  expiry.
- The snapshot date is a separate freshness concern. Every citation records
  when its page was saved (`accessed_at`) and the profile's freshness policy
  (30 days) reports `STALE` once that snapshot is too old. Validity says when
  a rule applies; freshness says how old our copy of the page is.
- `as_of` remains the applicability date the caller asks about, normally
  today. A profile whose `valid_from` and `valid_through` are both null accepts
  any date.

## What changed

| Area | Change |
| --- | --- |
| Contract | `DateRange.valid_from` is optional like `valid_through`; a new `covers(day)` method holds the single window check; the inverted-range guard applies only when both bounds are present ([contracts.py](../../packages/core/src/swisstip/core/contracts.py)) |
| Validation and runtime | Profile matching in [validation.py](../../packages/core/src/swisstip/core/validation.py) and evidence eligibility in [service.py](../../packages/runtime/src/swisstip/runtime/service.py) call `covers()` instead of comparing bounds inline |
| Schema | `packages/core/schemas/contracts-v1.schema.json` regenerated; `--check` passes |
| Curated data | `concept()` in [residence_mvp_curated.py](../../scripts/corpora/residence_mvp_curated.py) takes an optional `validity`; the UK employment concept declares `valid_from=2021-01-01` and gains a third claim quoting the page's Brexit dates (blocks 176 to 177) |
| Curated builder | [build_residence_mvp.py](../../scripts/corpora/build_residence_mvp.py) drops the global window, writes each concept's validity into its profile and evidence, dates the prepared requests with the build date, replaces the exclusion "Frozen snapshot test window only" by "Curated from official pages saved on 2026-09-10", replaces the `outside-test-window` negative case by `before-source-stated-commencement`, adds three temporal preflight checks, records `temporal_coverage.default` and `source_stated` in `validation.json`, and defaults to release v3 |
| Nationwide builders | [build_expanded_pack.py](../../scripts/corpora/build_expanded_pack.py) and [build_concept_pack.py](../../scripts/corpora/build_concept_pack.py) use an empty window and the build date for prepared requests, so future parts follow the same rule |
| Live check | The recorded boundary cases are now `as-of-far-future` (2099-12-31) and `as-of-far-past` (1990-01-01); they record outcomes and carry no expectation, as before |
| Caller harness | [run_opencode_test.py](../../scripts/test/mock-mcp/run_opencode_test.py) and its README default to release v3 |
| Tool description | `resolve` now says that `as_of` is normally today and that null bounds mean any date is covered |
| Tests | Three regressions: open bounds and `covers()` in `test_contracts.py`; unbounded acceptance plus enforced commencement and expiry in `test_validation.py`; unbounded evidence served for 1990, 2026 and 2099 with a stated commencement still refusing 2020-12-31 in `test_service.py` |

## Why the UK concept is dated

The SEM notification page (`doc-9b1cdec8a0d1eb938c6c`) states in block 176:
"Nach dem Austritt des Vereinigten Koenigreichs aus der Europaeischen Union
(EU) und bis zum Ende der vereinbarten Uebergangsphase am 31. Dezember 2020 ist
das Freizuegigkeitsabkommen (FZA) mit der EU nicht mehr auf die Beziehungen
zwischen der Schweiz und dem Vereinigten Koenigreich anwendbar. Seit dem
1. Januar 2021 gelten UK-Staatsangehoerige nicht mehr als EU-Buergerinnen und
-Buerger." The curated rule in block 182, that UK nationals can no longer use
the notification procedure for jobs of up to three months, therefore applies
from 1 January 2021. Block 177 gives 31 December 2029 as the expiry of the
separate services-mobility agreement; that expiry is quoted but not applied,
because it limits the agreement for posted service providers, not the AIG
employment rule. No other curated page states a commencement or expiry for the
claims it supports: the "Am 1. Dezember 2013 in Kraft getreten" line on the
biometric-permit page is a link label in its links section, not a statement
about the curated paragraphs, and the Fedlex AIG consolidation is treated as
current law (see limits below).

## Release identity

| Item | Value |
| --- | --- |
| Release ID | `hackathon-residence-semantic-2026-09-11-v3` |
| Location | `.local/mvp/residence-semantic-2026-09-11-v3/` (Git-ignored, 4.5 MB; `release.json` 1.2 MB) |
| `release.json` SHA-256 | `c8f02daf7b3fbc67fd5aa9901c201ea101aa9df2eb85b8c84320afbce7a08098` |
| Contents | 84 facts, 84 evidence spans, 20 rules, 35 concepts, 60 coverage profiles, 12 documents, 26 cantonal contacts (v2 had 83 facts and evidence spans; the UK Brexit-date claim is the addition) |
| Temporal coverage | Default unbounded; source-stated: `residence-uk-new-employment` from 2021-01-01 |
| Snapshot dates | All 12 pages saved on 2026-09-10 |
| Prepared requests | 60 resolves dated 2026-09-11 (build date), 4 negative cases (`missing-population`, `outside-canton`, `before-source-stated-commencement`, `wrong-release`), 3 temporal checks (`unbounded-far-past` 1990-01-01, `unbounded-far-future` 2099-12-31, `commencement-day` 2021-01-01), one evidence request |
| Builder checks | Release validated before and after serialisation; raw snapshot and normalized hashes; exact spans and block coordinates; packaged dependency hashes; 60 positive, 4 negative and 3 temporal preflight checks |

v1 and v2 remain in their sibling directories unchanged and still carry their
frozen windows.

## Verification

Test suites, rerun in the repository `.venv` after the change:

| Suite | Result |
| --- | --- |
| core | 87 pass (2 new) |
| runtime | 82 pass, 7 PostgreSQL cases skipped (1 new) |
| MCP server | 4 pass |
| corpora scripts | 36 pass |
| ingestion | 171 pass |
| knowledge builder | 182 pass |
| control API | 22 pass, 11 skipped |

Real stdio session against v3 (`mcp` SDK 1.29.1), every result validated
against the advertised output schema and the text/structured parity check:

| Request | `as_of` | Outcome |
| --- | --- | --- |
| `get_coverage` for `residence-uk-new-employment` | - | profile `temporal_coverage` `{valid_from: 2021-01-01, valid_through: null}` |
| `get_coverage` for `residence-zh-eu-b` | - | profile `temporal_coverage` `{null, null}`; exclusion "Curated from official pages saved on 2026-09-10; not complete Swiss legal coverage." |
| EU/EFTA registration deadline (federal) | 2026-09-11 | `SUPPORTED`, 2 facts, 2 evidence, `FRESH` |
| same | 2026-09-25 (hackathon) | `SUPPORTED` |
| same | 2099-12-31 | `SUPPORTED` |
| same | 1990-01-01 | `SUPPORTED` |
| Zurich EU/EFTA B permit (`CH-ZH`) | 2026-09-25 | `SUPPORTED`, 1 fact |
| UK new employment | 2020-12-31 | `OUT_OF_COVERAGE`, `unsupported_combination` |
| UK new employment | 2021-01-01 | `SUPPORTED`, 3 facts, 3 evidence |
| UK new employment | 2026-09-25 | `SUPPORTED` |

`run_opencode_test.py --server real --check-connection` lists the `swisstip`
server as connected on the v3 release. The live caller run (`--live`) was not
repeated in this pass; the standing Zurich case and the Chinese work-permit
case should be rerun against v3 before the demonstration.

## Consequences and limits

- Past-dated `as_of` values are now accepted for unbounded concepts. That is
  the rule as decided: the knowledge base describes the pages as saved on
  2026-09-10, and it makes no claim about earlier law unless the page states a
  commencement date. Callers asking about a past date receive current rules.
- The nationwide parts 001 to 004 still carry the 2026-09-11 window because
  they were built before this change. The updated builders produce unbounded
  parts; rebuilding parts 003 and 004 is cheap, parts 001 and 002 are not
  worth rebuilding before the event.
- Fedlex consolidations carry per-article "in Kraft seit" footnotes (for
  example Article 58a since 1 January 2019). The curated AIG claims are served
  as current consolidated law without article-level commencement dates. A
  later refinement can read those footnotes into `valid_from`.
- Freshness was unchanged in v3: the snapshots date from 2026-09-10 and, with
  the 30-day policy, turn `STALE` on 10 October 2026. Superseded on
  12 September by release v4 with a 60-day policy, see the
  [v4 freshness record](2026-09-12-residence-v4-freshness-60-days.md). The
  release should still be rebuilt from fresh snapshots in the week before the
  event, with the intermediate-hash guard updated deliberately.
- Shipping v3 inside the repository (audit proposal E2) is still open; the
  release lives under Git-ignored `.local/`.

## Reproduce

```shell
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/residence-semantic-2026-09-11-v3 --release-id hackathon-residence-semantic-2026-09-11-v3
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --check-connection
```

The builder refuses an existing output directory; choose a new directory and
release ID for any later rebuild.
