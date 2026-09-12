# Residence MCP pilot continuation checkpoint - 11 September 2026

Status: continued on 11 September. Corpus preparation and pitch statistics are
saved. Step 2 (live MCP test) is recorded in the
[live MCP check](2026-09-11-residence-live-mcp-check.md). The acquisition part of
step 3 is recorded in the [download recovery](2026-09-11-residence-download-recovery.md):
389 further raw responses were saved. Step 5 is recorded in the
[v2 extension](2026-09-11-residence-v2-extension.md): a four-part v2 collection
keeps the v1 parts unchanged and adds a source-assertion part for the recovered
pages and an assistant-authored V3 concept part for 100 of them. Exhaustive
discovery, scope review and human semantic review remain unfinished. Resume
here instead of restarting extraction prompt experiments.

Code, source inventory and pitch baseline: commit
`cc15341d52104251905d7348749a2330967197e4`
(`Expand residence source coverage and preserve multilingual evidence`).
The working tree was clean before adding this checkpoint and its navigation links.

## Objective and constraints

- The hackathon MVP is the MCP pilot for **Residence permit in Switzerland**.
- The requested corpus scope is all relevant government sources, all cantons and
  every language actually published by those sources. Contacts alone are insufficient.
- Discover and check published language versions before downloading and extracting.
- Prepare app-ingestible data directly, without invoking the SwissTIP extraction
  application or other LLMs. Local parsing, statistical language detection and OCR
  were used. No database import, release activation or application call occurred
  during this expanded preparation pass.
- Preserve earlier experiments and distinguish releases by their explicit IDs.
- Use repository-local `.venv` Python and the instructions in `AGENTS.md`.

## Recorded results

Snapshot date: **2026-09-11**. These counts describe the acquired experimental
corpus, including contextual and archival material. They do not certify legal
completeness or reviewed residence-permit rules.

| Measure | Result |
| --- | ---: |
| Identified URLs | 12,384 |
| Saved responses / failed downloads / normalization aliases | 11,728 / 475 / 181 |
| Pending URLs in the identified download frontier | 0 |
| Intermediate records | 11,728 |
| Records with native text / excluded source responses / no native text | 11,060 / 564 / 104 |
| Cantons represented by substantive source material | 26 |
| Published language links checked / links with identical substantive bodies | 22,850 / 2,427 |
| Publisher language tags represented in assertions | 31 |
| Original-language source assertion sections | 105,798 |
| Unique documents in serving / identical-document aliases | 9,811 / 1,097 |
| Serving evidence sections / quotation fragments | 96,197 / 139,783 |
| Validated release parts | 2 |
| Assertions excluded from serving | 534 |
| Local OCR jobs completed / jobs producing text | 665 / 442 |

The 534 serving exclusions comprise 269 assertions with undetermined language and
265 with broken native font mappings. Their records remain in the semantic
intermediate. Deferred discovery contains **10,404 links needing scope review**;
an empty pending queue does not mean exhaustive discovery.

Publisher language tags: `ar, bs, cs, de, el, en, es, fa, fi, fr, hbs, hr, hu,
it, ja, ku, pl, pt, rm, ru, sk, sl, so, sq, sr, ta, ti, tr, uk, vi, zh`.
Classifier-only assignments are separately flagged and can be wrong. These tags
are not a claim of 31 evaluated retrieval profiles or verified translations.

## Artifacts to preserve

Paths are relative to the repository. **`.local/` is Git-ignored**; committing the
code does not back up or transfer the downloaded corpus and releases.

| Artifact | Location |
| --- | --- |
| Source plan | [hackathon.sources.md](../../config/catalogs/hackathon.sources.md) |
| Expanded URL inventory | [hackathon.sources.expanded.json](../../config/catalogs/hackathon.sources.expanded.json) |
| Human-readable coverage | [hackathon.sources.coverage.md](../../config/catalogs/hackathon.sources.coverage.md) |
| Raw snapshots and discovery graph | `.local/corpora/hackathon-residence-all-languages-2026-09-11/` |
| Normalized documents, blocks and validation | `.local/intermediate/hackathon-residence-all-languages-2026-09-11/` |
| Source assertions and language/quality review ledgers | `.local/semantic/hackathon-residence-all-languages-2026-09-11/` |
| OCR images, jobs and unreviewed results | `.local/ocr/hackathon-residence-all-languages-2026-09-11/` |
| Completed serving collection | `.local/mvp/residence-all-languages-2026-09-11-v1/` |
| Live MCP check results (calls, summary, digest) | `.local/evaluations/residence-all-languages-2026-09-11-v1-live-mcp-check/` |
| Pre-recovery copies of the raw-corpus ledgers | `.local/corpora/hackathon-residence-all-languages-2026-09-11/pre-recovery-2026-09-11/` |
| Download recovery ledgers | `recovery-2026-09-11-results.json` and `recovery-2026-09-11-pass2-results.json` in the raw corpus |
| v2 collection (v1 parts unchanged plus parts 003 and 004) | `.local/mvp/residence-all-languages-2026-09-11-v2/` |
| Recovered-page intermediate and assertion export | `.local/intermediate/hackathon-residence-recovery-2026-09-11/`, `.local/semantic/hackathon-residence-recovery-2026-09-11/` |
| Assistant V3 extraction work directory (requests, responses, runs, results) | `.local/extraction/assistant-v3-2026-09-11/` |

Start with `coverage-report.json` in the raw corpus, `index.json` and
`validation.json` in the intermediate, and `collection.json` in the serving
directory. The raw corpus also contains `audit-state.json`, `source-coverage.json`,
`language-version-audit.json` and `deferred-scope-review.json`. After the
recovery, `audit-state.json`, `plan.json` and the checked-in expanded inventory
describe the current acquisition state (12,642 identified, 12,117 saved, 344
failed), while `coverage-report.json`, `source-coverage.json`, the language and
deferred-link ledgers and the checked-in coverage summary still describe the
pre-recovery snapshot that the v1 statistics were computed from.

The semantic directory contains `assertions.jsonl`, `summary.json`,
`source-disposition.json`, `language-assignment-audit.json` and
`text-quality-review.json`. Each release part contains `release.json`,
`validation.json`, `provenance.json`, `external-artifacts.json` and prepared
`mcp-requests.json`. The collection has `document-aliases.json` and
`unresolved-assertions.json`.

Earlier artifacts remain separate:

- `.local/corpora/hackathon-residence-2026-09-10/`
- `.local/intermediate/hackathon-residence-2026-09-11-v1/`
- `.local/mvp/residence-semantic-2026-09-11-v1/` - the earlier 81-fact pilot.
- `.local/mvp/residence-all-languages-2026-09-11-incomplete-build/` - an interrupted
  build, not a completed release; do not select it for testing.

## Release identity and validation

| File | SHA-256 |
| --- | --- |
| Semantic `assertions.jsonl` | `344f0154f8e9c7d7904c5068ee52effa0a05737479c4d71486f9d297a399970b` |
| Serving `part-001/release.json` | `cf8440b2b75f2ec59476e13cd326443a9666c3ee3142796971db13784fef1b26` |
| Serving `part-002/release.json` | `62caef3e80c9808d6dee192b3aa59033017e1e065193f403da635b378e52f207` |

Release IDs are `hackathon-residence-all-languages-2026-09-11-v1-part-001`
and `hackathon-residence-all-languages-2026-09-11-v1-part-002`.
The root `mcp-client.json` loads both into one server using repeated `--release`
arguments, with part 001 active by default. Requests must pin the appropriate
release ID; the server does not implicitly combine the two parts.

Recorded checks: **112 tests passed** (85 core, 2 pure runtime release validation,
25 standalone corpus tests), contract schema check passed, and both release parts
passed validation before and after serialization. Pure request preflight checked
88 representative cases in part 001 and 54 in part 002. Every normalized document
hash and block span was checked. Live MCP requests were not executed in the
preparation pass; the later [live MCP check](2026-09-11-residence-live-mcp-check.md)
records them separately, with 11 further standalone tests for the check,
recovery, concept-pack and assembly scripts (36 standalone corpus tests in total).

Additional source languages use opt-in `tip-language-catalog/v4` and
`evidence-object/v2`; legacy v3/v1 retains its five-language restrictions. This
does not add multilingual term projections, embeddings or evaluated semantic
retrieval. The collection serves annotated source quotations under
`read-source-assertions`; normalized eligibility rules remain unfinished.
The fixed 2026-09-11 applicability window and approval flags enable experimental
fixtures only and do not establish legal validity or human approval.

## Known acquisition and quality limitations

- Failed downloads include missing pages, rate limits, blocked hosts, connection
  failures and oversized documents. Retry transient failures deliberately and
  respect server pacing; the current crawler's normal run processes pending URLs,
  not every previously failed target automatically.
- Fedlex uses publication metadata and the latest available HTML/PDF version per
  language. Translation dates can differ; all historical consolidations were not
  downloaded. Old admin.ch legal links were resolved to Fedlex.
- Basel-Landschaft required published document-host links and multilingual Hallo
  pages; Schaffhausen required rendered navigation and `migrationsamt.sh.ch`.
  Supplement and rendered-discovery ledgers retain these additions.
- HTTP 200 soft errors, maintenance pages and empty application shells were
  excluded. Some ch.ch responses fell into this category.
- OCR is separate and unreviewed. Installed Windows recognizers were German,
  English and Russian; fallback-language flags must be respected.
- Published language metadata takes precedence over local Lingua guesses. Mixed
  language sections, font mappings, layout and translation equivalence need review.
  Some publisher pages expose machine translations.
- Source assertions and keyword annotations preserve statements and qualifications
  but do not constitute complete semantic interpretation or executable legal rules.

## Resume sequence

1. Done on 11 September: the three hashes above were confirmed and the v1
   artifacts were left unchanged. Repeat the hash check before any rebuild.
2. Done on 11 September: the [live MCP check](2026-09-11-residence-live-mcp-check.md)
   exercised `get_coverage`, `resolve` and `get_evidence` over stdio against both
   parts (217 calls, no contract failure, 84 sampled resolves across all
   jurisdictions). Re-run `scripts/corpora/live_mcp_check.py` with a new output
   directory for any later release. Its main finding is runtime latency of about
   5 to 9 s per call because the pinned release is re-validated on every request.
3. Continue the unfinished **corpus completeness** work. The acquisition retry is
   done and recorded in the [download recovery](2026-09-11-residence-download-recovery.md):
   176 previously failed targets and 213 newly discovered links were saved, 344
   failures remain with documented causes, and the frontier is empty again. Still
   open: relevance and scope review of the 10,404 deferred links and of the
   recovered pages, published language coverage verification, and the language,
   source-disposition and OCR ledgers.
4. Continue **semantic curation** with source-backed concepts, conditions,
   exceptions, procedural branches and applicability. The user's request for all
   information in all published languages is still open; do not mark it complete
   from quotation counts or contract validation alone.
5. Done on 11 September as the [v2 extension](2026-09-11-residence-v2-extension.md):
   the scripts were parameterized, the recovered pages were extracted, exported
   and packaged as part 003 under new identities, and an assistant-authored V3
   concept part 004 was added, all without touching the v1 directories. The
   v1 finalizer and coverage ledgers were deliberately not rerun. Any later
   change again goes into a new version with new release IDs.

The [standalone workflow](../../scripts/corpora/README.md) documents download,
Fedlex, rendered-page, four-shard extraction, OCR, assertion merge, packaging and
finalization commands. `build_expanded_pack.py` refuses an existing output
directory. Its release ID/date and several script input/output paths are currently
fixed to this snapshot; `--output` alone does not create a new release identity.
Update and test those settings when deliberately producing the next version.

## Pitch and wrap-up

The [MVP status and plan](../hackathon/2026-09-11-mvp-status-and-plan.md) wraps up
the 11 September work across the whole hackathon MVP and orders the next steps.

[Full presentation, slide 25](../pitch/full-presentation.md#slide-26---additional-info-nationwide-residence-permit-corpus)
contains these statistics and limitations. The one-minute pitch and first-round
deck have linked Q&A summaries outside their timed scripts. Keep preparation
metrics distinct from live MCP evaluation and reviewed semantic coverage.

No new download, extraction, server launch or database operation was performed
to save this checkpoint. The 11 September continuation launched the MCP server
locally for the live check and downloaded public government pages for the
recovery; it performed no extraction, model call or database operation. Existing
unrelated services and earlier experiments were left untouched.
