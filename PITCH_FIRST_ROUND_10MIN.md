# Swisscom Trusted Information Platform
## First-Round Pitch — Maximum 10 Minutes

**Format:** 7 slides, ~8:30 presentation + buffer.  
**Goal:** sell a credible hackathon vertical slice and the target product it validates.

---

# Slide 1 — The Idea
## From AI that talks to AI that knows what to trust

**Swisscom Trusted Information Platform** is a headless platform that turns authoritative and live information into trustworthy structured services for any application.

The hackathon MCP server is its first narrow vertical slice—not the complete product vision.

> **AI is infrastructure, not the interface.**

TIP can power myAI, a mobile app, eGovernment, a banking portal or an automated workflow.

**Speaker note (~60s):** The published challenge asks for Swiss public information through MCP. Our product hypothesis is larger: solve the underlying trusted-information problem as reusable infrastructure rather than another chatbot/RAG UI. The MCP server is the focused proof.

---

# Slide 2 — Hackathon Proof: admin.ch + zh.ch

We deliberately start small and authoritative:

```text
admin.ch / SEM
      +
Canton Zurich / zh.ch
```

Demo scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

This tests authority, jurisdiction and applicability rather than only semantic similarity.

**Speaker note (~60s):** Real official data, focused coverage, credible foundation.

---

# Slide 3 — Hackathon Vertical Slice: Build, Then Serve

Hackathon MVP:

```text
[ BUILD / FULL RELOAD ]
        ↓
scan + fetch official sources
        ↓
immutable snapshots
        ↓
normalize + semantic enrichment
       (Apertus preferred)
        ↓
Evidence Objects
        ↓
tests
        ↓
immutable Knowledge Release
        ↓
MCP / REST
```

Normal requests do **not** scrape government websites.

For the hackathon, builds are **on demand**. Scheduled/incremental Knowledge CI/CD remains in the production roadmap, not the MVP.

**Speaker note (~75s):** This gives predictable latency, citations, auditability and source etiquette without spending two days building scheduling infrastructure.

---

# Slide 4 — One Platform, Different Clients

```text
                    TIP
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
 Admin Control    OpenCode       Arrival
     Plane          MCP          Checklist
```

- **Admin Control Plane:** sources, build, evidence, tests, releases.
- **OpenCode:** one standards-compatible example client with a visible `swiss_information.resolve` call.
- **Arrival Checklist:** formal fields → typed result; no chat prompt.

Stretch only: **Flutter Swiss Hike** using 10–20 clearly labelled DEMO/MOCK routes plus mock transport/weather/places providers.

> **Same platform. No shared user interface.**

**Speaker note (~75s):** OpenCode demonstrates standard MCP compatibility; Arrival proves non-chat integration; Hike is only a stretch architecture proof. The server does not depend on OpenCode-specific behaviour.

---

# Slide 5 — Runtime: Search Returns Evidence, Not Answers

```text
Request
  ↓
Query Planner
  ↓
Authority / jurisdiction / date filters
  ↓
lexical + vector + concept search
  ↓
2–5 Evidence Objects
  ↓
Evidence / Rule Engine
  ↓
structured facts + Trust Envelope
  ↓
optional prose
```

Apertus is our preferred model for semantic uncertainty, but the core is model-independent and can use another compatible provider. Deterministic software handles dates, hashes, numeric constraints and rules.

**Speaker note (~75s):** The LLM does not receive dozens of documents and improvise. TIP first establishes the evidence and facts.

---

# Slide 6 — Target Product Vision: Why Swisscom?

**Team product and business hypothesis:**

```text
myAI / eGov / Mobile / Banking / Enterprise
                    ↓
                  TIP
                    ↓
             Apertus / Swiss AI Platform
```

Direct value: API/MCP usage, SaaS, managed knowledge, enterprise deployments, regulatory intelligence and increased AI-platform consumption.

**Target-product marketplace opportunity:** trusted publishers can distribute **Data Products** through TIP.

```text
Government │ SIX-like data providers │ Companies │ Experts
                         ↓
                    Data Products
                         ↓
                    Swisscom TIP
          hosting │ trust │ metering │ billing
                         ↓
                Apps / Enterprises / myAI
```

Possible commercial models: revenue share per request, monthly/annual licensing, one-time licensing, publisher-hosted SaaS, or free/open government packs.

**Important:** publisher onboarding, billing, metering and settlement are **not part of the hackathon MVP**.

**Speaker note (~90s):** The hackathon does not implement this commercial layer. It validates the source, evidence, trust, release and distribution concepts the target product needs. Swisscom can later monetize consumption while publishers gain a machine-consumption distribution channel.

---

# Slide 7 — Start Focused, Build a Platform

Hackathon proof:

```text
admin.ch + zh.ch
       ↓
on-demand trusted Knowledge Release
       ↓
Standard MCP clients + Arrival Checklist
        (OpenCode demo)
```

Target product:

```text
Swiss Public │ Mobility │ Hiking │ Housing
FINMA │ EMIR │ DORA │ Enterprise Knowledge
                 +
Publisher Data Product Marketplace
```

Reusable core:

```text
Source │ Authority │ Applicability │ Evidence
Version │ Trust │ Capability │ Information Product
Data Product │ Entitlement │ Usage
```

> **Apertus is our preferred semantic model; TIP remains model-independent.**<br>
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

**Speaker note (~75s):** This is one product across two horizons. The two-day vertical slice proves a working Swiss-grounding service; the target product evolves the same contracts into automated knowledge operations, more domains and a publisher ecosystem.

---

# Timing

| Slide | Target |
|---|---:|
| 1 | 1:00 |
| 2 | 1:00 |
| 3 | 1:15 |
| 4 | 1:15 |
| 5 | 1:15 |
| 6 | 1:30 |
| 7 | 1:15 |
| **Total** | **8:30** |

Keep detailed crawler design, database schemas, autonomous refresh, billing/settlement and marketplace workflows for later rounds/Q&A.
