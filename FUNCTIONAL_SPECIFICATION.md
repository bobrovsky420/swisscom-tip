# Swisscom Trusted Information Platform
## Functional & Solution Design Specification — V6

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

The runtime is deliberately more structured than ordinary RAG. A request is converted into an explicit **Execution Plan** describing intent, concepts, applicability, information class, required Knowledge Spaces/Capabilities and evidence budget. Retrieval then applies hard authority/jurisdiction/date filters before hybrid lexical/vector/concept search. The resulting Evidence Objects are reranked, facts are resolved by concept, overlaps and conflicts are handled explicitly, and a compact **Evidence Bundle + Trust Envelope** is returned. Natural-language generation is optional and happens only after the platform has established the evidence.

The demo uses four surfaces, in priority order:

1. **Admin Control Plane** — proves sourcing, ingestion, versioning, Knowledge CI/CD and operability.
2. **OpenCode** — proves standard MCP interoperability and visible agent tool selection.
3. **Swiss Arrival Checklist** — proves the same knowledge can power a formal non-chat application through REST.
4. **Swiss Hike Flutter app (stretch)** — proves TIP can power a completely different consumer product using structured inputs, live-capability abstractions and recommendation logic.

The hiking demo must not endanger the core hackathon delivery. It uses a small deterministic mocked hiking dataset and mocked/cached capability responses rather than attempting to build a production Swiss hiking data platform in two days.

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
12. **Search returns evidence, not answers.** Facts and rules are resolved from evidence before optional prose generation.
13. **Minimum sufficient evidence.** Runtime should normally return 2–5 diverse, high-quality Evidence Objects rather than large context dumps.

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
                   Query Planner
                         │
             Retrieval / Capability Engine
                         │
                Evidence / Rule Engine
                         │
                  Result Assembler
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
- `ExecutionPlan`
- `CandidateFact`
- `EvidenceBundle`
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

## 8.3 ExecutionPlan

```json
{
  "information_class": "AUTHORITATIVE",
  "knowledge_spaces": ["swiss-public"],
  "concepts": ["residence.registration", "residence.permit"],
  "applicability": {
    "jurisdiction": "CH-ZH",
    "nationality_group": "EU_EFTA",
    "purpose": "EMPLOYMENT"
  },
  "requested_date": "2026-09-04",
  "retrieval_strategy": "HYBRID",
  "max_evidence": 4
}
```

## 8.4 EvidenceBundle

```json
{
  "status": "SUPPORTED",
  "applicability": {
    "jurisdiction": "CH-ZH",
    "nationality_group": "EU_EFTA",
    "purpose": "EMPLOYMENT"
  },
  "facts": [
    {
      "concept": "residence.registration_deadline",
      "value": 14,
      "unit": "days",
      "evidence": ["ev-sem-registration-17", "ev-zh-registration-22"]
    }
  ],
  "evidence": ["ev-sem-registration-17", "ev-zh-registration-22"],
  "trust": {
    "knowledge_release": "swiss-public@2026.09.04.3",
    "confidence": 0.98
  }
}
```

## 8.5 TrustEnvelope

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
- candidate fact extraction for important concepts;
- semantic change analysis;
- candidate evaluation generation.

Apertus is not authoritative. Exact evidence remains linked to the source snapshot. High-risk numeric/date facts should be validated deterministically where practical.

Frequently used stable facts such as deadlines, rates, thresholds, effective dates and boolean obligations SHOULD be extracted during compilation when confidence and validation permit. This reduces runtime model work while retaining the original evidence as the basis for every fact.

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
                  concepts, candidate facts, relationships,
                  releases, evaluations
pgvector          semantic retrieval
PostgreSQL FTS    lexical retrieval
MinIO/filesystem  immutable raw snapshots
Redis optional    hot/live cache
```

Retrieval SHALL use hard filters before similarity search:

```text
Published Knowledge Release
        ↓
validity date
        ↓
jurisdiction / applicability
        ↓
authority / trust policy
        ↓
lexical + vector + concept retrieval
        ↓
merge / rerank
        ↓
diversity-aware selection
        ↓
2–5 Evidence Objects
```

Ranking SHOULD combine multiple signals rather than raw embedding similarity:

```text
final_score =
    lexical_relevance
  + semantic_relevance
  + concept_match
  + authority_weight
  + jurisdiction_specificity
  + applicability_match
  + temporal_validity
  + source_quality
```

Weights are domain-configurable. Selection should avoid returning several near-duplicate passages from one page when complementary authoritative evidence exists.

---

# 13. Module E — Trusted Information Runtime

The runtime is split logically into four engines:

```text
REQUEST
   ↓
1. Query Planner
   ↓
2. Retrieval / Capability Engine
   ↓
3. Evidence & Rule Engine
   ↓
4. Result Assembler
```

## 13.1 Query Planner

The Query Planner converts input into an explicit `ExecutionPlan`.

For natural-language MCP input, Apertus may extract intent, concepts and applicability. For structured Information Products such as Arrival Checklist or Swiss Hike, the input already contains most of this context and the LLM planning step can be skipped.

The planner determines:

- information class;
- Knowledge Spaces and/or Capabilities;
- concepts;
- jurisdiction and applicability;
- requested/effective date;
- retrieval strategy;
- evidence budget;
- whether optional AI synthesis is needed.

## 13.2 Retrieval / Capability Engine

For AUTHORITATIVE requests, retrieve from the current published Knowledge Release. For LIVE requests, call registered provider Capabilities. For hybrid/derived products, execute the required combination.

Authoritative retrieval uses metadata filters first, then lexical/vector/concept retrieval and reranking.

## 13.3 Evidence & Rule Engine

This engine determines what the selected evidence actually establishes.

It SHALL:

- group candidate facts by concept;
- combine corroborating evidence;
- recognize specialization (for example federal rule + more specific cantonal guidance);
- apply deterministic domain rules where available;
- detect unresolved contradictions;
- preserve evidence links for every resolved