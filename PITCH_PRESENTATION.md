# Pitch Presentation — Swisscom Trusted Information Platform

## Slide 1 — From AI that talks to AI that knows where to look

# Swisscom Trusted Information Platform

**Turning Switzerland's information into trustworthy infrastructure for applications and AI.**

Most AI systems are excellent at language but unreliable at knowing what is current, authoritative or applicable. We solve that problem once, as infrastructure, rather than separately inside every chatbot and application.

---

## Slide 2 — The Original Challenge

**Make authoritative Swiss public information accessible to AI assistants.**

The server must be:

- correct;
- current;
- cited;
- jurisdiction-aware;
- efficient;
- maintainable;
- easy to integrate.

Our insight:

> **The hard problem is not search. It is trust and maintenance.**

A useful system must know:

```text
Where does truth come from?
Does it apply here?
Is it current?
What changed?
Can the answer be defended?
```

---

## Slide 3 — Don't Build Another Chatbot

The common industry pattern is:

```text
Chat
 ↓
LLM
 ↓
RAG
```

Our proposal:

```text
PURPOSE-BUILT APPLICATION
          │
    structured intent
          │
          ▼
TRUSTED INFORMATION PLATFORM
          │
 Knowledge + Live Data
 + Context + Services
          │
          ▼
    structured result
```

> **AI is infrastructure, not the interface.**

Chat is only one possible client.

---

## Slide 4 — One Platform, Many Experiences

The same platform can power:

```text
myAI
municipality portal
Swiss Arrival Checklist
hiking mobile app
photo scouting app
housing application
banking portal
compliance workflow
insurance platform
```

No application needs to build its own crawling, RAG, freshness, source ranking and provenance infrastructure.

---

## Slide 5 — The Hackathon Demo: Federal + Zurich

Use a real everyday scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

The platform combines:

```text
Swiss Confederation
       │
       ▼
State Secretariat for Migration
       │ federal context
       ▼
Canton Zurich
       │ cantonal guidance
       ▼
Municipality
```

This demonstrates authority, jurisdiction, applicability and cross-source evidence rather than merely semantic search.

---

## Slide 6 — We Show Where the Knowledge Comes From

The demo starts before the question is asked.

```text
admin.ch / SEM + zh.ch
          ↓
       Scanner
          ↓
       Crawler
          ↓
       Fetcher
          ↓
  immutable snapshots
          ↓
      Normalize
          ↓
 Apertus enrichment
          ↓
  Evidence Objects
```

The audience sees authoritative information becoming an AI-ready Knowledge Release.

---

## Slide 7 — Stable Knowledge Is Compiled

Normal MCP requests do **not** scrape government websites.

```text
Official source
      ↓
versioned snapshot
      ↓
compiled knowledge
      ↓
local search/index
      ↓
MCP / REST
```

Benefits:

- low latency;
- reproducibility;
- auditability;
- resilience;
- source etiquette;
- lower token and network cost.

The government remains the canonical authority; the platform maintains a verified operational representation.

---

## Slide 8 — Different Questions Require Different Truth

**Authoritative**  
“Can my landlord prohibit cats?” → law/government sources.

**Live**  
“What does tomorrow's train cost?” → transport provider/API.

**Recommendation**  
“Which places are good for a first date?” → current places, reviews and preferences.

**Hybrid**  
“Which hike fits tomorrow's conditions?” → routes + transport + weather + places + preference scoring.

The platform uses the correct evidence strategy for each information type.

---

## Slide 9 — Autonomous Knowledge CI/CD

Knowledge should be maintained like software.

```text
Authoritative source
       ↓
change detected
       ↓
Apertus understands change
       ↓
affected knowledge rebuilt
       ↓
tests execute
       ↓
new version published
```

Routine updates require no human intervention. Humans review exceptions.

> **This is not static RAG. It is continuously tested knowledge.**

---

## Slide 10 — Apertus as the Knowledge Engineer

Apertus is not the source of truth.

Apertus provides semantic intelligence:

```text
classify documents
extract concepts
map multilingual terminology
analyse semantic changes
identify applicability candidates
generate evaluation tests
rerank evidence
explain recommendations
```

Deterministic software handles dates, hashes, numeric constraints, HTTP state and source identity.

> **Use AI for semantic uncertainty; software for deterministic certainty.**

---

## Slide 11 — The Trust Envelope

Every result tells the application not only **what**, but **why it should trust it**.

```text
information type
authority
source
jurisdiction
applicability
validity
freshness
knowledge version
confidence
limitations
```

A legal rule is deliberately represented differently from a restaurant recommendation.

---

## Slide 12 — Not Only MCP: Swiss Arrival Checklist

The same Knowledge Release powers a formal application.

Input:

```text
Nationality          EU/EFTA
Purpose              Employment
Duration             >3 months
Destination canton   Zurich
Municipality         Zurich
Arrival date         04.09.2026
Work start            08.09.2026
```

Output:

```text
Registration          REQUIRED
Residence permit      REQUIRED
Deadline              structured
Evidence              federal + cantonal
Trust                 HIGH
```

There is no natural-language prompt.

This proves that the platform is information infrastructure, not chatbot infrastructure.

---

## Slide 13 — Information Products

Developers can publish formal reusable capabilities.

Examples:

```text
Swiss Arrival Checklist
Swiss Hike Finder
Swiss Photo Scout
Swiss Housing Advisor
EMIR Applicability
Regulatory Impact
```

Each combines:

```text
Input Schema
+
Knowledge Spaces
+
Live Capabilities
+
Rules
+
Optional AI
+
Output Schema
```

The same product can be exposed through MCP, REST or an SDK.

---

## Slide 14 — Admin Control Plane

The platform includes an operational GUI, not an end-user chatbot.

It shows:

```text
Knowledge Spaces
Sources
Scanner/Crawler status
Source versions
Semantic changes
Evidence
Tests
Knowledge Releases
MCP/API integration
```

Without the Control Plane, a judge sees “question → answer”.

With it, the judge sees the actual platform:

```text
official source
→ snapshot
→ evidence
→ tests
→ release
→ application
```

---

## Slide 15 — The Demo Moment

1. Open the Admin Control Plane.
2. Show real SEM/admin.ch and zh.ch sources.
3. Build `swiss-public@17`.
4. Show immutable snapshots and Evidence Objects.
5. Ask the Swiss question through the standard MCP client.
6. Receive federal + Zurich evidence, citations and jurisdiction.
7. Open Swiss Arrival Checklist and obtain the same facts through structured inputs.
8. Change a controlled source mirror: `14 days → 8 days`.
9. Watch semantic change detection, rebuild and tests.
10. Publish `swiss-public@18`.
11. Repeat both clients; both now consume Release 18.

**One knowledge change updates multiple applications.**

---

## Slide 16 — Why This Belongs at Swisscom

Swisscom already owns adjacent layers:

- Swiss AI infrastructure and managed inference;
- Apertus availability;
- myAI and consumer AI experiences;
- eGovernment/eGovHub relationships;
- banking and regulatory services;
- Swiss infrastructure and trust positioning.

TIP adds the missing reusable layer:

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

Models provide intelligence. **TIP tells models and applications what to trust.**

---

## Slide 17 — Business Value for Swisscom

Potential direct revenue:

```text
Knowledge SaaS
API / MCP consumption
private enterprise tenants
managed knowledge services
premium Information Products
regulatory intelligence
marketplace commission
integration services
private deployment
```

Indirect value:

```text
Apertus inference
Swiss AI Platform consumption
eGovHub differentiation
myAI utility
banking services
enterprise retention
```

---

## Slide 18 — Consumer to Enterprise

Consumer Information Products:

```text
Swiss Public
Hiking
Cycling
Photo Scout
Housing
Local Discovery
```

Enterprise Information Products:

```text
FINMA
EMIR
DORA
internal policies
regulatory impact
```

Same platform primitives:

```text
knowledge
data
context
rules
trust
reasoning
structured result
```

---

## Slide 19 — Beyond the Hackathon

Today:

```text
Swiss Public → MCP + Arrival Checklist
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

---

## Slide 20 — Closing

**LLMs should not have to know everything.**

They—and ordinary applications—should know where trustworthy information comes from.

> **Apertus provides intelligence.**  
> **TIP provides truth, context and orchestration.**  
> **Swisscom provides trust, infrastructure and distribution.**

# Swisscom Trusted Information Platform

**Trustworthy information infrastructure for the AI economy.**
