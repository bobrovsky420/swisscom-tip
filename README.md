# Swisscom Trusted Information Platform

TIP's target is a discoverable, governed knowledge service for AI clients.
The planned MCP server exposes a versioned catalog and accepts structured scope,
context and optional multilingual retrieval terms, returning authoritative
evidence, citations, applicability and limitations. The calling LLM interprets
the user's question, selects catalog identifiers, collects missing facts and
composes the final answer.

The repository currently contains the TIP specifications and two
operator-triggered knowledge-builder proofs:

- A bounded crawler that reports source and snapshot metadata.
- A concept extractor that proposes evidence-backed candidate concepts from
  downloaded HTML, text, and Markdown pages.

The shared core now defines versioned catalog, context, evidence and structured
request contracts, with offline catalog/request validation. POC-01 has 30 frozen
source-first reference concepts and a draft comparison against the saved 8B/70B
proposals. The user's second review and quality evaluation remain pending. The
seed catalog is still a draft; release publication and the MCP tools are not implemented.

- [Product specification](docs/product/product-functional-specification.md)
- [Technical specification](docs/architecture/technical-specification.md)
- [Implementation gaps and validation plan](TODO.md)
- [Crawler and concept extraction demos](apps/knowledge-builder/README.md)
- [zh.ch Apertus 8B/70B experiment results](docs/experiments/2026-09-05-zhch-concept-extraction.md)
- [Semantic-model profiles](config/semantic-models.toml)
- [Core contracts and validation](packages/core/README.md)
- [Prepare and complete the POC-01 review](scripts/test/poc01/README.md)
- [POC-01 progress, draft findings and resulting requirements](docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md)

The concept extractor has three preconfigured model profiles: local Ollama,
Hugging Face Apertus 8B, and Hugging Face Apertus 70B. Switching
between them changes one `active_profile` value. All Python work uses the
repository-local `.venv`; see `AGENTS.md` and the demo setup instructions.
