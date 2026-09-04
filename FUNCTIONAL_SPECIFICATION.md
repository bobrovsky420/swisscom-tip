# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V4

**Working product name:** Swisscom Trusted Information Platform (TIP)  
**Hackathon domain:** Swiss Public Information  
**Primary demo sources:** Swiss Confederation / admin.ch ecosystem (including SEM) and Canton Zurich / zh.ch  
**Reference MCP demo client:** OpenCode  
**Primary hackathon transport:** MCP Streamable HTTP, with stdio optional for local development  
**Additional interfaces:** REST API; SDK/Webhooks as roadmap  
**Primary Swisscom semantic model:** Apertus  
**Deployment model:** Headless platform; SaaS/private SaaS/on-prem capable

---

# 1. Executive Summary

Swisscom Trusted Information Platform is a headless platform that converts authoritative information, live data, enterprise data and digital services into trustworthy, structured Information Products consumable by applications and AI agents.

It is explicitly **not a chatbot**.

> **AI is infrastructure, not the interface.**

The hackathon implementation solves the original Swiss public-information MCP challenge with a deliberately focused scope: authoritative federal information from the admin.ch ecosystem and cantonal information from zh.ch. Stable authoritative information is acquired ahead of runtime, stored as immutable source snapshots, normalized, semantically enriched, indexed, tested and published as an immutable Knowledge Release. Runtime MCP calls normally query this compiled release rather than scraping government sites.

The reference MCP client for development and the final demo is **OpenCode**. The same Knowledge Release also powers a small structured **Swiss Arrival Checklist** through REST, proving that TIP is reusable information infrastructure rather than chatbot infrastructure.

The main end-to-end demo is:

```text
admin.ch / SEM + zh.ch
        ↓
Source Registry / Scanner / Crawler
        ↓
immutable snapshots
        ↓
normalization + Apertus enrichment
        ↓
Evidence Objects
        ↓
evaluation + Knowledge Release
        ↓
        ├───────────────┐
        ▼               ▼
OpenCode via MCP   Swiss Arrival Checklist via REST
```

A controlled source-change simulation then demonstrates autonomous Knowledge CI/CD: detect → classify → rebuild → test → publish → both clients automatically consume the new release.

---

# 2. Product Vision

TIP answers a question that individual applications should not have to solve repeatedly:

> **When an application needs information, what source should it trust, how should that source be accessed, how current is it, where does it apply, and how can the result be verified?**

```text
                         APPLICATIONS

     OpenCode/myAI   Mobile App   eGov   Bank Portal   Agent
             \          |          |         |          /
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

# 3. Core Product Principles

1. **Stable information is compiled.** Laws, government guidance, administrative procedures and regulations are stored and indexed ahead of runtime.
2. **Live information is retrieved live.** Weather, fares, disruptions and availability use registered Capabilities with appropriate caching.
3. **The external authority remains canonical.** TIP stores a verified operational representation, not a replacement authority.
4. **Deterministic logic handles deterministic problems.** HTTP state, hashes, dates, numeric comparisons and version consistency do not require an LLM.
5. **Apertus handles semantic uncertainty.** Classification, concepts, multilingual mapping, semantic change and fuzzy ranking are appropriate AI tasks.
6. **Autonomous by default, human review by exception.**
7. **Structured output before generated prose.**
8. **Every result carries a machine-readable Trust Envelope.**
9. **MCP is an integration protocol, not the product architecture.**
10. **The core remains model-independent, with Apertus first-class in the Swisscom deployment.**

---

# 4. Information Classes

| Class | Example | Default strategy |
|---|---|---|
| AUTHORITATIVE | What are the residence-registration requirements? | Compiled Knowledge Space |
| LIVE | What does tomorrow's train cost? | Live Capability |
| PRIVATE | Does my lease permit cats? | Private Knowledge Space |
| CONSENSUS | What are good first-date locations? | Discovery/recommendation sources |
| DERIVED | Which hike best fits tomorrow's conditions? | Knowledge + capabilities + rules |
| HISTORICAL | What rule applied in 2024? | Versioned source repository |

---

# 5. Main Hackathon Scenario

The primary scenario is:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

It deliberately requires complementary federal and cantonal evidence:

```text
Swiss Confederation
       ↓
State Secretariat for Migration (SEM)
       ↓ federal context
Canton Zurich
       ↓ cantonal guidance
Municipality
```

Golden demo cases include:

- direct registration deadline question;
- EU/EFTA employee moving to Zurich;
- jurisdiction mismatch such as Geneva;
- German-language equivalent;
- unsupported exact municipal fee;
- source-version/history query;
- controlled source-change regression.

---

# 6. Architecture: Control Plane and Data Plane

TIP consists of a **Control Plane** that creates trustworthy knowledge and a **Data Plane** that serves published knowledge.

```text
                     CONTROL PLANE

 Admin GUI
    │
    ▼
 Source Registry
    ↓
 Scanner / Crawler / Fetcher
    ↓
 Snapshot / Normalize
    ↓
 Apertus Enrichment
    ↓
 Evidence Compilation
    ↓
 Index / Evaluate / Release

────────────────────────────────────────────

                       DATA PLANE

               Published Knowledge Release
                         │
               ┌─────────┼─────────┐
               ▼         ▼         ▼
              MCP       REST      SDK
               │         │         │
               ▼         ▼         ▼
           OpenCode   Arrival    Other Apps
                      Checklist
```

The Admin GUI is not required for Data Plane availability.

---

# 7. Hackathon Deployment Topology

Logical modules should not become unnecessary microservices during a two-day event. Recommended topology:

```text
Process 1  API + MCP Runtime
Process 2  Knowledge Worker
           scanner/crawler/fetcher/compiler/evaluation
Process 3  Admin Backend
Process 4  Admin Web UI

PostgreSQL + pgvector
MinIO or local object storage
Optional Redis
```

Everything should run through a reproducible `docker compose up` workflow.

---

# 8. Shared Contracts

The `/contracts` package is the first integration deliverable. Required shared types:

- `SourceDefinition`
- `DiscoveredResource`
- `SourceSnapshot`
- `NormalizedDocument`
- `EvidenceObject`
- `SemanticChange`
- `KnowledgeRelease`
- `RetrievalResult`
- `TrustEnvelope`
- `InformationProductRequest`
- `InformationProductResult`

Use Pydantic/JSON Schema and commit fixtures early.

## 8.1 EvidenceObject

```json
{
  "evidence_id": "ev-zh-registration-22",
  "source_id": "zh-arriving",
  "source_version": 22,
  "authority": {
    "publisher": "Canton Zurich",
    "level": "cantonal"
  },
  "jurisdiction": "CH-ZH",
  "concepts": [
    "residence.registration",
    "residence.registration_deadline"
  ],
  "applicability": {
    "destination_canton": "CH-ZH"
  },
  "content": "original supporting passage",
  "canonical_url": "...",
  "retrieved_at": "..."
}
```

Every Evidence Object must trace to an immutable source snapshot.

## 8.2 KnowledgeRelease

```json
{
  "knowledge_space": "swiss-public",
  "release": "2026.09.04.3",
  "source_versions": {
    "sem-working-switzerland": 17,
    "zh-arriving": 22
  },
  "evidence_count": 143,
  "evaluation": {"total": 84, "passed": 84},
  "status": "PUBLISHED"
}
```

## 8.3 TrustEnvelope

```json
{
  "information_class": "AUTHORITATIVE",
  "confidence": 0.98,
  "knowledge_release": "swiss-public@2026.09.04.3",
  "applicability": {"jurisdiction": "CH-ZH"},
  "last_verified": "...",
  "sources": [
    {"authority": "State Secretariat for Migration", "source_id": "sem-working-switzerland"},
    {"authority": "Canton Zurich", "source_id": "zh-arriving"}
  ],
  "limitations": []
}
```

---

# 9. Module A — Domain Configuration & Contracts

**Owner:** one developer/workstream.

Responsibilities:

- shared schemas;
- Swiss Public domain configuration;
- source definitions;
- concept vocabulary;
- applicability dimensions;
- fixtures for all downstream modules.

Example concepts:

```text
residence.registration
residence.registration_deadline
residence.permit
employment.start
health.insurance
```

Other teams must be able to develop entirely from fixtures before the real ingestion pipeline is ready.

---

# 10. Module B — Source Acquisition & Ingestion

**Responsibility:** discover, retrieve, version and normalize trusted source content.

Components:

```text
Source Registry
Scanner
Crawler
Scheduler
Fetcher
Snapshot Manager
Change Detector
Normalizer
```

## 10.1 Source Registry

Example:

```yaml
sources:
  - id: sem-working-switzerland
    publisher: State Secretariat for Migration
    canonical_url: https://www.sem.admin.ch/sem/en/home/overview-arbeit.html
    authority_level: federal
    jurisdiction: CH
    trust: authoritative
    topics: [employment, migration, residence]
    refresh_policy:
      mode: change_detection
      fallback_interval: 24h

  - id: zh-arriving
    publisher: Canton Zurich
    canonical_url: https://www.zh.ch/de/migration-integration/willkommen/english/arriving.html
    authority_level: cantonal
    jurisdiction: CH-ZH
    trust: authoritative
    topics: [residence, moving, registration, health-insurance]
    refresh_policy:
      mode: change_detection
      fallback_interval: 24h
```

## 10.2 Scanner

Discovers candidate resources using sitemaps, links, feeds, known APIs and manually registered pages. It does not automatically download every discovered page.

## 10.3 Crawler

Traverses only approved scopes:

```yaml
discovery:
  follow_links: true
  max_depth: 3
include:
  - "/migration-integration/**"
exclude:
  - "/search/**"
  - "/news/**"
  - "*.jpg"
  - "*.zip"
```

AI may suggest candidate sources but must never silently promote an external domain to authoritative status.

## 10.4 Fetcher

Handles HTTP requests, redirects, retries, timeouts, rate limits, content type, ETag and Last-Modified.

## 10.5 Snapshot Manager

Stores raw HTML/PDF/JSON immutably. Metadata belongs in PostgreSQL; raw bytes belong in object/file storage.

Raw versions support audit, historical queries, rebuilds, semantic diff, rollback and future model upgrades.

## 10.6 Change Detection

Use the cheapest mechanism first:

```text
ETag / Last-Modified
        ↓
raw content hash
        ↓
normalized content hash
        ↓
structural/text diff
        ↓
Apertus semantic analysis
```

Unchanged normalized content produces zero Apertus calls and zero recompilation.

## 10.7 Acquisition States

```text
DISCOVERED → ELIGIBLE → FETCHED → SNAPSHOTTED
           → NORMALIZED → READY_FOR_COMPILATION
```

Exception states:

```text
IGNORED
FETCH_FAILED
PARSE_FAILED
REVIEW_REQUIRED
REJECTED
```

---

# 11. Module C — Knowledge Compiler & Apertus Enrichment

Responsibilities:

- document classification;
- concept extraction;
- applicability extraction;
- multilingual terminology mapping;
- authority/source relationship analysis;
- Evidence Object compilation;
- semantic change analysis;
- candidate evaluation generation.

Apertus is not authoritative. It enriches and interprets content while preserving the exact source evidence.

Deterministic extraction should validate high-risk values such as dates and numeric thresholds where practical.

Example semantic change:

```json
{
  "change_type": "SUBSTANTIVE",
  "affected_concepts": ["residence.registration_deadline"],
  "old_value": {"value": 14, "unit": "days"},
  "new_value": {"value": 8, "unit": "days"},
  "impact": "HIGH"
}
```

---

# 12. Module D — Storage, Indexing & Retrieval

Recommended hackathon storage:

```text
PostgreSQL
  sources
  source_versions
  documents
  evidence
  concepts
  relationships
  knowledge_releases
  evaluations

pgvector              semantic retrieval
PostgreSQL FTS        lexical retrieval
MinIO/filesystem      immutable raw snapshots
Redis (optional)      hot/live cache
```

Retrieval pipeline:

```text
Applicability filter
        ↓
Authority / jurisdiction filter
        ↓
Lexical + vector retrieval
        ↓
Merge / rerank
        ↓
1–5 Evidence Objects
```

Internal retrieval contract:

```text
retrieve(query, concepts, jurisdiction,
         applicability, release, limit)
```

---

# 13. Module E — Trusted Information Runtime

Responsibilities:

- MCP endpoint;
- REST endpoint;
- query/applicability interpretation;
- retrieval orchestration;
- Trust Envelope generation;
- coverage/unsupported handling;
- compact response construction.

Runtime must normally access only a published Knowledge Release, not upstream government websites.

Supported statuses:

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

# 14. MCP Contract

Recommended MVP tools:

## `swiss_information.resolve`

Primary high-level tool. It should internally perform most retrieval so the agent usually needs one MCP call.

Example input:

```json
{
  "question": "I am an EU citizen moving to Zurich for work. What do I need to do after arrival?",
  "language": "en",
  "context": {}
}
```

Example output:

```json
{
  "status": "SUPPORTED",
  "applicability": {"jurisdiction": "CH-ZH"},
  "evidence": ["ev-sem-registration-17", "ev-zh-registration-22"],
  "trust": {
    "knowledge_release": "swiss-public@2026.09.04.3",
    "confidence": 0.98
  }
}
```

## `swiss_information.get_evidence`

Fetch expanded evidence by ID when required.

## `swiss_information.get_coverage`

Describe supported jurisdictions/topics and help the