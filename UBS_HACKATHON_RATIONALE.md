# Why We Should Choose the Swisscom TIP Challenge
## Short rationale for the UBS hackathon team

I think the Swisscom Trusted Information Platform (TIP) challenge is a stronger choice for our team than the UBS client-transaction-prediction challenge—not because the UBS use case is less valuable, but because TIP gives us a better combination of **hackathon feasibility, learning, technical breadth, reuse and visibility**.

> **Transaction prediction solves one UBS use case. TIP lets us build a reusable platform and bring the experience back into UBS.**

---

## 1. Better Fit for a Short Hackathon

The UBS transaction-prediction challenge depends heavily on sensitive internal data, feature quality, labels, backtesting and proving that a prediction is actually useful.

TIP can use real public data from `admin.ch` / SEM and `zh.ch` immediately. Success is also easier to demonstrate visibly:

- did we retrieve the right authority?
- did we apply the right jurisdiction?
- are citations correct?
- do we refuse unsupported questions?
- can OpenCode use our MCP server efficiently?
- can the same platform power a structured application?

For the hackathon we keep the implementation focused: **on-demand full knowledge build**, retrieval, MCP/REST, Admin UI and structured demo apps. Automated scheduling and incremental Knowledge CI/CD remain post-MVP.

---

## 2. We Learn More New Technology and Bring It Back to UBS

One condition of UBS employee participation is to share what we learn afterward. The Swisscom challenge is particularly useful because it exposes us to technologies and architectural patterns that may not yet be widely used in our normal UBS environment:

- **Apertus** and the Swiss open/sovereign AI ecosystem;
- **MCP** and MCP clients such as OpenCode;
- evidence-first AI architecture and provenance;
- hybrid lexical/vector/concept retrieval;
- knowledge compilation rather than runtime-only RAG;
- structured AI Information Products instead of chat-first applications;
- combining deterministic business logic with generative AI;
- future multi-tenant Data Product/platform patterns.

After the hackathon we can share concrete experience rather than theoretical research: an internal demo, architecture lessons, Apertus observations, MCP lessons learned and possible UBS follow-up use cases.

The value brought back to UBS is therefore not only the TIP idea—it is **hands-on technology scouting and practical experience with a different AI ecosystem**.

---

## 3. The Technology Is Directly Reusable at UBS

The Swiss demo uses:

```text
admin.ch + zh.ch
      ↓
trusted evidence
      ↓
MCP / REST / applications
```

The same architecture can later use:

```text
EMIR / EUR-Lex
ESMA
FINMA
DORA / MiFID
UBS policies and procedures
      ↓
trusted evidence
      ↓
UBS portal / workflow / agent
```

A concrete example is an **EMIR Applicability** application with formal transaction inputs and structured `REQUIRED / NOT REQUIRED / REVIEW` results backed by regulatory evidence.

So we are not choosing between “something for Swisscom” and “something useful to UBS”. We can build the generic technology externally and bring the architecture back into UBS.

---

## 4. Broader Engineering Challenge

TIP lets the team work across several interesting areas:

```text
source acquisition
→ immutable snapshots
→ Apertus enrichment
→ evidence compilation
→ PostgreSQL / pgvector retrieval
→ query planning and evidence resolution
→ MCP + REST
→ Admin Control Plane
→ structured applications
```

This creates meaningful work for software, data, AI, architecture, UX and product-oriented team members rather than making success depend primarily on one prediction model.

---

## 5. Better External and Professional Visibility

TIP is based predominantly on public information and standard interfaces, so—**subject to UBS and hackathon IP rules**—the MVP may be easier to keep as an externally visible technical artifact than a solution based on confidential UBS transaction data.

If permitted, a public repository under a permissive license such as Apache-2.0 could provide durable technical provenance through the repository, commit history, `AUTHORS`/`NOTICE` information and original architecture documentation.

The point is **not personal monetisation**. The benefit is durable attribution and professional visibility.

If Swisscom or another organization later develops a product based on the original concept, the team could credibly point to having designed and built the initial TIP prototype.

Participation in an external challenge also gives the team exposure to engineers, architects and product stakeholders outside UBS.

Before relying on this benefit, we should confirm the hackathon/UBS rules around repository ownership, open-source licensing and contributor attribution.

---

## 6. Cleaner Independence / Fairness Optics

There is also a small secondary advantage in competing on an external challenge.

A UBS team competing on a UBS-sponsored challenge could be perceived as having more familiarity with the business context or expected outcome, even if the competition is completely fair. Judges may also be particularly careful about the optics of awarding the UBS challenge to a UBS team.

Choosing the Swisscom challenge removes this question entirely:

> **We compete on the same external problem and public information as everyone else, so the result is a clean demonstration of the team's capability.**

This is not a claim that the jury would be biased—just that an external challenge avoids unnecessary perception issues.

---

## 7. Bigger Product Potential

TIP can eventually become more than the Swiss public-information MVP.

```text
CONSUMER
Swiss Public
Hiking
Cycling
Photo Scout
Housing

ENTERPRISE
FINMA
EMIR
DORA
internal policies
regulatory impact
```

Longer term, Swisscom could operate it as a multi-sided Data Product platform where government, professional data providers, companies or experts publish trusted packs and Swisscom provides hosting, distribution, trust, entitlements and metering.

That marketplace and automated Knowledge CI/CD are **not hackathon deliverables**; they simply show that the architecture has somewhere meaningful to go afterward.

---

## 8. Where the UBS Challenge Is Stronger

The UBS transaction-prediction challenge is closer to direct client revenue. If the data, modelling infrastructure and deployment route are already mature, it may produce a more immediate UBS business result.

So the argument is not that the UBS challenge is bad.

The argument is:

> **For this hackathon, TIP gives us a better combination of feasibility, technical novelty, learning value, reusable architecture and external visibility—while still producing knowledge and technology we can bring back into UBS.**

---

## Recommendation

Choose the **Swisscom TIP challenge** if our goal is to use the hackathon not only to solve a problem, but to explore new technology, build a reusable platform, demonstrate broader engineering capability and return to UBS with genuinely new experience.

In short:

```text
Better hackathon demo
        +
More new technology learned
        +
Reusable at UBS
        +
External challenge / network
        +
Potential durable technical attribution
        +
Larger product vision
```

That combination is difficult to get from the internal transaction-prediction challenge.