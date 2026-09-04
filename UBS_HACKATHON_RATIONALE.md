# Why We Should Choose the Swisscom TIP Challenge
## Short rationale for the UBS hackathon team

**Published challenge descriptions used for this comparison:**

- [Swiss Grounding MCP](https://zh.ai-weeks.ch/challenges/swiss-grounding-mcp)
- [UBS Transaction Activity Forecasting](https://zh.ai-weeks.ch/challenges/transaction-activity-forecasting)

I think the Swisscom **Swiss Grounding MCP** challenge, addressed through our Trusted Information Platform (TIP), is the stronger choice for our team if our priorities are **technology scouting, broad engineering experience, reusable architecture and external visibility**.

The working MCP server is the hackathon vertical slice; TIP is the target-product vision that the slice is intended to validate.

This is not because the UBS challenge lacks value. Transaction Activity Forecasting is a focused, data-ready financial AI problem with clear client benefits and measurable results. The distinction is the kind of experience we want from the hackathon:

> **The UBS challenge lets us investigate one important forecasting problem. The Swisscom challenge lets us build and test a reusable grounding capability and bring those architectural lessons back into UBS.**

---

## 1. We Learn More New Technology and Bring It Back to UBS

One condition of UBS employee participation is to share what we learn afterward. The Swisscom challenge exposes us to technologies and architectural patterns that may be less common in our normal UBS work:

- **MCP** contracts and integration with standard AI clients;
- evidence-first AI architecture and provenance;
- hybrid lexical/vector/concept retrieval;
- jurisdiction, applicability and freshness handling;
- knowledge compilation rather than runtime-only RAG;
- structured AI Information Products instead of chat-first applications;
- combining deterministic business logic with generative AI;
- evaluation of grounded agent tools for accuracy, citations, efficiency and operability.

We may also evaluate **Apertus** for semantic tasks such as multilingual retrieval, classification or reranking if access is available and it provides measurable value. The server's core should remain model-independent.

After the hackathon we can share concrete results: an internal demo, MCP design lessons, grounding and provenance patterns, evaluation results, operational lessons from public-source ingestion, and potential UBS applications.

The value brought back to UBS is therefore not only the TIP concept. It is **hands-on technology scouting and tested engineering experience with a different AI ecosystem**.

---

## 2. Broader Systems-Engineering Experience

The UBS challenge offers substantial data-science work: recurrence detection, feature engineering, sequence representation, comparison of modelling approaches, metric selection and interpretability.

The Swisscom challenge spans a different and broader set of system layers:

```text
source acquisition and refresh
→ immutable snapshots and provenance
→ normalization and evidence compilation
→ hybrid retrieval
→ jurisdiction and applicability resolution
→ MCP tool design
→ automated grounding and efficiency tests
→ reproducible deployment and operations
```

This creates meaningful work across software engineering, data engineering, AI, architecture, evaluation and product design. That breadth is a reason to choose it if it matches our team's skills and learning objectives—not evidence that the UBS modelling work is technically less demanding.

---

## 3. External Visibility and Open Contribution

The Swisscom challenge explicitly encourages, but does not require, teams to publish their MCP repository under a license that lets others use, extend and maintain it. Because the selected source material is public, the solution may be suitable for an externally visible technical artifact, subject to UBS, hackathon, source-licensing and intellectual-property rules.

If permitted, a public repository under an appropriate license could provide durable technical provenance through its code, commit history, `AUTHORS`/`NOTICE` information and architecture documentation. The purpose is professional attribution and contribution to Swiss AI infrastructure, not personal monetisation.

The UBS challenge uses synthetic rather than sensitive internal transaction data. Nevertheless, the permitted publication or redistribution of the supplied dataset, baseline and resulting artifacts still depends on the challenge terms. We should verify the applicable rules for either challenge before assuming that anything can be released publicly.

---

## 4. Reuse at UBS and Larger Product Horizon

TIP can eventually become more than the Swiss public-information MVP.

```text
PUBLIC / CONSUMER
Swiss administration
housing and relocation
mobility and recreation

ENTERPRISE
FINMA
EMIR
DORA
internal policies
regulatory applicability and impact
```

Longer term, the same foundation might support publisher-managed Data Products, entitlements and metering. That is product vision rather than a hackathon deliverable. The hackathon should prove only the trusted-information and MCP foundation needed for such future options.

The architecture also has a concrete reuse path at UBS.

The Swiss demo uses:

```text
admin.ch / SEM + zh.ch
          ↓
authoritative, versioned evidence
          ↓
MCP / applications / workflows
```

The same architectural patterns could later be evaluated with:

```text
EUR-Lex / EMIR
ESMA
FINMA
DORA / MiFID
UBS policies and procedures
          ↓
authoritative, versioned evidence
          ↓
UBS portal / workflow / agent
```

A possible application is an **EMIR Applicability** service with formal transaction inputs and structured `REQUIRED / NOT_REQUIRED / REVIEW` results backed by regulatory evidence.

This would require separate UBS governance, security, legal and implementation decisions; the hackathon does not prove production readiness for that use case. It does, however, let us test the underlying patterns on public information without using UBS data.

---

## Recommendation

Choose the **Swiss Grounding MCP** challenge if our primary goals are to:

- explore MCP and evidence-first agent architecture;
- build across data, AI, integration and operational layers;
- test reusable grounding patterns on authoritative public information;
- return to UBS with experience that differs from a conventional modelling exercise;
- potentially contribute a reusable Swiss grounding server publicly, if permitted.

Choose **Transaction Activity Forecasting** instead if our priority is to:

- work on a tightly defined financial time-series problem;
- start from a supplied synthetic dataset and baseline;
- focus on recurrence detection, feature engineering and sequence modelling;
- compare forecasting approaches quantitatively;
- investigate interpretable predictions tied directly to client financial activity.

For a team deliberately seeking broader platform-engineering and technology-scouting experience, I recommend **Swiss Grounding MCP**, implemented as a narrowly scoped and testable vertical slice of the TIP target product.
