# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V8

**Working product name:** Swisscom Trusted Information Platform (TIP)  
**Hackathon domain:** Swiss Public Information  
**Primary demo sources:** admin.ch ecosystem (including SEM) and zh.ch  
**Reference MCP client:** OpenCode  
**Reference structured app:** Swiss Arrival Checklist  
**Stretch app:** Swiss Hike — Flutter with DEMO/MOCK providers  
**Primary Swisscom semantic model:** Apertus  
**Deployment:** Headless; SaaS/private SaaS/on-prem capable

---

# 1. Executive Summary

TIP is a headless platform that converts authoritative knowledge, live data, private context and digital services into trustworthy structured Information Products consumable by applications and AI agents.

> **AI is infrastructure, not the interface.**

The hackathon MVP proves the core using selected admin.ch/SEM and zh.ch sources. It performs an **on-demand full build**: source acquisition, immutable snapshots, normalization, Apertus enrichment, Evidence Object compilation, indexing, evaluation and publication of a Knowledge Release. Runtime serves that release locally through MCP/REST rather than scraping government sites per request.

The full product extends this foundation with scheduled/incremental Knowledge CI/CD and a **Publisher & Data Product Marketplace**. Governments, exchanges/data providers, companies, associations and individual experts can publish governed Data Products, maintain them, define licensing and pricing, and receive compensation. Swisscom operates hosting, trust, distribution, metering, billing and settlement.

**The marketplace/commercial publisher functionality is explicitly NOT part of the hackathon MVP.** The MVP only keeps the architectural contracts compatible with it.

---

# 2. Product Vision

TIP answers:

> **When an application needs information, what should it trust, where should it obtain it, where does it apply, how current is it, and under what entitlement/commercial terms may it be consumed?**

```text
                         APPLICATIONS
 OpenCode/myAI │ Mobile │ eGov │ Bank Portal │ Enterprise Agent
                         │
                    MCP / REST / SDK
                         │
                         ▼
             TRUSTED INFORMATION PLATFORM
                         │
       Knowledge │ Live Data │ Context │ Rules
       Trust │ Entitlements │ Metering │ Actions
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Knowledge       Capabilities    Private data
     / Data Packs     / APIs          / policies
                         │
                      Apertus
                 where useful
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
6. Structured output precedes optional prose generation.
7. Search returns evidence, not answers.
8. Runtime uses minimum sufficient evidence, normally 2–5 objects.
9. Every result includes a Trust Envelope.
10. MCP is an integration protocol, not the product architecture.
11. The platform is model-independent, Apertus-first for Swisscom.
12. Publisher licensing/entitlements are first-class in the full platform.
13. Marketplace and autonomous refresh are roadmap/full-product capabilities, not MVP requirements.

---

# 4. Information Classes

| Class | Example | Strategy |
|---|---|---|
| AUTHORITATIVE | Residence-registration requirements | Compiled Knowledge Space |
| LIVE | Train fare tomorrow | Live Capability |
| PRIVATE | Does my lease allow cats? | Private Knowledge Space |
| CONSENSUS | Good first-date places | Discovery/recommendation data |
| DERIVED | Best hike tomorrow | Data + capabilities + constraints/ranking |
| HISTORICAL | Rule applicable in 2024 | Versioned source repository |

---

# 5. Platform Artifact Model

TIP distinguishes three important artifacts.

## 5.1 Knowledge Space

Internal technical representation of compiled knowledge: sources, snapshots, evidence, concepts, indexes, versions and tests.

Examples: `swiss-public`, `emir-core`, `finma`, `ubs-policy`.

## 5.2 Data Product

A distributable and optionally commercial artifact published by a provider. It may contain one or more Knowledge Spaces, structured datasets and/or Capabilities plus metadata, licensing and commercial terms.

Examples:

```text
Swiss Public Official
Swiss Hiking Routes Pro
SIX Market Data Product
Alpine Photo Locations
EMIR Expert Pack
```

## 5.3 Information Product

An application-level capability combining typed inputs, Knowledge Spaces/Data Products, Capabilities, rules, optional AI and typed output.

Examples: `swiss-arrival-checklist`, `swiss-hike-finder`, `emir-applicability`.

```text
Publisher → Data Product ─┐
Publisher → Capability ───┼→ Information Product → Application
Internal Knowledge ───────┘
```

---

# 6. Main Hackathon Scenario

Primary question:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation
       ↓
SEM / federal context
       ↓
Canton Zurich / cantonal guidance
       ↓
Municipality / user context
```

The demo proves authority, jurisdiction, applicability, citations, unsupported handling and local compiled retrieval.

---

# 7. Control Plane and Data Plane

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
Query Planner → Retrieval/Capabilities → Evidence & Rules → Result Assembler
  ↓
MCP / REST / SDK
  ↓
OpenCode │ Arrival Checklist │ Swiss Hike │ Other Apps
```

The Admin GUI is not required for runtime availability.

---

# 8. Hackathon Scope vs Full Product

## 8.1 Hackathon MVP — required

- configured admin.ch/SEM and zh.ch source scope;
- scanner/crawler/fetcher;
- **manual/on-demand full reload only**;
- immutable raw snapshots;
- normalization;
- Apertus semantic enrichment where useful;
- Evidence Objects;
- PostgreSQL full-text + pgvector retrieval;
- evaluation gate;
- immutable published Knowledge Release;
- MCP + REST runtime;
- OpenCode reference integration;
- Admin Control Plane;
- Swiss Arrival Checklist;
- explicit unsupported/conflicting states.

## 8.2 Hackathon stretch

- Flutter Swiss Hike;
- 10–20 DEMO/MOCK route records;
- MockTransportProvider, MockWeatherProvider, MockPlacesProvider;
- typed REST request/result;
- deterministic hard constraints and optional soft ranking.

## 8.3 Explicitly excluded from MVP

- scheduler;
- periodic source watcher;
- incremental refresh;
- automatic semantic-change promotion;
- autonomous Knowledge CI/CD;
- publisher self-service onboarding;
- Data Product marketplace UI;
- pricing/billing/metering/settlement;
- real publisher payouts;
- entitlement/licensing enforcement beyond basic tenant access;
- production SBB/weather/places integrations;
- marketplace discovery/rating/certification workflows.

These remain part of the full design and roadmap.

---

# 9. Shared Contracts

The `/contracts` package should define at least:

```text
SourceDefinition
DiscoveredResource
SourceSnapshot
NormalizedDocument
EvidenceObject
CandidateFact
SemanticChange
KnowledgeRelease
ExecutionPlan
EvidenceBundle
RetrievalResult
TrustEnvelope
CapabilityDefinition
DataProductDefinition        # roadmap-compatible
Entitlement                  # roadmap-compatible
UsageRecord                  # roadmap-compatible
InformationProductRequest
InformationProductResult
```

MVP implementations of `DataProductDefinition`, `Entitlement` and `UsageRecord` may be schemas/fixtures only; no commercial runtime is required.

---

# 10. Source Acquisition & Ingestion

Components:

```text
Source Registry
Scanner
Crawler
Fetcher
Snapshot Manager
Normalizer
```

For the MVP, the operator presses **Build / Full Reload**. The configured source scope is fetched and rebuilt from scratch into a candidate release.

Full-product roadmap adds Scheduler, Source Watcher, ETag/Last-Modified revalidation, content-hash diff, semantic diff and incremental compilation.

Acquisition states:

```text
DISCOVERED → ELIGIBLE → FETCHED → SNAPSHOTTED
           → NORMALIZED → READY_FOR_COMPILATION
```

Exceptions: `IGNORED`, `FETCH_FAILED`, `PARSE_FAILED`, `REVIEW_REQUIRED`, `REJECTED`.

---

# 11. Knowledge Compiler & Apertus

The compiler performs document classification, concept/applicability extraction, multilingual mapping, authority relationships, Evidence Object creation and candidate fact extraction.

Apertus is never treated as the authority. Exact evidence remains linked to immutable source snapshots.

Stable high-value facts such as deadlines, thresholds, effective dates and boolean obligations should be extracted at build time where practical, preserving evidence links.

---

# 12. Storage & Retrieval

Recommended MVP stack:

```text
PostgreSQL        metadata, sources, evidence, facts, releases, tests
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

Ranking combines relevance with authority, jurisdiction specificity, applicability and temporal validity.

---

# 13. Runtime Request Processing

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

Natural-language MCP input may use Apertus to derive an `ExecutionPlan`. Structured apps normally skip that step.

The Evidence & Rule Engine groups facts by concept, combines corroborating sources, recognizes federal/cantonal specialization, applies deterministic rules and exposes unresolved contradictions.

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

Optional prose is generated only after an Evidence Bundle has been established.

---

# 14. MCP & OpenCode

MVP tools:

- `swiss_information.resolve`
- `swiss_information.get_evidence`
- `swiss_information.get_coverage`

OpenCode is the reference MCP client. The core demo should make the `swiss_information.resolve` call visible and normally complete the request with one high-level tool call.

---

# 15. Admin Control Plane

Minimum MVP screens:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Scan/build status
5. Source detail / snapshots
6. Evidence Explorer
7. Evaluations
8. Knowledge Releases
9. MCP/REST integration status

MVP primary action:

```text
[ BUILD / FULL RELOAD ]
```

The UI shows progress from fetch through release publication. Scheduled refresh/change-review screens may be mocked or marked ROADMAP, but are not MVP requirements.

---

# 16. Evaluation & Release

```text
On-demand Full Build
       ↓
Candidate Knowledge Release
       ↓
Golden Evaluation Suite
       ↓
PASS → Publish immutable release
FAIL → Keep previous production release
```

Golden tests cover grounding, citations, jurisdiction, multilingual questions, unsupported cases, response size, tool count and latency.

---

# 17. Swiss Arrival Checklist

Formal inputs include nationality group, purpose, duration, destination canton/municipality, arrival date and work start date.

It calls TIP over REST and receives a typed checklist containing requirement status, deadlines, evidence IDs and Trust Envelope. No chat prompt is required.

---

# 18. Swiss Hike Flutter Stretch Demo

Use formal inputs: origin, date, target duration, difficulty, max travel time, scenery preferences, weather preference and restaurant requirement.

Mock architecture:

```text
Flutter
  ↓ REST
swiss-hike-finder
  ↓
DemoRouteRepository (10–20 routes)
MockTransportProvider
MockWeatherProvider
MockPlacesProvider
  ↓
hard filters
  ↓
soft preference ranking
  ↓
typed route cards
```

Files may include:

```text
demo/hiking/routes.json
demo/hiking/transport.json
demo/hiking/weather.json
demo/hiking/restaurants.json
```

All mock data must be visibly marked `DEMO/MOCK` and must not be presented as current authoritative data.

---

# 19. Full Product — Autonomous Knowledge CI/CD (Post-MVP)

Production evolution:

```text
Scheduler / Source Watcher
  ↓
cheap revalidation (ETag/Last-Modified/hash)
  ↓
semantic change analysis only when needed
  ↓
affected evidence / dependencies
  ↓
incremental build
  ↓
regression tests
  ↓
autonomous or approval-based promotion
```

Governance modes may include `AUTONOMOUS`, `AUTONOMOUS_WITH_AUDIT`, `APPROVAL_FOR_HIGH_RISK`, and `MANUAL`.

---

# 20. Full Product — Publisher & Data Product Marketplace (Post-MVP)

This is a strategic product capability and commercial model, **not a hackathon deliverable**.

## 20.1 Publisher Types

Potential publishers include:

- Swiss Confederation, cantons and municipalities;
- exchanges and commercial data providers such as SIX;
- tourism organizations;
- companies and industry associations;
- professional/legal/regulatory publishers;
- individual domain experts, e.g. hiking, cycling or photography specialists;
- enterprise tenants publishing private/internal packs.

## 20.2 Publisher Self-Service

Authorized publishers can eventually:

```text
create publisher account/tenant
register Data Product
upload/connect sources
configure build/refresh policy
set metadata and coverage
set license and entitlements
select pricing model
publish versions
inspect quality/usage/revenue
```

Swisscom may require certification/review before public marketplace publication.

## 20.3 DataProductDefinition

Illustrative schema:

```yaml
id: swiss-alpine-hiking-pro
publisher: provider-x
version: 3.2
contains:
  datasets: [routes, huts, pois]
  knowledge_spaces: [hiking-rules]
  capabilities: [route-search]
coverage:
  geography: CH
license:
  redistribution: restricted
commercial:
  model: revenue_share
  consumer_price_per_request: 0.05
  publisher_share_per_request: 0.03
trust:
  certification: VERIFIED
```

## 20.4 Commercial Models

TIP should support several models rather than assume one marketplace mechanism.

### Usage / revenue share

End consumer or consuming tenant pays per request/usage unit. Swisscom retains platform margin and settles the publisher share.

### Swisscom subscription/license purchase

Swisscom licenses a Data Product from a publisher for a monthly/annual amount and resells/bundles access to its customers.

### One-time license/acquisition

Swisscom pays a one-time fee for defined data/version/usage rights, subject to licensing terms.

### Publisher-hosted SaaS

Publisher pays Swisscom hosting/platform fees while making the Data Product free or independently priced for consumers.

### Free/open public product

Government/open-data packs may be free. Swisscom can still monetize hosting, SLA, API consumption, inference, enterprise overlays and derived Information Products.

## 20.5 Metering and Settlement

Every commercial execution should eventually produce a `UsageRecord`:

```json
{
  "request_id": "...",
  "consumer_tenant": "consumer-x",
  "information_product": "swiss-hike-finder",
  "data_products": [
    {"id": "swiss-alpine-hiking-pro", "units": 1, "publisher_cost": 0.03},
    {"id": "weather-product", "units": 1, "publisher_cost": 0.01}
  ],
  "platform_fee": 0.02,
  "model_cost": 0.002
}
```

The Commercial Control Plane should support metering, billing, publisher settlement, cost attribution, margin analysis and audit.

## 20.6 Licensing & Entitlements

TIP must know not only whether data exists but whether the consuming tenant is permitted to use it.

Entitlements may constrain:
