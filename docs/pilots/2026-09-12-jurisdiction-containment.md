# Jurisdiction containment and named coverage gaps - 12 September 2026

Status: applied and verified. Resolves the jurisdiction finding in the
[challenge audit](../hackathon/2026-09-11-challenge-audit-and-enhancements.md)
(section 3.1, proposal E6). Before this change a coverage profile matched a
request only when the two jurisdiction objects were equal field for field, so
the 25 federal profiles of the curated release refused every request that
named the user's canton, and the refusal said only "No evaluated profile covers
this combination and date".

## The rule

A jurisdiction is a typed object: `{CH}` is federal, `{CH, CH-ZH}` is Canton
Zurich, `{CH, CH-ZH, 261}` is the City of Zurich; the contract already
requires the country with a canton and the canton with a municipality.

- **Containment, downward only.** A profile serves every place inside its own
  jurisdiction: a federal profile answers for any canton or municipality, a
  cantonal profile for its municipalities. Nothing flows upward or sideways: a
  cantonal profile never answers a country-only request or another canton.
- **Honest level reporting.** `requested_scope` keeps what the caller asked;
  `executed_scope.jurisdiction` reports the profile's level; when the two
  differ the trust envelope carries a limitation such as "Published for CH and
  applied to CH-BE because CH-BE lies inside CH; CH-BE specifics are not
  covered by this profile". The status stays `SUPPORTED`.
- **Narrowest profile wins.** When several profiles match, the most specific
  jurisdiction answers; equally specific overlaps stay
  `ambiguous_coverage_profiles`, as before.
- **Named gaps.** When no profile matches, the result names the first
  dimension that left nothing, with the published values that would match,
  appended to the limitation text as "Published: ...":

| Reason code | Meaning | Published values listed |
| --- | --- | --- |
| `concept_set_not_published` | No single profile publishes the requested concept set | Profile IDs that publish any of the concepts |
| `more_specific_jurisdiction_required` | The concepts are published for a place inside the requested jurisdiction | Those jurisdictions, for example `CH-ZH/261` |
| `jurisdiction_not_covered` | The concepts are published for other jurisdictions | Those jurisdictions |
| `scope_mode_not_offered` | The matching profiles do not offer the scope mode | Offered modes |
| `date_outside_coverage` | The matching profiles do not cover `as_of` | Windows such as `from 2021-01-01` |
| `unsupported_combination` | No profile publishes the intent for the topic | - |

Leakage rules are unchanged: evidence still has to belong to the answering
profile, cantonal material never answers another canton, and federal evidence
enters a cantonal result only through a published rule.

## What changed

| Area | Change |
| --- | --- |
| Contract | `Jurisdiction` gains `contains()`, `specificity` and `describe()` ([contracts.py](../../packages/core/src/swisstip/core/contracts.py)); no field changed, the exported schema is unchanged |
| Validation | Profile matching uses containment; a `_coverage_gap` stage names the failing dimension; the narrowest jurisdiction is preferred among eligible profiles ([validation.py](../../packages/core/src/swisstip/core/validation.py)) |
| Runtime | Evidence eligibility compares against the answering profile's jurisdiction instead of the request's; `executed_scope` reports the profile jurisdiction; the level caveat is added to the limitations, capped at the contract's 30 entries; gap values are appended to `unresolved_portions[].limitation` ([service.py](../../packages/runtime/src/swisstip/runtime/service.py)) |
| Tool description | `resolve` now tells callers to give the most specific jurisdiction they know, explains that a profile serves every place inside its own jurisdiction, and lists the gap reason codes |
| Tests | `Jurisdiction` containment truth table; wider profile serves inner places and refuses upward and sideways requests with the right reason and values; narrowest profile wins; each gap dimension named; a runtime case where a federal profile serves `CH-BE` with the caveat and a `DE` request names `CH`. The former `test_no_jurisdiction_granularity_broadening`, which encoded exact matching, became `test_jurisdiction_never_broadens_upward` |

No release was rebuilt: the change is entirely in the contract, validator and
runtime, and applies to every loaded release including v4.

## Verification

Test suites after the change: core 91 pass (4 new), runtime 83 pass with 7
PostgreSQL cases skipped (1 new), MCP server 4 pass, corpora scripts 36 pass;
schema `--check` passes.

Real stdio session against release
`hackathon-residence-semantic-2026-09-12-v4`, every result validated against
the advertised output schema:

| Request | Outcome |
| --- | --- |
| Federal registration deadline, jurisdiction `CH-ZH` | `SUPPORTED`, 2 facts, executed scope `CH`, caveat "applied to CH-ZH ... CH-ZH specifics are not covered" |
| Same, `CH-BE` | `SUPPORTED`, executed scope `CH`, caveat for `CH-BE` |
| Same, City of Zurich (`CH-ZH/261`) | `SUPPORTED`, executed scope `CH` |
| Same, `CH` | `SUPPORTED`, no caveat |
| Zurich EU/EFTA B permit, `CH-ZH` | `SUPPORTED`, no caveat |
| Same, City of Zurich | `SUPPORTED`, executed scope `CH-ZH`, caveat for `CH-ZH/261` |
| Same, `CH` only | `OUT_OF_COVERAGE`, `more_specific_jurisdiction_required`, "Published: CH-ZH" |
| Same, `CH-BE` | `OUT_OF_COVERAGE`, `jurisdiction_not_covered`, "Published: CH-ZH" |
| City of Zurich arrival, `CH-ZH` without municipality | `OUT_OF_COVERAGE`, `more_specific_jurisdiction_required`, "Published: CH-ZH/261" |
| Two concepts in one call | `OUT_OF_COVERAGE`, `concept_set_not_published`, both profile IDs listed |
| UK employment, `as_of` 2020-12-31 | `OUT_OF_COVERAGE`, `date_outside_coverage`, "Published: from 2021-01-01" |
| Federal deadline, `scope_mode` descendants | `OUT_OF_COVERAGE`, `scope_mode_not_offered`, "Published: exact" |
| Bern migration-office contact, `CH-BE` | `SUPPORTED`, executed scope `CH-BE` |

The last row with the second shows the new combination the release can now
serve for every canton: the federal deadline plus the canton's own contact
office in one conversation.

## Live caller rerun

`run_opencode_test.py --server real --live` (OpenCode, model
`opencode/ling-3.0-flash-fin-free`, release v4, run
`.local/mock-mcp/runs/run-20260912-065216-real/`), the standing Zurich case
from POC-12. Distinct calls count each tool invocation once.

| Scenario | Turn 1 | Turn 2 | Result |
| --- | --- | --- | --- |
| work-first | 5 calls: root and domain discovery, one two-concept resolve answered `concept_set_not_published`, then the federal deadline and the Zurich registration concepts resolved with `CH-ZH` and today's date, both `SUPPORTED` | 2 calls: City of Zurich arrival and documents with municipality 261 | Both limits stated, no date computed before the arrival date was known, register by Tuesday 15 September 2026 with 27 September shown as the non-binding limit; SEM, Canton Zurich and City of Zurich cited |
| fourteen-days-first | 6 calls: three discovery levels, then the federal deadline, the Zurich registration and the city arrival concepts, all sent with `CH-ZH/261` and all `SUPPORTED` | 0 calls | Both limits stated, Tuesday 15 September 2026 named as the 14-day limit ahead of the 18 September start, B permit for the two-year contract |

Under the previous exact-match rule the federal deadline concept with `CH-ZH`
or `CH-ZH/261` returned `OUT_OF_COVERAGE`; the 11 September runs needed 6 and
8 calls in turn 1 and only passed because the tool description told the caller
to strip the canton. The harness assessment reports every check passed for
both scenarios.

## Consequences and limits

- A federal answer can read as complete where a canton adds steps or
  documents. The caveat and the executed scope make the level explicit; the
  caller should say so and name the cantonal office from the contact profile.
- Municipal profiles still require their municipality ID; a caller that knows
  only the canton gets `more_specific_jurisdiction_required` with the ID to
  use.
- The tool description carries the rule; a coverage summary at the root
  (audit proposal E7) would let a caller learn it in one call.
