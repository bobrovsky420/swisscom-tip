# Residence MCP live check - 11 September 2026

Status: completed. This is the live MCP test session requested in step 2 of the
[continuation checkpoint](2026-09-11-residence-mcp-checkpoint.md). It records real
stdio round trips against the expanded collection and is kept separate from the
pure validation and preflight already recorded there. It is a sample, not a full
evaluation of every prepared fixture, retrieval quality or semantic coverage.

## Setup

- Script: [live_mcp_check.py](../../scripts/corpora/live_mcp_check.py); unit tests in
  [test_live_mcp_check.py](../../scripts/corpora/test_live_mcp_check.py).
- Code: commit `cc15341d52104251905d7348749a2330967197e4` plus the uncommitted
  script, tests and documentation added on 11 September.
- Server: the collection's root `mcp-client.json`, loading both release parts
  with part 001 active. Python 3.14.3, `mcp` 1.29.1.
- Both `release.json` hashes were recomputed before the session and matched the
  checkpoint. The fixtures' `executed` flags and every v1 artifact were left
  unchanged.
- Sample: for each part, one fixture request per jurisdiction (federal plus 26
  cantons) chosen deterministically, plus 15 seeded random requests: 42 per part.
- Session: 11:24:39Z to 11:51:26Z (1,608 s wall clock). Results:
  `.local/evaluations/residence-all-languages-2026-09-11-v1-live-mcp-check/`
  (`calls.jsonl`, `summary.json`, `README.md`; Git-ignored).
- No extraction application, LLM, embedding or ranking provider, database or
  network call was made. Download recovery and ledger parsing ran on the same
  machine during part of the session.

## Recorded outcomes

| Measure | Result |
| --- | ---: |
| Server startup until `initialize` returned (both parts) | 100.5 s |
| Tool calls recorded | 217 |
| Structured content present / output schema failures / text parity failures | 217 / 0 / 0 |
| Negative expectations met | 12 / 12 |
| Fixture resolves executed (selected 84, budget exhausted: no) | 84 |
| Resolve status SUPPORTED / PARTIALLY_SUPPORTED | 52 / 32 |
| Returned evidence within the fixture's evidence IDs | 84 / 84 |
| `get_evidence` parity with the resolve evidence | 84 / 84 |
| Remaining-evidence batches requested / returned complete | 18 / 18 |
| Citations equal to the requested source URL | 77 / 84 |
| `get_coverage` latency (n 14): median / max | 5.2 s / 11.9 s |
| `resolve` latency (n 96): median / p90 / max | 8.2 s / 9.7 s / 79.4 s |
| `get_evidence` latency (n 106): median / max | 7.5 s / 9.7 s |
| `resolve` median, part 001 (520 MB) / part 002 (283 MB) | 9.3 s / 4.9 s |

Every executed resolve returned `PUBLISHED_FACTS_OR_RULES` support, the
`concept` channel only, no provider degradations and `FRESH` freshness within the
fixed 2026-09-11 window. Served evidence languages in the sample: part 001 de 26,
fr 9, zh 2, hr 2, bs, es, it, en; part 002 de 23, fr 13, it 3, en, rm, pl.

## Interpretation

- **PARTIALLY_SUPPORTED is the evidence budget, not missing support.** All 32
  partial results are documents with more than five evidence sections; all 52
  fully supported results have five or fewer. The unresolved reason is always
  `insufficient_verified_evidence`. The remaining sections were readable through
  `get_evidence` in batches of at most five IDs, as the fixtures state.
- **Citation URL differences are alias resolution.** Seven results cite the
  resolved document URL instead of the requested one: four Fedlex filestore
  version URLs, two Uri canonical service paths and one Appenzell Innerrhoden
  page variant. `document-aliases.json` records these identities.
- **Discovery shape.** Root discovery returns the active part; each part must be
  pinned explicitly. The catalog is `hackathon` > `immigration` > `residence` >
  14 category concepts, with the 7,033 and 3,850 document concepts beneath them.
  Topic-level discovery returned all 155 and 91 coverage profiles with one context
  schema. Cursor paging exists but was not exercised because the walk stopped at
  the category level. A limit of 101 is rejected before any release is loaded.
- **Negative cases behaved as contracted.** Unknown release, evidence from the
  other part, six evidence IDs, unknown evidence ID, a concept from the other
  part, an unknown field, a stringified object, an inactive part's parent without
  a release ID and an unknown tool name all returned the expected typed error.
- **Boundary cases.** `as_of` one day before or after the frozen window and
  `scope_mode=descendants` return `OUT_OF_COVERAGE`. A topic request without
  concept IDs is `INVALID_ARGUMENT` (`missing_concept_selector`). A German
  `retrieval_terms` entry is `UNSUPPORTED_LANGUAGE` (`unsupported_term_language`):
  the v4 language policy publishes no evaluated term routes, so retrieval terms
  are unusable in this collection, consistent with the checkpoint's statement
  that no multilingual term projections were added. `max_evidence=1` returns one
  evidence item as `PARTIALLY_SUPPORTED`. An unpublished intent is rejected.

## Limitations and observations

- **Latency is dominated by release re-parsing.** The runtime store validates
  the complete release JSON on every call, so each request costs about 9 s on
  the 520 MB part and 5 s on the 283 MB part, and startup took 100 s with the
  server holding about 5.8 GB. One resolve took 79 s while other local work ran.
  This is a serving-runtime property, not a corpus property; caching validated
  bundles would be the obvious runtime change and was not made here.
- The sample covered 84 of 10,883 prepared requests, all with exact document
  concepts, empty context and no retrieval terms. Context schemas, free-text
  interpretation and ranking were not exercised.
- One sampled fact statement from a SEM statistics PDF contains a replacement
  character, confirming that the text-quality review noted in the checkpoint is
  still open.
- Success here does not establish corpus completeness, translation equivalence,
  semantic review or legal validity. The approval flags remain test fixtures.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/live_mcp_check.py --output .local/evaluations/<new-directory>
```

The output directory must not exist. Defaults reproduce this sample
(`--per-jurisdiction 1 --random-sample 15 --seed 20260911 --time-budget 1800`).
