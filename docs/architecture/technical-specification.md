# Swisscom Trusted Information Platform
## Technical & Solution Architecture Specification - V9

**Hackathon:** Swiss Grounding MCP<br>
**Product and functional specification:** [`product-functional-specification.md`](../product/product-functional-specification.md)<br>
**Preferred semantic model:** Apertus<br>
**Model strategy:** pluggable and model-independent<br>
**Example MCP client:** OpenCode

---

# 1. Purpose

This document defines the implementation architecture and technical choices for the Trusted Information Platform (TIP). Functional scope, user-visible behaviour, priorities and product evolution are defined in the product and functional specification.

The immediate technical outcome is a reproducible MCP server that Swisscom can run through its evaluation harness and standards-compatible MCP clients. This hackathon implementation is a vertical slice of the target product: it must be narrow enough to deliver while preserving the contracts, boundaries and traceability needed for further product evolution.

---

# 2. Technical Design Principles

Technical decisions are classified as:

| Decision class | Meaning |
|---|---|
| Published challenge constraint | Necessary to satisfy the documented Swiss Grounding MCP brief |
| Team MVP choice | Chosen implementation for the hackathon vertical slice |
| Product-enabling design | Included now because it validates or protects a target-product capability |
| Target-product capability | Part of the product vision but not implemented during the hackathon |

1. The MCP server is the primary deliverable and must run independently of optional applications.
2. Stable authoritative information is compiled before request time.
3. Live information is accessed through registered provider interfaces.
4. Raw source snapshots and published releases are immutable.
5. Deterministic code handles dates, hashes, filtering, thresholds and explicit rules.
6. Semantic models handle classification, terminology, retrieval and explanation where they add measurable value.
7. Cross-language terminology expansion and retrieval are server responsibilities, not client responsibilities.
8. Concept extraction occurs after deterministic acquisition and produces candidates before governed aggregation and promotion.
9. Broad concepts route requests; answerable concepts ground independent actions, rules and facts.
10. Full source content remains in its original language; compact metadata projections provide bounded multilingual lexical retrieval.
11. Generic German, German (Germany) and Swiss German are accepted input variants that route to Swiss Standard German retrieval and generated prose; Swiss German is never generated as output.
12. Retrieval returns a small evidence bundle rather than an uncontrolled document dump.
13. Original-language evidence remains authoritative; translations are labelled derivative content.
14. Every result is traceable to source versions and processing metadata.
15. Refresh, cache state and source failures are observable.
16. All model, storage and client integrations are replaceable behind explicit interfaces.
17. The vertical slice should validate target-product concepts without implementing the entire target product.
18. Future commercial and autonomous capabilities influence contracts only where that does not endanger MVP delivery.

---

# 3. System Architecture

**Decision class: Product-enabling design, implemented as a focused team MVP choice**

```text
CONTROL PLANE
Source Registry
  ↓
Scan / Crawl / Fetch
  ↓
Snapshot / Normalize
  ↓
Semantic Enrichment
  ↓
Evidence Compile / Index / Evaluate
  ↓
Immutable Knowledge Release

DATA PLANE
Published Knowledge Release
  ↓
Query Planner
  ↓
Retrieval / Capability Providers
  ↓
Evidence and Rule Engine
  ↓
Result Assembler
  ↓
MCP / REST
  ↓
Swisscom Test Harness │ OpenCode │ Arrival Checklist │ Other Clients
```

The runtime data plane reads only published releases. A failed build must not invalidate or replace the last successful release.

---

# 4. Recommended Hackathon Stack

**Decision class: Team MVP choice**

| Concern | Recommended implementation | Notes |
|---|---|---|
| Backend language | Python | One backend language for ingestion, retrieval, evaluation, MCP and REST |
| Metadata, evidence, facts, releases and tests | PostgreSQL | Single durable operational store |
| Semantic retrieval | pgvector | Replaceable vector-store adapter |
| Lexical retrieval | PostgreSQL full-text search | Avoids another search service for the MVP |
| Raw snapshots | MinIO or filesystem | Immutable content-addressed objects |
| Semantic model | Apertus preferred | Accessed through a provider interface |
| Agent interface | MCP | Primary challenge deliverable |
| Structured application interface | REST | Secondary interface over the same runtime |
| Reference validation client | OpenCode as one example | The server must not depend on OpenCode-specific behaviour |

These are implementation recommendations, not challenge requirements. A simpler substitute is valid if it reduces delivery risk or demonstrably meets the evaluation criteria better. Replaceable adapters protect the target product from becoming permanently coupled to hackathon technology choices.

---

# 5. Backend Language Comparison and Decision

**Decision class: Team MVP choice with long-term architectural implications**

## 5.1 Decision drivers

The relevant decision is not which language can implement an MCP server; both Python and TypeScript can. The decision should optimize the difficult parts of TIP:

- heterogeneous website, document and dataset ingestion;
- normalization and evidence compilation;
- semantic processing and Apertus experimentation;
- hybrid lexical/vector retrieval;
- grounding and evaluation workflows;
- typed MCP and REST contracts;
- delivery speed during the hackathon;
- a credible evolution path to the target product.

The official MCP SDK catalogue currently classifies both Python and TypeScript as Tier 1. Both support MCP servers and clients, local and remote transports, and protocol-level type safety. MCP capability is therefore not a reason to prefer one over the other. See the [official MCP SDK list](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/sdk.mdx).

## 5.2 Comparison

| Criterion | Python | JavaScript/TypeScript | Assessment for TIP |
|---|---|---|---|
| MCP support | Official SDK, FastMCP, structured output, standard transports and Pydantic types | Official SDK, typed tools, Standard Schema/Zod and standard transports | Equivalent for the required server |
| Source acquisition | Strong HTTP, parsing, PDF, document and data-processing ecosystem | Excellent HTTP and browser automation ecosystem | Python has the advantage for heterogeneous documents |
| Semantic and AI work | Native ecosystem for embeddings, NLP, evaluation and local models | Strong for remote model APIs | Python has the advantage |
| Apertus | Direct Transformers integration and local-model path | Normally accessed through an inference API | Python has the advantage if experimentation extends beyond HTTP calls |
| Contract modelling | Pydantic runtime validation and JSON Schema generation | Strong compile-time types plus runtime validation with Zod or another Standard Schema provider | TypeScript is stricter at compile time; both are suitable at system boundaries |
| PostgreSQL and pgvector | Psycopg, SQLAlchemy, asyncpg and official pgvector integration | node-postgres and broad ORM/query-builder support with official pgvector integration | Equivalent for this design |
| Concurrent network I/O | `asyncio`/AnyIO are well suited to I/O-bound acquisition and service work | Node's event loop is excellent for high-concurrency I/O | Equivalent for hackathon load |
| CPU-heavy parsing or local inference | Direct access to native data/ML libraries and process workers | CPU work must be kept off the Node event loop | Python has the advantage |
| Evaluation and experimentation | Strong testing, notebooks and analytical tooling | Capable general testing ecosystem | Python has the advantage for grounding experiments |
| Web frontend reuse | Requires generated TypeScript types or clients | Can share language and selected schema code with web clients | TypeScript has the advantage |
| End-to-end hackathon simplicity | One language covers ingestion, AI, retrieval, MCP and REST | Excellent if all models are remote and the team is TypeScript-first | Python has the advantage when team skill is comparable |
| Future control-plane development | Suitable with FastAPI and generated OpenAPI | Attractive for web-heavy control planes and BFFs | Slight TypeScript advantage, but not decisive for the core |

Supporting implementation facts:

- The [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/get-started/installation.md) uses Pydantic for protocol models and schema validation, AnyIO for asynchronous execution, and supports standard HTTP and stdio use cases.
- The [official TypeScript MCP server guide](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/get-started/first-server.md) provides typed tool registration, schema validation and stdio/HTTP operation.
- FastAPI can generate JSON Schema, OpenAPI and interactive documentation from Pydantic models, allowing Python contracts to generate TypeScript clients rather than being maintained twice. See the [FastAPI request-model documentation](https://fastapi.tiangolo.com/tutorial/body/).
- The official pgvector ecosystem supports both [Python](https://github.com/pgvector/pgvector-python) and [Node.js/TypeScript](https://github.com/pgvector/pgvector-node), so vector storage does not determine the language.
- Apertus has direct support through the Python Transformers ecosystem; see the [Apertus Transformers documentation](https://huggingface.co/docs/transformers/model_doc/apertus).

## 5.3 Decision

Python is selected for the hackathon backend because TIP's primary complexity lies in source and document acquisition, semantic processing, retrieval and evaluation. The official Python MCP SDK provides the required protocol capability, while Python gives the clearest path to Apertus and the broader AI/data ecosystem.

The implementation boundary is:

```text
PYTHON - P0 BACKEND
source acquisition
normalization and evidence compilation
retrieval and deterministic rules
semantic-model providers
evaluation
MCP server
REST API

TYPESCRIPT - OPTIONAL P1 CLIENTS
Admin Control Plane
Arrival Checklist web client

FLUTTER - OPTIONAL P2 CLIENT
Swiss Hike
```

REST types and clients for TypeScript applications are generated from the Python OpenAPI contract. Frontends do not import database models or internal domain objects.

## 5.4 Conditions that justify TypeScript instead

TypeScript remains a valid alternative if the implementation team is materially more productive in TypeScript and all of the following hold:

- sources are primarily HTML or JSON rather than difficult document formats;
- Apertus and embedding models are consumed only through remote HTTP APIs;
- the web control plane is a major part of the judged delivery;
- shared frontend development speed outweighs local AI experimentation.

The P0 backend must not be split into a Python ingestion service and a TypeScript MCP gateway. That would add deployment, failure and contract boundaries without improving the judged outcome.

---

# 6. Proposed Python Workspace Structure

**Decision class: Team MVP choice designed for target-product evolution**

The repository uses one Python workspace, one lock file and a small number of internal packages. Package folders use concise boundary names. Published distribution names use the `swisstip-` prefix, while Python imports use the shared `swisstip.*` namespace.

The shared namespace improves readability:

```python
from swisstip.core.evidence import EvidenceObject
from swisstip.ingestion.compilation import EvidenceCompiler
from swisstip.runtime.resolution import Resolver
```

The `swisstip` directory is a Python namespace, not an architectural layer. With implicit namespace packaging, each contributing distribution omits `swisstip/__init__.py` and defines an `__init__.py` only in its component package.

```text
Hackathon2026/
├── README.md
├── LICENSE
├── NOTICE
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── compose.yaml
│
├── docs/
│   ├── product/
│   │   └── product-functional-specification.md
│   ├── architecture/
│   │   ├── technical-specification.md
│   │   └── decisions/
│   │       └── 0001-python-workspace.md
│   ├── challenge/
│   │   ├── coverage-and-limitations.md
│   │   ├── evaluation-plan.md
│   │   └── operations.md
│   ├── strategy/
│   │   └── ubs-challenge-rationale.md
│   └── pitch/
│       ├── first-round-10min.md
│       └── full-presentation.md
│
├── config/
│   ├── sources/
│   │   ├── sem.yaml
│   │   └── zh.yaml
│   ├── products/
│   │   └── swiss-arrival-checklist.yaml
│   └── evaluation/
│       ├── thresholds.yaml
│       └── test-cases.yaml
│
├── packages/
│   ├── core/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── core/
│   │               ├── __init__.py
│   │               ├── domain/
│   │               ├── contracts/
│   │               ├── ports/
│   │               └── rules/
│   │
│   ├── ingestion/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── ingestion/
│   │               ├── __init__.py
│   │               ├── scanning/
│   │               ├── fetching/
│   │               ├── sources/
│   │               │   ├── sem.py
│   │               │   └── zh.py
│   │               ├── normalization/
│   │               ├── enrichment/
│   │               ├── compilation/
│   │               └── publishing/
│   │
│   ├── runtime/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── runtime/
│   │               ├── __init__.py
│   │               ├── planning/
│   │               ├── retrieval/
│   │               ├── search/
│   │               ├── applicability/
│   │               ├── resolution/
│   │               └── assembly/
│   │
│   └── integrations/
│       ├── pyproject.toml
│       └── src/
│           └── swisstip/
│               └── integrations/
│                   ├── __init__.py
│                   ├── postgres/
│                   ├── snapshot_store/
│                   └── models/
│                       ├── apertus/
│                       └── fallback/
│
├── apps/
│   ├── knowledge-builder/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── builder/
│   │               ├── __init__.py
│   │               ├── main.py
│   │               ├── bootstrap.py
│   │               └── cli.py
│   │
│   ├── mcp-server/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── mcp_server/
│   │               ├── __init__.py
│   │               ├── main.py
│   │               ├── bootstrap.py
│   │               └── tools/
│   │                   ├── resolve.py
│   │                   ├── get_evidence.py
│   │                   └── get_coverage.py
│   │
│   ├── control-api/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── swisstip/
│   │           └── control_api/
│   │               ├── __init__.py
│   │               ├── main.py
│   │               └── routes/
│   │
│   ├── admin-console/
│   ├── arrival-checklist/
│   └── swiss-hike/
│
├── schemas/
│   ├── mcp/
│   ├── domain/
│   └── rest/
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   │   └── mcp/
│   ├── end_to_end/
│   └── fixtures/
│
├── evaluation/
│   ├── golden/
│   ├── grounding/
│   ├── efficiency/
│   ├── freshness/
│   └── reports/
│
├── data/
│   ├── demo/
│   │   └── hiking/
│   └── runtime/
│
└── docker/
    ├── server.Dockerfile
    └── entrypoint.sh
```

## 6.1 Distribution and import names

| Folder | Distribution name | Python import |
|---|---|---|
| `packages/core` | `swisstip-core` | `swisstip.core` |
| `packages/ingestion` | `swisstip-ingestion` | `swisstip.ingestion` |
| `packages/runtime` | `swisstip-runtime` | `swisstip.runtime` |
| `packages/integrations` | `swisstip-integrations` | `swisstip.integrations` |
| `apps/knowledge-builder` | `swisstip-knowledge-builder` | `swisstip.builder` |
| `apps/mcp-server` | `swisstip-mcp-server` | `swisstip.mcp_server` |
| `apps/control-api` | `swisstip-control-api` | `swisstip.control_api` |

Concise folder names avoid repeating the product name throughout the repository. Distribution names retain the product prefix for package-manager clarity, and the shared import namespace makes component boundaries explicit. Concatenated imports such as `swisstipcore` are not used.

## 6.2 Package responsibilities

### `swisstip.core`

Contains the stable shared language of the product:

- domain objects and value types;
- Pydantic contracts;
- statuses and Trust Envelope;
- repository and provider protocols;
- deterministic domain rules.

It imports neither MCP, FastAPI, PostgreSQL, Apertus, document parsers nor other internal packages.

### `swisstip.ingestion`

Implements the control-plane knowledge compiler:

```text
sources
→ snapshots
→ normalization
→ language detection
→ candidate concept extraction
→ corpus aggregation and concept graph validation
→ additional enrichment
→ evidence
→ release
```

It owns build-time candidate extraction, concept aggregation and graph validation and may use heavier parsing and semantic dependencies. It depends on `swisstip.core` and never on `swisstip.runtime`.

### `swisstip.runtime`

Implements the published-release query engine:

```text
request
→ query-to-concept resolution
→ broad/narrow concept planning
→ retrieval
→ applicability
→ evidence resolution
→ structured result
```

It consumes only the concept graph published with the active release. It depends on `swisstip.core` and never on `swisstip.ingestion`. This prevents request-time queries from invoking crawlers, candidate extraction, aggregation or other build logic.

### `swisstip.integrations`

Implements the storage and model ports declared by `swisstip.core`. Optional dependency groups should prevent source-parsing or local-model dependencies from being installed into the MCP runtime unless they are required.

## 6.3 Deployable applications

- `knowledge-builder` is a CLI or one-shot job that composes ingestion with source, storage and model integrations.
- `mcp-server` is a thin protocol adapter over runtime use cases. It contains MCP registration and translation, not grounding rules.
- `control-api` is a P1 FastAPI application for build initiation, evidence inspection, releases and structured Information Products.
- `admin-console` and `arrival-checklist` are P1 TypeScript clients of the Control API.
- `swiss-hike` is the P2 Flutter client.

Suggested executable entry points are defined in their owning application distributions:

```toml
[project.scripts]
swisstip-builder = "swisstip.builder.cli:main"
swisstip-mcp = "swisstip.mcp_server.main:main"
swisstip-api = "swisstip.control_api.main:main"
```

## 6.4 Dependency direction

```text
knowledge-builder ──→ swisstip.ingestion ──→ swisstip.core
        └────────────→ selected integrations ────────┘

mcp-server ─────────→ swisstip.runtime ─────→ swisstip.core
     └──────────────→ selected integrations ────────┘

control-api ────────→ ingestion / runtime / selected integrations
```

The enforced dependency rules are:

```text
swisstip.core          → no internal package dependencies
swisstip.ingestion     → swisstip.core
swisstip.runtime       → swisstip.core
swisstip.integrations  → swisstip.core
knowledge-builder      → core + ingestion + selected integrations
mcp-server             → core + runtime + selected integrations
control-api            → may compose both build and runtime capabilities
```

Ingestion and runtime communicate through published release contracts and storage, not through direct package imports.

## 6.5 Split criteria and restraint

The package split is justified by different dependencies, execution profiles and failure behaviour:

| Concern | Knowledge builder | MCP server |
|---|---|---|
| Lifetime | Batch job | Long-running service |
| Workload | Crawling, parsing, embedding and indexing | Low-latency reads and resolution |
| Dependencies | Document parsers and model tooling | MCP, retrieval and database client |
| Failure policy | Preserve the previous release | Continue serving the previous release |
| Scaling | Occasional compute-heavy work | Concurrent request handling |
| Network access | Outbound access to approved sources | Restricted runtime access |

Do not create separate packages for each source connector, MCP tool, domain object, storage technology or Information Product. Marketplace, billing and entitlement packages are added only when those target-product capabilities acquire implementation, ownership or deployment needs.

The workspace initially uses one repository, one lock file and one versioning policy. Packages are not independently published or versioned during the hackathon.

## 6.6 Hackathon implementation order

The P0 implementation path is:

```text
swisstip.core contracts and ports
→ swisstip.ingestion full build
→ selected storage and model integrations
→ swisstip.runtime resolution
→ mcp-server
→ grounding and integration evaluation
```

The initial deployables are the one-shot `knowledge-builder` and long-running `mcp-server`. The Control API, web clients and Flutter client remain P1/P2 consumers of the same packages.

---

# 7. Semantic Model Strategy

**Decision class: Team MVP choice with a product-enabling provider boundary**

## 7.1 Preferred provider

Apertus is the preferred semantic model for the hackathon because it supports the Swiss and sovereign-AI positioning and is a credible candidate for multilingual Swiss language work. The [official Apertus launch](https://ethz.ch/en/news-and-events/eth-news/news/2025/09/press-release-apertus-a-fully-open-transparent-multilingual-language-model.html) reports training on 15 trillion tokens across more than 1,000 languages, with 40% non-English data, and explicitly names Swiss German and Romansh among included underrepresented languages.

This training coverage is motivation for evaluation, not a performance guarantee. The [official Apertus FAQ](https://www.apertus-ai.org/docs/faq/) says that Apertus was trained on more than 1,800 languages but is fully conversational in only a few dozen, and recommends evaluation or fine-tuning for specific language needs. TIP therefore promotes an Apertus configuration only when it passes the same multilingual retrieval and rendering gates as any other provider.

Suitable uses include:

- source and document classification;
- concept and terminology extraction;
- query-language detection and canonical-concept resolution;
- multilingual terminology expansion, including evaluated generic German, German (Germany), Swiss German and Romansh input variants;
- applicability interpretation;
- evidence reranking;
- optional translation and supported output-language rendering after evidence has been established.

Apertus is a generative semantic provider in this architecture, not implicitly the vector-embedding model. Vector retrieval uses a separately configured multilingual embedding provider unless an Apertus-derived embedding implementation independently passes the retrieval evaluation gate.

## 7.2 Model independence

All model-assisted operations use explicit provider interfaces. Generative classification, expansion, reranking and rendering use `SemanticModelProvider`; vector generation uses `EmbeddingProvider`. An implementation may use another compatible LLM or embedding model when Apertus is unavailable, unsuitable for a task, or outperformed in evaluation.

The core server must continue to support deterministic acquisition, filtering, citation, freshness and unsupported-result handling without an Apertus-specific dependency.

Each semantic artifact records:

```text
provider
model identifier and version
operation
prompt/template version where applicable
generation timestamp
input content hash
output content hash
```

Provider changes require regression evaluation before publishing a release.

## 7.3 Multilingual capability contract

Cross-language retrieval is a P0 runtime capability for the source, concept, jurisdiction and language matrix declared by the active release. It must not depend on the requesting application translating or expanding the question.

TIP is not a universal translator. It exposes no standalone translation operation; translation is limited to bounded retrieval metadata and labelled derivative presentation for supported TIP results. The platform-approved language catalog is closed and versioned as `tip-language-catalog/v1`:

| Language profile | Approved query tags | Response tag | Source and projection tag | Notes |
|---|---|---|---|---|
| English | `en` | `en` | `en` | English is the query fallback language |
| Swiss Standard German | `de-CH`, `de`, `de-DE` | `de-CH` | `de-CH` | `de` and `de-DE` are input-only variants |
| French (Switzerland) | `fr-CH` | `fr-CH` | `fr-CH` | Bare `fr` is a detector-only alias |
| Italian (Switzerland) | `it-CH` | `it-CH` | `it-CH` | Bare `it` is a detector-only alias |
| Romansh (Switzerland) | `rm-CH` | `rm-CH` | `rm-CH` | Bare `rm` is a detector-only alias; enabled idioms are declared explicitly |
| Swiss German | `gsw`, `gsw-CH` | none | none | Input-only variants route to `de-CH` |

A hash-addressed registry within the catalog enumerates the permitted operation-scoped aliases, reviewed terminology sets, Swiss German dialect-profile identifiers and Romansh standard/idiom-profile identifiers. In `tip-language-catalog/v1`, bare `fr`, `it` and `rm` are detector-only aliases and the source-declaration alias set is empty; a `SourceDefinition` must use an exact source tag from the table. The table is a human-readable summary, not an extension point; an unlisted variant is outside the catalog even when a model recognizes it.

A release may enable an evaluated subset of this catalog, but it cannot add a profile, tag, alias, dialect, idiom, source language, projection language or response language. Model-provider capabilities, environment variables and source configuration never expand the catalog. Adding a language requires a new platform-catalog version, product approval, implementation support and release-gating evaluation. Build validation rejects a `LanguagePolicy` or source definition that exceeds the referenced platform catalog.

Build validation also requires the enabled subset to be referentially closed. Every client alias and detector-only alias targets an enabled query profile; every source-declaration alias targets an enabled source language; every query-to-projection route targets enabled query and projection tags; and every allowed pair, fixed response and default response references the appropriate enabled role sets and an applicable coverage profile. Every `MixedQueryCombination` must reference an existing coverage profile, use the same `coverage_profile_id` as its containing profile, set `carrier_query_profile` equal to that profile's singular query profile, contain a canonical non-empty set of distinct enabled secondary profiles that excludes the carrier, and have a passing evaluation tied to the candidate policy and suite versions. Duplicate or dangling combinations and combinations attached to failed or unpublished profiles block publication. Every published policy must enable `en` for query and response roles, evaluate the `en` query-to-`en` response route, provide an otherwise equivalent English-query/English-response counterpart for every natural-language coverage profile and declare `fallback_query_language=en`. This fallback requirement does not enable or imply English as a source language. Each Information Product's declared default response language, including the Arrival Checklist's initial `en` default, must be enabled and present in a coverage profile applicable to that product. Any dangling reference fails the build and prevents publication.

The mandatory reproducible path consists of:

- versioned canonical concept identifiers;
- a reviewed multilingual terminology registry for P0 concepts;
- server-side query expansion;
- routed-language lexical search over compact localized metadata projections;
- language-aware lexical retrieval;
- direct canonical-concept lookup;
- original-language evidence and citation preservation;
- release-gating evaluation across declared query/source-language pairs.

Multilingual vector retrieval, semantic concept resolution, reranking and translation supplement this path when they improve measured results. They must not be the only way to retrieve a P0 concept.

Every model provider declares supported operations, languages and model versions. Provider support is a prerequisite for an enabled operation, not permission to add a language. The initial evaluation matrix includes English (`en`), generic German (`de`), Swiss Standard German (`de-CH`), German (Germany) (`de-DE`), French (`fr-CH`), Italian (`it-CH`), Swiss German (`gsw` and `gsw-CH`) and Romansh (`rm-CH`) query variants for the principal scenario. Coverage declarations identify the accepted German query tags, tested Swiss German dialect forms and Romansh standard or idioms; training-data inclusion alone must not be represented as verified capability.

The default metadata projection languages are `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`. Generic German, German (Germany) and Swiss German are input-only query variants: reviewed `de`, `de-DE`, `gsw` and `gsw-CH` terminology routes to the `de-CH` projection, and generated response prose for those variants is always `de-CH`. A client using a query language outside the active release contract translates its request to English before calling TIP.

The initial language routing contract is:

| Query tag | Retrieval projection | Response rule |
|---|---|---|
| `en` | `en` | defaults to `en` |
| `de-CH` | `de-CH` | defaults to `de-CH` |
| `de`, `de-DE` | `de-CH` plus reviewed terminology | fixed to `de-CH` |
| `gsw`, `gsw-CH` | `de-CH` plus reviewed dialect aliases | fixed to `de-CH` |
| `fr-CH`, `it-CH`, `rm-CH` | matching projection | defaults to the query language |

The initial response-language set is `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`. The tags `de`, `de-DE`, `gsw` and `gsw-CH` are never valid output tags. BCP 47 tags are parsed and compared case-insensitively and emitted with canonical casing, so `DE-de` becomes `de-DE`. The initial release uses exact matching after canonicalization rather than accepting every `de-*` or `gsw-*` tag. Bare `gsw` is an explicit application alias for the `gsw-CH` query profile in this Swiss Knowledge Space; `de-AT` and other undeclared variants remain unsupported. This is an application routing policy, not BCP 47 fallback behaviour, and a new tag cannot be enabled without first revising the platform-approved catalog.

---

# 8. Core Components

```text
SourceRegistry
SourceScanner
SourceFetcher
SnapshotStore
DocumentNormalizer
LanguageDetector
LanguagePolicyRegistry
SemanticModelProvider
EmbeddingProvider
TerminologyRegistry
CandidateConceptExtractor
ConceptAggregator
ConceptGraphValidator
ConceptResolver
QueryExpander
MetadataProjectionBuilder
EvidenceCompiler
LexicalIndex
LocalizedMetadataIndex
VectorIndex
EvaluationRunner
ReleasePublisher
QueryPlanner
EvidenceRetriever
CapabilityRegistry
EvidenceRuleEngine
ResultAssembler
ResponseLanguageRenderer
McpServer
RestApi
```

Optional Admin and demo clients consume the same service interfaces. They must not be runtime dependencies of the MCP server.

---

# 9. Shared Contracts

MVP contracts:

```text
SourceDefinition
SourceSnapshot
NormalizedDocument
EvidenceObject
CandidateFact
LanguagePolicy
LanguageContext
LanguageSpan
MixedQueryCombination
ConceptDefinition
CandidateConcept
ConceptAssignment
ConceptRelation
ConceptGraph
TerminologyEntry
QueryVariant
TranslationMetadata
LocalizedRetrievalProjection
KnowledgeRelease
ExecutionPlan
EvidenceBundle
PresentationOutcome
TrustEnvelope
CapabilityDefinition
InformationProductRequest
InformationProductResult
```

The multilingual contracts contain at least:

```text
LanguagePolicy
  policy identifier, schema version, immutable policy version and content hash
  platform catalog identifier and version
  enabled query / response / source / projection language sets
  accepted client tags and explicit aliases by operation
  detector-only aliases and source-declaration aliases
  query-to-projection mappings
  allowed query-to-response combinations and fixed response mappings
  evaluated free-form mixed-query combinations as carrier profile plus secondary-profile set, by coverage profile
  evaluated Swiss German dialect and Romansh idiom profiles
  fallback query language
  language-detector identifier and version
  span-assignment confidence, minimum classifiable text, dominant-share and dominance-margin thresholds
  enabled terminology/entity registry identifiers and hashes
  protected-span kinds, matching modes, precedence, parser versions and material-span thresholds
  deterministic resolution mappings and typed mixed-query reason codes
  required projection fields and completeness thresholds
  evaluation result, suite version and approval status

LanguageContext
  requested_query_language       nullable canonical client-supplied tag
  detected_query_language        nullable canonical detector result
  effective_query_language       nullable release-gated query profile used by the planner
  query_language_resolution      supplied / detected / detector-alias / PROTECTED_TERM_PROFILE, or NOT_APPLICABLE, plus nullable confidence, dominant share, margin and reason
  mixed_language                 boolean
  language_spans                 ordered internal/auditable LanguageSpan records
  retrieval_projection_language  nullable routed metadata projection; never a source filter
  requested_response_language    nullable canonical client request
  response_language              effective response tag
  requested_source_languages     nullable canonical client filter
  effective_source_languages     nullable de-duplicated filter applied to evidence

LanguageSpan
  start / end                    half-open Unicode code-point offsets into the unchanged question
  detected language and profile  nullable, with detector confidence
  disposition                    CARRIER / EVALUATED_SECONDARY / REVIEWED_TERM / REGISTERED_ENTITY / STRUCTURED_VALUE / NEUTRAL_LITERAL / UNRESOLVED / UNSUPPORTED
  protected and material flags
  nullable terminology / concept / entity / structured-field reference

MixedQueryCombination
  stable combination identifier and coverage_profile_id
  carrier_query_profile
  canonical sorted, unique and non-empty secondary_query_profiles
  evaluation suite / version / result
  policy version and approval status

PresentationOutcome
  presentation_status            COMPLETE / DEGRADED
  degradations                   zero or more typed presentation degradations

PresentationDegradation
  code                           RESPONSE_RENDER_FAILED / TRANSLATED_EXCERPT_UNAVAILABLE
  component and target language
  evidence identifier            nullable; required for excerpt-translation failure
  safe provider error metadata   nullable

ConceptDefinition
  concept_id
  preferred labels by language
  concept type and granularity level
  jurisdiction/topic scope
  lifecycle status and owner
  concept relations
  schema version

CandidateConcept
  proposed labels, type and granularity
  candidate relations and terminology
  source evidence references
  extraction provider and model metadata
  confidence and validation state

ConceptAssignment
  concept_id
  document/evidence identifier
  assignment method and confidence
  supporting text spans

ConceptRelation
  source and target concept identifiers
  BROADER / NARROWER / RELATED / SAME_AS
  provenance, confidence and review status

ConceptGraph
  graph identifier and version
  concept and terminology versions
  aggregation configuration
  validation result

TerminologyEntry
  concept_id
  BCP 47 language tag
  term and normalized term
  WHOLE_TOKEN_CASE_SENSITIVE / WHOLE_TOKEN_SIMPLE_CASEFOLD match mode
  alias type
  jurisdiction scope
  provenance and review status
  version

QueryVariant
  text and language
  concept identifiers
  generation method
  source terminology/model reference

TranslationMetadata
  source and target languages
  provider, model and version
  generation timestamp
  original content hash

LocalizedRetrievalProjection
  document/section identifier
  source language and target language
  localized title and section headings
  localized keyphrases and short synopsis
  canonical concepts, named entities and jurisdiction references
  ORIGINAL_SAME_LANGUAGE / OFFICIAL_PARALLEL / CURATED / MODEL_TRANSLATION method per field
  provider/model metadata where applicable
  review status, field completeness, failure reason and original content hash
```

`QueryVariant.generation_method` distinguishes at least `ORIGINAL`, `CURATED_ALIAS`, `MODEL_TRANSLATION` and `SEMANTIC_EXPANSION`. Every variant language must belong to the active policy's query or projection set and must follow its query-to-projection mapping. A model response containing another language is discarded and recorded as a provider-contract failure; it never expands runtime coverage. This keeps deterministic and model-generated recall paths inspectable.

`LanguagePolicy` is a shared contract used by ingestion, runtime, MCP, REST, coverage reporting and evaluation. A `KnowledgeRelease` references its exact policy identifier, version and content hash. The referenced policy becomes immutable as soon as a release candidate is evaluated; any language-set, alias, mapping, threshold, dialect, idiom or fallback change creates a new policy version and requires a new release evaluation.

Target-product contracts:

```text
Publisher
DataProductDefinition
LicensePolicy
Entitlement
UsageRecord
PricingModel
SettlementRecord
```

Commercial contracts are target-product capabilities. At most, the hackathon preserves compatible identifiers and dependency metadata; it does not implement commercial workflows.

Every persisted contract includes a schema version. Published releases reference exact contract versions and content hashes.

## 9.1 Concept graph and governance

Canonical concepts use stable, language-neutral identifiers. Labels, translations and aliases may change without changing a concept identifier. Published records use these lifecycle states:

```text
CURATED
VERIFIED_AUTOMATIC
CANDIDATE
MERGED
DEPRECATED
REJECTED
```

Only `CURATED` and `VERIFIED_AUTOMATIC` concepts contribute to declared concept coverage and direct canonical-concept lookup. `CANDIDATE` concepts may contribute a bounded soft ranking signal but cannot establish applicability, support a fact or exclude a document. `MERGED` and `DEPRECATED` records retain redirects for compatibility; rejected candidates retain audit metadata without entering runtime indexes.

The graph supports multiple parents and typed `BROADER`, `NARROWER`, `RELATED` and `SAME_AS` edges. It must be acyclic for broader/narrower edges, while related and equivalence edges are validated separately. A normalized section or Evidence Object may have multiple `ConceptAssignment`s.

Concept governance is scoped by Knowledge Space. The producer owns seed concepts, granularity policy and P0 coverage. Reviewers approve curated changes. A published `KnowledgeRelease` references an immutable `ConceptGraph` version, its terminology versions, assignment set, extraction metadata and evaluation result.

---

# 10. Source Registry and Acquisition

A `SourceDefinition` contains at least:

```text
source_id
canonical authority
base URL and allowed URL patterns
source type
jurisdiction
declared languages
declared topic coverage
refresh policy
cache policy
robots/source-etiquette policy
enabled state
```

The hackathon operator triggers:

```text
[ BUILD / FULL RELOAD ]
```

```text
configured sources
  ↓
scan / crawl / fetch
  ↓
conditional HTTP validation
  ↓
immutable snapshots
  ↓
normalize
  ↓
language detection
  ↓
candidate concept extraction
  ↓
corpus aggregation + concept graph validation
  ↓
approved concepts + multilingual terminology
  ↓
compact localized metadata projections
  ↓
optional semantic enrichment
  ↓
Evidence Objects and candidate facts
  ↓
indexes
  ↓
evaluation gate
  ↓
immutable published release
```

## 10.1 Concept compilation

Concept compilation is a build-time semantic process over immutable normalized content. It is not executed by `SourceScanner` or `SourceFetcher` and never changes a source snapshot.

```text
normalized sections + language metadata
  ↓
per-section CandidateConcepts and ConceptAssignments
  ↓
cross-document and cross-language candidate aggregation
  ↓
match against seed concepts and existing stable identifiers
  ↓
merge synonyms / translations / abbreviations / dialect forms
  ↓
propose BROADER / NARROWER / RELATED / SAME_AS edges
  ↓
apply granularity and lifecycle policy
  ↓
validate graph, assignments and evidence provenance
  ↓
versioned ConceptGraph for release evaluation
```

Candidate extraction records the exact normalized section and text span supporting each proposal. Apertus may propose concepts, labels, relations and multilingual terminology through `SemanticModelProvider`. Deterministic matching handles known identifiers and reviewed terminology. Corpus aggregation considers labels, multilingual embeddings, shared evidence, source structure and jurisdiction, but no similarity threshold alone may merge or promote a P0 concept.

Granularity is policy-driven rather than a fixed tree depth:

```text
DOMAIN      top-level coverage, for example Immigration or Health
TOPIC       broad navigation or journey, for example Residence
ANSWERABLE  independent action, obligation or question with evidence
DETAIL      subtype, deadline, exemption or other precise fact
```

`ANSWERABLE` is the default retrieval and grounding unit. Split a candidate when user action, authority, applicability, deadline, legal effect, required documents, authoritative source or independently meaningful question differs. Merge candidates when they are translations, synonyms, spelling variants, abbreviations or dialect variants of the same scoped object.

Examples:

```text
Residence [TOPIC]
  Residence permit [ANSWERABLE]
    Permit B [DETAIL]
    Permit L [DETAIL]
    Permit C [DETAIL]
  Municipal registration [ANSWERABLE]
  Change of address [ANSWERABLE]
  Deregistration [ANSWERABLE]

Health [DOMAIN]
  Health insurance [ANSWERABLE]
  Healthcare access [ANSWERABLE]
  Emergency care [ANSWERABLE]
  Public health [ANSWERABLE]
```

Municipal conduct rules may be related to residence or living in a municipality, but are not automatically children of `Residence permit`. A model suggestion is a candidate relation until it meets configured validation or receives review.

## 10.2 Localized retrieval projection compilation

The builder creates compact search projections instead of machine-translating complete pages. Each included normalized section retains its original text and receives localized title, heading, keyphrase and short-synopsis fields for the configured projection languages.

```text
original normalized section
  ↓
unchanged original fields when target language equals source language
  ↓
official parallel-language fields when available
  ↓
curated terminology and concept labels
  ↓
model translation for remaining projection fields
  ↓
field-level provenance and validation
  ↓
LocalizedMetadataIndex
```

The field precedence is `ORIGINAL_SAME_LANGUAGE`, then `OFFICIAL_PARALLEL`, then `CURATED`, then `MODEL_TRANSLATION`. `ORIGINAL_SAME_LANGUAGE` copies the normalized field unchanged when source and target language are the same. Official content is linked through source provenance rather than copied without identity. Model-derived fields record provider, model, generation timestamp, original content hash and review status. Authorities, jurisdiction identifiers, dates, numeric values, canonical concept identifiers and other language-neutral structured values are copied without translation.

The default projection set is:

```text
en
de-CH
fr-CH
it-CH
rm-CH
```

The `rm-CH` configuration declares Rumantsch Grischun and any additional evaluated idioms. Generic German (`de`) and German (Germany) (`de-DE`) use reviewed terminology and the `de-CH` projection rather than separate projections. Swiss German (`gsw` and `gsw-CH`) also does not receive an automatic document-wide metadata projection because it has no single standardized written form. Its reviewed dialect aliases resolve to canonical concepts and Swiss Standard German terminology. All four input-only tags search the `de-CH` projection alongside the original-query lexical, concept and vector channels and always receive `de-CH` generated prose.

Projection records are derived retrieval artifacts and cannot support a fact or serve as cited evidence. The original section or an official parallel-language section remains the evidence target. Projection generation is cached by original content hash and provider/configuration version so unchanged content is not translated again.

Every projection field records `COMPLETE`, `OMITTED_NOT_REQUIRED` or `FAILED` and its method. The active `LanguagePolicy` defines the required title, heading, keyphrase and synopsis fields for each P0 section and projection language. Missing or failed required fields, a target language outside the policy, or a generated field that fails language validation blocks release promotion. Non-P0 omissions are permitted only when they are declared as coverage gaps and excluded from the corresponding coverage profile. A projection-provider failure never downgrades the requirement silently: the candidate release fails and the last successful release remains active.

## 10.3 Source-language normalization and validation

Source-language processing is governed by the candidate release's `LanguagePolicy`:

- A `SourceDefinition` may declare only exact source tags or source-declaration aliases enumerated for that operation in the platform catalog and enabled by the policy. The v1 source-declaration alias set is empty, so only `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH` can be declared before release-level filtering. A malformed tag is a configuration error; a well-formed tag outside the policy is unsupported and blocks the build.
- The builder stores the source-declared tag, detector result, confidence, normalization mapping and effective source language separately. Bare source declarations such as `fr`, `it`, `rm` or `de` are rejected in v1 even though some are valid for detector or query operations. There is no implicit base-language or regional fallback.
- A high-confidence conflict between declared and detected language quarantines the affected section until a reviewed override resolves it. A low-confidence or unknown language is also quarantined. Required quarantined content blocks release promotion; optional content is omitted and reported as a coverage gap.
- A mixed-language page is segmented at stable section boundaries. Each publishable `EvidenceObject` has one effective source language and retains a reference to the unchanged mixed-language snapshot. A section that cannot be separated or confidently assigned is quarantined rather than assigned to its dominant language.
- Invalid byte sequences, replacement-character damage or other material encoding corruption fails normalization for the affected section. The builder does not translate, repair by model inference or publish corrupted text as evidence.
- Official parallel pages are independent versioned sources linked by a parallel-content group. Retrieval time, source-reported revision, effective date and content hash are compared per language; URL similarity alone never establishes equivalence. A stale or substantively divergent parallel page cannot supply `OFFICIAL_PARALLEL` fields for a newer section. The builder instead uses an eligible curated or model-derived projection, or fails the projection gate, while citations continue to target the actual original-language evidence.

All quarantine, override and parallel-version decisions are included in the build report and release evaluation record.

Scheduled and incremental Knowledge CI/CD is a target-product capability, not part of the hackathon implementation. The MVP should nevertheless use ETag, Last-Modified and content hashes where available, record the last attempted and successful refresh, respect source rate limits, and expose failures without removing the previous release. This validates the lifecycle metadata on which later automation depends.

---

# 11. Snapshot and Release Model

Raw source responses are stored as immutable, content-addressed `SourceSnapshot`s with:

```text
canonical URL
retrieval timestamp
HTTP status and relevant headers
source-reported modification time
media type and language
content hash
raw-object location
fetch/build identifier
```

`NormalizedDocument` and `EvidenceObject` records contain at least `declared_language`, `detected_language`, `effective_source_language`, `language_detection_method`, confidence, any reviewed override, `canonical_concept_ids` and the original text or an immutable reference to it. A source may declare several languages while each published evidence object has exactly one effective source language from the active policy.

A `KnowledgeRelease` references the exact snapshots, normalized documents, evidence objects, indexes, schema versions, model metadata, evaluation result and immutable `LanguagePolicy` identifier, version and content hash used to create it.

Only a release that passes the configured evaluation gate can become the active release.

---

# 12. Storage and Retrieval

Recommended storage layout:

```text
PostgreSQL        source metadata / localized projections / evidence / facts / releases / tests
pgvector          semantic vectors
PostgreSQL FTS    original text + per-language compact metadata projections
MinIO/filesystem  immutable raw snapshots
```

Retrieval uses independent lexical, concept and semantic paths so a failure in one path does not silently remove otherwise relevant evidence:

```text
active published release
  ↓
query-language detection + contract validation + retrieval/response-language routing
  ↓
jurisdiction normalization + canonical-concept resolution
  ↓
multilingual terminology expansion
  ↓
parallel candidates:
  routed-language localized metadata + original-query lexical
  + expanded-query lexical
  + canonical concept + multilingual vector
  ↓
candidate union + rank fusion
  ↓
validity / jurisdiction / applicability / authority checks
  ↓
rerank / diversify
  ↓
2-5 Evidence Objects by default
```

Candidate retrieval uses a larger configurable pool than the final 2-5 evidence objects. Ranking may combine semantic relevance, lexical relevance, concept match, source authority, jurisdiction specificity, applicability and temporal validity. Every retrieval channel, query variant and ranking factor must be inspectable for evaluation and debugging.

Query language, retrieval-projection language and response language never act as implicit filters on source language. Source language is restricted only when a client explicitly supplies `source_languages`. Explicit authority, jurisdiction, applicability and temporal constraints remain hard checks before evidence is accepted as support.

For a declared standard language, lexical candidate generation searches its routed localized metadata projection across all source languages. Queries tagged `de` or `de-DE` search reviewed standard-German terminology and the `de-CH` projection. Queries tagged `gsw` or `gsw-CH` search reviewed Swiss German dialect terminology and the `de-CH` projection. Localized metadata is an additional candidate channel and must not become an exclusive prefilter for concept, original-query lexical or vector retrieval.

Concept lookup is one retrieval channel, not a gate. Original and expanded lexical search plus multilingual vector search continue to operate when concept extraction or query-to-concept resolution is missing or uncertain. No concept assignment may make a document invisible to the other channels.

---

# 13. Runtime Processing

```text
REQUEST
  ↓
Query Planner
  ↓
Retrieval / Capability Engine
  ↓
Evidence and Rule Engine
  ↓
Result Assembler
```

For a natural-language request, the `QueryPlanner`:

1. rejects an empty or whitespace-only `question` with `INVALID_ARGUMENT` before language detection;
2. stores a supplied tag as `requested_query_language`, parses and canonicalizes BCP 47 casing, and rejects malformed syntax with `INVALID_ARGUMENT`;
3. runs whole-query and span-level language analysis; when no tag is supplied, stores the qualifying carrier profile and confidence as `detected_query_language`; when a tag is supplied, detection remains an advisory mismatch and embedded-span check and never overwrites it silently;
4. resolves `effective_query_language` only through the active policy's accepted client tags, explicit aliases or detector-only mappings;
5. returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=query_language` and `fallback_query_language=en` for a well-formed requested or high-confidence detected tag outside the policy;
6. maps the explicit `gsw` alias to the `gsw-CH` query profile and applies only the policy's declared detector aliases, including high-confidence bare `fr`, `it` and `rm` detections to `fr-CH`, `it-CH` and `rm-CH`; bare client-supplied `fr`, `it` and `rm` remain unsupported unless a later platform-catalog version approves them;
7. preserves and canonicalizes `requested_response_language`, when supplied, before deriving any effective value;
8. for `de`, `de-DE`, `gsw` and `gsw-CH`, rejects any explicit response other than `de-CH` with `unsupported_component=language_combination` and `required_response_language=de-CH`, then sets `retrieval_projection_language=de-CH` and `response_language=de-CH`;
9. for other supported queries, rejects a requested tag outside the response-language set or disallowed by the policy's combination matrix, then uses the declared retrieval projection and defaults `response_language` to the query profile's response tag when no response was requested;
10. validates and applies `source_languages` as an independent evidence-language constraint;
11. normalizes generic German and German (Germany) with reviewed terminology and Swiss German with tested dialect aliases;
12. normalizes jurisdiction and other structured context;
13. resolves canonical concepts and selects the most specific supported concept that preserves the request meaning;
14. expands broad `DOMAIN` or `TOPIC` concepts into a bounded, diverse set of `ANSWERABLE` descendants;
15. creates multilingual `QueryVariant`s from reviewed terminology and optionally adds model-generated variants with provenance;
16. discards any `QueryVariant` whose language or route is outside the active policy and records a provider-contract failure;
17. produces an inspectable `ExecutionPlan` for parallel retrieval.

Language detection outcomes are deterministic. Every non-empty natural-language query passes through protected-span extraction and span validation below. Whole-query detection is recorded only as an audit and evaluation signal; it is not a fast path, does not select or override the span-derived carrier and never bypasses unsupported, unresolved or mixed-span checks. With no supplied tag, a single qualifying supported span-derived profile or detector-only alias proceeds; a qualifying unsupported span-derived profile returns `UNSUPPORTED_LANGUAGE`. Empty, numeric-only, acronym-only, very short or otherwise linguistically indeterminate input without a tag returns `NEEDS_CONTEXT` with `reason=query_language_undetermined` and the supported query tags. Low-confidence or tied single-language detection also returns `NEEDS_CONTEXT`; it never pivots to English.

Mixed-language resolution is governed only by the active `LanguagePolicy`; provider defaults cannot alter it. The resolver retains the original question, creates an NFC-normalized analysis copy and maintains a code-point offset map back to the unchanged input. It selects longest, non-overlapping protected spans before language scoring. A protected span is an exact normalized match to one of the following:

1. a release-approved `TerminologyEntry` from an enabled terminology-registry hash whose term profile is enabled for the query or projection role;
2. a reviewed alias in the versioned jurisdiction, authority or entity registries;
3. the exact representation of a schema-validated, non-free-text typed value supplied in `structured_context`;
4. a URL, email address, number, date or identifier recognized by a versioned deterministic parser.

Terminology and registered-name matching uses whole Unicode word-token sequences under the entry's explicit case-sensitive or Unicode simple-casefold mode. Full casefolding, substring matching and implicit `ss`/`ß` equivalence are forbidden; such spelling equivalence requires separate reviewed entries. Longest matches win. Equal-length cross-kind overlaps use the precedence order above. Same-kind matches to the same target are de-duplicated as concept or entity candidates while retaining the complete matched-entry, language-profile and provenance set; matches to different targets remain explicit candidates. Structured context and coverage constraints may resolve those candidates, but if more than one target remains the planner returns `NEEDS_CONTEXT` with `reason=ambiguous_protected_span`, offsets and candidate identifiers rather than choosing by score. The original text and each protected span remain unchanged for lexical retrieval and audit. Capitalization, quotation or a model-only entity label never makes a span protected. A protected terminology match may add a provenance-linked concept candidate, but it does not establish semantic equivalence, change jurisdiction, support a fact or grant free-form support for the term's language.

Protected-span extraction precedes carrier selection, while the whole-query detector can only corroborate the scored spans. When no non-protected classifiable text remains, a supplied supported query tag is used after protected-span validation. Without a supplied tag, the resolver collects every language profile retained on the unambiguous protected terminology matches. Exactly one query-enabled profile sets `effective_query_language` to that profile, leaves `detected_query_language=null` and sets `query_language_resolution=PROTECTED_TERM_PROFILE`; multiple query-enabled profiles return `NEEDS_CONTEXT` with `reason=mixed_query_language`; and zero query-enabled profiles return `UNSUPPORTED_LANGUAGE` with `unsupported_component=query_language`, `reason=protected_term_profile_not_query_enabled` and `fallback_query_language=en`. A request containing only registered entities, structured values or neutral literals returns `NEEDS_CONTEXT` with `reason=query_language_undetermined`. Thus term-only golden queries such as `Aufenthaltsbewilligung?` and `residence permit?` remain supported, while `Zurich?` alone does not acquire a language from the entity registry.

The initial hackathon policy classifies the remaining maximal alphabetic spans and assigns a profile only at detector confidence greater than or equal to `0.60`. An assigned span's weight is its number of Unicode letters multiplied by its confidence. Profile weight is the sum of its span weights; total assigned weight includes enabled and non-enabled profiles; dominant share is the leading profile weight divided by total assigned weight; and dominance margin is the leading share minus the runner-up share, with a missing runner-up defined as zero. The leading profile's letter-weighted mean confidence is its profile weight divided by its assigned Unicode-letter count. A carrier profile qualifies when at least three classifiable word tokens and eight classifiable Unicode letters remain, that mean confidence is at least `0.80`, dominant share is at least `0.70`, and dominance margin is at least `0.20`. Equality passes. These values, the detector identity and tokenization rules are versioned policy fields; any change creates a new policy version and requires release evaluation.

An evaluated free-form mixed-query combination is an ordered carrier profile plus an unordered, non-empty set of secondary profiles within one coverage profile; span order does not create another combination. The initial hackathon policy declares this set empty and guarantees mixed input only through the protected-span rule. A later release may add a free-form combination only after its retrieval, intent-preservation and response-language cases pass the release gate. Enabling the individual languages never enables their mixture implicitly.

A non-protected span is material when it contains at least two alphabetic word tokens, at least four Unicode letters in a whitespace-delimited script, or at least two letters in a script that is not normally whitespace-delimited. A material span assigned at confidence greater than or equal to `0.80` to a language outside the active query-language set returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=query_language`, `reason=unsupported_embedded_language`, the detected tag and span offsets. When a supported carrier is available, the error omits `fallback_query_language`, sets `required_query_language` to that carrier and sets `remediation=restate_span_in_required_query_language`. When no supported carrier exists, it sets `fallback_query_language=en` and `remediation=restate_entire_query_in_fallback_language`. A material span that is unassigned below `0.60`, or is assigned between `0.60` inclusive and `0.80` exclusive to a language outside the active query-language set, returns `NEEDS_CONTEXT` with `reason=unresolved_embedded_span`. TIP does not translate, discard or infer the meaning of either span. Shorter unclassified fragments are preserved, contribute no language weight and cannot add a concept or fact.

With no supplied tag, a qualifying enabled carrier becomes `detected_query_language` and `effective_query_language`. Failure to select one for mixed text returns `NEEDS_CONTEXT` with `reason=mixed_query_language`. A protected reviewed term in another policy-enabled query or projection profile sets `mixed_language=true` but does not change the carrier profile or require a free-form mixed-query combination. The planner records any non-protected secondary-profile set provisionally, resolves concept and jurisdiction without retrieving evidence, then validates the set against the selected coverage profile. It proceeds only when that profile nests a passing `MixedQueryCombination` whose carrier equals the profile's query profile and whose complete secondary set matches. An individually enabled but unevaluated mix returns `OUT_OF_COVERAGE` with `reason=unsupported_mixed_query_combination` and identifiers for the relevant evaluated combinations before evidence retrieval. The response default and retrieval projection follow the effective carrier profile.

Therefore `How to get Aufenthaltsbewilligung in Zurich?` resolves as an English query: `Aufenthaltsbewilligung` is a protected reviewed `de-CH` term, `Zurich` is a registered jurisdiction entity, `mixed_language=true`, and the remaining English text selects `effective_query_language=en`. The term contributes a provenance-linked candidate for the Swiss residence-permit concept, retrieval searches the source languages in the matching coverage profile, and the response defaults to `en` unless the client requests another response language permitted by that profile.

With a supplied supported tag, protected spans and evaluated secondary spans in another language do not constitute a mismatch. The tag remains authoritative when the remaining language evidence is below the carrier minimum or when the qualifying carrier is compatible through an explicit policy alias or detector mapping. A qualifying incompatible carrier returns `NEEDS_CONTEXT` with `reason=query_language_mismatch`, the requested and detected tags, and no retrieval. A material unsupported or unresolved span still returns the outcome above even when a supported tag was supplied. Compatibility includes explicit mappings such as `gsw`/`gsw-CH` and detector-only `fr` to requested `fr-CH`; it is never inferred from a shared base language. Thus the example also succeeds with `query_language=en`, while supplying `query_language=de-CH` returns the mismatch outcome when English passes the carrier thresholds.

Swiss German processing is limited to the dialect forms listed in the active policy, and Romansh processing is limited to its listed standard and idioms. A query positively identified as an undeclared dialect or idiom returns `OUT_OF_COVERAGE` with `reason=unsupported_language_variant`; an ambiguous variant returns `NEEDS_CONTEXT`. Neither case is rewritten by a model into a nominally supported form.

Structured clients normally supply relevant context directly, but clients are never required to translate questions, supply synonyms or know source languages. Curated terminology is preferred for P0 concepts; model-generated expansion is a fallback for unrecognized terminology or phrasing within an allowlisted query language.

The no-client-translation guarantee applies only to query languages declared by the active release. A client with an unsupported query language translates the request to English, sets `query_language=en` and accepts English as the TIP response language; any translation from English back to the user's language remains the client's responsibility. TIP does not silently select another pivot language. Invalid response languages and forbidden query-response combinations receive their own remediation and do not trigger query translation.

A narrow request searches its answerable concept and relevant details without automatically broadening to sibling topics. A broad request returns evidence grouped by answerable descendant and may produce `NEEDS_CONTEXT` if a required decision cannot be made. Any fallback broadening is recorded in the execution plan so unrelated topic leakage can be evaluated.

The Evidence and Rule Engine:

- combines corroborating evidence;
- resolves federal/cantonal specialization where deterministic rules allow it;
- preserves source-specific qualifications;
- checks temporal validity and release freshness;
- exposes unresolved contradictions;
- prevents a nearest semantic match from becoming an unsupported factual claim.

Optional prose is generated only after structured facts, statuses and evidence have been established. It is rendered in the effective `response_language`; `de`, `de-DE`, `gsw` and `gsw-CH` queries always use `de-CH`, and Swiss German is never generated. Any translated excerpt or other generated user-facing language also uses the effective response language. The original source excerpt remains the authoritative evidence; any translated excerpt is labelled as machine translation, records provider and model metadata, and links to the original excerpt and citation.

Rendering and excerpt translation are non-authoritative presentation steps. Generated content is language-validated before inclusion; output in a language other than the effective response language is a failure, not a fallback. If response rendering fails, the server returns the established structured facts and original evidence, omits generated prose and sets `presentation_status=DEGRADED` with a typed `RESPONSE_RENDER_FAILED` degradation containing the effective response language and safe provider error metadata. If an excerpt translation fails, only that `translated_excerpt` is omitted and a `TRANSLATED_EXCERPT_UNAVAILABLE` degradation identifies the evidence reference. The factual status remains unchanged, the failure is observable, and TIP never substitutes English, another response language or an unlabelled model output silently.

---

# 14. MCP Contract and Client Compatibility

Initial tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

`resolve` accepts:

```text
question             required
query_language       optional; BCP 47 tag, detected when absent
response_language    optional requested output BCP 47 tag; if supplied for `de`, `de-DE`, `gsw` or `gsw-CH`, it must be `de-CH`; otherwise the effective response follows policy defaults
source_languages     optional non-empty list of explicit evidence-language constraints
jurisdiction         optional
date                 optional
structured_context   optional
```

It returns a compact structured result containing the resolved language context, including requested, detected and effective query languages, query-language resolution metadata, requested and effective response languages, requested and effective source-language filters, factual status, `PresentationOutcome`, supported facts, evidence references, coverage information and a Trust Envelope. Factual `status` is one of `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NEEDS_CONTEXT`, `OUT_OF_COVERAGE`, `INSUFFICIENT_VERIFIED_EVIDENCE`, `CONFLICTING_EVIDENCE`, `STALE` or `UNSUPPORTED_LANGUAGE`. `INVALID_ARGUMENT` is a boundary validation error returned before a factual result, not a factual status. Each evidence reference exposes `source_language`, the original excerpt and citation, plus optional `translated_excerpt` and `translation_metadata`. A translated excerpt uses the effective response language and is never represented as the cited source.

Malformed BCP 47 syntax in any language field returns `INVALID_ARGUMENT` with the affected component. A well-formed tag outside the active policy returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=query_language|response_language|source_languages` without running factual resolution. A forbidden query-response pair returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=language_combination`; a fixed mapping includes `required_response_language=de-CH`, while another forbidden pair includes its allowed response tags. An unsupported whole-query language includes the supported query-language list and `fallback_query_language=en`. An unsupported embedded span with a supported carrier instead returns that `required_query_language`, the offending span offsets and `remediation=restate_span_in_required_query_language`; it asks for the entire query in fallback English only when no supported carrier exists. An unsupported response or source filter includes the corresponding supported set. No response or source error asks for query translation.

`source_languages` has these exact semantics:

- omitted or `null` means no evidence-language restriction;
- an empty array is invalid and returns `INVALID_ARGUMENT`;
- tags are canonicalized, then duplicates are removed while preserving first occurrence order;
- every remaining tag must be in the active policy's source-language set; query aliases and base-language fallback do not apply;
- a valid filter with no matching coverage profile for the resolved concept and jurisdiction returns `OUT_OF_COVERAGE` with `reason=no_coverage_in_requested_source_languages`, the effective filter and relevant coverage profiles;
- when a matching coverage profile exists but its eligible sources do not provide sufficient verified evidence for the request, the result is `INSUFFICIENT_VERIFIED_EVIDENCE` with the effective filter. Neither case retries without the filter.

`get_evidence` resolves evidence identifiers to source excerpts and provenance without returning entire source documents by default.

`get_coverage` returns the platform-catalog version and active `LanguagePolicy` identifier, version and hash, plus discovery lists for declared sources, concepts/topics, jurisdictions, query tags and aliases, source languages, response languages, projection languages, tested Swiss German dialect forms and Romansh variants. It also returns the mixed-query threshold summary, protected-span registry versions, the combination-aware `coverage_profiles` described below, `fallback_query_language=en`, exclusions, release version and freshness information. It does not expose a context-free global list of mixed-query combinations.

Authoritative coverage is combination-aware. The response includes stable `coverage_profile_id` values and `coverage_profiles`, where each profile identifies the valid combination of Knowledge Space, source, concept/topic, jurisdiction, query profile, source language, retrieval projection, allowed or fixed response languages, nested passing `MixedQueryCombination` records, evaluated dialect/idiom variant, temporal scope, projection completeness and evaluation status. Each mixed record exposes its ordered carrier, canonical secondary-profile set, policy/evaluation versions and status; there is no global or Cartesian mixed-language claim. A client must use a matching coverage profile before presenting a combination as supported, and omitted combinations are out of coverage.

The compatibility target is standard MCP clients and the Swisscom evaluation harness. OpenCode is a supported example and validation client, not a required, privileged or server-specific integration. A normal demo query should complete with one high-level `resolve` call whenever possible.

The repository must document:

- supported MCP transport;
- startup command;
- environment variables;
- example client configuration;
- tool input and output schemas;
- authentication/test-access procedure if required;
- coverage and limitations.

---

# 15. REST Interface

REST is a secondary adapter over the same runtime used by MCP. It must not contain separate grounding logic.

Structured Information Products submit typed `InformationProductRequest`s and receive typed `InformationProductResult`s containing requirements or facts, evidence identifiers, factual status, `PresentationOutcome` and Trust Envelope. A request without natural-language query text or a query-language field may supply `response_language` from the active policy; when omitted, it uses the Information Product's publication-validated default response language, initially `en` for the hackathon products. Its `LanguageContext` sets requested, detected and effective query language and retrieval projection to `null`, sets `query_language_resolution=NOT_APPLICABLE` with null dominance metrics, sets `mixed_language=false` and returns an empty `language_spans` list. It validates response language against coverage profiles applicable to that Information Product; query detection, query routing and fixed query-response mappings do not run. Input-only query tags are never accepted as response languages.

REST exposes the same `LanguagePolicy`, `LanguageContext`, validation statuses, source-filter semantics, coverage profiles and presentation degradations as MCP. Natural-language REST requests also use the same fixed German/Swiss German to `de-CH` response rules. Queryless typed Information Products use the explicit `NOT_APPLICABLE` query context above instead of inheriting query-only behavior. REST contract tests submit equivalent requests through both adapters and require semantically identical results; OpenAPI descriptions or static enums must not advertise tags beyond the active platform catalog.

Multilingual grounding and response content do not imply universal interface localization. For the hackathon, optional Admin and demo UI chrome may remain English-only; UI locale is a client concern distinct from TIP's `response_language`. Any later localized UI may enable only an approved catalog subset and must label unavailable interface locales rather than treating model translation as product support.

---

# 16. Admin Control Plane

**Decision class: Product-validation extension (P1)**

The optional MVP Admin UI uses control-plane APIs for:

1. dashboard and health;
2. Knowledge Spaces;
3. Source Registry;
4. full-build initiation and progress;
5. source snapshots and refresh state;
6. Evidence Explorer;
7. Concept Registry, candidates, assignments and graph diff;
8. concept review and lifecycle actions;
9. localized metadata projections, provenance and completeness;
10. evaluation results;
11. Knowledge Releases;
12. MCP/REST integration examples.

The UI is not required for MCP runtime availability.

---

# 17. Evaluation and Operability

Automated evaluation covers the challenge dimensions:

| Dimension | Technical checks |
|---|---|
| Grounding quality | factual correctness, authority, jurisdiction, temporal validity, citation support, unsupported/conflicting results |
| Useful coverage | combination-aware coverage profiles and representative questions per source/topic/jurisdiction/language combination |
| Concept quality | P0 assignment accuracy, duplicate/orphan rate, hierarchy consistency, multilingual alias correctness and stability across releases |
| Concept retrieval behaviour | broad-query descendant coverage, narrow-query precision, unrelated-topic leakage and retrieval recall with concept lookup disabled/enabled |
| Multilingual retrieval | cross-language candidate recall, final evidence hit rate, concept resolution, terminology expansion and source-language diversity |
| Language policy | closed-catalog enforcement, policy immutability, tag/alias mapping, provider isolation and Knowledge Release policy reference |
| Language resolution | malformed and unsupported tags, requested/detected/effective fields, low-confidence, short, carrier selection, protected spans, mixed combinations and mismatch outcomes |
| Source-language integrity | declaration/detection mismatch, mixed-section segmentation, encoding failures and parallel-page revision compatibility |
| Localized metadata | required projection completeness, original/official/curated/model provenance, provider-failure gating, routed-language lexical recall and original-evidence linkage |
| Response-language safety | supported response language, fixed `de`/`de-DE`/`gsw`/`gsw-CH` to `de-CH` mappings, absence of Swiss German generation, original evidence preservation, translation labelling and citation linkage |
| Presentation degradation | structured result preservation, typed render/translation warnings and absence of silent response-language fallback |
| Unsupported language | deterministic rejection by component, unsupported dialect/idiom outcome, separate query/response/source-language discovery and English query-fallback guidance |
| Agent efficiency | tool-call count, response bytes/tokens, evidence count and latency |
| Operability | clean setup, repeatable builds, cache behaviour, refresh, source failures, last-known-good release and monitoring |
| Integration readiness | schema validation, MCP/REST language parity and tests through standard MCP clients |

The evaluation configuration stores explicit thresholds for release promotion. For the finite P0 multilingual golden set, every required authoritative document must appear in the top 20 candidate pool and every required supported fact must have at least one supporting document in the final top 5 evidence objects. Every citation must resolve to original-language evidence. Operational latency and throughput targets should be calibrated against the available infrastructure before the event rather than embedded as unsupported estimates.

The golden suite covers every declared query/source-language pair and includes terminology, abbreviations, spelling variants, German compounds, Swiss German dialect forms and declared Romansh forms. At minimum it tests the residence-permit concept across `residence permit`, `Aufenthaltsbewilligung`, `Aufenthaltserlaubnis`, `Ausländerausweis`, `Bewilligung B/L/C`, `autorisation de séjour`, `permis de séjour` and corresponding evaluated Italian, Swiss German and Romansh variants. Broad requests such as `residence in Zurich` and `health` are contrasted with narrow requests such as `residence permit`, `municipal registration` and `health insurance`. A cross-border case such as `Gilt meine deutsche Aufenthaltserlaubnis in der Schweiz?` verifies that a named foreign status remains a distinct entity rather than being rewritten as a Swiss permit.

`Aufenthaltserlaubnis` is a reviewed `de-DE` query alias only when it semantically names the Swiss residence permit being sought or required. If it denotes an existing German or other foreign document or legal status, the planner preserves it as an entity and returns the coverage-appropriate result, including `OUT_OF_COVERAGE` when recognition or transfer is not covered. Ambiguous bare `Erlaubnis` without sufficient jurisdiction or concept context returns `NEEDS_CONTEXT`; neither term is normalized globally. The suite tests `de`, `de-CH`, `de-DE`, `gsw` and `gsw-CH`, query detection without a supplied tag, and canonicalization such as `DE-de` to `de-DE`. Undeclared variants such as `de-AT` remain unsupported.

Language-contract cases distinguish malformed tags from well-formed unsupported tags and cover empty, numeric-only, acronym-only and very short questions; low-confidence, tied and mixed-language detection; exact threshold boundaries; compatible aliases; high-confidence supplied/detected mismatch; and high-confidence bare `fr`, `it` and `rm` detector mappings to their Swiss profiles. Bare client-supplied `fr`, `it` and `rm` remain unsupported. Fixtures include Unicode normalization, accents, apostrophes, hyphens, umlauts, `ss`/`ß` distinctions and German compounds. Explicitly undeclared Swiss German dialects and Romansh idioms return `OUT_OF_COVERAGE`; ambiguous variants return `NEEDS_CONTEXT` without model rewriting.

Mixed-query golden fixtures assert the complete `LanguageContext`, ordered `LanguageSpan` dispositions, concept result, retrieval projection and response default. `How to get Aufenthaltsbewilligung in Zurich?`, both without a supplied tag and with `query_language=en`, must produce effective query language `en`, `mixed_language=true`, the Swiss residence-permit concept and default response language `en`. The reviewed term and registered jurisdiction must be protected while the original text remains unchanged. The same text with `query_language=de-CH` must return `NEEDS_CONTEXT` with `reason=query_language_mismatch` when the English carrier meets the policy thresholds.

An additional positive fixture, `Wie bekomme ich a residence permit in Zürich?` with `query_language=de-CH`, must produce effective query and response language `de-CH` because the reviewed English term is protected. Term-only fixtures verify `query_language_resolution=PROTECTED_TERM_PROFILE`; same-target matches retain every profile and exercise the zero-, one- and multiple-query-profile outcomes; entity-only input without a tag remains undetermined. Mocked span-classifier fixtures exercise equality at every carrier and materiality threshold. A threshold-failing English/German mix returns `NEEDS_CONTEXT` with `reason=mixed_query_language`; a three-profile mix and a free-form mix of individually enabled profiles absent from the applicable coverage profile return `OUT_OF_COVERAGE` with `reason=unsupported_mixed_query_combination`. A fixture policy with one passing combination verifies its container `coverage_profile_id`, carrier equality, complete secondary set, evaluation linkage and supplied-tag behavior; each invalid invariant must block publication.

A high-confidence Russian semantic span embedded in an English carrier returns `UNSUPPORTED_LANGUAGE` with `reason=unsupported_embedded_language`, `required_query_language=en`, span offsets and `remediation=restate_span_in_required_query_language`, but no redundant fallback field. The equivalent case without a supported carrier returns `fallback_query_language=en` and whole-query remediation. A material span forced below assignment confidence returns `NEEDS_CONTEXT` with `reason=unresolved_embedded_span`. Additional fixtures cover a decomposed accent such as `u` plus U+0308 and assert the normalized-to-original offset map and emitted offsets against the unchanged input; whole-token and declared-case matching; forbidden substring and implicit `ss`/`ß` matches; same-target de-duplication; different-target `ambiguous_protected_span` outcomes; source filtering combined with allowed and forbidden mixes; and the rule that capitalization, quotation and model-only entity labels cannot create protection.

Queryless typed REST contract tests assert null requested, detected and effective query languages and retrieval projection, `query_language_resolution=NOT_APPLICABLE` with null dominance metrics, `mixed_language=false` and `language_spans=[]`. They also assert that neither language detector nor mixed-query resolver is invoked.

The suite verifies that `de`, `de-DE`, `gsw` and `gsw-CH` queries route through the `de-CH` metadata projection and produce `de-CH` generated prose, including Swiss terminology and orthography such as `Aufenthaltsbewilligung` and `Strasse` rather than generated `Aufenthaltserlaubnis` or `Straße`. Original excerpts and proper names remain unchanged. It tests omitted and explicit `de-CH` response values, rejects explicit `de`, `de-DE`, `gsw` or `gsw-CH` output and rejects another response language for a fixed mapping. For `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`, default output and explicit supported cross-language responses remain release-gated. Each projected standard query language must retrieve the gold evidence through its routed metadata projection, while Swiss German must do so through declared aliases and German normalization.

Source-filter cases cover omission, `null`, empty arrays, malformed tags, unsupported tags, duplicates that collide after canonicalization, multiple valid tags and valid filters with no matching evidence. Ingestion fixtures cover declared/detected mismatch, unknown language, mixed-language sections, encoding corruption and official parallel pages with different revision dates. Coverage tests prove that independent discovery lists do not imply unsupported source/concept/jurisdiction/language combinations.

Failure-injection tests cover projection-provider errors, wrong-language projection fields, incomplete required projections, model-generated `QueryVariant`s outside the allowlist, response-render errors, wrong-language rendered output and individual excerpt-translation failures. Required projection failures block publication and preserve the last successful release; runtime presentation failures preserve structured facts and original evidence and emit the specified typed degradation without substituting a language. The same language cases run through MCP and REST and must produce equivalent semantics.

An unsupported query language such as Russian must return `UNSUPPORTED_LANGUAGE` with `unsupported_component=query_language` and `fallback_query_language=en`; the equivalent client-translated English request must resolve normally. Unsupported response, source-language and combination cases return their specific remediation without English query-fallback guidance. A catalog, policy, concept, projection, multilingual, language-routing, adapter-parity or query-granularity regression blocks release promotion.

Operational telemetry includes:

```text
build duration and state
source request count / cache hit / failure
last attempted and successful refresh
snapshot and release identifiers
platform catalog / language policy identifiers, versions and hashes
query latency
retrieval candidate and evidence counts
requested / detected / effective query language, resolution method, confidence and reason
effective retrieval projection / requested and effective response / requested and effective source languages
mixed-language, supplied/detected mismatch and unsupported-variant outcomes
resolved concepts and query-variant provenance
concept candidates / assignments / merges / promotions
concept graph version and graph-validation result
concept resolution level and descendant expansion
source declared / detected / effective language, quarantine, override and parallel-version decision
metadata projection language / method / completeness / failure reason
unsupported-language rejection by component and English query-fallback use
presentation status / typed rendering and excerpt-translation degradation
coverage-profile identifier and no-match reason
per-channel candidate ranks and multilingual fallback use
model/provider latency and errors
MCP tool calls and response size
```

---

# 18. Security and Repository Hygiene

- Secrets and credentials must never be committed.
- Required test access is provided through a secure channel.
- Source allowlists constrain crawling and redirects.
- Retrieved content is treated as untrusted input.
- Stored HTML and model output are escaped before display.
- Logs avoid unnecessary personal or request data.
- Dependency and model versions are pinned for reproducibility.
- Public release and source redistribution follow the applicable licenses and hackathon/UBS rules.

---

# 19. Structured Demo Implementations

**Decision class: Product-validation extensions**

## Swiss Arrival Checklist

The application sends formal nationality, purpose, duration, canton/municipality, date and optional `response_language` inputs through REST. It receives typed requirements, deadlines, evidence identifiers, optional localized presentation, `PresentationOutcome` and a Trust Envelope. Because it supplies neither query text nor a query-language field, its query-derived `LanguageContext` fields are not applicable and it performs no query detection, projection routing or fixed query-response validation. It validates only the response language against coverage profiles applicable to the product and defaults to the product definition's publication-validated `en` setting when omitted. Original-language evidence and citations remain authoritative; hackathon UI chrome may remain English-only.

## Swiss Hike stretch demo

```text
Flutter → REST → swiss-hike-finder
                    ↓
              DemoRouteRepository
              MockTransportProvider
              MockWeatherProvider
              MockPlacesProvider
                    ↓
              deterministic filters
                    ↓
              optional preference ranking
                    ↓
              typed route cards
```

Suggested mock assets:

```text
demo/hiking/routes.json
demo/hiking/transport.json
demo/hiking/weather.json
demo/hiking/restaurants.json
```

All mock data must be visibly labelled `DEMO/MOCK`.

---

# 20. Implementation Workstreams

| Priority | Workstream | Scope |
|---|---|---|
| P0 | Contracts and coverage | MCP schemas, language contracts, terminology, source definitions, coverage/limitations |
| P0 | Acquisition | scanner, fetcher, snapshots, normalizer and refresh metadata |
| P0 | Concepts | seed graph, candidate extraction, corpus aggregation, granularity policy, terminology and graph validation |
| P0 | Localized metadata | compact standard-language projections, provenance, caching, German-variant routing and Swiss German normalization |
| P0 | Evidence | compiler, concept assignments, authority/applicability metadata and citations |
| P0 | Retrieval | language-aware lexical, canonical-concept and multilingual vector retrieval plus hard checks |
| P0 | Runtime | language detection, server-side expansion, planner, evidence/rule engine, response rendering and MCP server |
| P0 | Evaluation | grounding, citations, multilingual recall, translation safety, unsupported queries, efficiency and freshness |
| P0 | Delivery | reproducible setup and standard MCP client validation |
| P1 | Control plane | build, evidence, evaluation and release views |
| P1 | Structured demo | REST and Arrival Checklist |
| P2 | Stretch demo | Swiss Hike with mock providers |

No hackathon workstream is required to implement scheduled/incremental builds or marketplace billing. Their future needs may shape stable identifiers, provenance and dependency metadata only after the P0 server is secure.

---

# 21. Technical Definition of Done

Swisscom can clone the repository, follow the documented setup, start the MCP server, inspect its declared coverage and limitations, run an on-demand build, and execute the supplied evaluation tests.

The server works through a standard MCP client and the Swisscom evaluation harness, normally resolves the principal demo - including cross-language and broad/narrow concept variants - with one high-level tool call, returns compact cited original-language evidence and explicit trust status, renders optional prose in the effective supported response language, maps `de`, `de-DE`, `gsw` and `gsw-CH` queries to `de-CH` generated prose, reports freshness, and preserves the last successful release when a source or build fails.

The active release exposes and immutably references a `LanguagePolicy` within the closed platform-approved catalog. MCP and REST enforce the same requested/detected/effective language resolution, source-language filters, fixed response mappings and combination-aware coverage profiles. Provider configuration cannot expand these capabilities, and a presentation-provider failure returns structured facts plus original evidence with a typed degradation rather than silently changing language.

Every included P0 section has complete, provenance-linked compact metadata projections for English, Swiss Standard German, French, Italian and the declared Romansh form. Generic German and German (Germany) requests resolve through reviewed terminology and the `de-CH` projection; Swiss German requests resolve through tested dialect aliases and the same projection. These input-only query variants produce `de-CH` generated prose while preserving original-language evidence. Requests outside the declared query-language contract receive `UNSUPPORTED_LANGUAGE` and English query-fallback guidance rather than best-effort silent translation.

The published release exposes a versioned concept graph with provenance and lifecycle status, returns grouped answerable descendants for broad requests, preserves narrow-query precision, and continues to retrieve relevant documents through lexical/vector paths when concept metadata is missing.

For the principal scenario, the published release passes the declared English, generic German, Swiss Standard German, German (Germany), French, Italian, Swiss German and Romansh query matrix without client-side translation or terminology expansion. It also passes the protected-term mixed-query fixtures, including `How to get Aufenthaltsbewilligung in Zurich?`, with the specified carrier language, concept and response behavior. The guarantee is limited to declared concepts, sources, jurisdictions, tested language variants and evaluated free-form mixed-query combinations; unsupported spans, dialects, idioms or source languages are reported through coverage and result status rather than inferred.

OpenCode is used as one demonstrated client without introducing OpenCode-specific server behaviour. Apertus is used where available and beneficial, while an alternative compatible provider can be configured without changing domain or MCP contracts.

At product-validation level, the implementation also demonstrates that the same source, release, evidence, trust and distribution contracts can support another Information Product without duplicating grounding logic.
