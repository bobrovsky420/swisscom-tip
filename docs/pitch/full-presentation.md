# Full Pitch Presentation - Swisscom Trusted Information Platform

## Slide 1 - Trusted Information Infrastructure

# Swisscom Trusted Information Platform

**Turning authoritative and live information into trustworthy services for any application.**

**Verified cross-language grounding across a predefined Swiss language catalog - not universal translation.**

> **AI is infrastructure, not the interface.**

---

## Slide 2 - Published Challenge

Build an MCP server that makes authoritative public Swiss information accessible effectively: grounded, cited, jurisdiction-aware, fresh, efficient, operable and easy to integrate.

Our insight:

> **The hard problem is not search. It is turning sources into trusted, maintainable, application-ready information.**

---

## Slide 3 - Team MVP: A Focused Vertical Slice

```text
admin.ch / SEM
      +
Canton Zurich / zh.ch
```

Scenario:

> I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?

Focused coverage demonstrates federal/cantonal authority, applicability and citations. It is the first vertical slice of TIP, not the limit of the product vision.

Multilingual proof: within a matching evaluated coverage profile, ask the same question in one of its declared query languages - including a declared Swiss German variant - retrieve evidence in another source language declared by that profile, and receive prose in a response language that profile permits, with the original citations preserved.

TIP's language catalog is finite and release-gated. Each release enables only an evaluated subset, and model or provider capabilities cannot expand it.

**Speaker note:** The hackathon target release accepts `en`, `de`, `de-CH`, `de-DE`, `fr-CH`, `it-CH`, `gsw`, `gsw-CH` and `rm-CH` for queries. Its response and metadata-projection languages are `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`. The input-only `de`, `de-DE`, `gsw` and `gsw-CH` variants route through the `de-CH` projection and always generate Swiss Standard German prose. Only a client with an unsupported query language receives guidance to translate the request into English and resubmit it; unsupported response languages, source-language filters and forbidden combinations receive their own explicit remediation.

---

## Slide 4 - On-Demand Knowledge Build

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
language detection
       ↓
per-section concept candidates (Apertus assisted)
       ↓
cross-document/language aggregation
       ↓
granularity + graph validation
       ↓
reviewed concept graph + terminology
       ↓
compact en/de-CH/fr-CH/it-CH/rm-CH metadata projections
       ↓
Evidence Objects
       ↓
index + tests
       ↓
publish Knowledge Release
```

No scheduler or incremental refresher is required in the MVP.

---

## Slide 5 - Stable Knowledge Is Compiled

Normal MCP requests do **not** scrape admin.ch or zh.ch.

Benefits:

- low latency;
- reproducibility;
- exact citations/source versions;
- resilience;
- source etiquette;
- predictable evaluation.

The government source remains canonical; TIP stores a verified operational representation.

The Knowledge Release also freezes the reviewed concept graph used for indexing: broad concepts navigate, while answerable concepts ground independent actions, obligations and facts.

---

## Slide 6 - Apertus for Swiss Multilingual Semantics

Apertus is the preferred model for language detection, concept extraction, multilingual terminology expansion, missing metadata translations, applicability interpretation, evidence reranking and optional rendering in the effective supported response language.

Why it fits: the [official Apertus launch](https://ethz.ch/en/news-and-events/eth-news/news/2025/09/press-release-apertus-a-fully-open-transparent-multilingual-language-model.html) reports 15 trillion training tokens across more than 1,000 languages, 40% non-English data, and explicitly includes Swiss German and Romansh. The [official FAQ](https://www.apertus-ai.org/docs/faq/) cautions that Apertus is fully conversational in only a few dozen languages and recommends evaluation or fine-tuning for specific needs.

Therefore TIP **tests rather than assumes** query understanding for every declared query language and response rendering for every declared response language. German and declared Swiss German input variants are never selected as response languages; they produce Swiss Standard German prose, and Swiss German prose is never generated. Apertus's breadth does not expand TIP's predefined language catalog. The core remains provider-independent, and vector retrieval uses a separately evaluated multilingual embedding provider.

**Speaker note:** The input-only query tags are `de`, `de-DE`, `gsw` and `gsw-CH`; each routes through the `de-CH` projection and fixes the effective response language to `de-CH`.

Deterministic software handles HTTP state, hashes, dates, numeric constraints and rules.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 7 - Search Returns Evidence, Not Answers

```text
Request in a declared query language
 ↓
language contract + most specific concept
 ↓
server-side multilingual terminology expansion
 ↓
matching or normalized metadata + lexical variants
 + concept lookup + multilingual vector retrieval
 ↓
authority / jurisdiction / date checks
 ↓
2-5 diverse Evidence Objects
 ↓
Evidence / Rule Engine
 ↓
structured facts + Trust Envelope
 ↓
prose in permitted effective response language + original-language citations
```

For declared query languages, the requesting application does not translate or supply synonyms, and the LLM never needs a large uncontrolled document dump.

Broad queries expand to a bounded and diverse set of answerable descendants. Narrow queries stay narrow. Concept lookup improves recall but never disables lexical or vector discovery.

TIP translates compact metadata and labelled derivative presentation, not complete pages, and exposes no standalone translation operation. Each query routes through one of five standard-language projections; original-language evidence remains unchanged. German and declared Swiss German input variants use reviewed terminology or tested dialect aliases and route to Swiss Standard German retrieval and generated prose.

**Speaker note:** The projection languages are `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`. The input-only tags `de`, `de-DE`, `gsw` and `gsw-CH` route through `de-CH` and require `de-CH` output. A client with an unsupported query language may translate and resubmit the request in English; TIP never pivots languages silently. An unsupported response language, source-language filter or forbidden combination is rejected with component-specific remediation. If optional rendering fails, facts and original evidence remain available with `presentation_status=DEGRADED`.

---

## Slide 8 - OpenCode: Example MCP Client

```text
OpenCode
   ↓
swiss_information.resolve
   ↓
"residence permit in Zurich" (English)
   ↓
residence_permit → Aufenthaltsbewilligung
   ↓
TIP / published release
   ├─ SEM evidence
   └─ zh.ch evidence
   ↓
English answer + original German/French citations
```

One high-level tool call should normally be sufficient. OpenCode demonstrates standard MCP compatibility; the server does not depend on OpenCode-specific behaviour.

---

## Slide 9 - Know When We Don't Know

TIP explicitly supports:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
UNSUPPORTED_LANGUAGE
```

A nearest semantic match is not silently treated as applicable truth.

Optional presentation is tracked separately: a rendering or excerpt-translation failure preserves the factual status and original evidence and returns `presentation_status=DEGRADED`.

---

## Slide 10 - Admin Control Plane

The Admin UI makes the platform visible:

```text
Knowledge Space: Swiss Public
Sources: SEM/admin.ch + zh.ch
Build: COMPLETE
Evidence: ...
Concept graph: VALIDATED
Candidate review: ...
Metadata projections: COMPLETE
Tests: PASS
Multilingual matrix: PASS
Production Release: ...
```

MVP primary operation: **Build / Full Reload**.

Scheduled refresh/change monitoring is post-MVP.

---

## Slide 11 - Not Another Chatbot: Arrival Checklist

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

## Slide 12 - Stretch: Swiss Hike Flutter App

A completely different client uses typed inputs:

```text
Origin │ Date │ Duration │ Difficulty │ Travel limit
Lake/Panorama │ Weather │ Restaurant
```

Hackathon backend uses 10-20 clearly labelled DEMO/MOCK routes and provider abstractions:

```text
MockTransportProvider
MockWeatherProvider
MockPlacesProvider
```

The app demonstrates architecture, not a production hiking database.

---

## Slide 13 - Target Product Model - Team Hypothesis

The remaining product vision builds on concepts exercised by the hackathon vertical slice.

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

## Slide 14 - Target Product Value for Swisscom

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

## Slide 15 - Business Hypothesis: Swisscom Economics

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

## Slide 16 - Target Product: Publisher & Data Product Marketplace

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

**Decision boundary:** the marketplace is a target-product capability, not a hackathon implementation. The vertical slice validates the source, evidence, release, trust and distribution foundations it would require.

---

## Slide 17 - Commercial Models

TIP should support several publisher relationships:

1. **Revenue share / usage:** end customer pays per request/unit; Swisscom retains margin and pays publisher share.
2. **Monthly/annual license:** Swisscom licenses a Data Product and bundles/resells access.
3. **One-time license:** Swisscom buys defined rights/version once.
4. **Publisher SaaS:** publisher pays Swisscom for hosting/distribution.
5. **Free/open:** government/open data is free while Swisscom monetizes hosting, SLA, inference and derived Information Products.

---

## Slide 18 - Example: Future Swiss Hike Economics

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

## Slide 19 - Licensing & Entitlements Matter

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

## Slide 20 - Publisher Incentive

Government can publish an OFFICIAL free Data Product.

A professional data company can sell licensed datasets.

A hiking/photography expert can monetize curated knowledge.

An enterprise can publish private internal Data Products.

Swisscom does not need to create all content itself; it creates the **trusted distribution and monetization infrastructure**.

---

## Slide 21 - Target Product: Autonomous Knowledge CI/CD

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

The hackathon proves repeatable on-demand builds and lifecycle metadata; automation is the target-product evolution.

---

## Slide 22 - From Swiss Public to Enterprise

```text
Swiss Public: admin.ch → zh.ch
Banking: EMIR → ESMA → FINMA → bank policy
Insurance: regulation → guidance → company policy → product/process
```

Same primitives: Source, Authority, Applicability, Evidence, Version, Trust, Data Product, Entitlement and Information Product.

---

## Slide 23 - Two Product Horizons

```text
HACKATHON VERTICAL SLICE
P0  admin.ch/zh.ch → concepts + localized metadata → multilingual retrieval → evidence → MCP
P1  Admin Control Plane + Arrival Checklist
P2  Swiss Hike composition demo with mock providers

TARGET PRODUCT
broader domains → Knowledge CI/CD → enterprise overlays
→ publisher Data Products → entitlement / metering / settlement
```

---

## Slide 24 - Closing

> **TIP delivers verified cross-language grounding across a predefined Swiss language catalog - not universal translation.**<br>
> **Apertus brings Swiss multilingual potential; TIP verifies it and remains model-independent.**<br>
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

**Hackathon:** prove a credible vertical slice using trusted Swiss information from admin.ch + zh.ch.<br>
**Target product:** trusted-information infrastructure where publishers and enterprises can govern, distribute and compose Data Products for any application.
