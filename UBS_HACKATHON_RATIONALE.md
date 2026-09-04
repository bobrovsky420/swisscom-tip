# Why the Swiss Trusted Information Challenge Is a Better Hackathon Bet for a UBS Team Than Client Transaction Prediction

## Executive View

Assuming the internal UBS challenge is primarily about predicting a client's likely next transaction from historical client/transaction data, I would choose the Swiss Trusted Information challenge for the hackathon.

Not because transaction prediction has lower business value. It may have very high direct value to UBS.

The reason is that the Trusted Information challenge creates a **broader reusable technology asset, has materially lower hackathon execution risk, demonstrates more architectural innovation, avoids dependence on confidential data, and remains directly applicable to UBS after the event.**

> **Transaction prediction optimizes one banking use case. Trusted Information creates infrastructure from which many banking use cases can be built.**

---

# 1. Comparison

| Dimension | Trusted Information Platform | Client transaction prediction |
|---|---:|---:|
| Hackathon feasibility | Very high | Medium |
| Data accessibility | Very high | Low/medium |
| Confidential-data dependency | Low | Very high |
| Demo clarity | Very high | Medium |
| Architectural breadth | Very high | Medium |
| Cross-industry reuse | Very high | Low |
| Reuse inside UBS | Very high | High |
| Direct short-term UBS revenue potential | Medium | Very high |
| Platform potential | Very high | Low/medium |
| Apertus/GenAI relevance | Very high | Low/medium |
| Open/public evaluation | High | Low |
| Regulatory/privacy complexity during hackathon | Low | High |
| Productization beyond the hackathon | Very high | Medium |
| Differentiation from standard ML | High | Lower |
| Ability to demonstrate end-to-end product | Very high | Data dependent |

---

# 2. Transaction Prediction Starts with a Difficult Dependency: UBS Data

A transaction prediction solution depends heavily on:

```text
transaction history
customer history
product taxonomy
client segmentation
temporal features
channel activity
appropriate labels
```

The majority of these are proprietary and sensitive.

A hackathon team must therefore spend significant effort on:

```text
data access
anonymisation
quality
feature interpretation
leakage
sampling
label definition
validation
```

before the actual product idea becomes visible.

With public Swiss information, useful real-world data exists immediately. The team can spend the hackathon building differentiating technology instead of negotiating with the dataset.

---

# 3. Prediction Quality Is Hard to Demonstrate Convincingly in Two Days

Suppose a model predicts:

```text
Client X:
60% probability of FX transaction
23% probability of transfer
17% probability of securities trade
```

The immediate question is: **Is that good?**

Answering properly requires:

```text
baseline comparison
precision/recall
business-value weighting
time-window definition
calibration
historical backtesting
segment analysis
```

Even an excellent score does not necessarily produce an exciting live demonstration.

Trusted Information has visible success criteria:

```text
Did it find the right authority?
Did it understand Zurich jurisdiction?
Did it cite the correct evidence?
Did it detect that the source changed?
Did the old answer automatically update?
Did it correctly say unsupported?
How many calls did it need?
```

Judges can see the value immediately.

---

# 4. The Swiss Challenge Rewards Broad System Engineering

Transaction prediction is fundamentally a prediction/recommendation problem.

The Trusted Information challenge combines:

```text
MCP
APIs
retrieval
structured data
knowledge modelling
Apertus
multilingual processing
authority
temporal logic
caching
source monitoring
evaluation
CI/CD
product APIs
admin/control-plane UX
```

It is particularly suitable for a mixed team containing product, software engineering, data engineering, AI, architecture, UX and business analysis skills.

---

# 5. It Makes Better Use of Generative AI

A client-transaction predictor may not need an LLM at all. Gradient boosting, sequence models, recommender systems or conventional ML may be more natural depending on the problem.

Trying to force an LLM into that architecture could feel artificial.

Trusted Information gives a language model legitimate jobs:

```text
document classification
semantic enrichment
multilingual terminology
semantic change detection
ontology generation
query interpretation
evaluation generation
evidence reranking
explanation
```

The LLM has a real architectural role while deterministic software handles deterministic operations.

---

# 6. The Resulting Technology Is Directly Reusable at UBS

After the hackathon, replace:

```text
swiss-public
```

with:

```text
EMIR
FINMA
MiFID
DORA
AML regulation
UBS policy
UBS procedures
```

The core engine remains largely unchanged.

A first UBS Information Product could be **EMIR Applicability**:

```text
Legal entity
Counterparty classification
Instrument
Execution date
Jurisdiction
        ↓
Trusted Information Platform
        ↓
Reporting requirement
Clearing requirement
Margin requirement
Evidence
```

Another could be **Regulatory Impact**:

```text
New regulation
      ↓
semantic change
      ↓
affected UBS policy
      ↓
affected process
      ↓
affected application
      ↓
owners / actions
```

This potentially addresses large ongoing operating and compliance costs.

---

# 7. It Is Useful Far Beyond Compliance

The same UBS platform could power several domains.

## Client Portal

Authoritative information about products, fees, tax implications, payment rules, documentation and market rules.

## Relationship Manager Tools

Combine public information, bank policy and product knowledge.

## Operations

Procedures and exception handling.

## Legal

Regulatory and contractual evidence retrieval.

## Technology

Internal architecture and operational policies.

## Employee Assistants

Policy-aware information without every team building a separate RAG implementation.

Transaction prediction is substantially narrower.

---

# 8. It Creates a Reusable Strategic Asset Rather Than a Single Model

A transaction model generally resembles:

```text
UBS data
   ↓
UBS model
   ↓
UBS prediction
```

Its value depends heavily on the dataset for which it was trained.

Trusted Information resembles:

```text
platform
   ↓
domain configuration
   ↓
Information Products
```

The asset is therefore the platform itself.

The team can switch domains:

```text
Swiss Public
   ↓
EMIR
   ↓
FINMA
   ↓
UBS policy
```

without redesigning the system.

---

# 9. Lower Privacy and Conduct Risk During a Hackathon

Transaction prediction can quickly move into sensitive areas involving:

```text
profiling
fairness
suitability
client consent
data minimisation
explainability
sales conduct
model governance
```

Those are solvable production problems but poor dependencies for a short hackathon.

The Swiss public-information challenge requires no confidential user data, so the team can demonstrate a complete real system without synthetic versions of the most important inputs.

---

# 10. It Is Easier to Showcase Externally

A powerful demo can use questions that everyone understands:

> How do I register after moving to Zurich?

> Can I keep cats in my rented apartment?

Then the same architecture can be shown as:

> Does this EMIR rule apply to this transaction?

This makes the platform understandable to technical and non-technical audiences. A next-transaction prediction model is naturally more bank-specific.

---

# 11. It Demonstrates Product Thinking, Not Just AI Modelling

The project requires deciding:

```text
who publishes information
who consumes it
how it remains current
how trust is communicated
how APIs are structured
how applications integrate it
how it is monetised
```

The result can potentially become SaaS, a private enterprise platform, MCP service, API platform, information marketplace or managed regulatory service rather than remaining a feature inside one UBS application.

---

# 12. Strong Direct UBS Economic Case

The platform can reduce:

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

The key enterprise extension is:

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

When the top of that chain changes, the platform can eventually identify downstream impact.

---

# 13. The Hackathon Architecture Itself Is Reusable at UBS

The modular platform developed for Swiss information maps directly to enterprise banking:

| Hackathon Module | UBS Reuse |
|---|---|
| Source Scanner/Crawler | Monitor regulators and internal repositories |
| Snapshot Store | Immutable regulatory/policy versions |
| Apertus Enrichment | Classification, concepts, semantic changes |
| Evidence Compiler | Regulatory evidence objects |
| Authority Graph | Regulation → guidance → UBS policy |
| Knowledge CI/CD | Continuous regulatory knowledge releases |
| Trusted Runtime | Banking portal/API/MCP integration |
| Admin Control Plane | Compliance/knowledge operations |
| Evaluation | Regulatory grounding and regression tests |

This is a much stronger reuse story than merely porting a hackathon UI.

---

# 14. Transaction Prediction Can Later Consume This Platform

The two ideas are not mutually exclusive.

Suppose UBS later has an excellent client-needs prediction engine:

```text
Client likely needs:
international payment
```

That prediction alone is not enough to build the customer experience. The portal still needs current information about fees, currencies, cut-off times, regulation, product eligibility, documentation and available actions.

The combined architecture becomes:

```text
         UBS Prediction Engine
                  │
           predicts intent
                  │
                  ▼
      Trusted Information Platform
                  │
      current product/regulatory data
                  │
                  ▼
             Client Portal
                  │
                  ▼
                ACTION
```

Trusted Information can therefore complement future transaction prediction rather than compete with it.

---

# 15. Where the UBS Internal Challenge Is Stronger

There is one area where transaction prediction clearly wins:

> **Direct proximity to UBS client revenue.**

If UBS already has clean data, established modelling infrastructure, a clear business metric and an obvious deployment route, improving prediction of client needs could deliver measurable revenue quickly.

Therefore the correct argument is not “the UBS challenge is worse.”

It is:

> **For a short innovation hackathon, the Swiss Trusted Information challenge has a superior ratio of technical novelty, demoability, feasibility and reusable platform value.**

For a production UBS initiative focused exclusively on near-term client monetisation, transaction prediction may reasonably rank higher.

---

# 16. Why Choose the Swiss Challenge

It offers three wins simultaneously.

## Hackathon Win

A highly demonstrable, testable and technically interesting solution with no dependency on confidential production data.

## UBS Win

A reusable foundation for regulatory intelligence, enterprise knowledge and banking applications.

## Broader Innovation Win

A platform architecture applicable to Swisscom, UBS, Swiss Re, government, mobility and consumer applications.

The team is not simply solving:

> **What will this customer do next?**

It is building infrastructure for a harder and increasingly important question:

> **When software or AI needs information to make a decision, how does it know what it can trust?**

That is a broader technology problem with a credible path back into UBS after the hackathon.
