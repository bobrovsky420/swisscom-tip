# Experimental residence MCP test data

Release: `hackathon-residence-semantic-2026-09-12-v4`. Classification: **experimental**.

84 assistant-curated facts, 84 exact source excerpts, 20 routing rules,
35 concepts and 60 coverage profiles from 12 saved official pages.
Scope: federal requirements, Zurich canton/city procedures and contacts for all 26 cantons.
Other downloaded pages are accounted for in `source-disposition.json`; they have not all been semantically curated.

`release.json` is the app-ingestible `serving-release/v1` bundle. It contains normalized
source documents, citations, facts, rules, catalog and resolution graph. `semantic-extraction.json`
is a readable semantic export; `provenance.json` maps facts to original blocks and acquisitions.
`sources/` contains the cited raw snapshots. External control files have real content hashes.

Use `mcp-client.json` to configure a local MCP client, or run:

```shell
./.venv/Scripts/python.exe -m swisstip.mcp_server.server --release .local/mvp/residence-semantic-2026-09-12-v4/release.json --active-release-id hackathon-residence-semantic-2026-09-12-v4
```

`mcp-requests.json` supplies discovery, 60 resolve examples, 4 negative cases,
3 temporal checks and an evidence request. Select exactly one concept per resolve and supply the
listed context. `as_of` is the applicability date the caller asks about, normally today; the examples use the
build date 2026-09-12. Validity is unbounded unless the cited source states a commencement or expiry date.
Source-stated limits in this release: residence-uk-new-employment (valid_from=2021-01-01).
Each citation records when its page was saved (`accessed_at`; 2026-09-10); the freshness policy reports
results as STALE once that snapshot is older than 60 days.
The deterministic concept/fact baseline requires no models. Free-text semantic retrieval,
embeddings, reranking and multilingual projections are outside this pack.

Assistant-curated experimental MVP data; no independent human or legal review. Contract `APPROVED`/`CURATED` flags enable this experimental fixture to be
loaded by the existing validator; they do not assert independent review or production approval.
Rules select pre-authored statements by population; they do not compute legal eligibility.
English statements paraphrase the cited original-language text; they are not official translations.

Validation checks contracts, sealed hashes, dependencies and exact source spans. It does not
prove the legal completeness of the statements. No application, database or external model
was called; example MCP requests passed schema and core scope/context checks but have not been executed.
The release has not been imported into the database or activated.
