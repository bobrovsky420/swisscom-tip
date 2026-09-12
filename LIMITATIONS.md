# Limitations

What this server does not do, and what a caller remains responsible for.
The coverage itself is listed in [COVERAGE.md](COVERAGE.md).

## Knowledge

- **Not reviewed.** Every served fact was curated by an AI assistant reading
  saved official pages, with exact spans recorded, but without independent
  human or legal review. Nothing here is legal advice.
- **English paraphrases.** Fact statements are English paraphrases of German
  originals; the original excerpt is returned with every fact and is the
  authoritative text.
- **One topic.** Residence permits and registration for foreign nationals:
  federal law and SEM guidance, Canton Zurich and City of Zurich procedures,
  and the migration-office contact of every canton. Other cantons' procedures,
  fees, processing times and unrelated topics are not covered.
- **Routing, not eligibility.** Context fields such as `population` or
  `sponsor_status` select the statements written for that group. They do not
  decide whether a particular person qualifies.
- **Federal answers carry a caveat.** A federal profile answers for any
  canton; the result then says which level answered and that cantonal
  specifics are not covered. The caller should repeat that caveat and can name
  the cantonal office from the contact profiles.
- **Validity is an assumption.** Facts have no commencement or expiry date
  unless the cited page states one. Asking about a past date returns current
  rules. Fedlex per-article commencement footnotes are not yet applied.
- **Snapshot age.** Pages were saved on 10 September 2026. Freshness is the age
  of that copy, not a check that the page is unchanged; results are reported
  `STALE` once the copy is older than 60 days.

## Interface

- **Catalog-driven, no free-text search.** A caller discovers concepts through
  `get_coverage` and resolves one concept per call. Retrieval terms return
  `UNSUPPORTED_LANGUAGE` because no term routes are published for this release.
- **Large discovery pages.** Topic-level discovery returns about 140 KB with
  every coverage profile and context schema inline. Clients with a small
  tool-output cap must raise it; the printed OpenCode configuration does so.
- **Strict requests.** `schema_version`, `release_id`, `as_of` and a valid
  context object are required; unknown fields are rejected. Refusals name the
  mismatching dimension and the published values that would match.
- **stdio only.** The server speaks MCP over stdio. There is no HTTP transport,
  authentication or hosted endpoint yet.
- **English labels.** Catalog labels exist in English only; questions in other
  languages must be interpreted by the caller.

## Operations

- **No refresh job.** Re-downloading sources and rebuilding a release is a
  manual procedure; nothing detects that a page changed.
- **Bundled release only.** The nationwide corpus prepared for this project
  (about 12,000 pages from all cantons) is not served: it lacks a concept layer
  and a search tool, and its release files are too large for this repository.
- **Approval flags.** `APPROVED` and `CURATED` values inside the release satisfy
  the serving contract's validator so that the curated data can be loaded; they
  do not assert independent review or production approval.

## What the caller owns

Interpreting the user's question, choosing the concept, collecting facts such
as nationality group or arrival date, deciding when to say that something is
out of coverage, and composing the final answer with the returned citations
and limitations.
