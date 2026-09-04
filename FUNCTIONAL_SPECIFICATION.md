# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V9

**Hackathon domain:** Swiss Public Information  
**Primary sources:** admin.ch/SEM + zh.ch  
**Reference MCP client:** OpenCode  
**Structured reference app:** Swiss Arrival Checklist  
**Stretch app:** Swiss Hike (Flutter, DEMO/MOCK data)  
**Primary Swisscom semantic model:** Apertus

---

# 1. Summary

TIP is a headless platform that converts authoritative knowledge, live data, private context and digital services into trustworthy structured Information Products for applications and AI agents.

> **AI is infrastructure, not the interface.**

The hackathon MVP performs an **on-demand full build** of selected admin.ch/SEM and zh.ch content: acquire → snapshot → normalize → enrich → compile Evidence Objects → index → evaluate → publish immutable Knowledge Release. Runtime serves the published release locally through MCP/REST.

The full product adds two major capabilities that are deliberately **excluded from the hackathon MVP**:

1. autonomous/scheduled incremental Knowledge CI/CD;
2. a multi-tenant **Publisher & Data Product Marketplace** with licensing, entitlements, usage metering, billing and publisher settlement.

---

# 2. Product Vision

TIP answers:

> **What information should an application trust, where should it obtain it, where does it apply, how current is it, and under what entitlement/commercial terms may it be consumed?**

```text
Applications: myAI │ Mobile │ eGov │ Bank Portal │ Agents
                         │
                    MCP / REST / SDK
                         │
                         ▼
             TRUSTED INFORMATION PLATFORM
       Knowledge │ Live │ Context │ Rules │ Trust
       Entitlements │ Metering │ Information Products
                         │
          Data Products / Capabilities / Private Data
                         │
                      Apertus
                         │
                  Structured Result
```

---

# 3. Core Principles

1. Stable authoritative information is compiled ahead of runtime.
2. Inherently live information uses registered Capabilities.
3. External publishers remain canonical authorities for their data.
4. Deterministic logic handles deterministic problems.
5. Apertus handles semantic uncertainty.
6. Search returns evidence, not answers.
7. Runtime uses minimum sufficient evidence, normally 2–5 objects.
8. Structured output precedes optional prose generation.
9. Every result includes a Trust Envelope.
10. MCP is an integration protocol, not the product architecture.
11. Publisher licensing/entitlements are first-class in the full platform.
12. Marketplace and autonomous refresh are post-MVP capabilities.

---

# 4. Information Classes

| Class | Example | Strategy |
|---|---|---|
| AUTHORITATIVE | Residence-registration rules | Compiled Knowledge Space |
| LIVE | Train fare/weather | Live Capability |
| PRIVATE | Lease/company policy | Private Knowledge Space |
| CONSENSUS | First-date recommendations | Discovery/recommendation data |
| DERIVED | Best hike tomorrow | Data + capabilities + constraints/ranking |
| HISTORICAL | Rule applicable in 2024 | Versioned repository |

---

# 5. Platform Artifacts

## Knowledge Space
Internal compiled representation: sources, snapshots, evidence, concepts, indexes, versions and tests. Examples: `swiss-public`, `emir-core`, `finma`.

## Data Product
Distributable and optionally commercial publisher artifact containing Knowledge Spaces, structured datasets and/or Capabilities plus metadata, coverage, license, entitlements and commercial terms. Examples: `Swiss Public Official`, `Swiss Hiking Routes Pro`, `SIX Market Data`, `Alpine Photo Locations`.

## Information Product
Application-level capability combining typed inputs, Knowledge Spaces/Data Products, Capabilities, deterministic rules, optional AI and typed output. Examples: `swiss-arrival-checklist`, `swiss-hike-finder`, `emir-applicability`.

```text
Publisher → Data Product ─┐
Publisher → Capability ───┼→ Information Product → Application
Private Knowledge ────────┘
```

---

# 6. Main Hackathon Scenario

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation → SEM/federal context
                           ↓
                    Canton Zurich
                           ↓
                 municipality/context
```

Golden tests cover factual grounding, federal/cantonal applicability, German queries, unsupported municipal details, citations, response size, tool calls and latency.

---

# 7. Architecture

```text
CONTROL PLANE
Admin GUI
  ↓
Source Registry → Scan/Crawl/Fetch → Snapshot/Normalize
  ↓
Apertus Enrichment → Evidence Compile → Index/Test → Release

DATA PLANE
Published Knowledge Release
  ↓
Query Planner → Retrieval/Capabilities → Evidence & Rules → Result
  ↓
MCP / REST / SDK
  ↓
OpenCode │ Arrival Checklist │ Swiss Hike │ Other Apps
```

---

# 8. Hackathon Scope

## Required MVP

- configured admin.ch/SEM + zh.ch scope;
- scanner/crawler/fetcher;
- **manual/on-demand full reload only**;
- immutable snapshots and normalized documents;
- Apertus enrichment where useful;
- Evidence Objects and candidate facts;
- PostgreSQL FTS + pgvector retrieval;
- evaluation gate + immutable Knowledge Release;
- MCP + REST;
- OpenCode integration;
- Admin Control Plane;
- Swiss Arrival Checklist;
- explicit unsupported/conflicting states.

## Stretch

- Flutter Swiss Hike;
- 10–20 DEMO/MOCK routes;
- MockTransportProvider, MockWeatherProvider, MockPlacesProvider;
- typed REST request/result;
- deterministic hard filters + optional soft ranking.

## Explicitly excluded from MVP

- scheduler / periodic watcher;
- incremental refresh / semantic-change promotion;
- autonomous Knowledge CI/CD;
- publisher self-service onboarding;
- marketplace UI/discovery;
- commercial pricing/billing/metering/settlement;
- real publisher payouts;
- production licensing/entitlement engine;
- real SBB/weather/places integrations.

---

# 9. Shared Contracts

Core contracts:

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

Roadmap-compatible contracts should also be reserved:

```text
Publisher
DataProductDefinition
LicensePolicy
Entitlement
UsageRecord
PricingModel
SettlementRecord
```

These commercial contracts may be schemas only during the hackathon.

---

# 10. Source Acquisition & Build

MVP operator action:

```text
[ BUILD / FULL RELOAD ]
```

Flow:

```text
configured source scope
  ↓
scan/crawl/fetch
  ↓
immutable raw snapshots
  ↓
normalize
  ↓
Apertus enrichment
  ↓
Evidence Objects / candidate facts
  ↓
index
  ↓
golden evaluations
  ↓
publish immutable release
```

No scheduler is required. Full-product roadmap adds cheap revalidation, source watching, semantic diff and incremental builds.

---

# 11. Storage & Retrieval

MVP stack:

```text
PostgreSQL        metadata/evidence/facts/releases/tests
pgvector          semantic retrieval
PostgreSQL FTS    lexical retrieval
MinIO/filesystem  immutable source snapshots
```

Retrieval:

```text
Published Release
  ↓
validity + jurisdiction + applicability + authority filters
  ↓
lexical + vector + concept search
  ↓
merge/rerank
  ↓
diversity-aware selection
  ↓
2–5 Evidence Objects
```

Ranking combines semantic/lexical relevance with concept match, authority, jurisdiction specificity, applicability and temporal validity.

---

# 12. Runtime Processing

```text
REQUEST
  ↓
Query Planner
  ↓
Retrieval / Capability Engine
  ↓
Evidence & Rule Engine
  ↓
Result Assembler
```

Natural-language MCP requests may use Apertus to derive an `ExecutionPlan`. Structured apps normally skip that step.

The Evidence & Rule Engine groups facts by concept, combines corroborating evidence, recognizes federal/cantonal specialization, applies deterministic rules and exposes unresolved contradictions.

Statuses:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
```

Optional prose is generated only after evidence/facts are established.

---

# 13. MCP & OpenCode

MVP tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

OpenCode is the reference MCP client. The main query should normally require one high-level `resolve` call and return compact evidence plus Trust Envelope.

---

# 14. Admin Control Plane

MVP screens:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Full-build status
5. Source snapshots
6. Evidence Explorer
7. Evaluations
8. Knowledge Releases
9. MCP/REST integration status

Scheduled-refresh/change-review screens are post-MVP.

---

# 15. Swiss Arrival Checklist

Formal fields: nationality group, purpose, duration, canton/municipality, arrival date, work start date.

The app calls REST and receives typed requirements, deadlines, evidence IDs and Trust Envelope. No natural-language prompt is required.

---

# 16. Swiss Hike Stretch Demo

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
              preference ranking
                    ↓
              typed route cards
```

Suggested files:

```text
demo/hiking/routes.json
demo/hiking/transport.json
demo/hiking/weather.json
demo/hiking/restaurants.json
```

All mock data must be labelled `DEMO/MOCK`.

---

# 17. Full Product — Autonomous Knowledge CI/CD (Post-MVP)

Production evolution:

```text
Scheduler / Source Watcher
  ↓
ETag/Last-Modified/hash revalidation
  ↓
semantic analysis only when needed
  ↓
affected evidence/dependencies
  ↓
incremental build + tests
  ↓
autonomous or approval-based promotion
```

This remains a key differentiator but is not required in two days.

---

# 18. Full Product — Publisher & Data Product Marketplace (Post-MVP)

## 18.1 Business Model

TIP is a multi-sided platform:

```text
Consumers / Apps / Enterprises
             │ pay / consume
             ▼
        SWISSCOM TIP
 hosting │ trust │ distribution │ metering │ billing
             │
        settlement / licensing
             ▼
Publishers / Data Providers
Government │ SIX-like providers │ Companies │ Experts │ Individuals
```

Swisscom can monetize platform requests directly while also compensating publishers whose Data Products contribute to those requests.

## 18.2 Publisher Self-Service

Future publishers can create a tenant/account, register Data Products, connect/upload sources, configure maintenance, define coverage, license and pricing, publish versions, and inspect usage/revenue. Public marketplace publication may require Swisscom certification.

## 18.3 Commercial Models

TIP should support multiple models:

- **Usage/revenue share:** consumer/tenant pays per request or unit; Swisscom retains margin and pays publisher share.
- **Monthly/annual license:** Swisscom licenses a pack and bundles/resells access.
- **One-time license/acquisition:** Swisscom purchases defined rights/version for a one-time payment.
- **Publisher SaaS:** publisher pays Swisscom hosting/platform fees and decides whether its product is free or paid.
- **Free/open product:** government/open-data product is free; Swisscom monetizes hosting, SLA, API use, inference, enterprise overlays and derived products.

## 18.4 Licensing & Entitlements

Before using a commercial Data Product, TIP must verify that the consuming tenant is entitled to it. Policies may restrict tenants, applications, geography, purpose, redistribution, retention, volume or time period.

This is particularly important for professional financial-data providers and enterprise/private packs.

## 18.5 Metering & Settlement

Every commercial execution eventually creates a `UsageRecord` identifying consumer, Information Product, Data Products/Capabilities used, units, publisher cost, platform fee and model/provider costs.

A Commercial Control Plane will support:

```text
usage metering
consumer billing
publisher settlement
cost attribution
margin analysis
entitlement audit
revenue reporting
```

## 18.6 Trust / Certification

Potential marketplace levels:

```text
COMMUNITY
VERIFIED
EXPERT VERIFIED
OFFICIAL
```

Trust certification is separate from commercial pricing: a free government pack may be OFFICIAL, while a paid expert pack may be EXPERT VERIFIED.

---

# 19. Example Marketplace Composition — Swiss Hike

Future production version:

```text
Swiss Hiking Routes Data Product      publisher A
Weather Capability/Data Product       publisher B
Transport Capability                  provider C
Places/Restaurants Product            provider D
                    ↓
             Swiss Hike Finder
                    ↓
             Flutter / myAI / web
```

A single end-user request can generate usage for several providers. TIP meters the dependency graph and applies the configured commercial model to each component.

For the hackathon this is simulated only by free `DEMO/MOCK` providers; there is no billing or settlement implementation.

---

# 20. Swisscom Alignment & Economics

TIP can strengthen:

- **myAI:** richer trusted Swiss information and capabilities;
- **eGovHub:** AI-ready government Data Products;
- **Swiss AI Platform/Apertus:** increased inference/platform consumption;
- **Banking:** FINMA/EMIR/regulatory Information Products;
- **Enterprise:** private Data Products and Knowledge Spaces;
- **Marketplace:** new distribution and monetization channel for trusted data providers.

Swisscom can earn through API/MCP usage, SaaS subscriptions, hosting, managed knowledge, enterprise deployments, regulatory intelligence, inference consumption and marketplace/platform margin.

Publishers gain a new machine-consumption distribution channel and can monetize expertise/data without building their own AI application platform.

---

# 21. Reuse for UBS / Swiss Re

Replace Swiss public sources with regulation and private policy while retaining the same primitives:

```text
EMIR / FINMA / DORA
      +
company policies / procedures
      +
transaction/product context
      ↓
Information Product
      ↓
portal / workflow / agent
```

Commercial third-party regulatory or market Data Products can be licensed through the same entitlement/metering layer in the full platform.

---

# 22. Hackathon Workstreams

| Workstream | Scope |
|---|---|
| A | Contracts + Swiss domain config |
| B | Scanner/crawler/fetcher/normalizer |
| C | Apertus enrichment + evidence compiler |
| D | PostgreSQL/pgvector retrieval |
| E | Runtime + MCP/REST + OpenCode |
| F | Admin Control Plane |
| G | Evaluation + Arrival Checklist; Hike stretch |

No workstream is required for scheduler/refresh automation or marketplace billing during the MVP.

---

# 23. Definition of Done

The MVP is complete when Swisscom can clone/start the repository, run an on-demand full build of configured admin.ch/SEM + zh.ch sources, inspect snapshots/evidence/tests/releases, connect OpenCode, obtain grounded cited results, see explicit unsupported/conflicting states, and use the same release through the structured Arrival Checklist.

Stretch: Flutter Swiss Hike demonstrates a different typed Information Product using clearly labelled mock providers.

---

# 24. Roadmap

```text
Phase 1  Hackathon: on-demand Swiss Public build + MCP/REST
Phase 2  production hardening + broader Swiss coverage
Phase 3  scheduled/incremental Knowledge CI/CD
Phase 4  live Capabilities + consumer Information Products
Phase 5  enterprise/private overlays
Phase 6  Publisher/Data Product self-service + entitlements
Phase 7  metering, billing, settlement + marketplace
Phase 8  regulatory impact + actions/workflows
```

---

# 25. Final Positioning

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context, entitlement and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

The hackathon