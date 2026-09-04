# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — From AI That Talks to AI That Knows What to Trust

# Swisscom Trusted Information Platform

**Turning authoritative Swiss information into trustworthy infrastructure for applications and AI.**

Most AI systems are good at language but unreliable at knowing what is current, authoritative or applicable. TIP solves that problem once as reusable infrastructure.

---

## Slide 2 — The Original Challenge

**Build an MCP server that makes authoritative public Swiss information accessible to AI assistants as effectively as possible.**

Our insight:

> **The hard problem is not search. It is converting authoritative sources into tested, versioned, AI-ready information that applications can trust.**

---

## Slide 3 — Hackathon Scope: admin.ch + zh.ch

We deliberately do not try to cover all Switzerland in two days.

```text
Swiss Confederation / admin.ch ecosystem
                 +
           Canton Zurich / zh.ch
```

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

This demonstrates authority, jurisdiction and applicability rather than mere semantic similarity.

---

## Slide 4 — Demo Starts With the Sources

The first surface is the **Admin Control Plane**:

```text
Knowledge Space: Swiss Public

SEM / admin.ch ecosystem    FEDERAL
Canton Zurich / zh.ch       CANTONAL
Status                      NOT BUILT

[ BUILD / FULL RELOAD ]
```

Sourcing is visible product functionality, not a hidden preprocessing script.

---

## Slide 5 — Hackathon Build: Simple on Purpose

For the hackathon we do **not** build a scheduler or continuous refresher.

```text
Build / Full Reload
        ↓
scan configured scope
        ↓
fetch official pages
        ↓
immutable snapshots
        ↓
normalize + Apertus enrichment
        ↓
Evidence Objects
        ↓
index + tests
        ↓
publish Knowledge Release
```

This is enough to prove the core architecture while keeping delivery realistic.

---

## Slide 6 — Stable Knowledge Is Compiled

Normal MCP requests do **not** scrape admin.ch or zh.ch.

```text
Official source
      ↓
immutable snapshot
      ↓
Evidence Objects
      ↓
local lexical + vector + metadata indexes
      ↓
Knowledge Release
```

Benefits: latency, reproducibility, auditability, source etiquette and resilience.

---

## Slide 7 — Apertus as Knowledge Engineer

Apertus is not the source of truth. It adds semantic intelligence:

```text
classification
concept extraction
multilingual terminology
applicability
federal/cantonal relationships
candidate fact extraction
fuzzy reranking/explanation
```

Software handles HTTP state, hashes, dates, numeric constraints and version consistency.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 8 — Search Returns Evidence, Not Answers

The runtime path is explicit:

```text
Request
  ↓
Execution Plan
  ↓
metadata filters
  ↓
lexical + vector + concept search
  ↓
rerank by authority / jurisdiction / validity
  ↓
2–5 Evidence Objects
  ↓
fact/rule resolution
  ↓
Evidence Bundle + Trust Envelope
```

Only then does a consuming LLM generate prose if prose is needed.

---

## Slide 9 — OpenCode Is the Reference MCP Client

```text
User
 ↓
OpenCode + evaluation LLM
 ↓
swiss_information.resolve
 ↓
TIP / published Swiss Public release
 ├─ SEM evidence
 └─ zh.ch evidence
 ↓
answer with citations
```

The tool call and evidence should be visible so judges can see agent efficiency and grounding.

---

## Slide 10 — Grounded Federal + Zurich Test

Ask:

> **I am an EU citizen moving to Zurich for work. What do I need to do after arrival?**

TIP returns:

- federal + Canton Zurich evidence;
- CH-ZH applicability;
- source versions and citations;
- compact facts;
- confidence and limitations.

**No government-site request occurs at question time.**

---

## Slide 11 — Know When We Don't Know

Ask for a local fact that was never sourced.

Expected:

```text
INSUFFICIENT_VERIFIED_EVIDENCE
```

or:

```text
OUT_OF_COVERAGE
```

> **The boundary of trusted knowledge is part of grounding quality.**

---

## Slide 12 — Not Another Chatbot: Swiss Arrival Checklist

The same Knowledge Release powers a formal application:

```text
Nationality          [ EU/EFTA ▼ ]
Purpose              [ Employment ▼ ]
Duration             [ >3 months ▼ ]
Destination canton   [ Zurich ▼ ]
Municipality         [ Zurich ▼ ]
Arrival date         [ ... ]
```

Output is a structured checklist of requirements, deadlines, evidence and trust. No prompt is required.

> **AI is infrastructure, not the interface.**

---

## Slide 13 — Stretch Demo: Swiss Hike on Flutter

If the core is complete, show a completely different client:

```text
Start              Zürich HB
Date               Tomorrow
Hiking time        ~4h
Difficulty         Moderate
Travel             ≤90 min
Scenery            Lake + Panorama
Weather            Good
Restaurant          Near finish
```

Flutter sends a typed REST request to `swiss-hike-finder`. No chat box and no hidden natural-language prompt.

---

## Slide 14 — Mock the Hiking Providers, Not the Architecture

Use 10–20 curated demo routes and deterministic mock providers:

```text
demo/hiking/routes.json
demo/hiking/transport.json
demo/hiking/weather.json
demo/hiking/restaurants.json
```

```text
TransportProvider → Mock now / Real adapter later
WeatherProvider   → Mock now / Real adapter later
PlacesProvider    → Mock now / Real adapter later
```

Mocks are explicitly marked **DEMO/MOCK**.

---

## Slide 15 — Four Surfaces, Four Messages

```text
ADMIN CONTROL PLANE
“How trusted information is built.”

OPENCODE
“Standard MCP/agent integration.”

ARRIVAL CHECKLIST
“Structured authoritative application.”

SWISS HIKE / FLUTTER
“Same headless platform can power a consumer product.”
```

**Same platform. No shared user interface.**

---

## Slide 16 — Full Product: Continuous Knowledge CI/CD

The hackathon uses manual full builds. The production platform extends the same release machinery:

```text
scheduled / change-triggered revalidation
        ↓
fetch new/changed content only
        ↓
semantic change analysis
        ↓
impact analysis
        ↓
incremental rebuild
        ↓
regression tests
        ↓
auto-publish or human approval
```

> **Hackathon proves the build/release model; production adds autonomous maintenance.**

---

## Slide 17 — Why This Belongs at Swisscom

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

TIP fills the missing layer: **what information can this application trust?**

---

## Slide 18 — Business Potential

TIP can strengthen:

- **myAI** — better Swiss information;
- **eGovHub** — AI-ready knowledge for cantons and municipalities;
- **Swiss AI Platform** — more Apertus/inference consumption;
- **Banking** — FINMA/EMIR/regulatory intelligence;
- **Enterprise** — private Knowledge Spaces and Information Products.

Potential revenue:

```text
Knowledge SaaS
API / MCP usage
managed knowledge services
private tenants
regulatory intelligence
integration / private deployment
future marketplace
```

---

## Slide 19 — From Swiss Public to Enterprise Regulation

```text
SWISS PUBLIC
admin.ch → zh.ch → municipality

BANKING
EMIR → RTS/ITS → ESMA guidance → bank policy

INSURANCE
regulation → guidance → company policy → product/process
```

Reusable primitives: Source, Authority, Applicability, Evidence, Capability, Version, Trust and Information Product.

---

## Slide 20 — Delivery Priority

```text
P0  admin.ch/zh.ch full load → storage → compiler → retrieval → MCP → OpenCode
P1  Admin Control Plane
P1  Swiss Arrival Checklist
P2  Flutter Swiss Hike with mock providers
P3  scheduled/incremental refresh prototype only if everything else is complete
```

The core submission must not depend on background infrastructure.

---

## Slide 21 — Challenge Criteria

```text
GROUNDING           official admin.ch/SEM + zh.ch evidence
CITATIONS           Evidence Objects trace to snapshots
JURISDICTION        federal + CH-ZH applicability
FRESHNESS           explicit build timestamp + repeatable full reload
AGENT EFFICIENCY    one high-level MCP call; compact evidence
SOURCE ETIQUETTE    no upstream fetch per question
OPERABILITY         reproducible builds, tests, releases, Admin UI
INTEGRATION         OpenCode MCP + REST apps
EXTENSIBILITY       production roadmap to autonomous Knowledge CI/CD
```

---

## Slide 22 — Closing

**LLMs should not have to know everything. Applications should know where trustworthy information comes from.**

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

# Swisscom Trusted Information Platform

**From admin.ch and zh.ch to trustworthy information products for any application.**
