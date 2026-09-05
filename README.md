# Swisscom Trusted Information Platform

The repository currently contains the TIP specifications and two
operator-triggered knowledge-builder proofs:

- A bounded crawler that reports source and snapshot metadata.
- A concept extractor that proposes evidence-backed candidate concepts from
  downloaded HTML, text, and Markdown pages.

- [Product specification](docs/product/product-functional-specification.md)
- [Technical specification](docs/architecture/technical-specification.md)
- [Crawler and concept extraction demos](apps/knowledge-builder/README.md)
- [Semantic-model profiles](config/semantic-models.toml)

The concept extractor has three preconfigured model profiles: local Ollama,
Hugging Face free-account testing, and Hugging Face paid-account use. Switching
between them changes one `active_profile` value. All Python work uses the
repository-local `.venv`; see `AGENTS.md` and the demo setup instructions.
