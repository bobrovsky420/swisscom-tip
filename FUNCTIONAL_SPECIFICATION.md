# Swisscom Trusted Information Platform
## Product & Functional Specification — V12

**Hackathon:** Swiss Grounding MCP using selected `admin.ch` / SEM and `zh.ch` sources<br>
**Primary deliverable:** Testable MCP server<br>
**Example MCP client:** OpenCode<br>
**Structured demo:** Swiss Arrival Checklist<br>
**Stretch demo:** Swiss Hike with clearly labelled mock data<br>
**Preferred semantic model:** Apertus, with a model-independent core<br>
**Technical design:** [`TECHNICAL_SPECIFICATION.md`](TECHNICAL_SPECIFICATION.md)

---

# 1. Summary

The Trusted Information Platform (TIP) turns authoritative knowledge, live data, private context and services into trustworthy structured Information Products for applications and AI agents.

> **AI is infrastructure, not the interface.**

TIP is the target product. The hackathon delivers a narrow vertical slice of it: a working MCP server for focused Swiss public information. That slice builds a versioned knowledge release from selected official sources, returns compact evidence with citations, distinguishes jurisdiction and applicability, reports freshness and explicitly declines unsupported questions.

The vertical slice is not a throwaway demonstration or the complete definition of the product. It is designed to validate the foundation for structured applications, private and enterprise knowledge, automated Knowledge CI/CD, and a publisher Data Product marketplace. Delivery discipline and product ambition are therefore treated as complementary horizons.

---

# 2. Product Vision and Strategic Hypothesis

**Decision class: Team product hypothesis**

TIP is envisioned as trusted-information infrastructure between authoritative data providers and the applications, workflows and AI agents that need reliable, governed and application-ready information.

## Target users and value

| User or customer | Need | TIP value |
|---|---|---|
| AI assistants and application teams | Reliable Swiss and domain-specific answers | Compact evidence, citations, context and structured results |
| Enterprises and regulated teams | Governed external and internal knowledge | Versioning, provenance, applicability, auditability and private overlays |
| Authorities and data publishers | Reusable machine-consumption channel | Maintained Data Products, declared coverage and distribution |
| Swisscom | Reusable trusted-information platform | Hosting, integration, sovereign AI consumption and future commercial services |

## Target-product capabilities

1. **Trusted supply:** onboard authoritative sources, datasets and live capabilities.
2. **Knowledge lifecycle:** version, evaluate, refresh and publish governed knowledge releases.
3. **Product composition:** combine Knowledge Spaces, Data Products, rules, capabilities and optional AI into Information Products.
4. **Distribution:** serve agents, applications and workflows through MCP, REST and future SDKs.
5. **Governance:** enforce provenance, coverage, trust, licensing and entitlements.
6. **Economics:** support usage attribution, commercial models, billing and publisher settlement where appropriate.

The product hypothesis is that Swisscom can provide the trusted infrastructure and distribution layer while authorities, enterprises and other publishers remain responsible for their canonical information. Government information may remain free while managed hosting, service levels, inference, enterprise overlays and derived Information Products create business value.

---

# 3. Hackathon Validation Outcome

**Published challenge requirement:** deliver an accessible, reproducible and testable Swiss-grounding MCP server.

**Team validation thesis:** a focused implementation can prove both immediate grounding quality and foundational capabilities of the larger TIP product.

The primary outcome is a GitHub repository that Swisscom can access, start and test with its evaluation harness and standards-compatible MCP clients.

| Validation level | Definition of success |
|---|---|
| Hackathon proof | A focused MCP server performs well on grounding, coverage, efficiency, operability and integration readiness |
| Product validation | The same implementation demonstrates reusable source, evidence, release, trust and distribution concepts that can evolve into the target product |

| Hackathon capability | Target-product hypothesis it validates |
|---|---|
| SEM and `zh.ch` source registry | Repeatable authority, publisher and source onboarding |
| Immutable snapshots and releases | Governed knowledge lifecycle and auditability |
| Evidence and Trust Envelope | Trusted, explainable Information Products |
| MCP server | Reusable agent distribution channel |
| Arrival Checklist | Structured Information Product composition |
| Provider abstractions | Composition of external datasets and live capabilities |
| Refresh and evaluation | Future Knowledge CI/CD |
| Provenance and dependency records | Future governance, entitlement, usage attribution and settlement |

The solution must demonstrate:

- correct use of authoritative Swiss sources;
- jurisdiction-aware and temporally valid evidence;
- precise citation support;
- honest unsupported, insufficient and conflicting states;
- useful declared coverage;
- efficient tool selection and compact responses;
- reproducible setup, refresh and caching behaviour;
- resilience, monitoring, source etiquette and maintainability;
- a coherent, extensible MCP contract.

OpenCode is one supported example and test client. It is not a required or privileged integration, and the server must not rely on OpenCode-specific behaviour.

---

# 4. Product Model

## Knowledge Space

An internal, compiled body of knowledge containing sources, snapshots, evidence, concepts, versions, coverage and tests. Examples include `swiss-public`, `emir-core` and `finma`.

## Data Product

A distributable publisher artifact containing knowledge, datasets and/or capabilities together with coverage, license, entitlement and commercial metadata. Examples include `Swiss Public Official`, `Swiss Hiking Routes Pro` and `SIX Market Data`.

## Information Product

An application capability combining typed inputs, Knowledge Spaces or Data Products, live capabilities, deterministic rules, optional AI and typed output. Examples include `swiss-arrival-checklist`, `swiss-hike-finder` and `emir-applicability`.

```text
Publisher Data Products ─┐
Live Capabilities ───────┼→ Information Product → Any Application
Private Knowledge ───────┘
```

---

# 5. Core Principles

1. Stable authoritative information is prepared before request time.
2. Inherently live information uses registered capabilities.
3. External publishers remain the canonical authorities.
4. Deterministic logic handles deterministic problems.
5. Semantic models handle semantic uncertainty only where they add value.
6. Apertus is preferred for relevant semantic tasks, while the core remains compatible with other providers.
7. Search returns evidence, not unsupported answers.
8. Runtime normally uses a small set of high-quality evidence.
9. Structured output precedes optional prose.
10. Every result carries a Trust Envelope.
11. MCP is the primary hackathon interface, not the entire product architecture.
12. Publisher licensing and entitlements are full-product concerns.
13. Marketplace features and autonomous refresh are post-MVP.

---

# 6. Information Classes

| Class | Example | Functional strategy |
|---|---|---|
| AUTHORITATIVE | Residence rules | Compiled Knowledge Space |
| LIVE | Train fare or weather | Live Capability |
| PRIVATE | Lease or company policy | Private Knowledge Space |
| CONSENSUS | Recommended places | Recommendation data |
| DERIVED | Best hike tomorrow | Data, capabilities and constraints |
| HISTORICAL | Rule in 2024 | Versioned knowledge release |

---

# 7. Hackathon Scenario and Coverage

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation → SEM / federal context
                           ↓
                    Canton Zurich
                           ↓
              declared local limitations
```

The demo tests authority, federal/cantonal applicability, citations, unsupported handling, multilingual queries and efficient retrieval.

The solution deliberately begins with selected `admin.ch` / SEM and `zh.ch` material. It does not claim complete Swiss, cantonal or municipal coverage. Exact sources, topics, languages, jurisdictions, exclusions and last refresh are exposed through the product and documented in the repository.

---

# 8. Hackathon Scope and Priority

## P0 — Published challenge outcome

- working MCP server in an accessible GitHub repository;
- clear setup, client configuration, coverage and limitations documentation;
- useful, declared authoritative Swiss coverage;
- grounded retrieval and exact citation support;
- compact responses designed for efficient agent use;
- explicit unsupported, insufficient, conflicting and stale states;
- reproducible refresh, caching, resilience and monitoring behaviour;
- compatibility with the Swisscom harness and standard MCP clients;
- safe secret and test-access handling.

## P0 — Team MVP choices

- focused `admin.ch` / SEM and `zh.ch` coverage;
- operator-triggered, on-demand knowledge builds;
- traceable source versions and immutable published releases;
- normalized evidence with authority, jurisdiction, applicability and temporal metadata;
- automated grounding, citation, efficiency, freshness and integration tests;
- compact Trust Envelopes and high-level resolution calls.

Semantic enrichment is optional and used only when it improves measured results. Apertus is the preferred provider; another compatible LLM or embedding model may be used without changing the platform's functional contracts.

## P1 — Product-validation extensions

- Admin Control Plane for sources, builds, evidence, tests and releases;
- REST access to the same published release;
- Swiss Arrival Checklist using typed inputs and outputs.

## P2 — Product-composition stretch

- Flutter Swiss Hike client;
- 10–20 clearly labelled `DEMO/MOCK` routes;
- mock transport, weather and places providers;
- deterministic filters and optional preference ranking.

## Target-product capabilities not implemented during the hackathon

```text
scheduler / periodic watcher
incremental build and promotion
autonomous Knowledge CI/CD
publisher self-service onboarding
marketplace discovery UI
pricing / billing / metering / settlement
publisher payouts
production entitlement engine
real SBB / weather / places integrations
```

These capabilities remain part of the target-product vision and influence current contracts and architectural boundaries. Their implementation is excluded from the hackathon vertical slice. The absence of a scheduler does not remove the requirement for an observable on-demand refresh, cache policy, freshness metadata and stale-result handling.

---

# 9. Knowledge Build Behaviour

An operator can initiate **Build / Full Reload** for the configured sources.

The product must:

1. show which sources are included;
2. acquire and preserve source versions;
3. normalize relevant source content;
4. derive evidence and optional candidate facts;
5. build the retrieval representation;
6. evaluate the candidate release;
7. publish it only if the evaluation gate passes;
8. preserve the last successful release if a build fails;
9. expose build progress, failures and freshness.

Normal MCP requests use the published release and do not scrape government sites at request time.

---

# 10. Resolution Behaviour

For a natural-language request, TIP must:

1. identify or request necessary context;
2. constrain evidence by coverage, authority, jurisdiction, applicability and date;
3. retrieve a small, relevant and diverse evidence bundle;
4. apply deterministic rules where appropriate;
5. expose unresolved uncertainty or conflicts;
6. return structured facts, evidence references and Trust Envelope;
7. generate optional prose only after the supported result is established.

Structured applications normally provide the relevant context directly and receive typed results without requiring a chat prompt.

---

# 11. Result Statuses

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
```

A nearest semantic match must never be silently presented as applicable truth.

Each result includes enough Trust Envelope information for a client to understand:

- the status;
- the active release and freshness;
- the relevant authority and jurisdiction;
- the supporting evidence and citations;
- any missing context, conflict, limitation or warning.

---

# 12. MCP Capability

The MCP server provides three user-facing capabilities:

1. resolve a Swiss-information request;
2. inspect cited evidence and provenance;
3. inspect declared coverage, limitations and freshness.

A normal supported request should require one high-level resolution call whenever possible. Evidence and coverage inspection remain available when the client or evaluator needs more detail.

Exact tool names, schemas, transports and client configuration are defined in the technical specification.

---

# 13. Admin Control Plane

The P1 Admin UI makes platform state inspectable through:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Full-build initiation and progress
5. Source snapshots and freshness
6. Evidence Explorer
7. Evaluations
8. Knowledge Releases
9. MCP/REST integration guidance

Its primary operation is **Build / Full Reload**. The Admin UI is not required for MCP runtime availability.

---

# 14. Swiss Arrival Checklist

The P1 structured application accepts:

- nationality group;
- purpose;
- duration;
- canton and municipality, within declared coverage;
- arrival date;
- work start date.

It returns typed requirements, deadlines, evidence identifiers, citations and a Trust Envelope. It does not require a natural-language prompt.

If municipal information is not included in the published coverage, the result must declare that limitation rather than infer a local requirement.

---

# 15. Swiss Hike Stretch Demo

The P2 Swiss Hike client demonstrates that the same platform can support a different typed Information Product.

Inputs may include origin, date, duration, difficulty, travel limit, scenery, weather and restaurant preferences. Outputs are typed route cards produced from clearly labelled mock routes and provider abstractions.

The demo illustrates composition and deterministic filtering; it does not claim production hiking, transport, weather or places coverage.

---

# 16. Target Product Capability: Knowledge CI/CD

**Decision class: Target-product capability; not implemented during the hackathon**

The full product may add scheduled source watching, cheap change detection, semantic impact analysis, incremental rebuilds, regression tests, and automatic or approval-based release promotion.

This is a strategic extension of the repeatable on-demand build proven during the hackathon, not a two-day deliverable.

---

# 17. Target Product Capability: Publisher and Data Product Marketplace

**Decision class: Target-product capability; not implemented during the hackathon**

TIP may evolve into a multi-sided platform:

```text
Consumers / Apps / Enterprises
             │ consume
             ▼
        Swisscom TIP
 hosting │ trust │ distribution │ metering │ billing
             │
      licensing / settlement
             ▼
Publishers / Data Providers
Government │ Companies │ Experts │ Individuals
```

Future publishers could create Data Products, connect sources, declare coverage and maintenance policy, configure licensing, publish versions and inspect usage or revenue. Public publication may require Swisscom review or certification.

Possible commercial relationships include usage/revenue share, recurring licenses, one-time licenses, publisher SaaS, and free/open public Data Products.

Before consuming a restricted Data Product, TIP would verify entitlement by tenant, application, purpose, geography, redistribution, retention, volume and contract period. Commercial executions could later create usage records for billing, cost attribution and publisher settlement.

Potential trust levels are:

```text
COMMUNITY
VERIFIED
EXPERT_VERIFIED
OFFICIAL
```

Trust level is independent of price.

---

# 18. Swisscom Alignment and Economics

**Decision class: Team product and business hypothesis**

TIP can strengthen myAI, eGovernment services, the Swiss AI Platform, Apertus-based services, banking services and enterprise AI.

Potential value includes API/MCP consumption, SaaS, hosting, managed knowledge, enterprise deployments, regulatory intelligence, inference consumption and future marketplace margin.

Publishers gain a machine-consumption distribution channel without having to build their own AI platform. Free public information can still support paid hosting, service levels, inference and derived Information Products.

---

# 19. Enterprise Reuse

**Decision class: Target-product reuse hypothesis**

For a UBS or Swiss Re context, public Swiss sources can be replaced or augmented by regulatory sources such as EMIR, ESMA, FINMA and DORA, together with governed internal policies and transaction or product context.

The reusable functional concepts are authority, jurisdiction, applicability, evidence, version, freshness, trust and explicit uncertainty. Any enterprise use would require separate governance, security, legal and production-readiness decisions.

---

# 20. Functional Definition of Done

Swisscom can:

- clone and start the repository from clear instructions;
- understand declared coverage and limitations;
- run an on-demand refresh of configured `admin.ch` / SEM and `zh.ch` sources;
- observe source versions, freshness, build outcome and the active release;
- connect its evaluation harness or another standard MCP client;
- obtain compact grounded results with exact citations;
- see explicit unsupported, insufficient, conflicting and stale states;
- reproduce the supplied grounding, efficiency and integration tests.

OpenCode is demonstrated as one compatible client, not treated as a required integration. Apertus is preferred where it adds evaluated value, while the server remains functional with another compatible semantic provider.

P1 completion additionally provides the Admin Control Plane and structured Swiss Arrival Checklist. P2 completion provides the clearly labelled mock Swiss Hike demonstration.

---

# 21. Product Evolution Roadmap

```text
1  Hackathon: focused Swiss public MCP server and on-demand releases
2  production hardening and broader declared Swiss coverage
3  scheduled/incremental Knowledge CI/CD
4  live capabilities and consumer Information Products
5  enterprise/private overlays
6  publisher self-service and Data Product entitlements
7  metering, billing, settlement and marketplace
8  regulatory impact and workflows
```

---

# 22. Final Positioning

> **Apertus is the preferred semantic model; the platform remains model-independent.**<br>
> **TIP provides trusted information, context and orchestration.**<br>
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

The hackathon vertical slice proves the working Swiss-grounding MCP foundation and tests the concepts on which the target product depends. Structured applications, autonomous Knowledge CI/CD, enterprise overlays and the publisher marketplace are the intended product evolution—not prerequisites for a credible two-day implementation.
