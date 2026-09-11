# SwissTIP hackathon MVP - status and plan, 11 September 2026

This note wraps up the residence-permit MVP as it stands at the end of
11 September and sets the order of work from here to the demonstration and
beyond. It replaces nothing: the [backlog](../../TODO.md) keeps the acceptance
gates, the [checkpoint](../pilots/2026-09-11-residence-mcp-checkpoint.md) keeps
the artifact identities, and the [project review](../pitch/project-review.md)
keeps the jury analysis. Claims below are limited to what was executed and
recorded.

## 1. Where the MVP stands

| Area | State on 11 September | Evidence |
| --- | --- | --- |
| Contracts, runtime, MCP server | Implemented and tested: versioned catalog, context, evidence and `structured-grounding/v1` contracts; release validation; `get_coverage`, `resolve`, `get_evidence` over stdio; scoped hybrid retrieval over synthetic releases | BUILD-01 to BUILD-05 in the backlog; 4 MCP tests |
| Source acquisition | Nationwide residence corpus: 12,642 URLs identified, 12,117 saved, 344 failed with documented causes, frontier empty; 10,404 discovered links still need scope review | [Recovery record](../pilots/2026-09-11-residence-download-recovery.md) |
| Served knowledge | Four-part v2 collection: v1 parts unchanged (9,811 unique documents, 96,197 evidence sections), part 003 with 333 recovered documents, part 004 with 377 assistant-authored concept candidates on 81 pages | [v2 extension record](../pilots/2026-09-11-residence-v2-extension.md) |
| Live MCP behaviour | v1 and v2 collections exercised over real stdio sessions: 217 and 253 calls, zero contract failures, every negative expectation met | [Live check record](../pilots/2026-09-11-residence-live-mcp-check.md) |
| Semantic extraction app | V3 profile with DeepSeek Flash is the default but has never run live; the V3 pipeline is proven end to end with assistant-authored completions; V4 ran on one Zurich page in September | [V3 switch note](../experiments/2026-09-10-v3-flash-switch.md) |
| Human review | None on any residence release; 30 POC-01 reference concepts reviewed earlier; all served entries are `VERIFIED_AUTOMATIC` test fixtures | Backlog BUILD-02 gates |
| Storage | PostgreSQL and pgvector pilot verified on 8 September; v1 and v2 exist only as files under `.local/` | [Storage guide](../storage.md) |
| Studio and control API | Implemented for job planning and candidate review, V3 and V4 display; no v2 job has been loaded into it | [Console README](../../apps/admin-console/README.md) |
| Deployment and transfer | Manual; no Compose stack, release bundle or export/import; `.local/` is not in Git | [Operations guide](hackathon-operations.md) |
| Pitch material | One-minute pitch, ten-minute deck, full deck with dated corpus, live-check and v2 notes; review recommends leading with the caller journey | [Project review](../pitch/project-review.md) |

## 2. What changed on 11 September

1. **Checkpoint verified.** All release hashes matched; the v1 artifacts were
   left untouched throughout.
2. **Live MCP check of v1.** 84 fixture resolves across all 26 cantons and the
   federal level returned cited original-language evidence. Main finding: the
   runtime re-parses the pinned release on every call, so a call costs 5 to 9 s
   on the large v1 parts and startup takes about 100 s.
3. **Download recovery.** Two paced retry passes and two bounded discovery
   batches saved 389 further pages (176 previously failed targets, 213 newly
   found links). Remaining failures are dead links, mailto redirects, defunct
   hosts, one host refusing connections and bot protection.
4. **v2 collection.** The snapshot-fixed scripts were parameterized, the
   recovered pages were exported and packaged as part 003, and the knowledge
   builder's V3 extraction ran unchanged over 100 recovered HTML pages with
   completions and review verdicts authored by the assistant instead of a
   model API (468 proposals, 377 retained), packaged as part 004. The app's own
   experimental-knowledge builder accepts the results.
5. **Live MCP check of v2.** All four parts served; the new small parts resolve
   in under a second, confirming that latency is release size, not runtime
   logic.
6. **Code, tests and records.** Five new scripts and three parameterized ones,
   36 passing standalone corpus tests, three pilot records, checkpoint, README,
   backlog pointer and pitch updates. The first half is committed as
   `27a54c4`; the v2 extension is in the working tree.

## 3. Gaps and risks

- **No human-reviewed knowledge.** Every served fact is an automatic assertion
  or an assistant-authored candidate. The jury story must call this an
  evidence-retrieval pilot, not verified applicability.
- **Latency.** Seconds per call on the v1 parts until the release store caches
  validated bundles; the database backend would be slower, not faster, because
  it re-parses and re-validates per call too.
- **Review consistency.** The V3 review request carries no page URL, so
  reviewers cannot verify a jurisdiction named in a candidate's scope; strict
  and lenient reviewers diverged on the same rule.
- **Relevance and coverage.** The recovered pages and the 10,404 deferred links
  are unreviewed for relevance; PDFs have no concept layer; OCR output is
  unreviewed; retrieval terms are unusable in every part.
- **Reproducibility.** The corpus and releases live outside Git; a clean
  checkout cannot reproduce the pilot without the data bundle.
- **Caller experience.** The end-user journey the jury will judge has not been
  rehearsed against real releases.

## 4. Plan

Order matters: each phase makes the next demonstrable. Effort is a working
estimate for one engineer with the assistant.

### Phase A - demo readiness (2 to 3 days)

| Step | Work | Acceptance |
| --- | --- | --- |
| A1 | Cache validated bundles per release ID in the file and database release stores, preserving immutability; add regression tests | v1 `resolve` median under 0.5 s in a repeated live check; startup unchanged |
| A2 | Pass the publisher URL into the V3 review payload, or drop unstated jurisdictions from `scope` in the extraction prompt; re-review the strict batches | Reviewer verdicts no longer depend on jurisdiction attribution; batch 003 candidates re-evaluated |
| A3 | Rehearse the caller journey against v2: "Aufenthaltsbewilligung in Zurich" from discovery through clarification, structured request, cited evidence, and a negative fee question that returns insufficient evidence | Scripted, timed run with saved outputs labelled as fallback |
| A4 | Clean-checkout rehearsal: pinned release IDs and hashes, bounded data bundle or rebuild procedure, documented credentials, recovery steps | A second machine serves the v2 collection from the written steps |
| A5 | Optional: import the v2 parts into PostgreSQL and repeat the live check in database mode | Same outcomes as file mode; documented differences |

### Phase B - knowledge quality (1 to 2 weeks)

| Step | Work | Acceptance |
| --- | --- | --- |
| B1 | Human review of a narrow SEM and Zurich slice through the studio; promote reviewed candidates with real approval provenance | A release with `CURATED` entries and published facts; served separately from test fixtures |
| B2 | Relevance and scope review of the recovered pages and the deferred links; drop print views, events and marketing from served scope | Scope ledger with decisions; next collection built only from in-scope pages |
| B3 | Extend the concept layer to the core permit pages of all 26 cantons and SEM (roughly 300 to 500 pages), either through the app with DeepSeek Flash or through the assistant path | Concept parts covering every canton's primary permit procedures with review verdicts |
| B4 | OCR review of the 11 recovered PDFs and the 665 earlier OCR jobs; text-quality review of broken font mappings | Ledgers closed or explicitly deferred |
| B5 | BUILD-04: source-language validation, evaluated term routes and five compact projections for a reviewed slice | Retrieval terms usable in at least German and French with recorded evaluation |

### Phase C - product and pitch (in parallel with B)

| Step | Work | Acceptance |
| --- | --- | --- |
| C1 | One caller experience: question, only necessary clarifications, readable evidence with source links, loading and failure states, explicit unsupported state | Usable by a jury member without guidance |
| C2 | Decks: lead with the relocation question and the live journey; add a dated implemented / demonstrated / remaining note; keep schemas for Q&A | Ten-minute run-through with a budgeted live slot |
| C3 | Fix status drift in the README, operations guide and deck tool names | Documents agree with the checkpoint |

### Phase D - platform hardening (after the hackathon)

BUILD-06 publication and promotion, retention and observability; Compose stack
with export and import of release bundles; sponsor harness and independent
client qualification; second consuming application only once the first
journey is reliable.

## 5. Decisions needed

- Whether assistant-authored candidates (part 004) may appear in the demo when
  clearly labelled, or whether only rule-based assertions are shown.
- V3 or V4 for further extraction: V3 is cheaper and proven end to end; V4
  yields condition trees but costs about three times the requests and had
  recorded quality problems.
- File or database backend for the demo; the choice does not change results
  today and only matters once A1 is done.
- Whether the release-store cache may hand out shared immutable bundles
  instead of fresh copies.

## 6. Reference

| Item | Location |
| --- | --- |
| v2 collection and root client config | `.local/mvp/residence-all-languages-2026-09-11-v2/` |
| Release IDs | `hackathon-residence-all-languages-2026-09-11-v1-part-001`, `...-v1-part-002`, `...-v2-part-003`, `...-v2-part-004` |
| Assistant extraction work directory | `.local/extraction/assistant-v3-2026-09-11/` |
| Live check results | `.local/evaluations/residence-all-languages-2026-09-11-v1-live-mcp-check/`, `...-v2-live-mcp-check/` |
| Raw corpus, recovery ledgers, pre-recovery copies | `.local/corpora/hackathon-residence-all-languages-2026-09-11/` |
| Scripts | [scripts/corpora/README.md](../../scripts/corpora/README.md) |
