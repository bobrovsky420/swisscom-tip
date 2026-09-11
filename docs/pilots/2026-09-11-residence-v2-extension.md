# Residence serving collection v2 - 11 September 2026

Status: built and validated. This is step 5 of the
[continuation checkpoint](2026-09-11-residence-mcp-checkpoint.md) applied to the
389 pages saved by the [download recovery](2026-09-11-residence-download-recovery.md).
The v1 parts are unchanged; v2 is a copy of them plus two new parts built only
from the recovered pages, carrying two different semantic layers. Nothing in v2
is human-reviewed, legally reviewed or an eligibility decision.

## Collection

Location: `.local/mvp/residence-all-languages-2026-09-11-v2/` (Git-ignored),
assembled by [assemble_collection.py](../../scripts/corpora/assemble_collection.py)
with a root `mcp-client.json` that loads all four parts (part 001 active).

| Part | Release ID | Documents | Facts | Evidence | Concepts | Content |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| part-001 | `...-v1-part-001` | 6,334 | 89,995 | 61,231 | 7,033 | v1 source assertions, byte-identical |
| part-002 | `...-v1-part-002` | 3,477 | 49,788 | 34,966 | 3,850 | v1 source assertions, byte-identical |
| part-003 | `...-v2-part-003` | 333 | 2,756 | 2,195 | 344 | source assertions for the recovered pages |
| part-004 | `...-v2-part-004` | 81 | 377 | 955 | 377 | assistant-authored V3 concept candidates |

Release identities: `hackathon-residence-all-languages-2026-09-11-v2-part-003`
(SHA-256 `725c2f04...`) and `...-v2-part-004` (SHA-256 `8ce7eafc...`); the full
hashes are in `collection.json`. Both parts passed `validate_release` before and
after serialization and their pure request preflights (14 and 10 representative
cases) returned READY.

## Layer 1: source assertions for the recovered pages (part 003)

The same rule-based pipeline as v1, run on the recovered pages only through the
newly parameterized scripts:

| Step | Result |
| --- | ---: |
| Intermediate records (`--retrieved-after 2026-09-11T11:39:00`) | 389 (385 extracted, 3 without text, 1 excluded) |
| Text characters / blocks | 2,816,232 / 22,566 |
| PDF documents with pages lacking native text | 11 (no OCR run) |
| Source assertion sections (lingua language detection, no model) | 2,379 |
| Unique documents in the part / identical-document aliases | 333 / 13 |
| Assertions excluded (undetermined language or broken fonts) | 40 |

Assertion languages: de 1,944, fr 179, en 156, it 45, fa 18, ta 8, tr 8, ar 5,
es 1, sq 1, undetermined 14. The intermediate lives in
`.local/intermediate/hackathon-residence-recovery-2026-09-11/`, the export in
`.local/semantic/hackathon-residence-recovery-2026-09-11/`, the built part in
`.local/mvp/residence-all-languages-2026-09-11-v2-part-003-build/`. The v1
finalizer was not run because it rewrites the v1 ledgers; the v1 coverage report
therefore still describes the pre-recovery snapshot.

## Layer 2: assistant-authored V3 concept extraction (part 004)

The knowledge-builder's V3 concept extraction ran unchanged through
[assistant_extraction.py](../../scripts/corpora/assistant_extraction.py), with a
file-exchange provider in place of a model. The app normalized each page,
built its chunks and evidence spans, and issued its ordinary requests. The
assistant (Claude, working from those requests) wrote every extraction
completion and every review verdict; the app validated them, attached exact
quotations and wrote its ordinary `swisstip.concept-proposal-batch/v1` results.
No DeepSeek, Hugging Face, Groq or Ollama call was made. Completions carry the
identity `anthropic-assistant` / `claude-fable-5-1`, and the app's own
experimental-knowledge builder accepted the results (331 concepts from the first
nine batches at the time of the check).

| Measure | Result |
| --- | ---: |
| Recovered HTML pages staged / skipped | 100 / 128 (114 print or share views, 10 duplicates, 4 unusable) |
| Extraction requests (chunks) / review requests | 119 / 118 |
| Candidates proposed / accepted by the app parser | 468 / 468 |
| Retained after review / rejected | 377 / 91 |
| Rejections by issue | unsupported claim 60, missing condition 12, irrelevant 11, unanswerable question 4, insufficient context 3, wrong scope 1 |
| Retained by type | RULE 148, PROCESS 77, DOCUMENT 66, SERVICE 38, ENTITY 33, OTHER 15 |
| Retained by page language | de-CH 172, en 61, de 57, fr 55, it 22, fr-CH 8, undeclared 2 |
| Pages with retained candidates | 81 |

Prompt identities: extraction `ccd968b7...` (the V3 hash recorded in the
10 September switch note), review `893394d8...`. The work directory
`.local/extraction/assistant-v3-2026-09-11/` keeps every request, response,
run manifest, progress log and result; `revisions/batch-001-round-1/` keeps the
superseded extraction responses.

### Findings about the V3 review

- **Jurisdiction attribution is unverifiable inside the review.** The review
  request carries the page title, language, sections and proposals but no URL
  or publisher. Extractors naturally write the canton or office into `scope`;
  reviewers who applied the prompt strictly marked such proposals uncertain
  (batch 001 round 1: 20 of 46; batch 003: 37 of 44), while other reviewers
  accepted the page title or domain as disambiguation. Passing the publisher
  into the review payload, or keeping unstated jurisdictions out of `scope`,
  would remove this inconsistency.
- **Batch 001 was revised once.** Its Thurgau labour-office pages on study,
  internship and notification permits are core residence content, so the
  21 affected scopes were rewritten without the unstated attribution and the
  five chunks were reviewed again: 18 of 22 supported, the rest rejected for
  incomplete document checklists. Batch 003 (Thurgau passport, identity-card
  and authentication pages for Swiss citizens) was left as reviewed; its
  candidates remain in the results as rejected with reasons.
- **Off-topic pages produce few or no concepts.** Sitemaps, contact forms,
  share links and marketing pages were left empty or given single low-confidence
  concepts, and the review removed most of the latter.
- **Reviewers rejected two 2015 Federal Council press releases as news**, the
  FDFA helpline contact blocks as furniture, and several document checklists
  that omitted mandatory items visible in the same section.

### How part 004 is served

[build_concept_pack.py](../../scripts/corpora/build_concept_pack.py) re-normalizes
each page with the app's normalizer, verifies every quotation offset, and emits
one concept entry and one fact per retained candidate under
`residence > candidate-type-<type>`, with evidence objects citing the page's
final URL and coverage profiles per jurisdiction under the intent
`read-concept-candidates`. Serving contracts only load `CURATED` or
`VERIFIED_AUTOMATIC` entries, so the candidate status is carried by the notice,
the evaluation policy and `provenance.json` (candidate JSON and review verdicts),
not by the lifecycle. The batch results themselves are stored as controls in
the part.

## Live MCP check of v2

`live_mcp_check.py` ran against the four-part root `mcp-client.json` from
17:11:51Z to 17:28:10Z (980 s wall clock; results in
`.local/evaluations/residence-all-languages-2026-09-11-v2-live-mcp-check/`).
All four release hashes matched `collection.json` before the session.

| Measure | Result |
| --- | ---: |
| Server startup, four parts | 95.3 s |
| Tool calls / output schema failures / text parity failures | 253 / 0 / 0 |
| Negative expectations met | 14 / 14 |
| Fixture resolves executed (one per jurisdiction plus 5 random per part; budget not exhausted) | 94 / 94 |
| Evidence within fixture / `get_evidence` parity | 94 / 94 both |
| `resolve` median per part: 001 / 002 / 003 / 004 | 7.1 s / 3.4 s / 0.25 s / 0.14 s |

Statuses: part 001 21 supported and 11 partial, part 002 20 and 12, part 003
11 and 5, part 004 14 supported and none partial. Partial results again
correspond to documents with more than five evidence sections; every part 004
request is fully supported because each candidate is one fact with at most five
quotations. The small parts resolve in well under a second, confirming that the
multi-second latency of the v1 parts is release re-parsing, not the runtime
itself. Citation URLs differed from the requested URL in 8 of the 30 new-part
requests, all alias resolutions to the page's final URL. Discovery shows part
003 with 13 category concepts under `residence` and part 004 with 6 type
categories; boundary and negative outcomes were identical to the v1 check.

## Limitations

- Old pages have only the assertion layer; the concept layer covers 100 of the
  recovered HTML pages and none of the PDFs.
- The concept layer is one assistant's proposals reviewed by the same assistant
  through the app's review prompt. It is not human review, and reviewer
  strictness varied as described above.
- Relevance of the recovered pages to residence permits is unreviewed; several
  concern passports for Swiss citizens, integration events or economic
  promotion.
- The v1 coverage ledgers and the checked-in coverage summary are pre-recovery.
- Retrieval terms remain unusable in every part (no evaluated term routes).
