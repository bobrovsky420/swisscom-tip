# Swisscom Trusted Information Platform
## First-Round Pitch — Maximum 10 Minutes

**Recommended format:** 7 slides, ~8 minutes presentation + ~2 minutes buffer/questions.  
**Goal:** sell the idea and differentiation without overloading the first round with production-operations detail.

---

# Slide 1 — The Idea
## From AI that talks to AI that knows what to trust

### Swisscom Trusted Information Platform

**A headless platform that turns authoritative and live information into trustworthy information services for any application.**

Most AI systems are good at language but unreliable at knowing:

- which source is authoritative;
- where a rule applies;
- whether information is current;
- whether an answer can be defended.

> **AI is infrastructure, not the interface.**

TIP can power a chatbot, mobile app, eGovernment portal or banking workflow.

### Speaker notes — ~60 sec

The hackathon asks for an MCP server for Swiss public information. We see a larger opportunity: solve trusted information once as reusable infrastructure. The product is not another chatbot or generic RAG UI.

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

This requires complementary federal and cantonal evidence.

```text
Swiss Confederation
       ↓
SEM / federal guidance
       ↓
Canton Zurich guidance
       ↓
user context
```

### Speaker notes — ~60 sec

Rather than pretending to cover all Switzerland in two days, we prove a credible architecture with real official sources. The scenario tests authority, jurisdiction and applicability rather than only semantic matching.

---

# Slide 3 — Build Trusted Knowledge Once, Serve It Fast

For the hackathon we intentionally keep operations simple:

```text
[ BUILD / FULL RELOAD ]
          ↓
admin.ch / zh.ch
          ↓
immutable source snapshots
          ↓
normalize + Apertus enrichment
          ↓
Evidence Objects
          ↓
index + tests
          ↓
Knowledge Release
          ↓
MCP / REST
```

Normal user questions do **not** scrape government sites.

> **Hackathon: repeatable full builds. Production: autonomous Knowledge CI/CD.**

### Speaker notes — ~75 sec

We do not need a scheduler or continuous refresher to prove the platform. An administrator triggers a full build of the configured scope. The resulting local release is versioned and tested. Scheduled revalidation, semantic change detection and incremental refresh are part of the production design, not the hackathon critical path.

---

# Slide 4 — One Platform, Different Clients

The demo uses three core surfaces:

```text
                    TIP
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
 Admin Control    OpenCode       Arrival
     Plane          MCP          Checklist
```

**Admin Control Plane**  
Shows official sources, the Build/Full Reload action, snapshots, evidence, tests and releases.

**OpenCode**  
Reference MCP client; shows the `swiss_information.resolve` call and evidence.

**Swiss Arrival Checklist**  
Formal inputs → structured result. No chat prompt.

### Speaker notes — ~75 sec

OpenCode proves standard MCP integration, but the Arrival Checklist is equally important because it proves TIP is not chatbot infrastructure. Both consume the same published knowledge.

---

# Slide 5 — Search Returns Evidence, Not Answers

Internally:

```text
Request
  ↓
Execution Plan
  ↓
filter by authority / jurisdiction / date
  ↓
lexical + semantic + concept retrieval
  ↓
2–5 best Evidence Objects
  ↓
resolve facts / conflicts
  ↓
Trust Envelope
```

Only then does an LLM generate prose if the client needs prose.

Optional stretch proof: a small Flutter **Swiss Hike** app submits structured constraints and consumes typed results using 10–20 demo routes plus mocked transport/weather/places providers.

### Speaker notes — ~75 sec

This is deliberately not “vector search and let the LLM decide.” TIP knows why evidence applies. Hard facts and rules are resolved before optional natural-language generation. The hiking app, if time allows, demonstrates the same headless platform for a totally different consumer product.

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
- **Swiss AI Platform:** Apertus/inference consumption;
- **Banking:** FINMA/EMIR/regulatory intelligence;
- **Enterprise:** private Knowledge Spaces and Information Products.

### Speaker notes — ~90 sec

This is not an unrelated startup idea. TIP sits naturally between Swisscom's AI infrastructure and the applications that need reliable information. It creates direct SaaS/API opportunities while increasing the value of the underlying AI platform.

---

# Slide 7 — Start Small, Grow Into a Platform

Hackathon:

```text
admin.ch + zh.ch
       ↓
on-demand full build
       ↓
Swiss Public release
       ↓
OpenCode + Arrival Checklist
```

Production evolution:

```text
scheduled source monitoring
incremental refresh
semantic change analysis
Knowledge CI/CD
live capabilities
consumer Information Products
FINMA / EMIR / private enterprise knowledge
```

### Closing

> **Apertus provides semantic intelligence.**  
> **TIP provides trusted information, context and orchestration.**  
> **Swisscom provides infrastructure, sovereignty and distribution.**

**We start with admin.ch and zh.ch—but we are building trustworthy information infrastructure for any application.**

### Speaker notes — ~75 sec

The key is disciplined scope. We prove the source → evidence → release → application path first. Autonomous refresh is a logical production extension once the core model is proven.

---

# Optional 60-Second Live Demo

1. Show Admin Control Plane with configured `admin.ch/SEM` + `zh.ch` and the latest successful full build.
2. Briefly show the published release and test status.
3. Switch to OpenCode.
4. Ask the Zurich-arrival question.
5. Show one `swiss_information.resolve` call returning federal + CH-ZH evidence.
6. End on the Arrival Checklist for 5–10 seconds.

Do **not** spend first-round time demonstrating automatic source refresh; it is explicitly production roadmap.

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
| Buffer | **1:30** |

---

# What NOT to Put Into the First-Round Pitch

Keep for technical/final discussions:

- scheduler implementation;
- semantic diff pipeline;
- incremental refresh machinery;
- PostgreSQL schema;
- full crawler state machine;
- every MCP schema;
- detailed hiking mock JSON;
- detailed UBS comparison;
- full marketplace model.

The jury should leave with four messages:

1. **This solves the original Swiss public-information challenge.**
2. **It creates versioned, testable trusted evidence instead of doing scrape-on-demand RAG.**
3. **It is a headless platform, not another chatbot.**
4. **It has a credible path into Swisscom's consumer, public-sector and enterprise businesses.**
