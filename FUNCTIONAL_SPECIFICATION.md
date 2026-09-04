# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V10

**Hackathon:** Swiss Public Information using admin.ch/SEM + zh.ch  
**Reference MCP client:** OpenCode  
**Structured app:** Swiss Arrival Checklist  
**Stretch app:** Swiss Hike (Flutter, DEMO/MOCK providers)  
**Semantic model:** Apertus-first, model-independent core

---

# 1. Summary

TIP is a headless platform that converts authoritative knowledge, live data, private context and services into trustworthy structured Information Products for applications and AI agents.

> **AI is infrastructure, not the interface.**

Hackathon MVP: **on-demand full build** of selected official sources → immutable snapshots → normalized documents → Apertus enrichment → Evidence Objects → indexes/tests → immutable Knowledge Release → MCP/REST runtime.

Full product, explicitly **outside the MVP**, adds scheduled/incremental Knowledge CI/CD and a multi-tenant **Publisher & Data Product Marketplace** with licensing, entitlements, metering, billing and publisher settlement.

---

# 2. Product Model

## Knowledge Space
Internal compiled knowledge: sources, snapshots, evidence, concepts, indexes, versions and tests. Examples: `swiss-public`, `emir-core`, `finma`.

## Data Product
Distributable publisher artifact containing knowledge, datasets and/or Capabilities plus coverage, license, entitlement and commercial metadata. Examples: `Swiss Public Official`, `Swiss Hiking Routes Pro`, `SIX Market Data`, `Alpine Photo Locations`.

## Information Product
Application capability combining typed inputs, Knowledge Spaces/Data Products, Capabilities, deterministic rules, optional AI and typed output. Examples: `swiss-arrival-checklist`, `swiss-hike-finder`, `emir-applicability`.

```text
Publisher Data Products ─┐
Live Capabilities ───────┼→ Information Product → Any Application
Private Knowledge ───────┘
```

---

# 3. Core Principles

1. Stable authoritative information is compiled before runtime.
2. Inherently live information uses registered Capabilities.
3. External publishers remain canonical authorities.
4. Deterministic logic handles deterministic problems.
5. Apertus handles semantic uncertainty.
6. Search returns evidence, not answers.
7. Runtime normally uses 2–5 high-quality Evidence Objects.
8. Structured output precedes optional prose.
9. Every result carries a Trust Envelope.
10. MCP is an interface, not the product architecture.
11. Publisher licensing/entitlements are first-class in the full product.
12. Marketplace and autonomous refresh are post-MVP.

---

# 4. Information Classes

| Class | Example | Strategy |
|---|---|---|
| AUTHORITATIVE | Residence rules | Compiled Knowledge Space |
| LIVE | Train fare/weather | Live Capability |
| PRIVATE | Lease/company policy | Private Knowledge Space |
| CONSENSUS | First-date places | Recommendation data |
| DERIVED | Best hike tomorrow | Data + capabilities + constraints |
| HISTORICAL | Rule in 2024 | Versioned repository |

---

# 5. Hackathon Scenario

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation → SEM/federal context
                           ↓
                    Canton Zurich
                           ↓
                 municipality/context
```

The demo tests authority, federal/cantonal applicability, citations, unsupported handling, multilingual queries and efficient retrieval.

---

# 6. Architecture

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

The Admin GUI is not required for runtime availability.

---

# 7. Hackathon Scope

## Required

- configured admin.ch/SEM + zh.ch scope;
- scanner/crawler/fetcher;
- **manual/on-demand full reload only**;
- immutable source snapshots;
- normalization;
- Apertus enrichment where useful;
- Evidence Objects/candidate facts;
- PostgreSQL FTS + pgvector retrieval;
- golden evaluation gate;
- immutable Knowledge Release;
- MCP + REST;
- OpenCode integration;
- Admin Control Plane;
- Swiss Arrival Checklist;
- explicit unsupported/conflicting states.

## Stretch

- Flutter Swiss Hike;
- 10–20 DEMO/MOCK routes;
- mock transport/weather/places providers;
- deterministic filters + optional preference ranking.

## Explicitly excluded from MVP

```text
scheduler / periodic watcher
incremental refresh
semantic-change promotion
autonomous Knowledge CI/CD
publisher self-service onboarding
marketplace UI/discovery
pricing/billing/metering/settlement
publisher payouts
production entitlement engine
real SBB/weather/places integrations
```

---

# 8. Shared Contracts

MVP:

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

Roadmap-compatible schemas:

```text
Publisher
DataProductDefinition
LicensePolicy
Entitlement
UsageRecord
PricingModel
SettlementRecord
```

Commercial schemas need not have working implementations during the hackathon.

---

# 9. Source Acquisition & Build

MVP operator action:

```text
[ BUILD / FULL RELOAD ]
```

```text
configured sources
  ↓
scan/crawl/fetch
  ↓
immutable snapshots
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
publish immutable release
```

No scheduler is required. The full product later adds ETag/Last-Modified/hash revalidation, source watching, semantic diff and incremental builds.

---

# 10. Storage & Retrieval

Recommended MVP stack:

```text
PostgreSQL        metadata/evidence/facts/releases/tests
pgvector          semantic retrieval
PostgreSQL FTS    lexical retrieval
MinIO/filesystem  immutable raw snapshots
```

Retrieval applies hard filters before similarity search:

```text
Published Release
 ↓
validity + jurisdiction + applicability + authority
 ↓
lexical + vector + concept search
 ↓
merge/rerank/diversify
 ↓
2–5 Evidence Objects
```

Ranking includes semantic/lexical relevance, concept match, authority, jurisdiction specificity, applicability and temporal validity.

---

# 11. Runtime Processing

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

Natural-language MCP input may use Apertus to derive the `ExecutionPlan`. Structured apps normally skip that step.

The Evidence & Rule Engine combines corroborating sources, recognizes federal/cantonal specialization, applies deterministic rules and exposes unresolved contradictions.

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

Optional prose is generated only after facts/evidence are established.

---

# 12. MCP & OpenCode

MVP tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

OpenCode is the reference client. The normal demo query should use one high-level `resolve` call and return compact evidence plus Trust Envelope.

---

# 13. Admin Control Plane

Minimum MVP screens:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Full-build progress
5. Source snapshots
6. Evidence Explorer
7. Evaluations
8. Knowledge Releases
9. MCP/REST integration

Primary operation: **Build / Full Reload**. Scheduled refresh/change review is post-MVP.

---

# 14. Swiss Arrival Checklist

Formal inputs: nationality group, purpose, duration, canton/municipality, arrival date, work start date.

REST output: typed requirements, deadlines, evidence IDs and Trust Envelope. No chat prompt is required.

---

# 15. Swiss Hike Stretch Demo

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

Suggested files: `demo/hiking/routes.json`, `transport.json`, `weather.json`, `restaurants.json`. All mock data is visibly labelled `DEMO/MOCK`.

---

# 16. Full Product: Autonomous Knowledge CI/CD — Post-MVP

```text
Scheduler / Source Watcher
 ↓
cheap metadata/hash revalidation
 ↓
semantic analysis only when needed
 ↓
affected evidence/dependencies
 ↓
incremental build + tests
 ↓
autonomous or approval-based promotion
```

This remains a strategic differentiator, but is not a two-day requirement.

---

# 17. Full Product: Publisher & Data Product Marketplace — Post-MVP

TIP becomes a multi-sided platform:

```text
Consumers / Apps / Enterprises
             │ pay / consume
             ▼
        SWISSCOM TIP
 hosting │ trust │ distribution │ metering │ billing
             │
      licensing / settlement
             ▼
Publishers / Data Providers
Government │ SIX-like providers │ Companies │ Experts │ Individuals
```

## Publisher capabilities

Future publishers can register a tenant/account, create Data Products, connect/upload sources, define coverage and maintenance policy, configure licensing/pricing, publish versions and inspect usage/revenue. Public publication may require Swisscom review/certification.

## Commercial models

- **Usage/revenue share:** customer pays per request/unit; Swisscom retains margin and pays publisher share.
- **Monthly/annual license:** Swisscom licenses a pack and bundles/resells access.
- **One-time license:** Swisscom purchases defined data/version/usage rights once.
- **Publisher SaaS:** publisher pays Swisscom for hosting/distribution and sets its own free/paid policy.
- **Free/open:** government/open Data Product is free; Swisscom monetizes hosting, SLA, inference, enterprise overlays and derived Information Products.

## Licensing & entitlements

Before consuming a Data Product, TIP verifies entitlement. Policies can restrict tenant/application, purpose, geography, redistribution, retention, volume and contract period.

## Metering & settlement

Commercial executions create `UsageRecord`s identifying consumer, Information Product, Data Products/Capabilities used, units, publisher cost, platform fee and provider/model costs.

Future Commercial Control Plane:

```text
usage metering
consumer billing
publisher settlement
cost attribution
margin analysis
entitlement audit
revenue reporting
```

## Trust levels

```text
COMMUNITY
VERIFIED
EXPERT VERIFIED
OFFICIAL
```

Trust level is independent of price: an official government pack can be free; an expert pack can be paid.

---

# 18. Marketplace Example: Swiss Hike

Future production composition:

```text
Hiking Routes Data Product      Publisher A
Weather Data Product            Publisher B
Transport Capability            Provider C
Places Product                  Provider D
              ↓
       Swiss Hike Finder
              ↓
     Flutter / myAI / web
```

One request can consume several products. TIP meters the dependency graph and applies commercial rules. In the hackathon all hiking components remain free `DEMO/MOCK`; no billing is implemented.

---

# 19. Swisscom Alignment & Economics

TIP strengthens myAI, eGovHub, Swiss AI Platform/Apertus, banking services and enterprise AI.

Swisscom revenue can include API/MCP usage, SaaS, hosting, managed knowledge, enterprise deployments, regulatory intelligence, inference consumption and marketplace margin.

Publishers gain a machine-consumption distribution channel and can monetize trusted data/expertise without building their own AI platform.

---

# 20. Enterprise Reuse

For UBS/Swiss Re, replace Swiss sources with EMIR/FINMA/DORA plus internal policies and transaction/product context. The same platform can also govern licensed third-party market/regulatory Data Products through entitlement and metering in the full product.

---

# 21. Hackathon Workstreams

| Workstream | Scope |
|---|---|
| A | Contracts + Swiss domain config |
| B | Scanner/crawler/fetcher/normalizer |
| C | Apertus enrichment + evidence compiler |
| D | PostgreSQL/pgvector retrieval |
| E | Runtime + MCP/REST + OpenCode |
| F | Admin Control Plane |
| G | Evaluation + Arrival Checklist; Hike stretch |

No workstream is required for scheduler/refresh automation or marketplace billing.

---

# 22. Definition of Done

Swisscom can clone/start the repository, run an on-demand full build of configured admin.ch/SEM + zh.ch sources, inspect snapshots/evidence/tests/releases, connect OpenCode, obtain grounded cited results, see explicit unsupported/conflicting states, and consume the same release through the structured Arrival Checklist.

Stretch: Flutter Swiss Hike demonstrates another typed Information Product with clearly labelled mock providers.

---

# 23. Roadmap

```text
1  Hackathon: on-demand Swiss Public build + MCP/REST
2  production hardening + broader Swiss coverage
3  scheduled/incremental Knowledge CI/CD
4  live Capabilities + consumer Information Products
5  enterprise/private overlays
6  publisher self-service + Data Product entitlements
7  metering, billing, settlement + marketplace
8  regulatory impact + actions/workflows
```

---

# 24. Final Positioning

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context, entitlement and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

The hackathon proves the trusted-information foundation. Autonomous refresh and the publisher marketplace are the scalable product built on top of it.