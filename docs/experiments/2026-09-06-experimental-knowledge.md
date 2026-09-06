# Short path from extractor output to usable test data

`swisstip.builder.experimental_knowledge` builds a local, queryable bundle directly
from retained extractor candidates. It requires no human review, decision CSV,
approval import, additional model inference or external service. Use it for
hackathons, retrieval experiments, application prototypes and integration tests.

The Python adapter and CLI provide a small concept catalog, lexical search,
concept lookup and exact evidence lookup. Each response identifies the bundle
and carries `EXPERIMENTAL_UNREVIEWED` metadata. Downstream code can consume these
records immediately. This experimental contract does not implement the production
`structured-grounding/v1` service or its eligibility decisions.

## Start with the prepared bundle

A local bundle was built from the saved `8b-v3-02` and `70b-v3-05` runs:

- Directory: `.local/experiments/hackathon-unreviewed-v1`
- 102 candidates, 215 evidence spans and 12 source/model report records across
  six original pages. These are separate proposals, not 102 deduplicated concepts.
- No new model calls or human decisions. The frozen reports remain unchanged.

From the repository root, search the bundle:

```shell
.venv/bin/python -m swisstip.builder.experimental_knowledge search .local/experiments/hackathon-unreviewed-v1 "Familiennachzug" --limit 5
.venv/bin/python -m swisstip.builder.experimental_knowledge list .local/experiments/hackathon-unreviewed-v1 --limit 10
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
The local bundle is ignored by Git. Another checkout can build its own bundle
from extractor reports using the command below.

## Build from new or existing extractor output

Supply either an individual proposal report or a batch, using any extraction
profile v1-v4. Multiple files are supported:

```shell
.venv/bin/python -m swisstip.builder.experimental_knowledge build proposals.json --output-dir .local/experiments/my-demo
```

For new source pages, run the normal extractor first. Model review and bounded
repair still run when enabled by the extraction profile; the human-review queue
does not block this experimental build:

```shell
.venv/bin/python -m swisstip.builder.concept_cli downloaded/page.html --structured > proposals.json
.venv/bin/python -m swisstip.builder.experimental_knowledge build proposals.json --output-dir .local/experiments/my-demo
```

The output directory must be new. The builder validates the inputs before writing,
then writes the manifest last. Files are:

- `knowledge.json`: versioned experimental concepts, evidence, source references,
  model assessments, gaps and provenance.
- `reports/<sha256>.json`: exact copies of the input reports, retaining complete
  extraction and repair histories and human-review queue entries.
- `manifest.json`: bundle identity, counts and file hashes.

Builds are deterministic for the same input bytes, independent of input argument
order. Repeated identical files are deduplicated. Each source/model revision keeps
its own candidate identities and evidence. Overlapping or conflicting model
proposals are preserved without an automatic merge. `exp-concept-*` IDs identify
one experimental revision; they are not permanent public catalog IDs.

## Use from an application

```python
from swisstip.builder.experimental_knowledge import ExperimentalKnowledge

knowledge = ExperimentalKnowledge(".local/experiments/hackathon-unreviewed-v1")
page = knowledge.list_concepts(limit=20, offset=0)
results = knowledge.search("Familiennachzug", language="de", limit=5)
if results["matches"]:
    match = results["matches"][0]
    detail = knowledge.get_concept(match["concept_id"])
    claims = detail["concept"]["candidate"].get("structured_claims", [])
    citations = detail["evidence"]
    evidence = knowledge.get_evidence(match["evidence_ids"][0])
```

`get_concept` returns the full candidate, all linked evidence and its source report
metadata. v4 structured claims, conditions, exceptions and limitations remain
exactly as the extractor produced them. Older profiles retain their original prose
and citations; the builder does not invent missing structured claims.

CLI lookup uses the same returned IDs:

```shell
.venv/bin/python -m swisstip.builder.experimental_knowledge get .local/experiments/my-demo exp-concept-ID
.venv/bin/python -m swisstip.builder.experimental_knowledge evidence .local/experiments/my-demo exp-evidence-ID
```

Search uses Unicode case folding and weighted word overlap in labels, aliases,
description, scope and example questions. It provides deterministic ranking for
prototypes; it does not infer synonyms, translate queries, determine applicability
or assess semantic support. `--language` is an exact filter on the report's language
hint, which this path does not independently validate. Lists support `--offset`
and return `next_offset`; limits are bounded to 1-100 records.

## What the short path bypasses and retains

Human approval is not a prerequisite for consuming the bundle. Candidates remain
`CANDIDATE`, with experimental metadata, and production approval/release validators
are unchanged. The bundle deliberately uses a separate schema and ID namespace;
it cannot masquerade as an approved Knowledge Release.

Only the extractor's retained `candidates` are indexed. Rejected proposals and
coverage gaps stay in the source metadata and archived reports. Model assessment
is preserved as model assessment, and `verified_coverage` remains false. Every
response includes `publication_eligible: false`; this does not prevent experimental
apps from using the data.

The builder still checks report shape, required evidence, offsets and duplicate
candidate IDs. v4 quotes must match their source inventory exactly. Older report
quotes are bound to the archived report and marked `extractor_report_only`; the
builder does not re-fetch sources or reconstruct historical normalized pages.
Load checks artifact hashes and bundle identity. Hashes detect accidental mutation,
not source authority or factual accuracy. New extractor output requires a new bundle.

Offline tests cover the complete build/search/concept/evidence path, multiple models,
language filtering, pagination, citation integrity, v4 claims and gaps, rejected
proposal handling, deterministic rebuilds and corrupted artifacts. Production
publication, catalog mapping, independent semantic evaluation and MCP serving
remain separate implementation tasks.
