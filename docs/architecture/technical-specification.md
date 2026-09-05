# Swisscom Trusted Information Platform
## Technical & Solution Architecture Specification - V4

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
8. Retrieval returns a small evidence bundle rather than an uncontrolled document dump.
9. Original-language evidence remains authoritative; translations are labelled derivative content.
10. Every result is traceable to source versions and processing metadata.
11. Refresh, cache state and source failures are observable.
12. All model, storage and client integrations are replaceable behind explicit interfaces.
13. The vertical slice should validate target-product concepts without implementing the entire target product.
14. Future commercial and autonomous capabilities influence contracts only where that does not endanger MVP delivery.

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
→ enrichment
→ evidence
→ release
```

It may use heavier parsing and semantic dependencies. It depends on `swisstip.core` and never on `swisstip.runtime`.

### `swisstip.runtime`

Implements the published-release query engine:

```text
request
→ retrieval
→ applicability
→ evidence resolution
→ structured result
```

It depends on `swisstip.core` and never on `swisstip.ingestion`. This prevents request-time queries from invoking crawlers or build logic.

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
- multilingual terminology expansion, including evaluated Swiss German and Romansh variants;
- applicability interpretation;
- evidence reranking;
- optional translation and response-language rendering after evidence has been established.

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

The mandatory reproducible path consists of:

- versioned canonical concept identifiers;
- a reviewed multilingual terminology registry for P0 concepts;
- server-side query expansion;
- language-aware lexical retrieval;
- direct canonical-concept lookup;
- original-language evidence and citation preservation;
- release-gating evaluation across declared query/source-language pairs.

Multilingual vector retrieval, semantic concept resolution, reranking and translation supplement this path when they improve measured results. They must not be the only way to retrieve a P0 concept.

Every model provider declares supported operations, languages and model versions. The initial evaluation matrix includes English (`en`), German (`de-CH`), French (`fr-CH`), Italian (`it-CH`), Swiss German (`gsw-CH`) and Romansh (`rm-CH`) query variants for the principal scenario. Coverage declarations identify the tested Swiss German dialect forms and Romansh standard or idioms; training-data inclusion alone must not be represented as verified capability.

---

# 8. Core Components

```text
SourceRegistry
SourceScanner
SourceFetcher
SnapshotStore
DocumentNormalizer
LanguageDetector
SemanticModelProvider
EmbeddingProvider
TerminologyRegistry
ConceptResolver
QueryExpander
EvidenceCompiler
LexicalIndex
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
LanguageContext
ConceptDefinition
TerminologyEntry
QueryVariant
TranslationMetadata
KnowledgeRelease
ExecutionPlan
EvidenceBundle
TrustEnvelope
CapabilityDefinition
InformationProductRequest
InformationProductResult
```

The multilingual contracts contain at least:

```text
LanguageContext
  query_language
  response_language
  source_languages
  detection_method and confidence

ConceptDefinition
  concept_id
  preferred labels by language
  jurisdiction/topic scope
  schema version

TerminologyEntry
  concept_id
  BCP 47 language tag
  term and normalized term
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
```

`QueryVariant.generation_method` distinguishes at least `ORIGINAL`, `CURATED_ALIAS`, `MODEL_TRANSLATION` and `SEMANTIC_EXPANSION`. This keeps deterministic and model-generated recall paths inspectable.

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
canonical concepts + multilingual terminology
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

`NormalizedDocument` and `EvidenceObject` records contain at least `detected_language`, `language_detection_method`, `canonical_concept_ids` and the original text or an immutable reference to it. A source may declare several languages while an individual evidence object normally has one detected language.

A `KnowledgeRelease` references the exact snapshots, normalized documents, evidence objects, indexes, schema versions, model metadata and evaluation result used to create it.

Only a release that passes the configured evaluation gate can become the active release.

---

# 12. Storage and Retrieval

Recommended storage layout:

```text
PostgreSQL        source metadata / evidence / facts / releases / tests
pgvector          semantic vectors
PostgreSQL FTS    lexical search documents
MinIO/filesystem  immutable raw snapshots
```

Retrieval uses independent lexical, concept and semantic paths so a failure in one path does not silently remove otherwise relevant evidence:

```text
active published release
  ↓
query-language detection + response-language selection
  ↓
jurisdiction normalization + canonical-concept resolution
  ↓
multilingual terminology expansion
  ↓
parallel candidates:
  original-query lexical + expanded-query lexical
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

Query language and response language never act as implicit filters on source language. Source language is restricted only when a client explicitly supplies `source_languages`. Explicit authority, jurisdiction, applicability and temporal constraints remain hard checks before evidence is accepted as support.

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

1. accepts or detects `query_language`;
2. selects `response_language`, defaulting to the query language;
3. normalizes jurisdiction and other structured context;
4. resolves canonical concepts;
5. creates multilingual `QueryVariant`s from reviewed terminology;
6. optionally adds model-generated variants, recording their provenance;
7. produces an inspectable `ExecutionPlan` for parallel retrieval.

Structured clients normally supply relevant context directly, but clients are never required to translate questions, supply synonyms or know source languages. Curated terminology is preferred for P0 concepts; model-generated expansion is a fallback for unrecognized language or phrasing.

The Evidence and Rule Engine:

- combines corroborating evidence;
- resolves federal/cantonal specialization where deterministic rules allow it;
- preserves source-specific qualifications;
- checks temporal validity and release freshness;
- exposes unresolved contradictions;
- prevents a nearest semantic match from becoming an unsupported factual claim.

Optional prose is generated only after structured facts, statuses and evidence have been established. It is rendered in `response_language`. The original source excerpt remains the authoritative evidence; any translated excerpt is labelled as machine translation, records provider and model metadata, and links to the original excerpt and citation.

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
response_language    optional; BCP 47 tag, defaults to query language
source_languages     optional explicit evidence-language constraint
jurisdiction         optional
date                 optional
structured_context   optional
```

It returns a compact structured result containing the resolved language context, status, supported facts, evidence references, coverage information and a Trust Envelope. Each evidence reference exposes `source_language`, the original excerpt and citation, plus optional `translated_excerpt` and `translation_metadata`. A translated excerpt is never represented as the cited source.

`get_evidence` resolves evidence identifiers to source excerpts and provenance without returning entire source documents by default.

`get_coverage` returns declared sources, topics, jurisdictions, query languages, source languages, response languages, tested Swiss German dialect forms and Romansh variants, exclusions, release version and freshness information.

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

Structured Information Products submit typed `InformationProductRequest`s and receive typed `InformationProductResult`s containing requirements or facts, evidence identifiers, status and Trust Envelope.

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
7. evaluation results;
8. Knowledge Releases;
9. MCP/REST integration examples.

The UI is not required for MCP runtime availability.

---

# 17. Evaluation and Operability

Automated evaluation covers the challenge dimensions:

| Dimension | Technical checks |
|---|---|
| Grounding quality | factual correctness, authority, jurisdiction, temporal validity, citation support, unsupported/conflicting results |
| Useful coverage | declared coverage matrix and representative questions per source/topic |
| Multilingual retrieval | cross-language candidate recall, final evidence hit rate, concept resolution, terminology expansion and source-language diversity |
| Response-language safety | requested response language, original evidence preservation, translation labelling and citation linkage |
| Agent efficiency | tool-call count, response bytes/tokens, evidence count and latency |
| Operability | clean setup, repeatable builds, cache behaviour, refresh, source failures, last-known-good release and monitoring |
| Integration readiness | schema validation and tests through standard MCP clients |

The evaluation configuration stores explicit thresholds for release promotion. For the finite P0 multilingual golden set, every required authoritative document must appear in the top 20 candidate pool and every required supported fact must have at least one supporting document in the final top 5 evidence objects. Every citation must resolve to original-language evidence. Operational latency and throughput targets should be calibrated against the available infrastructure before the event rather than embedded as unsupported estimates.

The golden suite covers every declared query/source-language pair and includes terminology, abbreviations, spelling variants, German compounds, Swiss German dialect forms and declared Romansh forms. At minimum it tests the residence-permit concept across `residence permit`, `Aufenthaltsbewilligung`, `Aufenthaltserlaubnis`, `Ausländerausweis`, `Bewilligung B/L/C`, `autorisation de séjour`, `permis de séjour` and corresponding evaluated Italian, Swiss German and Romansh variants. A multilingual regression blocks release promotion.

Operational telemetry includes:

```text
build duration and state
source request count / cache hit / failure
last attempted and successful refresh
snapshot and release identifiers
query latency
retrieval candidate and evidence counts
detected query / response / source languages
resolved concepts and query-variant provenance
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

The application sends formal nationality, purpose, duration, canton/municipality and date inputs through REST. It receives typed requirements, deadlines, evidence identifiers and a Trust Envelope.

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
| P0 | Evidence | compiler, authority/applicability metadata and citations |
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

The server works through a standard MCP client and the Swisscom evaluation harness, normally resolves the principal demo - including cross-language variants - with one high-level tool call, returns compact cited original-language evidence and explicit trust status, renders optional prose in the requested language, reports freshness, and preserves the last successful release when a source or build fails.

For the principal scenario, the published release passes the declared English, German, French, Italian, Swiss German and Romansh query matrix without client-side translation or terminology expansion. The guarantee is limited to declared concepts, sources, jurisdictions and tested language variants; unsupported dialects, idioms or source languages are reported through coverage and result status rather than inferred.

OpenCode is used as one demonstrated client without introducing OpenCode-specific server behaviour. Apertus is used where available and beneficial, while an alternative compatible provider can be configured without changing domain or MCP contracts.

At product-validation level, the implementation also demonstrates that the same source, release, evidence, trust and distribution contracts can support another Information Product without duplicating grounding logic.
