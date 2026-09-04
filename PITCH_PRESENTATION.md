# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — From AI that talks to AI that knows where to look

# Swisscom Trusted Information Platform

**Turning authoritative Swiss information into trustworthy infrastructure for applications and AI.**

Most AI systems are excellent at language but unreliable at knowing what is current, authoritative or applicable. We solve that problem once, as infrastructure, rather than separately inside every chatbot and application.

---

## Slide 2 — The Original Challenge

**Build an MCP server that makes authoritative public Swiss information accessible to AI assistants as effectively as possible.**

The server must be:

- correct and grounded;
- based on authoritative sources;
- jurisdiction-aware;
- fresh and citable;
- efficient in tool calls, tokens and latency;
- reproducible and maintainable;
- easy to integrate with standard MCP clients.

Our insight:

> **The hard problem is not search. It is continuously turning authoritative sources into trusted, maintainable AI-ready information.**

---

## Slide 3 — Our Hackathon Scope: admin.ch + zh.ch

We deliberately do **not** try to index all of Switzerland in two days.

The MVP starts with two authoritative ecosystems:

```text
Swiss Confederation / admin.ch ecosystem
                 +
           Canton Zurich / zh.ch
```

Primary test scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

This forces the system to combine federal context with cantonal guidance and demonstrate authority, jurisdiction and applicability rather than merely semantic similarity.

---

## Slide 4 — The Demo Starts With the Sources, Not the Question

The first thing we show is the **Admin Control Plane**.

```text
Knowledge Space: Swiss Public

Sources
────────────────────────────────────
SEM / admin.ch ecosystem    FEDERAL
Canton Zurich / zh.ch       CANTONAL

Status                      NOT BUILT
Knowledge Release           —
```

We then build the Knowledge Space from the actual configured official sources.

This makes sourcing a visible part of the product rather than a hidden preprocessing script.

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

The crawler operates only inside explicit trusted scopes.

It does not blindly download all of `admin.ch` or `zh.ch`.

The platform records:

```text
canonical source
authority
jurisdiction
HTTP metadata
content hash
retrieval time
raw immutable version
```

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

The external government site remains the canonical authority.

TIP stores a **verified, versioned operational representation** of that authority.

Benefits:

- low latency;
- reproducible answers;
- auditability;
- resilience to source outages;
- source etiquette;
- fewer network and model calls.

---

## Slide 7 — Apertus as the Knowledge Engineer

Apertus is **not** the source of truth.

It adds semantic intelligence during knowledge compilation:

```text
classify documents
extract concepts
map multilingual terminology
identify applicability candidates
relate federal and cantonal evidence
analyse semantic changes
generate candidate evaluation tests
rerank evidence
```

Deterministic software handles:

```text
HTTP state
hashes
source identity
date arithmetic
numeric comparisons
version consistency
```

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 8 — From Documents to Evidence

We do not simply split pages into arbitrary vector chunks.

The compiler creates traceable **Evidence Objects**:

```text
Evidence
────────────────────────
Concept       residence.registration
Authority     Canton Zurich
Jurisdiction  CH-ZH
Source        zh.ch / Arriving
Version       22
Retrieved     04.09.2026
Content       original supporting passage
```

Every piece of evidence points back to the exact source snapshot and canonical government page.

This is the basis for citations, auditability and historical reconstruction.

---

## Slide 9 — Knowledge CI/CD

Knowledge should be maintained like software.

```text
Authoritative source
       ↓
change detected
       ↓
semantic change analysis
       ↓
affected evidence rebuilt
       ↓
regression tests execute
       ↓
immutable Knowledge Release
       ↓
publish
```

Routine changes require no human intervention. Humans review exceptions or high-risk changes.

> **This is not static RAG. It is CI/CD for knowledge.**

---

## Slide 10 — The Runtime Uses a Published Release

```text
                 BUILD PLANE

admin.ch + zh.ch
       ↓
compile + test
       ↓
swiss-public@17
       ↓
     PUBLISH

────────────────────────────────────

                 RUNTIME PLANE

MCP request
       ↓
local metadata + lexical + vector retrieval
       ↓
1–5 Evidence Objects
       ↓
Trust Envelope
       ↓
MCP response
```

A user query never sees a half-built knowledge base.

Runtime consumes one immutable published release.

---

## Slide 11 — First Test: The Standard MCP Client

Ask through the same MCP-compatible client used by the hackathon evaluation:

> **I am an EU citizen moving to Zurich for work. What do I need to do after arrival?**

TIP should retrieve:

```text
Federal SEM evidence
        +
Canton Zurich evidence
        ↓
CH-ZH applicability
        ↓
compact evidence bundle
```

The result includes:

```text
authority
jurisdiction
citations
source versions
Knowledge Release
confidence
limitations
```

The important point: **no admin.ch or zh.ch request occurs at query time.**

---

## Slide 12 — Second Test: Know When We Don't Know

Ask something outside compiled coverage, for example an exact local fee that was never sourced.

The expected result is not the nearest semantically similar paragraph.

It is:

```text
INSUFFICIENT_VERIFIED_EVIDENCE
```

or:

```text
OUT_OF_COVERAGE
```

with the missing jurisdiction/source identified where possible.

> **Knowing the boundary of trusted knowledge is part of grounding quality.**

---

## Slide 13 — Third Test: Prove It Is Not Live Web Search

After the Knowledge Release is published, temporarily disable upstream network access in the controlled demo environment.

Run the same MCP query again.

It still succeeds from the locally compiled release.

This proves visibly:

```text
MCP ≠ web search
MCP ≠ scrape-on-demand
```

The system serves versioned, previously verified evidence.

---

## Slide 14 — Fourth Test: Autonomous Freshness

Use a controlled mirror of one ingested demo source.

Simulate a substantive change:

```text
14 days
   ↓
8 days
```

The Source Watcher detects the changed content hash.

Apertus classifies:

```text
Change           SUBSTANTIVE
Concept          residence.registration_deadline
Old value        14 days
New value        8 days
Impact           HIGH
```

The real admin.ch/zh.ch source is never modified; the mirror exists only to demonstrate the production update pipeline safely.

---

## Slide 15 — Watch the Knowledge Rebuild Itself

The Admin Control Plane shows:

```text
Source version        22 → 23
Evidence affected     2
Evaluations affected  7

        ↓
Incremental compile
        ↓
Regression tests
        ↓
PASS
        ↓
swiss-public@18
        ↓
PRODUCTION
```

Ask the same MCP question again.

It now consumes Release 18.

This demonstrates freshness, autonomous maintenance, versioning, regression testing and operability in one sequence.

---

## Slide 16 — Not Another Chatbot: Swiss Arrival Checklist

The exact same Knowledge Release also powers a formal application.

Input:

```text
Nationality          [ EU/EFTA ▼ ]
Purpose              [ Employment ▼ ]
Duration             [ >3 months ▼ ]
Destination canton   [ Zurich ▼ ]
Municipality         [ Zurich ▼ ]
Arrival date         [ 04.09.2026 ]
Work start           [ 08.09.2026 ]
```

Output:

```text
Registration          REQUIRED
Residence permit      REQUIRED
Deadlines              structured
Evidence               federal + cantonal
Trust                  HIGH
```

There is no natural-language prompt.

> **AI is infrastructure, not the interface.**

---

## Slide 17 — One Knowledge Release, Many Applications

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
        myAI      Arrival Checklist   eGov App
```

A future source change is compiled once and automatically becomes available to every downstream application after release promotion.

The application does not own a separate RAG pipeline.

---

## Slide 18 — Different Information Requires Different Strategies

The admin.ch/zh.ch demo proves the **compiled authoritative knowledge** path.

The production platform additionally supports:

**Live**  
Train fares, weather, disruptions → authoritative APIs.

**Private**  
Lease, company policy → private Knowledge Spaces.

**Recommendation**  
First-date locations → places, reviews and preference scoring.

**Derived**  
Hiking/photo recommendations → structured data + live capabilities + deterministic constraints + AI ranking.

The platform chooses the appropriate information strategy rather than treating everything as RAG.

---

## Slide 19 — Why This Belongs at Swisscom

Swisscom already owns adjacent layers:

```text
                    EXPERIENCES
          myAI / eGov / Banking / Apps
                         │
                         ▼
             TRUSTED INFORMATION
                   PLATFORM
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

TIP adds the missing reusable layer between AI infrastructure and applications:

> **What information can this application trust, and how do we keep it trustworthy?**

---

## Slide 20 — Direct Swisscom Business Potential

The same technology can strengthen existing Swisscom propositions:

```text
myAI
→ richer and more trustworthy Swiss information

eGovHub
→ managed AI-ready knowledge for cantons and municipalities

Swiss AI Platform
→ more Apertus and inference consumption

Banking
→ regulatory knowledge and change intelligence

Enterprise AI
→ private Knowledge Spaces and Information Products
```

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

---

## Slide 21 — From Swiss Public to Enterprise Regulation

The architecture is domain-independent.

```text
SWISS PUBLIC
admin.ch → zh.ch → municipality
```

becomes:

```text
BANKING
EMIR → RTS/ITS → ESMA guidance → bank policy
```

or:

```text
INSURANCE
regulation → supervisory guidance → company policy → product/process
```

Reusable primitives remain the same:

```text
Source
Authority
Applicability
Evidence
Version
Knowledge Release
Trust Envelope
Knowledge CI/CD
```

---

## Slide 22 — Beyond the Hackathon

Today:

```text
admin.ch + zh.ch
       ↓
Swiss Public Knowledge Space
       ↓
MCP + Swiss Arrival Checklist
```

Tomorrow:

```text
Swiss Public
Swiss Mobility
Swiss Outdoors
Swiss Housing
FINMA
EMIR
Enterprise Knowledge
        │
        ▼
Trusted Information Platform
        │
        ▼
ANY APPLICATION
```

The hackathon implementation is therefore useful by itself while proving a much larger reusable platform.

---

## Slide 23 — What the Demo Proves Against the Challenge Criteria

```text
GROUNDING
→ official admin.ch/SEM + zh.ch evidence

CITATIONS
→ every Evidence Object traces to its source version

JURISDICTION
→ federal + CH-ZH applicability

FRESHNESS
→ autonomous source watcher + Knowledge CI/CD

AGENT EFFICIENCY
→ local compiled retrieval; small evidence bundles

SOURCE ETIQUETTE
→ no upstream crawl per user query

OPERABILITY
→ snapshots, tests, releases, rollback, Admin Control Plane

INTEGRATION READINESS
→ standard MCP + structured REST contract
```

The architecture is designed directly around the evaluation criteria rather than adding them after implementation.

---

## Slide 24 — Closing

**LLMs should not have to know everything.**

Applications should know where trustworthy information comes from—and that information should remain current without every application maintaining its own crawler and RAG stack.

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

# Swisscom Trusted Information Platform

**From admin.ch and zh.ch to continuously verified information infrastructure for any application.**
