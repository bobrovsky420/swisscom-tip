# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V7

**Working product name:** Swisscom Trusted Information Platform (TIP)  
**Hackathon domain:** Swiss Public Information  
**Primary demo sources:** Swiss Confederation / admin.ch ecosystem (including SEM) and Canton Zurich / zh.ch  
**Reference MCP client:** OpenCode  
**Primary MCP transport:** Streamable HTTP; stdio optional for local development  
**Reference structured app:** Swiss Arrival Checklist  
**Stretch consumer reference app:** Swiss Hike — Flutter  
**Primary Swisscom semantic model:** Apertus  
**Deployment model:** Headless platform; SaaS/private SaaS/on-prem capable

---

# 1. Executive Summary

Swisscom Trusted Information Platform is a headless platform that converts authoritative knowledge, live data, private context and digital services into trustworthy structured Information Products consumable by applications and AI agents.

It is explicitly **not a chatbot**.

> **AI is infrastructure, not the interface.**

The hackathon MVP deliberately focuses on the core value path. Selected official content from the admin.ch ecosystem and zh.ch is loaded **on demand**, stored as immutable source snapshots, normalized, enriched with Apertus where useful, indexed, evaluated and published as a Knowledge Release. Runtime requests search the published local release rather than scraping government sites per question.

For the hackathon there is **no scheduler, continuous source watcher, incremental refresh worker or automatic Knowledge CI/CD loop**. An administrator presses **Build / Full Reload**, or invokes the equivalent CLI/API command. The platform then reloads the configured source scope, rebuilds the Knowledge Space, runs tests and publishes a new release.

The full product architecture still includes scheduled revalidation, incremental refresh, semantic change detection, impact analysis, approval policies and autonomous Knowledge CI/CD. These are explicitly roadmap/production capabilities rather than hackathon dependencies.

The runtime itself is more structured than ordinary RAG. A request becomes an explicit Execution Plan. Hard metadata filters are applied before hybrid retrieval. Evidence is reranked using authority, jurisdiction, applicability and validity. Facts are resolved by concept, conflicts are handled explicitly, and a compact Evidence Bundle + Trust Envelope is returned. Natural-language generation is optional and happens only after the evidence has been established.

---

# 2. Product Vision

TIP answers:

> **When an application needs information, what source should it trust, how should that source be accessed, how current is it, where does it apply, and how can the result be verified?**

```text
                           APPLICATIONS

 OpenCode/myAI   Arrival App   Flutter App   eGov   Bank Portal
       \             |             |          |         /
                    MCP / REST / SDK
                          │
                          ▼
        ┌────────────────────────────────┐
        │ TRUSTED INFORMATION PLATFORM  │
        │ Knowledge │ Live │ Context     │
        │ Rules │ Recommendations │ Trust│
        └────────────────┬───────────────┘
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
     Compiled         Live APIs       Private data
     knowledge        & services      / policies
          └──────────────┼───────────────┘
                         ▼
                      Apertus
                where semantically useful
                         │
                         ▼
                  STRUCTURED RESULT
```

---

# 3. Product Principles

1. **Stable authoritative information is compiled ahead of runtime.**
2. **Live information is obtained through registered Capabilities when needed.**
3. **The external authority remains canonical; TIP stores a verified operational copy.**
4. **Deterministic logic handles deterministic problems.**
5. **Apertus handles semantic uncertainty.**
6. **Structured output precedes generated prose.**
7. **Every result carries provenance, applicability and trust metadata.**
8. **MCP is an interface, not the product architecture.**
9. **Search returns evidence, not answers.**
10. **Minimum sufficient evidence:** normally 2–5 high-quality Evidence Objects.
11. **Hackathon simplicity:** full reload on demand; no background refresh dependency.
12. **Production autonomy:** scheduled/incremental Knowledge CI/CD remains part of the target design.

---

# 4. Information Classes

| Class | Example | Default strategy |
|---|---|---|
| AUTHORITATIVE | Residence-registration requirements | Compiled Knowledge Space |
| LIVE | Train fare tomorrow | Live Capability |
| PRIVATE | Does my lease permit cats? | Private Knowledge Space |
| CONSENSUS | Good first-date locations | Discovery/recommendation sources |
| DERIVED | Best hike for tomorrow's constraints | Knowledge + capabilities + rules |
| HISTORICAL | What rule applied in 2024? | Versioned source repository |

---

# 5. Main Hackathon Scenario

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation
       ↓
State Secretariat for Migration (SEM)
       ↓ federal context
Canton Zurich
       ↓ cantonal guidance
Municipality / user context
```

Golden cases include:

- direct registration question;
- EU/EFTA employee moving to Zurich;
- jurisdiction mismatch such as Geneva;
- German-language equivalent;
- unsupported municipal detail;
- exact citation/provenance checks;
- query after a manually triggered new full build.

---

# 6. Scope Split: Hackathon MVP vs Target Product

## 6.1 Hackathon MVP

Implemented:

```text
Configured admin.ch/SEM + zh.ch sources
        ↓
Manual Build / Full Reload
        ↓
scan configured scope
        ↓
fetch + immutable snapshots
        ↓
normalize
        ↓
Apertus enrichment
        ↓
Evidence Objects + candidate facts
        ↓
index
        ↓
evaluate
        ↓
publish Knowledge Release
        ↓
MCP / REST runtime
```

Not required:

- background scheduler;
- periodic source watcher;
- ETag-driven recurring jobs;
- incremental rebuilds;
- semantic diff UI;
- automatic impact analysis;
- autonomous release promotion.

## 6.2 Full Product / Production Design

Retained in the architecture:

```text
Scheduler / Source Watcher
        ↓
cheap revalidation
        ↓
new / changed sources only
        ↓
semantic change analysis
        ↓
impact analysis
        ↓
incremental compilation
        ↓
regression tests
        ↓
auto-publish or approval policy
```

This separation keeps the hackathon feasible without weakening the long-term product story.

---

# 7. Control Plane and Data Plane

```text
                     CONTROL PLANE

 Admin GUI / CLI
    ↓
 Source Registry
    ↓
 [Build / Full Reload]
    ↓
 Scanner / Crawler / Fetcher
    ↓
 Immutable Snapshot / Normalize
    ↓
 Apertus Enrichment
    ↓
 Evidence Compilation
    ↓
 Index / Evaluate / Publish

────────────────────────────────────────────

                       DATA PLANE

               Published Knowledge Release
                         │
                   Query Planner
                         │
             Retrieval / Capability Engine
                         │
                Evidence / Rule Engine
                         │
                  Result Assembler
                         │
               ┌─────────┼──────────────┐
               ▼         ▼              ▼
              MCP       REST           SDK
               │         │              │
               ▼         ├────────┐     ▼
           OpenCode   Arrival   Swiss Hike   Other Apps
                      Checklist   Flutter
```

The Data Plane does not depend on the Admin GUI being available.

---

# 8. Hackathon Deployment Topology

Use a modular monorepo rather than unnecessary microservices.

```text
Process 1  API + MCP Runtime
Process 2  Build Worker
           scanner/crawler/fetcher/compiler/evaluation
Process 3  Admin Backend
Process 4  Admin Web UI
Process 5  optional mock-capability service for Swiss Hike

PostgreSQL + pgvector
MinIO or local object storage
Optional Redis
```

No scheduler process is required for the hackathon.

Typical setup:

```text
docker compose up
→ configure sources
→ Build / Full Reload
→ release published
→ OpenCode / REST apps consume release
```

---

# 9. Shared Contracts

The `/contracts` package is the first integration deliverable.

Required types:

- `SourceDefinition`
- `DiscoveredResource`
- `SourceSnapshot`
- `NormalizedDocument`
- `EvidenceObject`
- `CandidateFact`
- `KnowledgeRelease`
- `ExecutionPlan`
- `EvidenceBundle`
- `RetrievalResult`
- `TrustEnvelope`
- `CapabilityDefinition`
- `InformationProductRequest`
- `InformationProductResult`

Use Pydantic/JSON Schema and commit fixtures early so modules can develop independently.

## 9.1 EvidenceObject

```json
{
  "evidence_id": "ev-zh-registration-22",
  "source_id": "zh-arriving",
  "source_version": 22,
  "authority": {"publisher": "Canton Zurich", "level": "cantonal"},
  "jurisdiction": "CH-ZH",
  "concepts": ["residence.registration", "residence.registration_deadline"],
  "applicability": {"destination_canton": "CH-ZH"},
  "content": "original supporting passage",
  "canonical_url": "...",
  "retrieved_at": "..."
}
```

## 9.2 ExecutionPlan

```json
{
  "information_class": "AUTHORITATIVE",
  "knowledge_spaces": ["swiss-public"],
  "concepts": ["residence.registration", "residence.permit"],
  "applicability": {
    "jurisdiction": "CH-ZH",
    "nationality_group": "EU_EFTA",
    "purpose": "EMPLOYMENT"
  },
  "requested_date": "2026-09-04",
  "retrieval_strategy": "HYBRID",
  "max_evidence": 4
}
```

## 9.3 EvidenceBundle

```json
{
  "status": "SUPPORTED",
  "facts": [
    {
      "concept": "residence.registration_deadline",
      "value": 14,
      "unit": "days",
      "evidence": ["ev-sem-registration-17", "ev-zh-registration-22"]
    }
  ],
  "evidence": ["ev-sem-registration-17", "ev-zh-registration-22"],
  "trust": {
    "knowledge_release": "swiss-public@2026.09.04.3",
    "confidence": 0.98
  }
}
```

---

# 10. Module A — Domain Configuration & Contracts

Responsibilities:

- schemas;
- Swiss Public configuration;
- trusted source definitions;
- concept vocabulary;
- applicability dimensions;
- fixtures.

Example concepts:

```text
residence.registration
residence.registration_deadline
residence.permit
employment.start
health.insurance
```

---

# 11. Module B — Source Acquisition & Ingestion

## Hackathon responsibility

Perform a bounded full scan/fetch whenever Build is triggered.

Components:

```text
Source Registry
Scanner
Crawler
Fetcher
Snapshot Manager
Normalizer
```

The scanner discovers resources from configured roots using links/sitemaps where practical. The crawler obeys explicit include/exclude scopes. The fetcher handles HTTP state, retries, rate limits, redirects and content types. Raw HTML/PDF/JSON is stored immutably. The normalizer removes boilerplate while preserving meaningful structure.

Example source policy:

```yaml
source: zh.ch
discovery:
  follow_links: true
  max_depth: 2
include:
  - /migration-integration/**
exclude:
  - /search/**
  - /news/**
```

Hackathon build states:

```text
DISCOVERED → ELIGIBLE → FETCHED → SNAPSHOTTED
           → NORMALIZED → READY_FOR_COMPILATION
```

Exceptions:

```text
IGNORED
FETCH_FAILED
PARSE_FAILED
REVIEW_REQUIRED
REJECTED
```

## Production extension

Add Scheduler, Source Watcher, ETag/Last-Modified revalidation, content hashes and incremental fetching. These interfaces should be anticipated but need not be implemented in the MVP.

---

# 12. Module C — Knowledge Compiler & Apertus Enrichment

Responsibilities:

- classification;
- concept extraction;
- applicability extraction;
- multilingual terminology mapping;
- authority/source relationship analysis;
- Evidence Object compilation;
- candidate fact extraction;
- candidate evaluation generation.

Apertus is not authoritative. Original source evidence is always preserved.

Stable facts such as deadlines, rates, thresholds, effective dates and boolean obligations SHOULD be extracted during build when reliable, reducing runtime inference.

Production extension: semantic old/new change analysis and affected-concept impact detection.

---

# 13. Module D — Storage, Indexing & Retrieval

Recommended MVP stack:

```text
PostgreSQL        sources, snapshots, documents, evidence,
                  concepts, candidate facts, releases, evaluations
pgvector          semantic retrieval
PostgreSQL FTS    lexical retrieval
MinIO/filesystem  immutable raw snapshots
```

Retrieval applies hard filters before similarity search:

```text
Published Release
        ↓
validity date
        ↓
jurisdiction / applicability
        ↓
authority / trust
        ↓
lexical + vector + concept retrieval
        ↓
merge / rerank
        ↓
diversity-aware selection
        ↓
2–5 Evidence Objects
```

Ranking signals:

```text
lexical relevance
semantic relevance
concept match
authority weight
jurisdiction specificity
applicability match
temporal validity
source quality
```

---

# 14. Module E — Trusted Information Runtime

The runtime contains four logical engines:

```text
REQUEST
   ↓
1. Query Planner
   ↓
2. Retrieval / Capability Engine
   ↓
3. Evidence & Rule Engine
   ↓
4. Result Assembler
```

## 14.1 Query Planner

Natural-language MCP requests may use Apertus to extract intent, concepts and applicability. Structured apps usually skip this step because their inputs are already typed.

The planner decides:

- information class;
- Knowledge Spaces / Capabilities;
- concepts;
- jurisdiction/applicability;
- effective date;
- evidence budget.

## 14.2 Retrieval / Capability Engine

AUTHORITATIVE requests use the published Knowledge Release. LIVE requests use registered Capabilities. DERIVED products can combine both.

## 14.3 Evidence & Rule Engine

The engine:

- groups facts by concept;
- combines corroborating evidence;
- recognizes specialization, e.g. federal + cantonal guidance;
- applies deterministic rules;
- detects unresolved contradictions;
- preserves evidence links.

If two sources disagree, the engine checks applicability, specificity, authority and validity. If the conflict cannot be resolved, return `CONFLICTING_EVIDENCE` rather than silently choosing one.

## 14.4 Result Assembler

Produces:

```text
status
facts
applicability
evidence
Trust Envelope
limitations
optional explanation context
```

OpenCode may generate prose from this bundle. Arrival Checklist can directly render typed facts with no final LLM call.

Supported states:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
```

---

# 15. MCP Contract and OpenCode

MVP tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

The high-level `resolve` tool should normally require one agent call.

The repository should include `opencode.jsonc` and a smoke-test sequence for the Streamable HTTP endpoint.

Visible demo path:

```text
OpenCode
   ↓
swiss_information.resolve
   ↓
Execution Plan
   ↓
swiss-public release
   ↓
SEM + zh.ch Evidence Bundle
   ↓
answer with citations
```

---

# 16. Admin Control Plane

The Admin GUI is required because it makes the knowledge lifecycle visible.

## Hackathon screens

1. Dashboard
2. Knowledge Space
3. Source Registry
4. Build / Full Reload
5. Build progress/results
6. Source snapshots
7. Evidence Explorer
8. Evaluations
9. Knowledge Releases
10. MCP/REST integration status

Example:

```text
SWISS PUBLIC                        HEALTHY
Production release                 build-003
Configured sources                 8
Last full build                    13:10
Evidence                           421
Tests                              42 / 42 PASS

[ BUILD / FULL RELOAD ]
```

Do not spend MVP time on scheduler configuration, source-watch dashboards or semantic diff approval screens.

## Production Control Plane extension

Add:

- refresh schedules;
- source-watch status;
- new/changed document counts;
- semantic diff review;
- impact analysis;
- approval policies;
- automatic promotion/rollback controls.

---

# 17. Build, Evaluation and Releases

## Hackathon

Each Build / Full Reload creates a candidate release:

```text
Build triggered
      ↓
full configured source load
      ↓
compile
      ↓
index
      ↓
run golden tests
      ↓
PASS → publish new release
FAIL → keep previous production release
```

This still proves versioning, reproducibility and quality gating without implementing background CI/CD.

A useful demo can build once before the session, then optionally trigger a second manual rebuild from a controlled fixture/mirror if time permits. It should not be presented as an autonomous watcher.

## Production

Extend the same release machinery into full Knowledge CI/CD:

```text
scheduled/change-triggered revalidation
→ incremental rebuild
→ semantic impact analysis
→ regression suite
→ policy-based publish/review
```

---

# 18. Reference Application — Swiss Arrival Checklist

Purpose: prove that the admin.ch/zh.ch Knowledge Release can power a formal non-chat application.

Inputs:

```text
Nationality category
Purpose of stay
Employment duration
Destination canton
Municipality
Arrival date
Work start date
```

Example REST request:

```json
{
  "nationality_group": "EU_EFTA",
  "purpose": "EMPLOYMENT",
  "employment_duration": "MORE_THAN_3_MONTHS",
  "destination": {"canton": "CH-ZH", "municipality": "Zurich"},
  "arrival_date": "2026-09-04",
  "employment_start_date": "2026-09-08"
}
```

Output is a typed checklist with requirement status, deadlines, evidence IDs and Trust Envelope. No natural-language prompt is required.

---

# 19. Stretch Reference Application — Swiss Hike / Flutter

Swiss Hike is P2/stretch only.

Structured input:

```text
origin
date
target hiking duration
difficulty
max transport time
scenery preferences
weather preference
restaurant near end
```

Mock strategy:

```text
demo/hiking/routes.json        10–20 curated demo routes
demo/hiking/transport.json     fixed travel times
demo/hiking/weather.json       deterministic forecast scenarios
demo/hiking/restaurants.json   deterministic nearby places
```

Provider interfaces:

```text
TransportProvider
 ├─ MockTransportProvider       ← hackathon
 └─ RealProviderAdapter         ← future

WeatherProvider
 ├─ MockWeatherProvider         ← hackathon
 └─ RealProviderAdapter         ← future

PlacesProvider
 ├─ MockPlacesProvider          ← hackathon
 └─ RealProviderAdapter         ← future
```

Mocks must be clearly labelled `DEMO/MOCK` and never represented as current authoritative data.

Execution:

```text
route candidates
      ↓
hard filters: duration, difficulty, transport
      ↓
mock capability enrichment
      ↓
soft preference ranking
      ↓
structured result cards
```

---

# 20. Independent Hackathon Workstreams

| Workstream | Responsibility | Fixture boundary |
|---|---|---|
| A | Contracts/domain config | shared schemas |
| B | Scanner/crawler/full-load ingestion | SourceDefinition |
| C | Apertus compiler/enrichment | NormalizedDocument |
| D | DB/index/retrieval | EvidenceObject |
| E | Runtime/MCP/REST | RetrievalResult/EvidenceBundle |
| F | Admin GUI | mocked Admin API |
| G | Evaluation + reference apps | mocked runtime endpoints |

No one needs to implement a scheduler or background refresher during the hackathon.

---

# 21. Recommended Python Stack

If Python is selected:

```text
FastAPI + Pydantic v2        API/contracts
Official MCP Python SDK      MCP adapter
PostgreSQL                   persistent metadata/facts
pgvector                     vector retrieval
PostgreSQL FTS               lexical retrieval
SQLAlchemy 2 + Alembic       persistence/migrations
httpx                        source fetching
BeautifulSoup + trafilatura  HTML structure/content
PyMuPDF                      PDF extraction
pytest                       unit/contract/golden tests
uv                           environment/package management
Docker Compose               reproducible deployment
React/Vue                    Admin GUI
Flutter                      optional Swiss Hike app
```

Not required for MVP: APScheduler, Celery, Kafka, Kubernetes, LangChain, LlamaIndex, LangGraph, Neo4j, Elasticsearch or a dedicated vector database.

A production scheduler can later use APScheduler, Celery, Temporal, Kubernetes jobs or an equivalent operational mechanism without changing the ingestion contracts.

---

# 22. Hackathon Demo Flow

1. Open Admin Control Plane.
2. Show configured admin.ch/SEM + zh.ch sources.
3. Trigger **Build / Full Reload** or show the completed build record.
4. Show snapshots → Evidence Objects → tests → published release.
5. Open OpenCode and ask the Zurich-arrival question.
6. Make the single `swiss_information.resolve` call visible.
7. Show federal + CH-ZH evidence and citations.
8. Ask an unsupported question and show explicit refusal/coverage state.
9. Open Swiss Arrival Checklist and submit typed fields against the same release.
10. If P2 is ready, show Swiss Hike Flutter using mocked providers.

Optional technical/final-round demo: manually modify a controlled fixture/mirror, press **Build / Full Reload** again, and show that a new release changes downstream results. Make clear that automatic change watching is a production roadmap capability.

---

# 23. Hackathon Definition of Done

The submission is successful when:

1. official admin.ch/SEM and zh.ch sources are configured;
2. Build / Full Reload acquires the configured scope;
3. raw snapshots are stored immutably;
4. normalized documents and Evidence Objects are produced;
5. Apertus enriches semantic fields;
6. evidence is locally indexed;
7. golden tests run;
8. a Knowledge Release is published;
9. OpenCode connects through MCP;
10. normal requests do not scrape government sites;
11. the runtime filters by jurisdiction/applicability before hybrid retrieval;
12. compact Evidence Bundles contain citations and Trust metadata;
13. unsupported/conflicting evidence is represented explicitly;
14. Swiss Arrival Checklist consumes the same release through REST;
15. the whole stack starts reproducibly;
16. no scheduler or background-refresh infrastructure is required for completion.

---

# 24. Target Product Roadmap

### Phase 1 — Hackathon
On-demand full builds, Swiss Public Knowledge Space, OpenCode MCP, Admin GUI, Arrival Checklist.

### Phase 2 — Operational Knowledge Platform
Scheduled source watching, conditional HTTP revalidation, incremental builds, semantic change analysis, automatic regression and approval workflows.

### Phase 3 — Live Capabilities
Transport, weather, places, public datasets.

### Phase 4 — Consumer Information Products
Hiking, cycling, photography, housing, local discovery.

### Phase 5 — Enterprise Overlay
Private policies, enterprise context and governance.

### Phase 6 — Regulatory Intelligence
FINMA, EMIR, DORA, dependency/impact analysis.

### Phase 7 — Actions and Marketplace
Transactions, workflows, reusable Knowledge Packs and Capabilities.

---

# 25. Final Architecture Principle

For the hackathon:

```text
CONFIGURE SOURCES
      ↓
BUILD / FULL RELOAD
      ↓
COMPILE + TEST
      ↓
PUBLISH
      ↓
SERVE LOCALLY THROUGH MCP/REST
```

For the production platform:

```text
CONTINUOUS SOURCE WATCHING
      ↓
INCREMENTAL KNOWLEDGE CI/CD
      ↓
VERSIONED TRUSTED INFORMATION
      ↓
ANY APPLICATION
```

The hackathon proves the information model, build pipeline, evidence retrieval, trust model and integrations. Continuous autonomous maintenance is the natural production extension—not a dependency for proving the core concept in two days.
