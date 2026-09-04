# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — From AI that talks to AI that knows where to look

# Swisscom Trusted Information Platform

**Turning authoritative Swiss information into trustworthy infrastructure for applications and AI.**

Most AI systems are excellent at language but unreliable at knowing what is current, authoritative or applicable. We solve that problem once, as infrastructure, rather than separately inside every chatbot and application.

---

## Slide 2 — The Original Challenge

**Build an MCP server that makes authoritative public Swiss information accessible to AI assistants as effectively as possible.**

Our insight:

> **The hard problem is not search. It is continuously turning authoritative sources into trusted, maintainable AI-ready information.**

---

## Slide 3 — Hackathon Scope: admin.ch + zh.ch

We deliberately do not try to index all Switzerland in two days.

```text
Swiss Confederation / admin.ch ecosystem
                 +
           Canton Zurich / zh.ch
```

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

This demonstrates authority, jurisdiction and applicability rather than merely semantic similarity.

---

## Slide 4 — Demo Starts With the Sources

The first screen is the **Admin Control Plane**:

```text
Knowledge Space: Swiss Public

SEM / admin.ch ecosystem    FEDERAL
Canton Zurich / zh.ch       CANTONAL
Status                      NOT BUILT
```

We build from configured official sources. Sourcing is visible product functionality, not a hidden script.

---

## Slide 5 — Autonomous Source Acquisition

```text
admin.ch / SEM + zh.ch
          ↓
Source Registry → Scanner → Crawler → Fetcher
          ↓
immutable raw snapshots
          ↓
Normalizer
```

TIP records canonical source, authority, jurisdiction, HTTP metadata, hashes, retrieval time and immutable versions.

---

## Slide 6 — Stable Knowledge Is Compiled

Normal MCP requests do **not** scrape admin.ch or zh.ch.

```text
Official source
      ↓
immutable snapshot
      ↓
normalized document
      ↓
Apertus enrichment
      ↓
Evidence Objects
      ↓
local indexes
      ↓
Knowledge Release
```

Benefits: latency, reproducibility, auditability, resilience, source etiquette and lower network/model cost.

---

## Slide 7 — Apertus as Knowledge Engineer

Apertus is not the source of truth. It adds semantic intelligence:

```text
classification
concept extraction
multilingual terminology
applicability
federal/cantonal relationships
semantic change analysis
candidate test generation
fuzzy reranking/explanation
```

Software handles HTTP state, hashes, dates, numeric constraints and version consistency.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 8 — From Documents to Evidence

TIP creates traceable Evidence Objects, not arbitrary vector chunks:

```text
Concept       residence.registration
Authority     Canton Zurich
Jurisdiction  CH-ZH
Source        zh.ch / Arriving
Version       22
Content       original supporting passage
```

Every object traces to an exact immutable snapshot and canonical page.

---

## Slide 9 — Knowledge CI/CD

```text
Authoritative source
       ↓
change detected
       ↓
semantic change analysis
       ↓
affected evidence rebuilt
       ↓
regression tests
       ↓
immutable Knowledge Release
       ↓
publish
```

> **This is not static RAG. It is CI/CD for knowledge.**

---

## Slide 10 — OpenCode Is the Reference MCP Client

OpenCode provides a neutral MCP integration surface. We make the tool call visible:

```text
User
 ↓
OpenCode + evaluation LLM
 ↓
swiss_information.resolve
 ↓
TIP / swiss-public@17
 ├─ SEM evidence
 └─ zh.ch evidence
 ↓
answer with citations
```

The repository should support `git clone → docker compose up → OpenCode → TIP available`.

---

## Slide 11 — Test 1: Grounded Federal + Zurich Answer

Ask:

> **I am an EU citizen moving to Zurich for work. What do I need to do after arrival?**

TIP returns federal + Canton Zurich evidence, CH-ZH applicability, citations, source versions, Knowledge Release, confidence and limitations.

**No admin.ch or zh.ch request occurs at query time.**

---

## Slide 12 — Test 2: Know When We Don't Know

Ask for a local fact never sourced.

Expected:

```text
INSUFFICIENT_VERIFIED_EVIDENCE
```

or `OUT_OF_COVERAGE`, rather than an invented nearest answer.

---

## Slide 13 — Test 3: Prove It Is Not Live Web Search

Disable upstream network access in the controlled environment and repeat the OpenCode query.

It still succeeds from the published release.

```text
MCP ≠ web search
MCP ≠ scrape-on-demand
```

---

## Slide 14 — Test 4: Autonomous Freshness

Use a controlled mirror and simulate:

```text
14 days → 8 days
```

Watcher detects change → Apertus classifies it as substantive → affected evidence and tests are identified. The real official site is never modified.

---

## Slide 15 — Watch Knowledge Rebuild Itself

```text
Source version        22 → 23
Evidence affected     2
Evaluations affected  7
        ↓
Incremental compile
        ↓
Regression tests PASS
        ↓
swiss-public@18 → PRODUCTION
```

Repeat the OpenCode query; it now consumes Release 18.

---

## Slide 16 — Not Another Chatbot: Swiss Arrival Checklist

The same release powers a formal application:

```text
Nationality          [ EU/EFTA ▼ ]
Purpose              [ Employment ▼ ]
Duration             [ >3 months ▼ ]
Destination canton   [ Zurich ▼ ]
Municipality         [ Zurich ▼ ]
Arrival date         [ 04.09.2026 ]
```

Output is a structured checklist of requirements, deadlines, evidence and trust. No prompt is required.

> **AI is infrastructure, not the interface.**

---

## Slide 17 — Stretch Demo: Swiss Hike on Flutter

If the core demo is complete, pick up a phone and open a completely different application:

```text
Swiss Hike

Start              Zürich HB
Date               Tomorrow
Hiking time        ~4h
Difficulty         Moderate
Travel             ≤90 min
Scenery            Lake + Panorama
Weather            Good
Restaurant          Near finish

[ FIND HIKES ]
```

No chat box. No hidden English prompt. The Flutter app sends a typed REST request to TIP.

---

## Slide 18 — We Do Not Build a Hiking Platform in Two Days

The hiking app is an **architectural reference**, not a production hiking service.

Use a tiny deterministic demo dataset:

```text
10–20 curated fictional/demo route records
+
mocked transport times
+
mocked weather scenarios
+
mocked restaurant availability
```

Store under:

```text
demo/hiking/routes.json
demo/hiking/transport.json
demo/hiking/weather.json
demo/hiking/restaurants.json
```

The data is explicitly marked **DEMO/MOCK** in the app and API. No fake data is presented as live or authoritative.

---

## Slide 19 — Hiking Shows the Information Product Pattern

Flutter sends:

```json
{
  "origin": "Zurich HB",
  "date": "tomorrow",
  "target_duration_minutes": 240,
  "difficulty": "moderate",
  "max_transport_minutes": 90,
  "preferences": ["lake", "panorama"],
  "good_weather": true,
  "restaurant_near_end": true
}
```

TIP executes:

```text
route candidates
      +
transport capability
      +
weather capability
      +
restaurant capability
      ↓
hard deterministic filters
      ↓
soft preference ranking
      ↓
structured route cards
```

This is the same platform abstraction applied to a DERIVED information product.

---

## Slide 20 — Mocking Strategy Still Preserves Architecture

Mock at **provider boundaries**, not inside business logic.

```text
TransportProvider
 ├─ MockTransportProvider      ← hackathon
 └─ RealProviderAdapter        ← future

WeatherProvider
 ├─ MockWeatherProvider        ← hackathon
 └─ RealProviderAdapter        ← future

PlacesProvider
 ├─ MockPlacesProvider         ← hackathon
 └─ RealProviderAdapter        ← future
```

The recommendation engine and Flutter app do not know whether the provider is mocked or real.

That means the demo code is a credible foundation rather than disposable hard-coded UI logic.

---

## Slide 21 — Four Surfaces, Four Messages

```text
ADMIN CONTROL PLANE
“How trusted information is built and maintained.”

OPENCODE
“Standard MCP/agent integration.”

ARRIVAL CHECKLIST
“Structured non-chat authoritative application.”

SWISS HIKE / FLUTTER
“Same headless platform can power a consumer product.”
```

**Same platform. No shared user interface.**

---

## Slide 22 — One Platform, Many Information Products

```text
Trusted Information Platform
        │
        ├─ Swiss Public / Arrival
        ├─ Swiss Hike
        ├─ Swiss Photo Scout
        ├─ Swiss Housing
        ├─ FINMA
        ├─ EMIR
        └─ Regulatory Impact
```

Each Information Product combines typed inputs, Knowledge Spaces, Capabilities, rules, optional AI and typed outputs.

---

## Slide 23 — Different Information Requires Different Strategies

- **Authoritative:** admin.ch/zh.ch → compiled versioned knowledge.
- **Live:** weather/fares/disruptions → provider APIs.
- **Private:** lease/company policy → private Knowledge Spaces.
- **Recommendation:** places/reviews/preferences → discovery sources.
- **Derived:** hiking/photo → structured data + live capabilities + constraints + ranking.

Everything is not forced through RAG.

---

## Slide 24 — Why This Belongs at Swisscom

```text
                    EXPERIENCES
       myAI / eGov / Mobile / Banking / Apps
                         │
                         ▼
             TRUSTED INFORMATION PLATFORM
                         │
              Knowledge │ Data │ Services
                         │
                         ▼
                     APERTUS
                         │
                         ▼
               SWISS AI PLATFORM
                         │
                         ▼
             SWISS INFRASTRUCTURE
```

TIP fills the missing layer: **what information can this application trust, and how do we keep it trustworthy?**

---

## Slide 25 — Business Potential

TIP can strengthen myAI, eGovHub, Swiss AI Platform, banking services and future consumer Information Products.

Potential value:

```text
Knowledge SaaS
API / MCP consumption
managed knowledge services
private enterprise tenants
premium Information Products
regulatory intelligence
integration/private deployment
future marketplace commission
more Apertus/Swiss AI Platform consumption
```

---

## Slide 26 — From Swiss Public to Enterprise Regulation

```text
SWISS PUBLIC
admin.ch → zh.ch → municipality

BANKING
EMIR → RTS/ITS → ESMA guidance → bank policy

INSURANCE
regulation → guidance → company policy → product/process
```

Reusable primitives: Source, Authority, Applicability, Evidence, Capability, Version, Knowledge Release, Trust Envelope and Knowledge CI/CD.

---

## Slide 27 — Challenge Criteria

```text
GROUNDING           official admin.ch/SEM + zh.ch evidence
CITATIONS           Evidence Objects trace to source versions
JURISDICTION        federal + CH-ZH applicability
FRESHNESS           source watcher + Knowledge CI/CD
AGENT EFFICIENCY    one high-level MCP call; compact evidence
SOURCE ETIQUETTE    no upstream crawl per query
OPERABILITY         snapshots, tests, releases, rollback, Admin UI
INTEGRATION         OpenCode MCP + REST apps
EXTENSIBILITY       Arrival + optional Flutter Hike reference apps
```

---

## Slide 28 — Delivery Priority

```text
P0  admin.ch/zh.ch → storage → compiler → retrieval → MCP → OpenCode
P1  Admin Control Plane
P1  Swiss Arrival Checklist
P2  Flutter Swiss Hike with mock providers
P3  additional MCP/chat clients
```

The stretch app must never put the core challenge solution at risk.

---

## Slide 29 — Closing

**LLMs should not have to know everything. Applications should know where trustworthy information comes from.**

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

# Swisscom Trusted Information Platform

**From admin.ch and zh.ch to trustworthy information products for any application.**
