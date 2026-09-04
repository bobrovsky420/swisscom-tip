# Swisscom Trusted Information Platform
## First-Round Pitch — Maximum 10 Minutes

**Recommended format:** 7 slides, ~8 minutes presentation + ~2 minutes buffer/questions.  
**Goal:** sell the idea and differentiation. Do not explain every architectural component.

---

# Slide 1 — The Idea
## From AI that talks to AI that knows what to trust

### Swisscom Trusted Information Platform

**A headless platform that turns authoritative and live information into trustworthy, continuously maintained information services for any application.**

Most AI systems are good at language but unreliable at knowing:

- which source is authoritative;
- where a rule applies;
- whether information is current;
- what changed;
- whether an answer can be defended.

Our principle:

> **AI is infrastructure, not the interface.**

TIP can power a chatbot, a mobile app, an eGovernment portal or a banking workflow.

### Speaker notes — ~60 sec

The hackathon asks us to make Swiss public information available through MCP. We see a larger opportunity: solve the trusted-information problem once as reusable infrastructure. The product is not a chatbot and not another RAG UI. It is the layer applications use when they need reliable information.

---

# Slide 2 — Hackathon Proof: admin.ch + zh.ch

We start deliberately small and authoritative:

```text
Swiss Confederation / admin.ch ecosystem
                 +
           Canton Zurich / zh.ch
```

Demo scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

The answer requires complementary federal and cantonal information.

```text
Swiss Confederation
       ↓
SEM / federal guidance
       ↓
Canton Zurich guidance
       ↓
Municipality / user context
```

This tests **authority + jurisdiction + applicability**, not just semantic search.

### Speaker notes — ~60 sec

Rather than claiming all-Switzerland coverage after two days, we demonstrate a credible foundation using real official sources. The scenario is simple to understand but technically useful because the system has to combine federal and Zurich-specific evidence correctly.

---

# Slide 3 — The Differentiator: Knowledge CI/CD

Normal user requests do **not** scrape government websites.

```text
admin.ch / zh.ch
       ↓
scan + fetch
       ↓
immutable source snapshots
       ↓
normalize + Apertus enrichment
       ↓
Evidence Objects
       ↓
tests
       ↓
Knowledge Release
       ↓
MCP / REST
```

When a source changes:

```text
change detected
      ↓
semantic impact analysed
      ↓
affected evidence rebuilt
      ↓
regression tests
      ↓
new version published
```

> **CI/CD for knowledge, not static RAG.**

### Speaker notes — ~75 sec

This is the core differentiator. Stable authoritative information is compiled ahead of time, locally stored, versioned and tested. That improves latency, reproducibility, source etiquette and auditability. Apertus is used where semantic intelligence matters—classification, concepts, multilingual mapping and semantic change detection—while deterministic software handles hashes, dates and versions.

---

# Slide 4 — One Platform, Different Clients

The demo uses three surfaces, each proving something different:

```text
                    TIP
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
 Admin Control    OpenCode       Arrival
     Plane          MCP          Checklist
       │             │              │
       ▼             ▼              ▼
 build/maintain   AI agent      structured app
```

**Admin Control Plane**  
Shows sources, versions, changes, evidence, tests and releases.

**OpenCode**  
Reference MCP client; makes `swiss_information.resolve` and its evidence visible.

**Swiss Arrival Checklist**  
Formal inputs → structured result. No chat prompt.

### Speaker notes — ~75 sec

OpenCode proves standard MCP integration, but we explicitly do not want the project to look like another chatbot. The Arrival Checklist consumes exactly the same Knowledge Release through REST using typed fields. The Admin GUI exposes how the knowledge is sourced and maintained.

---

# Slide 5 — Stretch Proof: Swiss Hike Mobile App

If the core demo is complete, we add a tiny Flutter reference app:

```text
Starting point       Zürich HB
Date                 Tomorrow
Hiking time          ~4h
Difficulty           Moderate
Travel               ≤90 min
Preferences          Lake + Panorama
                     Good weather
                     Restaurant near end

                [ Find hikes ]
```

No hidden natural-language prompt.

The app calls a typed Information Product:

```text
Flutter
   ↓ REST
swiss-hike-finder
   ↓
structured route results
```

### Demo data strategy

Do **not** build a complete hiking-data ecosystem during the hackathon.

Use 10–20 curated deterministic demo routes plus replaceable mock providers:

```text
routes.json
transport.json
weather.json
restaurants.json
```

```text
MockTransportProvider
MockWeatherProvider
MockPlacesProvider
```

All mock responses are visibly marked `DEMO/MOCK`.

Hard constraints are deterministic; soft preferences can use Apertus/ranking.

### Speaker notes — ~75 sec

The hiking app is a stretch demonstration, not part of the critical path. Its purpose is to prove that TIP can power a completely different consumer product. We mock data behind the same provider interfaces that future real SBB/weather/places adapters would implement, so the application contract does not change.

---

# Slide 6 — Why Swisscom?

TIP connects businesses Swisscom already has:

```text
                    EXPERIENCES
          myAI / eGov / Banking / Apps
                         │
                         ▼
             TRUSTED INFORMATION
                   PLATFORM
                         │
              Knowledge │ Data
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

Potential value:

- **myAI:** richer trustworthy Swiss information;
- **eGovHub:** AI-ready knowledge for cantons and municipalities;
- **Swiss AI Platform:** drives Apertus/inference consumption;
- **Banking:** FINMA/EMIR/regulatory intelligence;
- **Enterprise:** private Knowledge Spaces and Information Products.

Possible monetisation:

**SaaS + API/MCP usage + managed knowledge + enterprise tenants + regulatory intelligence + future marketplace.**

### Speaker notes — ~90 sec

This does not ask Swisscom to create an unrelated business. TIP sits between its AI infrastructure and the applications that need reliable information. It can generate direct platform revenue while also increasing the value and consumption of Apertus, Swiss AI Platform, eGovHub and banking services.

---

# Slide 7 — Why It Can Become Much Bigger

The hackathon starts here:

```text
admin.ch + zh.ch
       ↓
Swiss Public
       ↓
OpenCode + Arrival Checklist
```

The same primitives extend to:

```text
CONSUMER
Swiss Hiking
Cycling
Photo Scout
Housing
Local discovery

ENTERPRISE
FINMA
EMIR
DORA
internal policies
regulatory impact
```

Reusable core:

```text
Source
Authority
Applicability
Evidence
Version
Trust
Knowledge CI/CD
Information Product
```

### Closing

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

**We start with admin.ch and zh.ch—but we are building trustworthy information infrastructure for any application.**

### Speaker notes — ~75 sec

The Swiss Public MCP is the first domain pack and first integration, not the end product. The architecture is deliberately reusable. Replace admin.ch and zh.ch with EMIR, FINMA and internal policies and the same platform becomes enterprise regulatory infrastructure.

---

# Optional 60-Second Live Demo

If the first-round format allows a live demo, use only one short sequence rather than the full technical demonstration:

1. Show Admin Control Plane with `admin.ch/SEM` + `zh.ch` and `swiss-public@17` healthy.
2. Switch to OpenCode.
3. Ask the Zurich-arrival question.
4. Briefly show that `swiss_information.resolve` was called once and returned federal + CH-ZH evidence.
5. End on the Arrival Checklist or Flutter Hike screen for 5–10 seconds to reinforce that TIP is not a chatbot.

Do **not** demonstrate source-change simulation in round one unless specifically asked; keep that for the technical/final round.

---

# Timing Guide

| Part | Target |
|---|---:|
| Slide 1 | 1:00 |
| Slide 2 | 1:00 |
| Slide 3 | 1:15 |
| Slide 4 | 1:15 |
| Slide 5 | 1:15 |
| Slide 6 | 1:30 |
| Slide 7 | 1:15 |
| **Total slides** | **8:30** |
| Buffer / transition / short question | **1:30** |

If a 60-second live demo is included, shorten Slides 4–5 and target ~7:30 of spoken presentation.

---

# What NOT to Put Into the First-Round Pitch

Keep these for technical questions or the final round:

- PostgreSQL table design;
- pgvector implementation details;
- full crawler state machine;
- every MCP schema;
- detailed source-change simulation;
- all 7 hackathon workstreams;
- detailed UBS comparison;
- full marketplace model;
- complete hiking mock JSON schemas.

The first round should leave the jury with four messages:

1. **This solves the original Swiss public-information challenge.**
2. **Knowledge CI/CD makes it materially different from ordinary RAG.**
3. **It is a headless platform, not another chatbot.**
4. **It has a credible strategic and commercial fit with Swisscom.**
