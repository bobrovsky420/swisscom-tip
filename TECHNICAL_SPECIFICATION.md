# Swisscom Trusted Information Platform
## Technical & Solution Architecture Specification — V1

**Hackathon:** Swiss Grounding MCP<br>
**Product and functional specification:** [`FUNCTIONAL_SPECIFICATION.md`](FUNCTIONAL_SPECIFICATION.md)<br>
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
7. Retrieval returns a small evidence bundle rather than an uncontrolled document dump.
8. Every result is traceable to source versions and processing metadata.
9. Refresh, cache state and source failures are observable.
10. All model, storage and client integrations are replaceable behind explicit interfaces.
11. The vertical slice should validate target-product concepts without implementing the entire target product.
12. Future commercial and autonomous capabilities influence contracts only where that does not endanger MVP delivery.

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

# 5. Semantic Model Strategy

**Decision class: Team MVP choice with a product-enabling provider boundary**

## 5.1 Preferred provider

Apertus is the preferred semantic model for the hackathon because it supports the Swiss and sovereign-AI positioning and gives the team an opportunity to evaluate it on multilingual Swiss information.

Suitable uses include:

- source and document classification;
- concept and terminology extraction;
- multilingual query and evidence matching;
- applicability interpretation;
- evidence reranking;
- optional explanations after evidence has been established.

## 5.2 Model independence

All semantic operations must use a `SemanticModelProvider` interface. The implementation may use another compatible LLM or embedding model when Apertus is unavailable, unsuitable for a task, or outperformed in evaluation.

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

---

# 6. Core Components

```text
SourceRegistry
SourceScanner
SourceFetcher
SnapshotStore
DocumentNormalizer
SemanticModelProvider
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
McpServer
RestApi
```

Optional Admin and demo clients consume the same service interfaces. They must not be runtime dependencies of the MCP server.

---

# 7. Shared Contracts

MVP contracts:

```text
SourceDefinition
SourceSnapshot
NormalizedDocument
EvidenceObject
CandidateFact
KnowledgeRelease
ExecutionPlan
EvidenceBundle
TrustEnvelope
CapabilityDefinition
InformationProductRequest
InformationProductResult
```

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

# 8. Source Registry and Acquisition

A `SourceDefinition` contains at least:

```text
source_id
canonical authority
base URL and allowed URL patterns
source type
jurisdiction
language
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

# 9. Snapshot and Release Model

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

A `KnowledgeRelease` references the exact snapshots, normalized documents, evidence objects, indexes, schema versions, model metadata and evaluation result used to create it.

Only a release that passes the configured evaluation gate can become the active release.

---

# 10. Storage and Retrieval

Recommended storage layout:

```text
PostgreSQL        source metadata / evidence / facts / releases / tests
pgvector          semantic vectors
PostgreSQL FTS    lexical search documents
MinIO/filesystem  immutable raw snapshots
```

Retrieval applies hard constraints before relevance ranking:

```text
active published release
  ↓
validity / jurisdiction / applicability / authority filters
  ↓
lexical + vector + concept candidates
  ↓
merge / rerank / diversify
  ↓
2–5 Evidence Objects by default
```

Ranking may combine semantic relevance, lexical relevance, concept match, source authority, jurisdiction specificity, applicability and temporal validity. Every factor must be inspectable for evaluation and debugging.

---

# 11. Runtime Processing

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

Natural-language requests may use the configured semantic provider to derive an `ExecutionPlan`. Structured clients normally supply the relevant context directly.

The Evidence and Rule Engine:

- combines corroborating evidence;
- resolves federal/cantonal specialization where deterministic rules allow it;
- preserves source-specific qualifications;
- checks temporal validity and release freshness;
- exposes unresolved contradictions;
- prevents a nearest semantic match from becoming an unsupported factual claim.

Optional prose is generated only after structured facts, statuses and evidence have been established.

---

# 12. MCP Contract and Client Compatibility

Initial tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

`resolve` accepts the question plus optional language, jurisdiction, date and structured context. It returns a compact structured result containing status, supported facts, evidence references, coverage information and a Trust Envelope.

`get_evidence` resolves evidence identifiers to source excerpts and provenance without returning entire source documents by default.

`get_coverage` returns declared sources, topics, jurisdictions, languages, exclusions, release version and freshness information.

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

# 13. REST Interface

REST is a secondary adapter over the same runtime used by MCP. It must not contain separate grounding logic.

Structured Information Products submit typed `InformationProductRequest`s and receive typed `InformationProductResult`s containing requirements or facts, evidence identifiers, status and Trust Envelope.

---

# 14. Admin Control Plane

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

# 15. Evaluation and Operability

Automated evaluation covers the challenge dimensions:

| Dimension | Technical checks |
|---|---|
| Grounding quality | factual correctness, authority, jurisdiction, temporal validity, citation support, unsupported/conflicting results |
| Useful coverage | declared coverage matrix and representative questions per source/topic |
| Agent efficiency | tool-call count, response bytes/tokens, evidence count and latency |
| Operability | clean setup, repeatable builds, cache behaviour, refresh, source failures, last-known-good release and monitoring |
| Integration readiness | schema validation and tests through standard MCP clients |

The evaluation configuration stores explicit thresholds for release promotion. Final targets should be calibrated against the available infrastructure before the event rather than embedded as unsupported estimates.

Operational telemetry includes:

```text
build duration and state
source request count / cache hit / failure
last attempted and successful refresh
snapshot and release identifiers
query latency
retrieval candidate and evidence counts
model/provider latency and errors
MCP tool calls and response size
```

---

# 16. Security and Repository Hygiene

- Secrets and credentials must never be committed.
- Required test access is provided through a secure channel.
- Source allowlists constrain crawling and redirects.
- Retrieved content is treated as untrusted input.
- Stored HTML and model output are escaped before display.
- Logs avoid unnecessary personal or request data.
- Dependency and model versions are pinned for reproducibility.
- Public release and source redistribution follow the applicable licenses and hackathon/UBS rules.

---

# 17. Structured Demo Implementations

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

# 18. Implementation Workstreams

| Priority | Workstream | Scope |
|---|---|---|
| P0 | Contracts and coverage | MCP schemas, source definitions, coverage/limitations |
| P0 | Acquisition | scanner, fetcher, snapshots, normalizer and refresh metadata |
| P0 | Evidence | compiler, authority/applicability metadata and citations |
| P0 | Retrieval | lexical/vector retrieval and hard filters |
| P0 | Runtime | planner, evidence/rule engine, MCP server |
| P0 | Evaluation | grounding, citations, unsupported queries, efficiency and freshness |
| P0 | Delivery | reproducible setup and standard MCP client validation |
| P1 | Control plane | build, evidence, evaluation and release views |
| P1 | Structured demo | REST and Arrival Checklist |
| P2 | Stretch demo | Swiss Hike with mock providers |

No hackathon workstream is required to implement scheduled/incremental builds or marketplace billing. Their future needs may shape stable identifiers, provenance and dependency metadata only after the P0 server is secure.

---

# 19. Technical Definition of Done

Swisscom can clone the repository, follow the documented setup, start the MCP server, inspect its declared coverage and limitations, run an on-demand build, and execute the supplied evaluation tests.

The server works through a standard MCP client and the Swisscom evaluation harness, normally resolves the principal demo with one high-level tool call, returns compact cited evidence and explicit trust status, reports freshness, and preserves the last successful release when a source or build fails.

OpenCode is used as one demonstrated client without introducing OpenCode-specific server behaviour. Apertus is used where available and beneficial, while an alternative compatible provider can be configured without changing domain or MCP contracts.

At product-validation level, the implementation also demonstrates that the same source, release, evidence, trust and distribution contracts can support another Information Product without duplicating grounding logic.
