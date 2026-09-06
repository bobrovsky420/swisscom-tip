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

- [Product specification](docs/product/product-functional-specification.md)
- [Technical specification](docs/architecture/technical-specification.md)
- [Implementation gaps and validation plan](TODO.md)
- [Crawler and concept extraction demos](apps/knowledge-builder/README.md)
- [zh.ch Apertus 8B/70B experiment results](docs/experiments/2026-09-05-zhch-concept-extraction.md)
- [Semantic-model profiles](config/semantic-models.toml)

The concept extractor has three preconfigured model profiles: local Ollama,
Hugging Face Apertus 8B, and Hugging Face Apertus 70B. Switching
between them changes one `active_profile` value. All Python work uses the
repository-local `.venv`; see `AGENTS.md` and the demo setup instructions.
