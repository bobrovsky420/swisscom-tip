# Swisscom Trusted Information Platform

TIP's target is a discoverable, governed knowledge service for AI clients.
The planned MCP server exposes a versioned catalog and accepts structured scope,
context and optional multilingual retrieval terms, returning authoritative
evidence, citations, applicability and limitations. The calling LLM interprets
the user's question, selects catalog identifiers, collects missing facts and
composes the final answer.

The repository currently contains the TIP specifications and
operator-triggered knowledge-builder proofs:

- A bounded crawler that reports source and snapshot metadata.
- A source-only residence catalogue for the `hackathon` Knowledge Space, with
  59 official source references across all 26 cantons, offline crawl plans and
  an opt-in runner that saves HTML snapshots for later extraction. Limited seeds
  prefer German; multilingual selections retain every chosen official version.
- A concept extractor that proposes evidence-backed candidate concepts from
  downloaded HTML, text, and Markdown pages.
- An opt-in [structured extraction and human review workflow](docs/experiments/2026-09-06-structured-extraction.md)
  with logical source blocks, explicit claim conditions, omission audits, bounded
  repair and revision-bound review annotations. Live quality validation is pending.
- An [experimental short path](docs/experiments/2026-09-06-experimental-knowledge.md)
  that builds searchable test bundles directly from extractor candidates without
  human review, with Python/CLI concept and evidence lookup.
- A [structured knowledge runtime](packages/runtime/README.md) and
  [stdio MCP server](apps/mcp-server/README.md) implementing release-pinned
  discovery, resolution and evidence lookup, tested with synthetic releases.

The shared core now defines versioned catalog, context, evidence and structured
request contracts, with offline catalog/request validation. POC-01 has 30 frozen
source-first reference concepts. The user's same-person second review accepted
all 30 references and agreed with 60 comparisons against the saved 8B/70B proposals;
eight references are selected for seed authoring. Independent quality evaluation
remains pending. The seed catalog is still a draft; production release publication
is not implemented. The runtime now integrates scoped multilingual lexical,
concept and vector retrieval, semantic ranking, verified-equivalence selection
and declared provider fallback. Its [BUILD-05 checks](docs/experiments/2026-09-07-build05-retrieval.md)
use synthetic releases; real reviewed coverage and live model qualification remain pending.

- [One-minute jury pitch](docs/pitch/one-page-pitch.md)
- [One-slide PowerPoint pitch with speaker notes](docs/pitch/swisstip-one-slide.pptx)
- [Project and pitch review against the jury criteria](docs/pitch/project-review.md)
- [Product specification](docs/product/product-functional-specification.md)
- [Technical specification](docs/architecture/technical-specification.md)
- [Hackathon operations, deployment and data transfer](docs/hackathon/hackathon-operations.md)
- [Implementation gaps and validation plan](TODO.md)
- [Pilot knowledge and lessons](docs/pilots/2026-09-08-retrieval-pilot.md)
- [Residence MCP corpus continuation checkpoint - 11 September](docs/pilots/2026-09-11-residence-mcp-checkpoint.md)
- [PostgreSQL and pgvector setup, migration and smoke tests](docs/storage.md)
- [Local ingestion GUI: sources, parsing, builds and draft review](apps/admin-console/README.md)
- [Paused extraction experiment and resume checkpoint](docs/experiments/2026-09-10-extraction-pause-checkpoint.md)
- [V3 and DeepSeek Flash switch with the prepared Zurich plan](docs/experiments/2026-09-10-v3-flash-switch.md)
- [Crawler and concept extraction demos](apps/knowledge-builder/README.md)
- [Hackathon residence source catalogue and later crawl/extraction commands](config/catalogs/README.md)
- [zh.ch Apertus 8B/70B experiment results](docs/experiments/2026-09-05-zhch-concept-extraction.md)
- [Semantic-model profiles](config/semantic-models.toml)
- [Shared model catalog and extraction/retrieval configuration](config/README.md)
- [Core contracts and validation](packages/core/README.md)
- [Prepare and complete the POC-01 review](scripts/test/poc01/README.md)
- [POC-01 progress, draft findings and resulting requirements](docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md)

The concept extractor has preconfigured profiles for local Ollama,
Hugging Face Apertus 8B/70B, and direct DeepSeek V4 Pro and V4.1 Flash. Switching
between them changes one `active_profile` value. Extraction and retrieval share
model definitions in `config/model-profiles.toml`; each keeps its own role settings
and active selections. All Python work uses the
repository-local `.venv`; see `AGENTS.md` and the demo setup instructions.
