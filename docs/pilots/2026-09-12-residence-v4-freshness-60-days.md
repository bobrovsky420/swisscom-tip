# Freshness policy raised to 60 days and curated release v4 - 12 September 2026

Status: applied and verified. Follows the
[v3 validity record](2026-09-11-residence-v3-unbounded-validity.md) and
mitigates the freshness finding in the
[challenge audit](../hackathon/2026-09-11-challenge-audit-and-enhancements.md)
(section 3.1): with the 30-day policy the curated release would have reported
every result as `STALE` from 10 October 2026.

## How freshness works

- Each coverage profile carries `freshness_policy.max_age_days` and a
  `policy_ref` naming the control artifact that justifies the number.
- Each evidence object records `citation.accessed_at`, the moment its page was
  saved. At resolve time the runtime takes the oldest `accessed_at` among the
  evidence it selected and compares it with the server's current UTC clock.
  If that age exceeds the limit, the result status is `STALE`; the facts and
  excerpts are still returned, and the `freshness` block carries `checked_at`
  and `oldest_source_at` so a caller can say when the page was read.
- The applicability date `as_of` plays no part: validity (unbounded unless
  the source states a date) says when a rule applies; freshness says how old
  our copy of the page is.
- The limit measures the age of the saved copy, not whether the page changed.
  Becoming fresh again requires re-downloading and rebuilding, because
  `accessed_at` is part of the sealed evidence hash.

## What changed

| Area | Change |
| --- | --- |
| Default | `FRESHNESS_DAYS = 60` in [build_residence_mvp.py](../../scripts/corpora/build_residence_mvp.py), replacing the literal 30 in every profile; the nationwide builders [build_expanded_pack.py](../../scripts/corpora/build_expanded_pack.py) and [build_concept_pack.py](../../scripts/corpora/build_concept_pack.py) import the same constant, so future parts follow it |
| Policy control | The evaluation control file (`mvp-experimental-test-policy`) now states `freshness_policy_semantics`: the 60-day snapshot-age limit, how it is counted, that stale results keep their facts, and that it does not detect page changes |
| Release README | Names the 60-day limit next to the snapshot dates |
| Caller harness | [run_opencode_test.py](../../scripts/test/mock-mcp/run_opencode_test.py) and its README default to release v4 |
| Documents | Rebuild plan, audit and the v3 record point at v4 |

The runtime and the contract are unchanged; the synthetic runtime fixture
keeps its own 30-day policy because its tests assert the `STALE` transition on
a fixed date.

## Release identity

v4 is a copy of v3 with the policy change only: the same 12 snapshots saved on
2026-09-10, the same 84 facts, 84 evidence spans, 20 rules, 35 concepts and 60
coverage profiles, the same unbounded validity with the UK employment concept
from 2021-01-01. Profile contents changed, so every hash changed.

| Item | Value |
| --- | --- |
| Release ID | `hackathon-residence-semantic-2026-09-12-v4` |
| Location | `.local/mvp/residence-semantic-2026-09-12-v4/` (Git-ignored) |
| `release.json` SHA-256 | `96a03b81321d01449a7b563ef9129f98a7cfce6f43ed94f0b176426b726d1170` |
| Freshness policy | 60 days on all 60 profiles, `policy_ref` `mvp-experimental-test-policy` |
| Oldest citation | `2026-09-10T20:05:56Z`; newest `2026-09-10T20:13:39Z` |
| `STALE` from | the evening of 9 November 2026 (oldest citation plus 60 days) |
| Builder checks | Release validated before and after serialisation; snapshot, normalized and dependency hashes; exact spans; 60 positive, 4 negative and 3 temporal preflight checks |

v3 remains in its sibling directory unchanged.

## Verification

- Corpora script suite: 36 pass after the builder change.
- In-process resolves of the EU/EFTA registration-deadline concept on v4 with
  an injected read clock:

| Read time (UTC) | Status | Freshness |
| --- | --- | --- |
| 2026-09-12 12:00 | `SUPPORTED` | `FRESH` |
| 2026-09-25 12:00 (hackathon) | `SUPPORTED` | `FRESH` |
| 2026-11-09 12:00 | `SUPPORTED` | `FRESH` |
| 2026-11-09 21:00 | `STALE` | `STALE`, 2 facts retained |
| 2026-11-10 12:00 | `STALE` | `STALE`, 2 facts retained |

- Discovery of the concept reports `max_age_days` 60.
- `run_opencode_test.py --server real --check-connection` lists the `swisstip`
  server as connected on v4.

## Still open

- Rebuild from fresh snapshots in the week before the event so the copy the
  jury tests is days old, not weeks; update the intermediate-hash guard
  deliberately.
- A verification ledger (source ID, last verified time, hash match) outside
  the sealed evidence would let an unchanged page stay fresh without
  re-curating; recorded as the first freshness follow-up in the audit
  discussion, not implemented.
- Per-source limits (statutes longer, municipal procedure pages shorter) once
  more than one source class is curated.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/residence-semantic-2026-09-12-v4 --release-id hackathon-residence-semantic-2026-09-12-v4
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p "test_*.py"
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --check-connection
```

The builder refuses an existing output directory; choose a new directory and
release ID for any later rebuild.
