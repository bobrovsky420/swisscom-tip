# Why the Swiss Trusted Information Challenge Is a Better Hackathon Bet for a UBS Team Than Client Transaction Prediction

## Executive View

Assuming the internal UBS challenge is primarily about predicting a client's likely next transaction from historical client/transaction data, the Swiss Trusted Information challenge is the stronger **hackathon** bet—not because transaction prediction lacks business value, but because TIP creates a broader reusable technology asset, has lower execution risk, uses real non-confidential data, is easier to evaluate visibly, and remains directly reusable inside UBS.

> **Transaction prediction optimizes one banking use case. Trusted Information creates infrastructure from which many banking use cases can be built.**

The final hackathon demo is also deliberately neutral: the team uses **OpenCode as the reference MCP client**, an Admin Control Plane to expose the knowledge lifecycle, and a structured Swiss Arrival Checklist to prove the platform is not merely a chatbot.

---

# 1. Comparison

| Dimension | Trusted Information Platform | Client transaction prediction |
|---|---:|---:|
| Hackathon feasibility | Very high | Medium |
| Real data accessibility | Very high | Low/medium |
| Confidential-data dependency | Low | Very high |
| Demo clarity | Very high | Medium |
| Architectural breadth | Very high | Medium |
| Cross-industry reuse | Very high | Low |
| Reuse inside UBS | Very high | High |
| Direct short-term UBS revenue potential | Medium | Very high |
| Platform potential | Very high | Low/medium |
| GenAI/Apertus relevance | Very high | Low/medium |
| Open/public evaluation | High | Low |
| Regulatory/privacy complexity during hackathon | Low | High |
| Productization beyond hackathon | Very high | Medium |
| Ability to demonstrate end-to-end product | Very high | Data dependent |

---

# 2. Transaction Prediction Starts With a Difficult Dependency: UBS Data

A credible transaction predictor depends on transaction history, customer history, product taxonomy, client segmentation, temporal features, channel activity and appropriate labels. These are proprietary and sensitive.

A hackathon team therefore risks spending much of the event on data access, anonymisation, quality, leakage, sampling, feature interpretation and label definition before the actual innovation becomes visible.

TIP uses real public authoritative sources immediately. The team can demonstrate actual admin.ch/SEM and zh.ch sourcing, not synthetic approximations of the most important input data.

---

# 3. Prediction Quality Is Harder to Demonstrate in Two Days

A result such as:

```text
Client X
60% FX transaction
23% transfer
17% securities trade
```

immediately raises: **is that good?**

A convincing answer needs baselines, calibration, precision/recall, business-value weighting, historical backtesting and segment analysis.

TIP has immediately visible tests:

```text
Did it use the right authority?
Did it understand CH vs CH-ZH jurisdiction?
Did it cite the exact evidence?
Did it refuse unsupported knowledge?
Did it detect a source change?
Did it publish a new tested release?
How many MCP calls were needed?
Did the same release work in a non-chat application?
```

---

# 4. The Demo Is Neutral and Reproducible

The reference agent client is **OpenCode**, connected to TIP through standard MCP. This is strategically useful because the demo is not dependent on a proprietary assistant UI.

```text
OpenCode + evaluation LLM
          ↓
standard MCP
          ↓
TIP
          ↓
published Knowledge Release
```

The tool call is made visible so judges can see that the model selected `swiss_information.resolve`, how many calls were required and what structured evidence TIP returned.

The same Knowledge Release is then consumed through REST by the Swiss Arrival Checklist. This demonstrates protocol and UX independence.

For UBS, this matters: the eventual consumer could be a banking portal, employee application, workflow engine or internal agent rather than the hackathon client.

---

# 5. The Challenge Rewards Broad System Engineering

TIP combines:

```text
MCP / Streamable HTTP
REST
source scanning/crawling
versioned storage
retrieval
structured data
knowledge modelling
Apertus
multilingual processing
authority/applicability
caching
source monitoring
evaluation
Knowledge CI/CD
admin/control-plane UX
structured application integration
```

This suits a mixed team of software, data, AI, architecture, product and UX engineers. Success does not depend on one prediction model.

---

# 6. It Makes More Natural Use of Generative AI

A transaction predictor may be better served by gradient boosting, sequence models or recommender systems. Adding an LLM can be artificial.

TIP gives Apertus legitimate semantic jobs:

```text
document classification
concept extraction
multilingual terminology
semantic change detection
applicability extraction
evaluation generation
evidence reranking
explanation
```

Deterministic software still owns deterministic operations.

---

# 7. The Resulting Technology Maps Directly to UBS

After the hackathon, replace:

```text
admin.ch + zh.ch
```

with:

```text
EUR-Lex / EMIR
ESMA
FINMA
DORA
MiFID
AML regulation
UBS policies
UBS procedures
```

The pipeline remains:

```text
Source Registry
→ Scanner/Fetcher
→ immutable snapshots
→ semantic compilation
→ Evidence Objects
→ evaluation
→ Knowledge Release
→ MCP / REST / portal
```

This is platform reuse, not merely code reuse.

---

# 8. Example UBS Information Product: EMIR Applicability

A formal application should use typed inputs rather than chat:

```text
Legal entity
Counterparty classification
Instrument
Execution date
Trading venue
Notional
Jurisdiction
```

and return:

```text
Reporting     REQUIRED / NOT REQUIRED / REVIEW
Clearing      REQUIRED / NOT REQUIRED / REVIEW
Margin        REQUIRED / NOT REQUIRED / REVIEW
Evidence      regulation + guidance + internal policy
Trust         applicability + source versions + confidence
```

The same TIP runtime that serves OpenCode in the hackathon can serve a UBS portal through REST or an internal agent through MCP.

---

# 9. Example UBS Information Product: Regulatory Impact

```text
New regulatory publication
        ↓
Source watcher
        ↓
semantic change
        ↓
Authority / dependency graph
        ↓
affected UBS policy
        ↓
affected process
        ↓
affected application
        ↓
owners / actions
```

This turns Knowledge CI/CD into regulatory change intelligence.

---

# 10. Reuse Beyond Compliance

The same platform can support:

- **Client portals:** current product, fee, tax and documentation information.
- **Relationship managers:** public rules + product knowledge + internal policy.
- **Operations:** procedures and exception handling.
- **Legal:** regulatory and contractual evidence.
- **Technology:** architecture and operational policy.
- **Employee tools:** policy-aware information without every team building its own RAG stack.

Transaction prediction is substantially narrower.

---

# 11. It Creates a Strategic Asset Rather Than a Single Model

Transaction prediction:

```text
UBS data → UBS model → UBS prediction
```

TIP:

```text
Reusable platform
      ↓
domain configuration
      ↓
Knowledge Spaces
      ↓
Information Products
      ↓
MCP / REST / applications
```

The platform can move from Swiss Public to EMIR to FINMA to UBS policy without redesigning the core.

---

# 12. Lower Privacy and Conduct Risk During the Hackathon

Transaction prediction can immediately involve profiling, fairness, suitability, client consent, data minimisation, sales conduct and model governance.

These are important production issues but poor dependencies for a short hackathon.

The Swiss challenge allows a complete real implementation with authoritative public sources and no confidential production client data.

---

# 13. The Architecture Itself Is Reusable at UBS

| Hackathon Module | UBS Reuse |
|---|---|
| Source Registry | Regulators + approved internal sources |
| Scanner/Crawler | Monitor regulators/internal repositories |
| Snapshot Store | Immutable regulatory/policy versions |
| Apertus Enrichment | Classification, concepts, semantic changes |
| Evidence Compiler | Regulatory evidence objects |
| Retrieval | Authority/applicability-aware evidence retrieval |
| Knowledge CI/CD | Continuous regulatory knowledge releases |
| MCP Runtime | Agent integration such as OpenCode during development |
| REST Runtime | Banking portal and workflow integration |
| Admin Control Plane | Compliance/knowledge operations |
| Evaluation | Grounding and regression tests |

The neutral OpenCode demo reinforces this reuse story: OpenCode is only one client, not a dependency of the platform.

---

# 14. It Is Easier to Showcase Externally

The hackathon story is understandable without banking expertise:

1. show real admin.ch/SEM and zh.ch sources;
2. compile them into a tested Knowledge Release;
3. ask a Swiss question in OpenCode;
4. show the exact MCP tool call and citations;
5. show explicit unsupported handling;
6. change a controlled source mirror;
7. watch the knowledge rebuild and republish;
8. repeat the query with the new release;
9. show the same release in a structured Arrival Checklist.

This is visually stronger than a model-quality metric alone.

---

# 15. It Demonstrates Product Thinking, Not Just AI Modelling

The project forces decisions about:

```text
who publishes information
what counts as authoritative
how sources are acquired
how information remains current
how applicability is modelled
how trust is communicated
how clients integrate it
how the platform is operated
how it can be monetised
```

The result can become SaaS, a private enterprise platform, MCP/REST service, managed regulatory service or marketplace foundation.

---

# 16. Strong Direct UBS Economic Case

TIP can reduce:

```text
manual regulatory research
duplicated RAG infrastructure
policy interpretation effort
regulatory change monitoring
impact-analysis effort
operational support
incorrect interpretation
time-to-implement regulatory changes
```

The high-value enterprise chain is:

```text
EXTERNAL AUTHORITY
        ↓
REGULATION
        ↓
UBS INTERPRETATION
        ↓
UBS POLICY
        ↓
PROCESS
        ↓
APPLICATION
```

When the top changes, TIP can eventually determine downstream impact.

---

# 17. Transaction Prediction Can Later Consume TIP

The ideas are complementary.

```text
UBS Prediction Engine
       ↓ predicts client need
Trusted Information Platform
       ↓ supplies current product/regulatory facts
Client Portal
       ↓
ACTION
```

A prediction that a client may need an international payment still requires current fees, currencies, cut-offs, eligibility, documentation and regulation. TIP can supply that trusted context.

---

# 18. Where the UBS Internal Challenge Is Stronger

Transaction prediction clearly has one advantage:

> **Direct proximity to UBS client revenue.**

If UBS already has clean data, a proven modelling environment, clear business metrics and an obvious deployment route, next-transaction prediction may deliver near-term revenue faster.

The correct argument is therefore not that the UBS challenge is worse. It is:

> **For a short innovation hackathon, TIP has a superior ratio of technical novelty, demoability, feasibility and reusable platform value.**

---

# 19. Why Choose the Swiss Challenge

It produces three simultaneous wins:

**Hackathon:** real data, clear evaluation, visible end-to-end demo, neutral OpenCode MCP client, no confidential-data dependency.

**UBS:** reusable foundation for regulatory intelligence, enterprise knowledge and banking applications.

**Broader innovation:** an architecture applicable to Swisscom, UBS, Swiss Re, government, mobility and consumer applications.

The team is not only solving:

> **What will this customer do next?**

It is building infrastructure for:

> **When software or AI needs information to make a decision, how does it know what it can trust—and how is that trusted information kept current?**

That is a broader technology problem with a credible path back into UBS after the hackathon.
