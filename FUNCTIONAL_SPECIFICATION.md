# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V3

**Working product name:** Swisscom Trusted Information Platform  
**Generic platform name:** Trusted Information Platform (TIP)  
**Hackathon domain:** Swiss Public Information  
**Primary demo sources:** Swiss Confederation / admin.ch ecosystem and Canton Zurich / zh.ch  
**Primary hackathon integration:** MCP  
**Additional target interfaces:** REST API, SDK, Webhooks  
**Primary Swisscom semantic model:** Apertus  
**Deployment model:** Headless platform; SaaS/private SaaS/on-prem capable

---

# 1. Executive Summary

Swisscom Trusted Information Platform is a headless platform that converts authoritative information, live data, enterprise data and digital services into trustworthy, structured Information Products consumable by applications.

It is explicitly **not a chatbot**. Applications consume structured APIs or MCP tools and receive typed results containing facts, evidence, applicability, provenance, freshness, confidence and limitations.

> **AI is infrastructure, not the interface.**

The first implementation addresses the hackathon challenge: make authoritative Swiss public information effectively accessible to AI systems.

The main demonstration uses real federal and Canton Zurich information to show the complete lifecycle:

```text
admin.ch / zh.ch
       ↓
source registration
       ↓
ingestion
       ↓
local versioned storage
       ↓
knowledge compilation
       ↓
Apertus enrichment
       ↓
tests
       ↓
published Knowledge Space
       ↓
MCP / REST
       ↓
AI client / structured application
```

When an authoritative source changes, the platform detects the change, determines whether it is semantically meaningful, rebuilds affected knowledge, reruns evaluations and publishes a new immutable version.

The same architecture can subsequently support Swiss Hiking, Swiss Cycling, Swiss Photo Scout, Swiss Housing, FINMA, EMIR, DORA, UBS internal policies and Swiss Re regulatory knowledge without redesigning the core platform.

---

# 2. Product Vision

The platform answers:

> **When an application needs information, what source should it trust, how should that source be accessed, how current is it, where does it apply, and how can the result be verified?**

```text
                         APPLICATIONS

       myAI   Mobile App   eGov   Bank Portal   Agent
          \       |         |         |          /
                 MCP / REST / SDK
                       │
                       ▼
        ┌───────────────────────────────┐
        │ TRUSTED INFORMATION PLATFORM │
        │ Knowledge                     │
        │ Live capabilities             │
        │ Context                       │
        │ Rules                         │
        │ Recommendations               │
        │ Trust                         │
        └───────────────┬───────────────┘
                        │
          ┌─────────────┼───────────────┐
          ▼             ▼               ▼
     Knowledge       Live APIs       Private data
          │             │               │
          └─────────────┼───────────────┘
                        ▼
                     Apertus
               where semantically useful
                        │
                        ▼
                STRUCTURED RESULT
```

---

# 3. Core Product Principles

1. **Stable information is compiled.** Laws, government guidance, regulatory requirements, administrative procedures and enterprise policies are fetched before runtime, stored, normalized, enriched, indexed, tested and versioned.
2. **Live information is retrieved at runtime.** Train fares, weather, disruptions, availability and similar volatile facts use registered live Capabilities.
3. **The external authority remains canonical.** Local storage is a verified, versioned operational representation of the source, not a replacement authority.
4. **Deterministic logic handles deterministic problems.** Hashes, dates, numeric constraints, HTTP state and jurisdiction filters should not depend on an LLM.
5. **Apertus handles semantic uncertainty.** Classification, concept extraction, multilingual mapping, semantic changes and explanations are appropriate AI tasks.
6. **Autonomous by default, human review by exception.**
7. **Structured output before generated prose.**
8. **Every result communicates its epistemic status through a Trust Envelope.**
9. **Model-independent core, Apertus-first Swisscom deployment.**

---

# 4. Information Classes

| Class | Example | Default strategy |
|---|---|---|
| AUTHORITATIVE | What are the residence-registration requirements? | Compiled Knowledge Space |
| LIVE | What does this train cost tomorrow? | Live Capability |
| PRIVATE | Does my lease permit cats? | Private Knowledge Space |
| CONSENSUS | What are good first-date locations? | Discovery/recommendation sources |
| DERIVED | Which hike best fits tomorrow's conditions? | Knowledge + capabilities + rules |
| HISTORICAL | What rule applied in 2024? | Versioned source repository |

A single Information Product may combine several classes.

---

# 5. Main Hackathon Demo Scenario

The primary demo scenario is:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

The scenario deliberately combines federal and cantonal information. Federal migration guidance supplies national work/residence context, while Canton Zurich supplies cantonal arrival and registration guidance.

```text
Swiss Confederation
       │
       ▼
State Secretariat for Migration
       │ federal rule/context
       ▼
Canton Zurich
       │ cantonal implementation/guidance
       ▼
Municipality
```

The demo showcases federal versus cantonal jurisdiction, authority relationships, corroborating evidence, applicability, multilingual content, versioning and autonomous maintenance.

Golden demo queries should include:

- Direct: “I moved to Zurich yesterday. When must I register?”
- Contextual: “I'm an EU citizen moving to Zurich to start a job. What do I need to do after arrival?”
- Jurisdictional: “Does the Canton Zurich guidance apply if I move to Geneva?”
- Temporal: “What did the source say before its most recent update?”
- Multilingual: “Ich ziehe nach Zürich. Wie lange habe ich Zeit, mich anzumelden?”
- Unsupported: an exact municipal fee that has not been ingested.

---

# 6. Top-Level Architecture

The platform consists of four primary subsystems plus a Control Plane.

```text
┌───────────────────────────────────────────────────────┐
│ 1. SOURCE ACQUISITION & INGESTION                    │
│ Registry → Scan → Crawl → Fetch → Snapshot → Normalize│
└─────────────────────────┬─────────────────────────────┘
                          ▼
┌───────────────────────────────────────────────────────┐
│ 2. KNOWLEDGE COMPILATION & CI/CD                     │
│ Enrich → Evidence → Index → Evaluate → Release        │
└─────────────────────────┬─────────────────────────────┘
                          ▼
┌───────────────────────────────────────────────────────┐
│ 3. TRUSTED INFORMATION RUNTIME                       │
│ Retrieve → Apply → Rank → Trust Envelope → Result     │
└─────────────────────────┬─────────────────────────────┘
                          ▼
┌───────────────────────────────────────────────────────┐
│ 4. INFORMATION PRODUCT & INTEGRATION LAYER           │
│ MCP │ REST │ SDK │ Structured Applications │ Events   │
└───────────────────────────────────────────────────────┘

                ┌──────────────────────┐
                │ ADMIN CONTROL PLANE  │
                │ observes & controls  │
                │ subsystems 1–4       │
                └──────────────────────┘
```

The Admin Control Plane is separate from end-user applications and must not be required for runtime availability.

---

# 7. Hackathon Deployment Principle

Module boundaries are logical, not mandatory microservice boundaries. For a two-day hackathon use a modular monorepo with a few runnable processes:

```text
Process 1: API + MCP Runtime
Process 2: Knowledge Worker (scanner/crawler/ingestion/compiler)
Process 3: Admin Backend
Process 4: Admin Web UI
Storage: PostgreSQL + pgvector + MinIO/local object storage
```

This permits parallel development without introducing unnecessary distributed-system complexity.

---

# 8. Shared Contract Layer

The first integration artifact is `/contracts`. All modules depend on stable shared schemas.

Primary contracts:

- `SourceDefinition`
- `SourceSnapshot`
- `NormalizedDocument`
- `EvidenceObject`
- `SemanticChange`
- `KnowledgeRelease`
- `TrustEnvelope`
- `InformationProductRequest`
- `InformationProductResult`

Use JSON Schema or Pydantic models and commit fixtures early so downstream teams can develop without waiting for upstream modules.

## 8.1 SourceDefinition

```json
{
  "source_id": "sem-working-switzerland",
  "publisher": "State Secretariat for Migration",
  "canonical_url": "https://www.sem.admin.ch/sem/en/home/overview-arbeit.html",
  "authority": {
    "level": "federal",
    "jurisdiction": "CH",
    "trust": "AUTHORITATIVE"
  },
  "topics": ["migration", "employment", "residence"],
  "discovery": {"follow_links": true, "max_depth": 2},
  "refresh": {"strategy": "CHANGE_DETECTION"}
}
```

## 8.2 SourceSnapshot

```json
{
  "snapshot_id": "snap-123",
  "source_id": "sem-working-switzerland",
  "retrieved_at": "2026-09-04T08:30:00Z",
  "content_type": "text/html",
  "etag": "...",
  "last_modified": "...",
  "content_hash": "sha256:...",
  "storage_uri": "sources/sem-working-switzerland/17/raw.html"
}
```

Snapshots are immutable.

## 8.3 NormalizedDocument

```json
{
  "document_id": "sem-working-switzerland:v17",
  "source_snapshot": "snap-123",
  "title": "Working in Switzerland",
  "language": "en",
  "sections": [
    {"id": "eu-efta-work", "heading": "...", "text": "..."}
  ]
}
```

## 8.4 EvidenceObject

```json
{
  "evidence_id": "ev-sem-registration-17",
  "source_id": "sem-working-switzerland",
  "source_version": 17,
  "authority": {
    "publisher": "State Secretariat for Migration",
    "level": "federal"
  },
  "jurisdiction": "CH",
  "concepts": ["residence.registration", "residence.registration_deadline"],
  "applicability": {
    "nationality_group": "EU_EFTA",
    "purpose": "employment"
  },
  "content": "...original supporting passage...",
  "canonical_url": "...",
  "retrieved_at": "..."
}
```

An Evidence Object must be traceable to an exact source snapshot.

## 8.5 KnowledgeRelease

```json
{
  "knowledge_space": "swiss-public",
  "release": "2026.09.04.3",
  "created_at": "...",
  "source_versions": {
    "sem-working-switzerland": 17,
    "zh-arriving": 22
  },
  "evidence_count": 143,
  "evaluation": {"total": 84, "passed": 84},
  "status": "PUBLISHED"
}
```

## 8.6 TrustEnvelope

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

# 9. Module A — Domain Configuration & Shared Contracts

**Responsibility:** define the common domain model and Swiss Public configuration.

Owned components:

```text
/contracts
/domains/swiss-public
```

Deliverables:

- shared schemas;
- source configuration format;
- concept identifiers;
- applicability vocabulary;
- Swiss Public domain definition;
- realistic fixtures.

Example concepts:

```text
residence.registration
residence.registration_deadline
residence.permit
employment.start
health.insurance
```

The module must provide fixtures immediately so Runtime, Retrieval and Admin teams can work before the crawler is complete.

---

# 10. Module B — Source Acquisition & Ingestion

**Responsibility:** discover, retrieve, version and normalize trusted source content.

Components:

- Source Registry
- Scanner
- Crawler
- Scheduler
- Fetcher
- Snapshot Manager
- Change Detector
- Normalizer

## 10.1 Source Registry

Stores trusted roots, authority metadata, jurisdiction, crawl policy and refresh policy.

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

  - id: zh-new-arrival
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

Determines what content exists within a trusted source using sitemap discovery, HTML links, RSS/Atom, known APIs and manual registration.

The Scanner discovers resources but does not necessarily download every page.

## 10.3 Crawler

Traverses approved source relationships under explicit scope rules.

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

The platform must not blindly download all of `zh.ch`.

## 10.4 Fetcher

Handles HTTP requests, timeouts, retries, rate limits, redirects, content types, ETag and Last-Modified.

## 10.5 Snapshot Manager

Stores immutable raw versions in object/file storage and metadata in PostgreSQL.

```text
sources/
  sem-working-switzerland/
     001/raw.html
     002/raw.html
  zh-arriving/
     001/raw.html
     002/raw.html
```

Raw snapshots enable audit, historical queries, semantic diff, rebuilds, model upgrades and rollback.

## 10.6 Change Detector

Use cheap deterministic checks before AI:

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

If normalized content is unchanged: zero Apertus calls and zero recompilation.

## 10.7 Normalizer

Converts source-specific content into `NormalizedDocument`, removing navigation, cookie banners, repeated page furniture and tracking while preserving headings, lists, tables, meaningful links and language.

## 10.8 Acquisition State Machine

```text
DISCOVERED
    ↓
ELIGIBLE
    ↓
FETCHED
    ↓
SNAPSHOTTED
    ↓
NORMALIZED
    ↓
READY_FOR_COMPILATION
```

Exception states:

```text
IGNORED
FETCH_FAILED
PARSE_FAILED
REVIEW_REQUIRED
REJECTED
```

The Admin GUI exposes these states.

---

# 11. Module C — Knowledge Compiler & Apertus Enrichment

**Responsibility:** transform normalized documents into retrieval-ready knowledge.

Components:

- document classifier;
- concept extractor;
- applicability extractor