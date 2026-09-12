# Same-language retrieval terms on the curated release - 12 September 2026

Status: applied and verified; release rebuilt and bundled as v6. Resolves
proposal E12 of the
[challenge audit](../hackathon/2026-09-11-challenge-audit-and-enhancements.md),
narrower than proposed: `retrieval_terms` tagged `de` or `en` now rank
evidence instead of returning `UNSUPPORTED_LANGUAGE`; French is not enabled.

## The problem

Every real release was built with an empty language policy: no term
languages, no projection languages, no routes. The request validator accepts
a term language only if the policy enables it, so a term in any language was
refused with `UNSUPPORTED_LANGUAGE`, reason `unsupported_term_language` and
an empty list of allowed values. The pitch shows a German term as its first
example request. Discovery and `LIMITATIONS.md` stated the gap honestly, but a
juror following the pitch would hit an error on the first call with a term.

## What changed

- **Language policy.** `scripts/corpora/build_residence_mvp.py` enables each
  source language of the cited pages (`de`, `en`) as a term language and a
  projection language, with one policy route per language that maps the term
  language to itself.
- **Profile routes.** Every coverage profile publishes one evaluated route per
  source language it cites: term language equals projection language equals
  source language, bound to the release's evaluation control. The profile
  declares that language's projection complete, because in the deterministic
  baseline the original excerpt is the text a term is matched against; no
  projection asset exists or is needed.
- **Evaluation control.** `controls/mvp-experimental-test-policy.json` gains
  `retrieval_terms_semantics`: terms are relevance signals only, ranked by
  lexical overlap with the original excerpt, same language only, no
  translation, projection or model.
- **Preflight checks.** The builder runs four retrieval-term checks against
  the pure core validator and records them as `term_checks` in
  `mcp-requests.json`: a German term on a German-sourced concept and an
  English term on an English-sourced concept are `READY`; a French term is
  `UNSUPPORTED_LANGUAGE` (`unsupported_term_language`); a German term on an
  English-sourced concept is `OUT_OF_COVERAGE`
  (`unevaluated_language_combination`).
- **Derived limit.** `coverage_summary.derived_limits` at root discovery used
  to say that terms are unsupported. When routes exist it now derives the
  rule from them: "Retrieval terms are evaluated only for: de terms against de
  sources, en terms against en sources. Other term languages are refused and
  other term/source combinations are out of coverage."
  `coverage_summary.languages.retrieval_terms` lists `de` and `en`.
- **Release v6.** `hackathon-residence-semantic-2026-09-12-v6` is built from
  the same snapshots and spans as v5; only the policy, the profile routes, the
  evaluation control and the prepared checks differ. It is the active bundled
  release. v5 stays reproducible from the builder at commit `9f23a2a`.

## Why not French, and why not cross-language

No cited page is French, so a `fr` route would have no source to rank and
the validator would reject it (route sources must belong to the profile). A
German term against English sources, or the reverse, is exactly the
cross-language route the pitch promises; in the baseline it would score zero
overlap and silently degrade to concept ranking. Publishing it would claim an
evaluation that has not happened. The hybrid configuration, which requires
all five projection languages complete for every evidence item, is the place
for that claim. The pitch's five-language statement remains unproven and
should be narrowed to what v6 serves.

## Measured on release v6 through the runtime service

| Check | Result |
| --- | --- |
| German term, Zurich cantonal contact (German source) | `SUPPORTED`; channels concept and lexical; route `de` to `de` over `de` sources |
| English term, federal permit authority (English source) | `SUPPORTED`; channels concept and lexical; route `en` to `en` over `en` sources |
| French term | `UNSUPPORTED_LANGUAGE`, `retrieval_terms.0.language`, allowed `de`, `en` |
| German term on an English-sourced concept | `OUT_OF_COVERAGE`, `unevaluated_language_combination` |
| Same request with and without a term | identical facts and evidence |
| German term naming Geneva, Bern, Valais, taxes and 2030 | `SUPPORTED`, jurisdiction unchanged (CH-ZH), identical facts |
| German term with an `en` source filter on German sources | `OUT_OF_COVERAGE`, `no_coverage_in_requested_source_languages` |
| Root `get_coverage` | 5,815 bytes |

## Verification

- `packages/runtime/tests/test_service.py`: the fixture, which has routes,
  now serves the derived route limit with and without a scope statement;
  adversarial terms still cannot widen scope or fill context.
- `packages/core/tests`, `packages/runtime/tests`, `apps/mcp-server/tests`
  (including the bundled stdio test against v6) and the `scripts/corpora`
  suite pass; `swisstip.core.schemas --check` passes with no contract change.
- `COVERAGE.md` regenerated from v6 shows `de, en` as retrieval-term
  languages and the derived rule.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/residence-semantic-2026-09-12-v6 --release-id hackathon-residence-semantic-2026-09-12-v6
./.venv/Scripts/python.exe scripts/releases/publish_release.py --source .local/mvp/residence-semantic-2026-09-12-v6 --activate
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -p "test_service.py"
```
