# Swisscom Trusted Information Platform
## First-Round Pitch — Maximum 10 Minutes

**Format:** 7 slides, ~8:30 presentation + buffer.  
**Goal:** sell the core hackathon idea and Swisscom potential without expanding MVP scope.

---

# Slide 1 — The Idea
## From AI that talks to AI that knows what to trust

**Swisscom Trusted Information Platform** is a headless platform that turns authoritative and live information into trustworthy structured services for any application.

> **AI is infrastructure, not the interface.**

TIP can power myAI, a mobile app, eGovernment, a banking portal or an automated workflow.

**Speaker note (~60s):** The hackathon asks for Swiss public information through MCP. We solve the underlying trusted-information problem as reusable infrastructure rather than another chatbot/RAG UI.

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

# Slide 3 — Build Trusted Knowledge, Then Serve It

Hackathon MVP:

```text
[ BUILD / FULL RELOAD ]
        ↓
scan + fetch official sources
        ↓
immutable snapshots
        ↓
normalize + Apertus enrichment
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
- **OpenCode:** independent MCP integration and visible `swiss_information.resolve` call.
- **Arrival Checklist:** formal fields → typed result; no chat prompt.

Stretch only: **Flutter Swiss Hike** using 10–20 clearly labelled DEMO/MOCK routes plus mock transport/weather/places providers.

> **Same platform. No shared user interface.**

**Speaker note (~75s):** OpenCode proves MCP; Arrival proves non-chat integration; Hike is only a stretch architecture proof.

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

Apertus handles semantic uncertainty; deterministic software handles dates, hashes, numeric constraints and rules.

**Speaker note (~75s):** The LLM does not receive dozens of documents and improvise. TIP first establishes the evidence and facts.

---

# Slide 6 — Why Swisscom? And Where the Business Can Go

```text
myAI / eGov / Mobile / Banking / Enterprise
                    ↓
                  TIP
                    ↓
             Apertus / Swiss AI Platform
```

Direct value: API/MCP usage, SaaS, managed knowledge, enterprise deployments, regulatory intelligence and increased AI-platform consumption.

**Post-MVP marketplace opportunity:** trusted publishers can distribute **Data Products** through TIP.

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

**Speaker note (~90s):** Swisscom can monetize consumption while publishers gain a machine-consumption distribution channel. Free public data can still drive hosting, SLA, inference and derived-product revenue.

---

# Slide 7 — Start Focused, Build a Platform

Hackathon:

```text
admin.ch + zh.ch
       ↓
on-demand trusted Knowledge Release
       ↓
OpenCode + Arrival Checklist
```

Full product:

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

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

**Speaker note (~75s):** The marketplace and autonomous refresh are the product vision, not two-day deliverables. The hackathon proves the foundation they need.

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