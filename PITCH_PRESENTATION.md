# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — From AI that talks to AI that knows where to look

# Swisscom Trusted Information Platform

**Turning authoritative Swiss information into trustworthy infrastructure for applications and AI.**

Most AI systems are excellent at language but unreliable at knowing what is current, authoritative or applicable. We solve that problem once, as infrastructure, rather than separately inside every chatbot and application.

---

## Slide 2 — The Original Challenge

**Build an MCP server that makes authoritative public Swiss information accessible to AI assistants as effectively as possible.**

The server must be correct, authoritative, jurisdiction-aware, fresh, citable, efficient, maintainable and straightforward to integrate with standard MCP clients.

Our insight:

> **The hard problem is not search. It is continuously turning authoritative sources into trusted, maintainable AI-ready information.**

---

## Slide 3 — Our Hackathon Scope: admin.ch + zh.ch

We deliberately do **not** try to index all of Switzerland in two days.

```text
Swiss Confederation / admin.ch ecosystem
                 +
           Canton Zurich / zh.ch
```

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

This forces the system to combine federal context with cantonal guidance and demonstrate authority, jurisdiction and applicability rather than merely semantic similarity.

---

## Slide 4 — The Demo Starts With the Sources, Not the Question

The first screen is the **Admin Control Plane**:

```text
Knowledge Space: Swiss Public

SEM / admin.ch ecosystem    FEDERAL
Canton Zurich / zh.ch       CANTONAL

Status                      NOT BUILT
Knowledge Release           —
```

We build the Knowledge Space from actual configured official sources. Sourcing is visible product functionality, not a hidden preprocessing script.

---

## Slide 5 — Autonomous Source Acquisition

```text
admin.ch / SEM + zh.ch
          ↓
     Source Registry
          ↓
        Scanner
          ↓
        Crawler
          ↓
        Fetcher
          ↓
 immutable raw snapshots
          ↓
       Normalizer
```

The crawler stays inside explicit trusted scopes and records canonical source, authority, jurisdiction, HTTP metadata, content hash, retrieval time and immutable raw version.

---

## Slide 6 — Stable Knowledge Is Compiled, Not Retrieved Per Question

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

Benefits: low latency, reproducibility, auditability, resilience, source etiquette and fewer network/model calls.

---

## Slide 7 — Apertus as the Knowledge Engineer

Apertus is **not** the source of truth. It adds semantic intelligence:

```text
classify documents
extract concepts
map multilingual terminology
identify applicability
relate federal/cantonal evidence
analyse semantic changes
generate candidate tests
rerank evidence
```

Software handles HTTP state, hashes, source identity, dates, numeric comparisons and version consistency.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 8 — From Documents to Evidence

The compiler creates traceable **Evidence Objects**, not arbitrary vector chunks:

```text
Concept       residence.registration
Authority     Canton Zurich
Jurisdiction  CH-ZH
Source        zh.ch / Arriving
Version       22
Retrieved     04.09.2026
Content       original supporting passage
```

Every Evidence Object points to the exact source snapshot and canonical page.

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

Routine updates require no human intervention; exceptions or high-risk changes can require review.

> **This is not static RAG. It is CI/CD for knowledge.**

---

## Slide 10 — The Runtime Uses a Published Release

```text
BUILD PLANE
admin.ch + zh.ch → compile → test → swiss-public@17 → PUBLISH

DATA PLANE
MCP → local retrieval → 1–5 Evidence Objects → Trust Envelope
```

A user never sees a half-built knowledge base. Runtime consumes one immutable published release.

---

## Slide 11 — OpenCode Is Our Reference MCP Client

For the hackathon we use **OpenCode** as the neutral reference client.

Why:

- it is MCP-compatible and close to the evaluation style described in the challenge;
- it supports local MCP servers over stdio and remote servers over Streamable HTTP;
- it keeps attention on **our MCP server**, not on a proprietary assistant UI;
- it can expose TIP tools directly, making tool selection and call count visible.

Repository configuration should allow:

```text
git clone
→ docker compose up
→ open OpenCode
→ TIP MCP available
```

Only TIP should be enabled during the core evaluation to keep tool choice and context usage clean.

---

## Slide 12 — Make the Tool Call Visible

The audience should see the actual integration path:

```text
User
  ↓
OpenCode + evaluation LLM
  ↓
swiss-tip_swiss_information_resolve
  ↓
TIP
  ├─ Knowledge Release: swiss-public@17
  ├─ Jurisdiction: CH-ZH
  ├─ SEM evidence
  └─ zh.ch evidence
  ↓
LLM response with citations
```

This directly demonstrates MCP integration, tool-selection quality and agent efficiency.

---

## Slide 13 — First Test: Grounded Federal + Zurich Answer

Ask in OpenCode:

> **I am an EU citizen moving to Zurich for work. What do I need to do after arrival?**

TIP retrieves federal SEM evidence + Canton Zurich evidence, applies CH-ZH context and returns a compact evidence bundle with authority, jurisdiction, citations, source versions, Knowledge Release, confidence and limitations.

**No admin.ch or zh.ch request occurs at query time.**

---

## Slide 14 — Second Test: Know When We Don't Know

Ask for an exact local fee that was never sourced.

Expected:

```text
INSUFFICIENT_VERIFIED_EVIDENCE
```

or:

```text
OUT_OF_COVERAGE
```

> **Knowing the boundary of trusted knowledge is part of grounding quality.**

---

## Slide 15 — Third Test: Prove It Is Not Live Web Search

After publishing the Knowledge Release, disable upstream network access in the controlled demo environment and repeat the OpenCode query.

It still succeeds from locally compiled evidence.

```text
MCP ≠ web search
MCP ≠ scrape-on-demand
```

---

## Slide 16 — Fourth Test: Autonomous Freshness

Use a controlled mirror of one ingested source and simulate:

```text
14 days → 8 days
```

The watcher detects the changed content hash. Apertus classifies the change as substantive, identifies `residence.registration_deadline`, and marks the impact high. The real official site is never modified.

---

## Slide 17 — Watch the Knowledge Rebuild Itself

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

Repeat the OpenCode query: it now consumes Release 18.

---

## Slide 18 — Not Another Chatbot: Swiss Arrival Checklist

The same Knowledge Release powers a formal application:

```text
Nationality          [ EU/EFTA ▼ ]
Purpose              [ Employment ▼ ]
Duration             [ >3 months ▼ ]
Destination canton   [ Zurich ▼ ]
Municipality         [ Zurich ▼ ]
Arrival date         [ 04.09.2026 ]
Work start           [ 08.09.2026 ]
```

Output is structured: registration requirement, permit requirement, deadlines, evidence and trust. There is no natural-language prompt.

> **AI is infrastructure, not the interface.**

---

## Slide 19 — Three Demo Surfaces, Three Messages

```text
ADMIN CONTROL PLANE
“Here is how trusted knowledge is built and maintained.”

OPENCODE
“Here is the standard MCP/agent integration.”

SWISS ARRIVAL CHECKLIST
“Here is the same platform powering a non-chat application.”
```

Together they prevent TIP from being perceived as another chatbot or RAG demo.

---

## Slide 20 — One Knowledge Release, Many Applications

```text
                   admin.ch + zh.ch
                         ↓
                  swiss-public@18
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
         MCP            REST           SDK
          │              │              │
          ▼              ▼              ▼
      OpenCode/myAI   Arrival App     eGov App
```

Compile once; consume everywhere.

---

## Slide 21 — Different Information Requires Different Strategies

The demo proves compiled authoritative knowledge. Production TIP additionally supports:

- **Live:** train fares, weather, disruptions → authoritative APIs.
- **Private:** lease/company policy → private Knowledge Spaces.
- **Recommendation:** first-date locations → places/reviews/preferences.
- **Derived:** hiking/photo recommendations → structured data + live capabilities + deterministic constraints + AI ranking.

Everything is not forced through RAG.

---

## Slide 22 — Why This Belongs at Swisscom

```text
                    EXPERIENCES
          myAI / eGov / Banking / Apps
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

## Slide 23 — Business Potential

TIP can strengthen myAI, eGovHub, Swiss AI Platform, banking services and enterprise AI.

Potential revenue:

```text
Knowledge SaaS
API / MCP consumption
managed knowledge services
private enterprise tenants
premium Information Products
regulatory intelligence
integration/private deployment
future marketplace commission
```

It also drives Apertus inference and Swiss AI Platform consumption.

---

## Slide 24 — From Swiss Public to Enterprise Regulation

```text
SWISS PUBLIC
admin.ch → zh.ch → municipality

BANKING
EMIR → RTS/ITS → ESMA guidance → bank policy

INSURANCE
regulation → supervisory guidance → company policy → product/process
```

Reusable primitives: Source, Authority, Applicability, Evidence, Version, Knowledge Release, Trust Envelope and Knowledge CI/CD.

---

## Slide 25 — Challenge Criteria

```text
GROUNDING           official admin.ch/SEM + zh.ch evidence
CITATIONS           Evidence Objects trace to source versions
JURISDICTION        federal + CH-ZH applicability
FRESHNESS           source watcher + Knowledge CI/CD
AGENT EFFICIENCY    one high-level MCP call; compact evidence
SOURCE ETIQUETTE    no upstream crawl per query
OPERABILITY         snapshots, tests, releases, rollback, Admin UI
INTEGRATION         OpenCode + standard MCP + REST reference app
```

---

## Slide 26 — Closing

**LLMs should not have to know everything. Applications should know where trustworthy information comes from.**

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

# Swisscom Trusted Information Platform

**From admin.ch and zh.ch to continuously verified information infrastructure for any application.**
