# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — Trusted Information Infrastructure

# Swisscom Trusted Information Platform

**Turning authoritative and live information into trustworthy services for any application.**

> **AI is infrastructure, not the interface.**

---

## Slide 2 — Original Challenge

Build an MCP server that makes authoritative public Swiss information accessible effectively: grounded, cited, jurisdiction-aware, fresh, efficient, operable and easy to integrate.

Our insight:

> **The hard problem is not search. It is turning sources into trusted, maintainable, application-ready information.**

---

## Slide 3 — Hackathon Scope

```text
admin.ch / SEM
      +
Canton Zurich / zh.ch
```

Scenario:

> I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?

Focused coverage demonstrates federal/cantonal authority, applicability and citations.

---

## Slide 4 — On-Demand Knowledge Build

For the hackathon:

```text
[ BUILD / FULL RELOAD ]
       ↓
scan / crawl / fetch
       ↓
immutable snapshots
       ↓
normalize
       ↓
Apertus enrichment
       ↓
Evidence Objects
       ↓
index + tests
       ↓
publish Knowledge Release
```

No scheduler or incremental refresher is required in the MVP.

---

## Slide 5 — Stable Knowledge Is Compiled

Normal MCP requests do **not** scrape admin.ch or zh.ch.

Benefits:

- low latency;
- reproducibility;
- exact citations/source versions;
- resilience;
- source etiquette;
- predictable evaluation.

The government source remains canonical; TIP stores a verified operational representation.

---

## Slide 6 — Apertus as Semantic Infrastructure

Apertus can support classification, concept extraction, multilingual terminology, applicability interpretation, evidence reranking and explanations.

Deterministic software handles HTTP state, hashes, dates, numeric constraints and rules.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 7 — Search Returns Evidence, Not Answers

```text
Request
 ↓
Query Planner
 ↓
Authority / jurisdiction / date filters
 ↓
lexical + vector + concept retrieval
 ↓
2–5 diverse Evidence Objects
 ↓
Evidence / Rule Engine
 ↓
structured facts + Trust Envelope
 ↓
optional natural-language explanation
```

The LLM never needs a large uncontrolled document dump.

---

## Slide 8 — OpenCode: Reference MCP Client

```text
OpenCode
   ↓
swiss_information.resolve
   ↓
TIP / published release
   ├─ SEM evidence
   └─ zh.ch evidence
   ↓
answer with citations
```

One high-level tool call should normally be sufficient.

---

## Slide 9 — Know When We Don't Know

TIP explicitly supports:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
```

A nearest semantic match is not silently treated as applicable truth.

---

## Slide 10 — Admin Control Plane

The Admin UI makes the platform visible:

```text
Knowledge Space: Swiss Public
Sources: SEM/admin.ch + zh.ch
Build: COMPLETE
Evidence: ...
Tests: PASS
Production Release: ...
```

MVP primary operation: **Build / Full Reload**.

Scheduled refresh/change monitoring is post-MVP.

---

## Slide 11 — Not Another Chatbot: Arrival Checklist

Formal fields:

```text
Nationality       EU/EFTA
Purpose           Employment
Duration          >3 months
Canton            Zurich
Arrival date      ...
```

REST returns typed requirements, deadlines, evidence and Trust Envelope. No natural-language prompt is required.

---

## Slide 12 — Stretch: Swiss Hike Flutter App

A completely different client uses typed inputs:

```text
Origin │ Date │ Duration │ Difficulty │ Travel limit
Lake/Panorama │ Weather │ Restaurant
```

Hackathon backend uses 10–20 clearly labelled DEMO/MOCK routes and provider abstractions:

```text
MockTransportProvider
MockWeatherProvider
MockPlacesProvider
```

The app demonstrates architecture, not a production hiking database.

---

## Slide 13 — Three Platform Artifacts

### Knowledge Space
Internal compiled knowledge.

### Data Product
A distributable publisher artifact containing knowledge, datasets and/or capabilities plus license/commercial metadata.

### Information Product
An application capability combining Data Products/Knowledge Spaces, live capabilities, rules and optional AI.

```text
Data Products + Capabilities
          ↓
   Information Product
          ↓
     Any Application
```

---

## Slide 14 — Why Swisscom?

```text
myAI / eGov / Mobile / Banking / Enterprise
                    ↓
                   TIP
                    ↓
              Apertus
                    ↓
          Swiss AI Platform
```

TIP creates a reusable trusted-information layer above Swisscom's AI infrastructure and below its applications.

---

## Slide 15 — Direct Swisscom Economics

Potential revenue:

```text
API / MCP consumption
Knowledge SaaS
managed knowledge
enterprise/private tenants
regulatory intelligence
integration/private deployment
Apertus / AI-platform consumption
```

But TIP can become more than a Swisscom-owned content service.

---

## Slide 16 — Post-MVP: Publisher & Data Product Marketplace

```text
Government │ SIX-like providers │ Companies │ Experts │ Individuals
                         ↓
                    DATA PRODUCTS
                         ↓
                   SWISSCOM TIP
       hosting │ trust │ distribution │ metering │ billing
                         ↓
              myAI │ Apps │ Enterprises │ Agents
```

Publishers maintain their own trusted packs and can monetize machine consumption. Swisscom operates the platform and distribution channel.

**This marketplace is not part of the hackathon MVP.**

---

## Slide 17 — Commercial Models

TIP should support several publisher relationships:

1. **Revenue share / usage:** end customer pays per request/unit; Swisscom retains margin and pays publisher share.
2. **Monthly/annual license:** Swisscom licenses a Data Product and bundles/resells access.
3. **One-time license:** Swisscom buys defined rights/version once.
4. **Publisher SaaS:** publisher pays Swisscom for hosting/distribution.
5. **Free/open:** government/open data is free while Swisscom monetizes hosting, SLA, inference and derived Information Products.

---

## Slide 18 — Example: Future Swiss Hike Economics

```text
Hiking Routes Product      Publisher A
Weather Product            Publisher B
Transport Capability       Provider C
Places Product             Provider D
          ↓
     Swiss Hike Finder
          ↓
      end-user request
```

One request may consume several paid/free products. TIP records which components were used and applies entitlement, pricing and settlement rules.

For the hackathon all hiking providers remain FREE + DEMO/MOCK.

---

## Slide 19 — Licensing & Entitlements Matter

TIP must eventually know not only whether information exists but whether the consumer may use it.

Entitlements can constrain:

```text
tenant / application
purpose
geography
redistribution
retention
volume
contract period
```

This makes the marketplace applicable to professional providers and regulated enterprises.

---

## Slide 20 — Publisher Incentive

Government can publish an OFFICIAL free Data Product.

A professional data company can sell licensed datasets.

A hiking/photography expert can monetize curated knowledge.

An enterprise can publish private internal Data Products.

Swisscom does not need to create all content itself; it creates the **trusted distribution and monetization infrastructure**.

---

## Slide 21 — Post-MVP: Autonomous Knowledge CI/CD

Production evolution:

```text
source watcher
 ↓
cheap change checks
 ↓
semantic change analysis
 ↓
incremental rebuild
 ↓
regression tests
 ↓
automatic/approved promotion
```

The hackathon proves repeatable on-demand builds; automation comes later.

---

## Slide 22 — From Swiss Public to Enterprise

```text
Swiss Public: admin.ch → zh.ch
Banking: EMIR → ESMA → FINMA → bank policy
Insurance: regulation → guidance → company policy → product/process
```

Same primitives: Source, Authority, Applicability, Evidence, Version, Trust, Data Product, Entitlement and Information Product.

---

## Slide 23 — Delivery Priority

```text
P0  admin.ch/zh.ch → full build → retrieval → MCP → OpenCode
P1  Admin Control Plane
P1  Arrival Checklist
P2  Flutter Swiss Hike with mock providers
POST-MVP scheduler/incremental Knowledge CI/CD
POST-MVP publisher marketplace/billing/settlement
```

---

## Slide 24 — Closing

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

**Hackathon:** prove trusted Swiss information from admin.ch + zh.ch.  
**Product vision:** a marketplace and runtime where trusted publishers can distribute and monetize Data Products for any application.