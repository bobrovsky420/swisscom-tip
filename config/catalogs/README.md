# Draft Zurich residence seed

`zh-residence.seed.json` is a BUILD-01 authoring scaffold, with one Knowledge
Space, one domain, one topic and six candidate concepts based on documented
source-page topics. These grouping choices and draft labels await human review.
They are not a completed answerable-concept catalog.

All entries remain `CANDIDATE`. The catalog has no coverage profiles, facts,
rules or context schemas. Its draft language policy enables no evaluated routes.
The proposed `requirements` operation and the five P0 projection targets are
recorded in `zh-residence.authoring.json`; they are not published capabilities.
The draft release identifier is only a reference for authoring and contract
tests. It does not name an available immutable Knowledge Release.

Complete the source-only [POC-01 review](../../scripts/test/poc01/README.md) before
using these proposed labels to avoid leading the source annotation. Then choose
5-10 reviewed answerable concepts, finalize stable IDs/granularity, and supply
the supported operations, canonical jurisdictions, conditional context and exact
source evidence. Model proposal IDs remain provenance references.

Metadata provenance points to the canonical JSON hash of
`zh-residence.authoring.json`, independent of indentation and checkout line endings.
The language policy and catalog use canonical contract-content hashes from
`swisstip.core.identity`. Editing a dependency requires updating its reference
and resealing dependent contracts. Sealing records content identity; it never
changes candidate or approval state. Tests check integrity and prevent this
draft from being mistaken for supported public coverage.
