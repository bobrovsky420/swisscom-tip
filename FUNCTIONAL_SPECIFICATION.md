# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V5

**Working product name:** Swisscom Trusted Information Platform (TIP)  
**Hackathon domain:** Swiss Public Information  
**Primary demo sources:** Swiss Confederation / admin.ch ecosystem (including SEM) and Canton Zurich / zh.ch  
**Reference MCP client:** OpenCode  
**Primary MCP transport:** Streamable HTTP; stdio optional for local development  
**Reference structured app:** Swiss Arrival Checklist  
**Stretch consumer reference app:** Swiss Hike — Flutter  
**Additional interfaces:** REST API; SDK/Webhooks as roadmap  
**Primary Swisscom semantic model:** Apertus  
**Deployment model:** Headless platform; SaaS/private SaaS/on-prem capable

---

# 1. Executive Summary

Swisscom Trusted Information Platform is a headless platform that converts authoritative knowledge, live data, private context and digital services into trustworthy structured Information Products consumable by applications and AI agents.

It is explicitly **not a chatbot**.

> **AI is infrastructure, not the interface.**

The hackathon MVP focuses on real authoritative federal and Canton Zurich information. Content from the admin.ch ecosystem and zh.ch is acquired ahead of runtime, stored as immutable snapshots, normalized, enriched with Apertus where useful, indexed, evaluated and published as immutable Knowledge Releases. Runtime requests normally query those releases rather than scraping government sites.

The demo uses four surfaces, in priority order:

1. **Admin Control Plane** — proves sourcing, ingestion, versioning, Knowledge CI/CD and operability.
2. **OpenCode** — proves standard MCP interoperability and visible agent tool selection.
3. **Swiss Arrival Checklist** — proves the same knowledge can power a formal non-chat application through REST.
4. **Swiss Hike Flutter app (stretch)** — proves TIP can power a completely different consumer product using structured inputs, live-capability abstractions and recommendation logic.

The hiking demo must not endanger the core hackathon delivery. It therefore uses a small deterministic mocked hiking dataset and mocked/cached capability responses rather than attempting to build a production Swiss hiking data platform in two days.

---

# 2. Product Vision

TIP solves a problem individual applications should not repeatedly solve themselves:

> **When an application needs information, what source should it trust, how should that source be accessed, how current is it, where does it apply, and how can the result be verified?**

```text
                           APPLICATIONS

 OpenCode/myAI   Arrival App   Flutter App   eGov   Bank Portal
       \             |             |          |         /
                    MCP / REST / SDK
                          │
                          ▼
        ┌────────────────────────────────┐
        │ TRUSTED INFORMATION PLATFORM  │
        │ Knowledge │ Live │ Context     │
        │ Rules │ Recommendations │ Trust│
        └────────────────┬───────────────┘
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
     Compiled         Live APIs       Private data
     knowledge        & services      / policies
          └──────────────┼───────────────┘
                         ▼
                      Apertus
                where semantically useful
                         │
                         ▼
                  STRUCTURED RESULT
```

---

# 3. Core Product Principles

1. **Stable information is compiled.** Laws, government guidance, administrative procedures and regulations are stored and indexed ahead of runtime.
2. **Live information is retrieved live.** Weather, fares, disruptions and availability use registered Capabilities with appropriate caching.
3. **The external authority remains canonical.** TIP stores a verified operational representation, not a replacement authority.
4. **Deterministic logic handles deterministic problems.** HTTP state, hashes, dates, numeric comparisons, route constraints and version consistency do not require an LLM.
5. **Apertus handles semantic uncertainty.** Classification, concepts, multilingual mapping, semantic change and fuzzy preference ranking are appropriate AI tasks.
6. **Autonomous by default, human review by exception.**
7. **Structured output before generated prose.**
8. **Every result carries a machine-readable Trust Envelope.**
9. **MCP is an integration protocol, not the product architecture.**
10. **The core remains model-independent, with Apertus first-class in the Swisscom deployment.**
11. **Reference applications demonstrate the platform; they are not the platform itself.**

---

# 4. Information Classes

| Class | Example | Default strategy |
|---|---|---|
| AUTHORITATIVE | What are the residence-registration requirements? | Compiled Knowledge Space |
| LIVE | What does tomorrow's train cost? | Live Capability |
| PRIVATE | Does my lease permit cats? | Private Knowledge Space |
| CONSENSUS | What are good first-date locations? | Discovery/recommendation sources |
| DERIVED | Which hike best fits tomorrow's conditions? | Knowledge + capabilities + rules |
| HISTORICAL | What rule applied in 2024? | Versioned source repository |

---

# 5. Main Hackathon Scenario — admin.ch + zh.ch

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation
       ↓
State Secretariat for Migration (SEM)
       ↓ federal context
Canton Zurich
       ↓ cantonal guidance
Municipality
```

Golden cases include direct registration questions, EU/EFTA employment context, jurisdiction mismatch, German-language queries, unsupported municipal details, historical/source-version questions and controlled source-change regression.

---

# 6. Architecture — Control Plane and Data Plane

```text
                     CONTROL PLANE
 Admin GUI
    ↓
 Source Registry
    ↓
 Scanner / Crawler / Fetcher
    ↓
 Immutable Snapshot / Normalize
    ↓
 Apertus Enrichment
    ↓
 Evidence Compilation
    ↓
 Index / Evaluate / Release

────────────────────────────────────────────

                       DATA PLANE
               Published Knowledge Release
                         │
               ┌─────────┼──────────────┐
               ▼         ▼              ▼
              MCP       REST           SDK
               │         │              │
               ▼         ├────────┐     ▼
           OpenCode   Arrival   Swiss Hike   Other Apps
                      Checklist   Flutter
```

The Admin GUI is not required for Data Plane availability.

---

# 7. Hackathon Deployment Topology

Use logical modules without unnecessary microservices:

```text
Process 1  API + MCP Runtime
Process 2  Knowledge Worker
           scanner/crawler/fetcher/compiler/evaluation
Process 3  Admin Backend
Process 4  Admin Web UI
Process 5  optional mock-capability service for Swiss Hike

PostgreSQL + pgvector
MinIO or local object storage
Optional Redis
```

Everything should start reproducibly with `docker compose up`. The Flutter app runs separately and points to the REST endpoint.

---

# 8. Shared Contracts

The `/contracts` package is the first integration deliverable. Required types:

- `SourceDefinition`
- `DiscoveredResource`
- `SourceSnapshot`
- `NormalizedDocument`
- `EvidenceObject`
- `SemanticChange`
- `KnowledgeRelease`
- `RetrievalResult`
- `TrustEnvelope`
- `CapabilityDefinition`
- `InformationProductRequest`
- `InformationProductResult`

Use Pydantic/JSON Schema and commit fixtures early so all workstreams can develop independently.

## 8.1 EvidenceObject

```json
{
  "evidence_id": "ev-zh-registration-22",
  "source_id": "zh-arriving",
  "source_version": 22,
  "authority": {"publisher": "Canton Zurich", "level": "cantonal"},
  "jurisdiction": "CH-ZH",
  "concepts": ["residence.registration", "residence.registration_deadline"],
  "applicability": {"destination_canton": "CH-ZH"},
  "content": "original supporting passage",
  "canonical_url": "...",
  "retrieved_at": "..."
}
```

## 8.2 KnowledgeRelease

```json
{
  "knowledge_space": "swiss-public",
  "release": "2026.09.04.3",
  "source_versions": {"sem-working-switzerland": 17, "zh-arriving": 22},
  "evidence_count": 143,
  "evaluation": {"total": 84, "passed": 84},
  "status": "PUBLISHED"
}
```

## 8.3 TrustEnvelope

```json
{
  "information_class": "AUTHORITATIVE",
  "confidence": 0.98,
  "knowledge_release": "swiss-public@2026.09.04.3",
  "applicability": {"jurisdiction": "CH-ZH"},
  "last_verified": "...",
  "sources": [
    {"authority": "State Secretariat for Migration", "source_id": "sem-working-switzerland"},
    {"authority": "Canton Zurich", "source_id": "zh-arriving"}
  ],
  "limitations": []
}
```

---

# 9. Module A — Domain Configuration & Contracts

Responsibilities: shared schemas, Swiss Public domain configuration, source definitions, concept vocabulary, applicability dimensions and fixtures.

Example concepts:

```text
residence.registration
residence.registration_deadline
residence.permit
employment.start
health.insurance
```

Fixtures must allow downstream teams to work before ingestion is complete.

---

# 10. Module B — Source Acquisition & Ingestion

Components:

```text
Source Registry
Scanner
Crawler
Scheduler
Fetcher
Snapshot Manager
Change Detector
Normalizer
```

The Scanner discovers candidate resources using sitemaps, links, feeds, known APIs and registered pages. The Crawler traverses only approved scopes. The Fetcher handles HTTP state, retries, rate limits, ETag and Last-Modified. The Snapshot Manager stores immutable HTML/PDF/JSON versions. The Normalizer removes boilerplate while preserving meaningful structure.

Change detection uses the cheapest mechanism first:

```text
ETag / Last-Modified
        ↓
raw content hash
        ↓
normalized content hash
        ↓
structural/text diff
        ↓
Apertus semantic analysis
```

Unchanged normalized content produces zero Apertus calls and zero recompilation.

States:

```text
DISCOVERED → ELIGIBLE → FETCHED → SNAPSHOTTED
           → NORMALIZED → READY_FOR_COMPILATION
```

Exceptions: `IGNORED`, `FETCH_FAILED`, `PARSE_FAILED`, `REVIEW_REQUIRED`, `REJECTED`.

---

# 11. Module C — Knowledge Compiler & Apertus Enrichment

Responsibilities:

- document classification;
- concept and applicability extraction;
- multilingual terminology mapping;
- authority/source relationship analysis;
- Evidence Object compilation;
- semantic change analysis;
- candidate evaluation generation.

Apertus is not authoritative. Exact evidence remains linked to the source snapshot. High-risk numeric/date facts should be validated deterministically where practical.

Example semantic change:

```json
{
  "change_type": "SUBSTANTIVE",
  "affected_concepts": ["residence.registration_deadline"],
  "old_value": {"value": 14, "unit": "days"},
  "new_value": {"value": 8, "unit": "days"},
  "impact": "HIGH"
}
```

---

# 12. Module D — Storage, Indexing & Retrieval

Recommended stack:

```text
PostgreSQL        sources, versions, documents, evidence,
                  concepts, relationships, releases, evaluations
pgvector          semantic retrieval
PostgreSQL FTS    lexical retrieval
MinIO/filesystem  immutable raw snapshots
Redis optional    hot/live cache
```

Retrieval:

```text
Applicability filter
        ↓
Authority / jurisdiction filter
        ↓
Lexical + vector retrieval
        ↓
Merge / rerank
        ↓
1–5 Evidence Objects
```

---

# 13. Module E — Trusted Information Runtime

Responsibilities:

- MCP and REST endpoints;
- query/applicability interpretation;
- retrieval orchestration;
- Trust Envelope generation;
- coverage/unsupported handling;
- Information Product execution;
- compact structured responses.

Supported states:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
```

Runtime normally accesses only published releases or registered live Capabilities, never arbitrary web pages.

---

# 14. MCP Contract and OpenCode

MVP tools:

- `swiss_information.resolve` — high-level resolution, normally one agent call.
- `swiss_information.get_evidence` — expanded evidence by ID.
- `swiss_information.get_coverage` — supported domains/jurisdictions.

OpenCode is the reference MCP client. Repository setup should include `opencode.jsonc` configured for the local Streamable HTTP endpoint and a smoke-test sequence.

The demo must make the tool invocation visible:

```text
OpenCode
   ↓
swiss_information.resolve
   ↓
TIP / swiss-public@17
   ↓
SEM + zh.ch Evidence Objects
```

Only TIP should be enabled in the core evaluation profile to keep tool selection and context use clean.

---

# 15. Module F — Admin Control Plane

The Admin GUI is required for the hackathon because it makes otherwise invisible differentiation visible.

Minimum screens:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Scanner/Crawler status
5. Source detail and immutable versions
6. Semantic changes
7. Evidence Explorer
8. Evaluations
9. Knowledge Releases / rollback
10. MCP/REST integration status

Example dashboard:

```text
SWISS PUBLIC                       ● HEALTHY
Production release                2026.09.04.3
Sources                            43
Evidence                           1,274
Tests                              183 / 183 PASS
Last scan                          11 min ago
Changes today                      4
Review required                    0
```

The Admin GUI is the Control Plane, not an end-user chatbot.

---

# 16. Module G — Evaluation & Knowledge CI/CD

Golden tests cover factual grounding, citations, jurisdiction, multilingual queries, unsupported cases, temporal/source-version behavior, response size, tool calls and latency.

Release flow:

```text
Candidate knowledge
      ↓
Build immutable release
      ↓
Regression evaluation
      ↓
PASS ──→ publish
FAIL ──→ reject/review
```

Controlled demo change:

```text
14 days → 8 days
```

Use a local/test mirror of an ingested source. Never modify or pretend to modify the official site. Demonstrate detect → semantic classify → rebuild → test → publish → clients consume new release.

---

# 17. Reference Application 1 — Swiss Arrival Checklist

Purpose: prove that the admin.ch/zh.ch Knowledge Release can power a formal non-chat application.

Inputs:

```text
Nationality category
Purpose of stay
Employment duration
Destination canton
Municipality
Arrival date
Work start date
```

Example REST request:

```json
{
  "nationality_group": "EU_EFTA",
  "purpose": "EMPLOYMENT",
  "employment_duration": "MORE_THAN_3_MONTHS",
  "destination": {"canton": "CH-ZH", "municipality": "Zurich"},
  "arrival_date": "2026-09-04",
  "employment_start_date": "2026-09-08"
}
```

Output is a typed checklist containing requirement status, deadlines, authorities, evidence IDs and Trust Envelope. No natural-language prompt is required.

---

# 18. Reference Application 2 — Swiss Hike Flutter App (Stretch)

## 18.1 Purpose

Swiss Hike is a deliberately small mobile reference application demonstrating that TIP can power a completely different consumer product. It is **not part of the critical path** and must only be implemented after the admin.ch/zh.ch → Knowledge Release → OpenCode → Arrival Checklist path works end-to-end.

It proves:

- TIP is not chatbot-specific;
- applications can submit formal structured intent;
- TIP can combine stable data, live-capability abstractions and deterministic constraints;
- Flutter/mobile clients consume the same headless REST platform;
- AI can rank/explain fuzzy preferences without becoming the UI.

## 18.2 UI

```text
┌────────────────────────────────────┐
│ Swiss Hike                         │
│                                    │
│ Start        [ Zürich HB       ▼ ] │
│ Date         [ Tomorrow        ▼ ] │
│ Hiking time  [ 4h              ]   │
│ Difficulty   [ Moderate        ▼ ] │