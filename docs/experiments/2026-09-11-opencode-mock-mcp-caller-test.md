# OpenCode caller test with a mock residence MCP server - 11 September 2026

Purpose: test the calling LLM, not the knowledge base. A chat application had
answered the question below by counting 14 days from the first working day and
by ignoring that registration must precede the start of work. The corpus
confirms the rule (SEM FAQ in de/en/fr/it: within 14 days of arrival and before
taking up work; AIG Art. 12 para. 1; VZAE Art. 10; Zurich Migration Office
directive on the Free Movement Agreement, sections 2.3 and 3.4.4).

Test question, sent verbatim:

> I'm a Czech citizen and starting my work in Zurich next week. By when latest
> should I register my stay on the municipal authority?

## Setup

- Server: [mock_residence_mcp.py](../../scripts/test/mock-mcp/mock_residence_mcp.py),
  stdio, tools `get_coverage`, `resolve`, `get_evidence`, constants only, no
  access to the corpus or releases. `resolve` returns the facts, the user facts
  still needed (arrival date, first working day, contract length) and a decision
  rule; it does not compute the deadline.
- Harness: [run_opencode_test.py](../../scripts/test/mock-mcp/run_opencode_test.py),
  OpenCode 1.18.29, model `opencode/ling-3.0-flash-fin-free`, agent with all
  built-in tools disabled and a short system prompt that mentions the SwissTIP
  tools without saying when to call them. Configuration passed to the child
  process only; the user's OpenCode configuration was not changed.
- Self-check without an LLM: 15 of 15 checks passed
  ([check_mock_mcp.py](../../scripts/test/mock-mcp/check_mock_mcp.py)).
- Run: `.local/mock-mcp/runs/run-20260911-182413/` (Git-ignored transcripts and
  summary). An earlier run, `run-20260911-181152`, sent the question with two
  typos ("should a reguster") and reached the same decisions.

## Results

| Scenario | Turn 1 tool calls | Turn 1 answer | Turn 2 input | Turn 2 answer |
| --- | --- | --- | --- | --- |
| work-first | get_coverage; resolve with an invented concept ID (typed error); resolve with the advertised ID, `employment_duration: UNKNOWN` | Both limits stated; asked for arrival date and first working day; noted that the rule assumes a contract longer than three months; no date computed | arrival Sun 13 Sep, first working day Wed 16 Sep, open-ended | Binding limit is before the first working day, register by Tuesday 15 Sep 2026; 27 Sep shown as the non-binding 14-day limit |
| fourteen-days-first | get_coverage; resolve with the advertised ID, no `employment_duration` | Both limits stated; asked for arrival date, first working day and contract length; no date computed, but anticipated that "next week" makes the work-start limit the likely one | arrived Tue 1 Sep, first working day Fri 18 Sep, two-year contract | Binding deadline Tuesday 15 Sep 2026 (14 days after arrival); Thursday 17 Sep shown as the later work-start limit |

Both sessions called the MCP before answering, derived `EU_EFTA`, `EMPLOYMENT`
and `CH-ZH` from the question without asking, and left the date calculation
until the arrival date was known. The decision between the two limits was
correct in both scenarios, and the weekdays were right.

Observations:

- One `resolve` call used a guessed concept ID (`registration_arrival`) instead
  of the one returned by `get_coverage`; the typed error led to an immediate
  correct retry. The same happened in the earlier run. The real server behaves
  the same way, so this costs one round trip, not correctness.
- The earlier run had labelled 15 September 2026 a Wednesday (it is a Tuesday)
  and misspelled Personenmeldeamt; neither slip recurred.
- The harness assessment is heuristic string matching on the final answer; the
  transcripts are the evidence. Every check passed for both scenarios.

## Full message exchange

Run `.local/mock-mcp/runs/run-20260911-182413/`, model `opencode/ling-3.0-flash-fin-free`.
User messages, tool inputs, tool outputs and assistant texts are reproduced from the
JSONL transcripts in the order they occurred. The only edit is the replacement of
em and en dashes in the model's answers by hyphens, following the repository
convention. The tool outputs are the exact JSON returned by the mock server.

### Scenario work-first

#### Turn 1

User:

```text
I'm a Czech citizen and starting my work in Zurich next week. By when latest should I register my stay on the municipal authority?
```

Assistant:

```text
Let me look up the relevant information about registering your stay in Switzerland
```

Tool call 1: `swisstip_mock_get_coverage`, status completed

Input:

```json
{}
```

Output:

```json
{
  "release_id": "mock-residence-registration-2026-09-11",
  "knowledge_space": "hackathon",
  "topics": [
    {
      "topic_id": "immigration/residence",
      "title": "Residence in Switzerland: registration, permits and deadlines after arrival",
      "jurisdictions": [
        "CH",
        "CH-ZH"
      ],
      "concepts": [
        {
          "concept_id": "eu-efta-municipal-registration-after-arrival",
          "title": "Registration with the municipality of residence after arriving in Switzerland (EU/EFTA nationals taking up employment): deadline and order of steps",
          "answers_questions_like": [
            "By when must I register my stay with the municipal authority?",
            "I start work in Zurich soon. When do I have to register at the Kreisbuero?",
            "Is the 14-day registration deadline counted from arrival or from the first working day?"
          ],
          "jurisdictions": [
            "CH",
            "CH-ZH"
          ],
          "context_schema": {
            "nationality_group": {
              "type": "string",
              "enum": [
                "EU_EFTA",
                "THIRD_COUNTRY"
              ],
              "description": "EU_EFTA for citizens of an EU or EFTA state (for example Czech, German, Norwegian), otherwise THIRD_COUNTRY."
            },
            "purpose": {
              "type": "string",
              "enum": [
                "EMPLOYMENT",
                "SELF_EMPLOYMENT",
                "NO_EMPLOYMENT",
                "FAMILY_REUNIFICATION"
              ],
              "description": "Main purpose of the stay in Switzerland."
            },
            "employment_duration": {
              "type": "string",
              "enum": [
                "UP_TO_3_MONTHS",
                "MORE_THAN_3_MONTHS",
                "UNKNOWN"
              ],
              "description": "Contract length. Jobs of up to three months per calendar year follow a different notification procedure."
            },
            "canton_code": {
              "type": "string",
              "description": "ISO 3166-2 code of the canton of residence, for example CH-ZH for Zurich."
            }
          },
          "required_context": [
            "nationality_group",
            "purpose"
          ]
        }
      ]
    }
  ],
  "limitations": [
    "Mock server: hardcoded content for this one concept, taken from official pages saved on 2026-09-11. It is not the SwissTIP knowledge base and not legal advice."
  ]
}
```

Tool call 2: `swisstip_mock_resolve`, status error

Input:

```json
{
  "concept_id": "registration_arrival",
  "nationality_group": "EU_EFTA",
  "canton_code": "CH-ZH",
  "purpose": "EMPLOYMENT",
  "employment_duration": "UNKNOWN"
}
```

Error returned to the model:

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "issues": [
      {
        "path": "concept_id",
        "message": "Unknown concept_id 'registration_arrival'. Call get_coverage and use 'eu-efta-municipal-registration-after-arrival'."
      }
    ]
  }
}
```

Tool call 3: `swisstip_mock_resolve`, status completed

Input:

```json
{
  "concept_id": "eu-efta-municipal-registration-after-arrival",
  "nationality_group": "EU_EFTA",
  "canton_code": "CH-ZH",
  "purpose": "EMPLOYMENT",
  "employment_duration": "UNKNOWN"
}
```

Output:

```json
{
  "release_id": "mock-residence-registration-2026-09-11",
  "concept_id": "eu-efta-municipal-registration-after-arrival",
  "status": "SUPPORTED",
  "applicability": {
    "nationality_group": "EU_EFTA",
    "purpose": "EMPLOYMENT",
    "employment_duration": "UNKNOWN",
    "jurisdiction": "CH (federal rule), with City of Zurich details"
  },
  "facts": [
    {
      "fact_id": "f-14-days-and-before-work",
      "statement": "EU/EFTA nationals taking up employment in Switzerland for more than three months must register in person with the municipality of residence and apply for a residence permit within 14 days of their arrival in Switzerland AND before taking up work. Both limits apply at the same time.",
      "evidence_ids": [
        "e-sem-faq-en",
        "e-sem-faq-de",
        "e-aig-art12"
      ]
    },
    {
      "fact_id": "f-period-starts-at-arrival",
      "statement": "The 14-day period starts on the day of arrival in Switzerland (moving in), not on the first working day. The first working day does not define the arrival date.",
      "evidence_ids": [
        "e-sem-faq-en",
        "e-vzae-art10"
      ]
    },
    {
      "fact_id": "f-register-before-work",
      "statement": "Work may only be taken up after the personal registration and the submission of the residence application at the residents' registration office. Registration therefore has to be completed before the first working day, even if fewer than 14 days have passed since arrival.",
      "evidence_ids": [
        "e-aig-art12",
        "e-zh-weisung-fza"
      ]
    },
    {
      "fact_id": "f-documents",
      "statement": "Bring a valid identity card or passport and the employer's written confirmation of employment (for example the employment contract stating duration and working hours).",
      "evidence_ids": [
        "e-sem-faq-en"
      ]
    },
    {
      "fact_id": "f-zh-canton-14-days",
      "statement": "The canton of Zurich instructs EU/EFTA nationals who will work longer than 90 days to register in person with their municipality within 14 days.",
      "evidence_ids": [
        "e-zh-eu-efta"
      ]
    },
    {
      "fact_id": "f-zh-city-appointment",
      "statement": "In the City of Zurich, registration is possible only from the actual move-in date, and registration after arriving from abroad requires a booked appointment at the Personenmeldeamt (in person).",
      "evidence_ids": [
        "e-stadt-zh-zuzug"
      ]
    }
  ],
  "required_user_facts": [
    {
      "name": "arrival_date",
      "status": "NOT_PROVIDED_BY_SERVICE",
      "instruction": "Ask the user for the date on which they arrive (or arrived) in Switzerland. Never assume the arrival date equals the first working day; people usually arrive earlier. Without the arrival date the 14-day limit cannot be computed."
    },
    {
      "name": "first_working_day",
      "status": "NOT_PROVIDED_BY_SERVICE",
      "instruction": "Confirm the exact first working day; registration must be completed before it."
    },
    {
      "name": "employment_duration",
      "status": "UNKNOWN",
      "instruction": "If unknown, confirm that the contract exceeds three months; otherwise the short-term notification procedure applies instead of this rule."
    }
  ],
  "decision_rule": {
    "description": "The binding deadline is the EARLIER of two limits: (A) 14 days after the arrival date and (B) before the first working day.",
    "steps": [
      "1. Obtain arrival_date and first_working_day from the user; do not guess them.",
      "2. Compute limit A = arrival_date + 14 days.",
      "3. Limit B = registration completed before the first working day, i.e. at the latest on the last working day of the office before the first working day.",
      "4. If limit B falls before limit A, tell the user to register before the first working day and name that date. Otherwise tell the user to register within 14 days of arrival and name the date of limit A.",
      "5. State both limits so the user understands which one binds, and note that registration is only possible after the actual move-in."
    ]
  },
  "citations": [
    {
      "evidence_id": "e-sem-faq-en",
      "source_title": "SEM - FAQ: EU/EFTA citizens in Switzerland (English)",
      "url": "https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
      "language": "en",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-sem-faq-de",
      "source_title": "SEM - FAQ: EU/EFTA-Buergerinnen und -Buerger in der Schweiz (Deutsch)",
      "url": "https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-aig-art12",
      "source_title": "AIG (SR 142.20) Art. 12 Anmeldepflicht",
      "url": "https://www.fedlex.admin.ch/eli/cc/2007/758/de",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-vzae-art10",
      "source_title": "VZAE (SR 142.201) Art. 10 Aufenthalt mit Anmeldung",
      "url": "https://www.fedlex.admin.ch/eli/cc/2007/759/de",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-zh-weisung-fza",
      "source_title": "Kanton Zuerich - Weisung Freizuegigkeitsabkommen EU-26, EFTA-Staaten, Ziff. 2.3 und 3.4.4",
      "url": "https://www.zh.ch/content/dam/zhweb/bilder-dokumente/themen/migration-integration/einreise-aufenthalt/weisungen/Freiz%C3%BCgigkeitsabkommen%20EU-26,%20EFTA-Staaten_IW.pdf",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-zh-eu-efta",
      "source_title": "Kanton Zuerich - Aufenthalt fuer EU/EFTA-Staatsangehoerige",
      "url": "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-stadt-zh-zuzug",
      "source_title": "Stadt Zuerich - Zuzug anmelden",
      "url": "https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    }
  ],
  "limitations": [
    "Mock server: hardcoded content for this one concept, taken from official pages saved on 2026-09-11. It is not the SwissTIP knowledge base and not legal advice.",
    "Office opening hours and appointment availability are not covered."
  ]
}
```

Assistant:

```text
I found the right concept. Let me resolve it properly and get the evidence
```

Assistant:

```text
Good news - I found the official rules. Here's what applies to you as a Czech (EU/EFTA) citizen starting employment in Zurich:

## Key Rules (from official sources)

There are **two binding limits** that apply **simultaneously**, and the earlier one controls:

| Limit | Rule |
|-------|------|
| **A) 14 days after arrival** | The clock starts on your **move-in day**, not your first working day. |
| **B) Before first working day** | You may only start work **after** completing in-person registration and submitting your residence application. |

**The binding deadline is whichever comes first.** So if you arrive more than 14 days before your first working day, the 14-day rule binds. If you arrive shortly before (e.g., a week before), you must register **before your first working day** regardless.

### What you'll need for registration (City of Zurich):
- Valid identity card or passport
- Employer's written confirmation of employment (e.g., employment contract with duration & hours)
- A **booked appointment** at the *Personenmeldeamt* (registration is only possible from your actual move-in date)

> **Important caveat:** These rules apply to employment **longer than 3 months**. If your contract is shorter, a different (short-term notification) procedure applies.

---

## To give you the exact date, I need two facts:

1. **What is your arrival date** in Switzerland? (The day you move in - not necessarily the first working day.)
2. **What is your first working day?** (e.g., Monday, 14 September 2026?)

Once you give me those, I can compute the precise deadline and tell you which limit binds.
```

#### Turn 2

User:

```text
I will arrive in Zurich on Sunday 13 September 2026 and my first working day is Wednesday 16 September 2026. My contract is open-ended.
```

Assistant:

```text
With those dates, the answer is clear. Let me compute both limits:

| Limit | Calculation | Deadline |
|-------|------------|----------|
| **A) 14 days after arrival** | 13 Sep + 14 days | **27 September 2026** |
| **B) Before first working day** | - | **Before Wednesday, 16 September 2026** |

**Limit B wins.** The binding deadline is **before your first working day, Wednesday 16 September 2026** - that's the earlier of the two limits.

This means you effectively have just **Sunday 13, Monday 14, and Tuesday 15 September** to complete registration. Since registration in the City of Zurich requires a **booked appointment** at the *Personenmeldeamt* and is only possible from your actual move-in date, you should **book that appointment as soon as possible** - ideally today or tomorrow.

### Summary of what to do:
1. **Book a registration appointment** at the Zurich Personenmeldeamt now (slots can fill up quickly)
2. **Bring**: valid passport/ID card + your employer's written confirmation of employment
3. **Register by Tuesday 15 September at the latest** - you may not take up work before registration is complete

Sources: [SEM FAQ (EN)](https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html), [Kanton Zürich - EU/EFTA-Aufenthalt](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html), [Stadt Zürich - Zuzug](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html)
```

### Scenario fourteen-days-first

#### Turn 1

User:

```text
I'm a Czech citizen and starting my work in Zurich next week. By when latest should I register my stay on the municipal authority?
```

Tool call 1: `swisstip_mock_get_coverage`, status completed

Input:

```json
{}
```

Output:

```json
{
  "release_id": "mock-residence-registration-2026-09-11",
  "knowledge_space": "hackathon",
  "topics": [
    {
      "topic_id": "immigration/residence",
      "title": "Residence in Switzerland: registration, permits and deadlines after arrival",
      "jurisdictions": [
        "CH",
        "CH-ZH"
      ],
      "concepts": [
        {
          "concept_id": "eu-efta-municipal-registration-after-arrival",
          "title": "Registration with the municipality of residence after arriving in Switzerland (EU/EFTA nationals taking up employment): deadline and order of steps",
          "answers_questions_like": [
            "By when must I register my stay with the municipal authority?",
            "I start work in Zurich soon. When do I have to register at the Kreisbuero?",
            "Is the 14-day registration deadline counted from arrival or from the first working day?"
          ],
          "jurisdictions": [
            "CH",
            "CH-ZH"
          ],
          "context_schema": {
            "nationality_group": {
              "type": "string",
              "enum": [
                "EU_EFTA",
                "THIRD_COUNTRY"
              ],
              "description": "EU_EFTA for citizens of an EU or EFTA state (for example Czech, German, Norwegian), otherwise THIRD_COUNTRY."
            },
            "purpose": {
              "type": "string",
              "enum": [
                "EMPLOYMENT",
                "SELF_EMPLOYMENT",
                "NO_EMPLOYMENT",
                "FAMILY_REUNIFICATION"
              ],
              "description": "Main purpose of the stay in Switzerland."
            },
            "employment_duration": {
              "type": "string",
              "enum": [
                "UP_TO_3_MONTHS",
                "MORE_THAN_3_MONTHS",
                "UNKNOWN"
              ],
              "description": "Contract length. Jobs of up to three months per calendar year follow a different notification procedure."
            },
            "canton_code": {
              "type": "string",
              "description": "ISO 3166-2 code of the canton of residence, for example CH-ZH for Zurich."
            }
          },
          "required_context": [
            "nationality_group",
            "purpose"
          ]
        }
      ]
    }
  ],
  "limitations": [
    "Mock server: hardcoded content for this one concept, taken from official pages saved on 2026-09-11. It is not the SwissTIP knowledge base and not legal advice."
  ]
}
```

Tool call 2: `swisstip_mock_resolve`, status completed

Input:

```json
{
  "concept_id": "eu-efta-municipal-registration-after-arrival",
  "nationality_group": "EU_EFTA",
  "purpose": "EMPLOYMENT",
  "canton_code": "CH-ZH"
}
```

Output:

```json
{
  "release_id": "mock-residence-registration-2026-09-11",
  "concept_id": "eu-efta-municipal-registration-after-arrival",
  "status": "SUPPORTED",
  "applicability": {
    "nationality_group": "EU_EFTA",
    "purpose": "EMPLOYMENT",
    "employment_duration": "UNKNOWN",
    "jurisdiction": "CH (federal rule), with City of Zurich details"
  },
  "facts": [
    {
      "fact_id": "f-14-days-and-before-work",
      "statement": "EU/EFTA nationals taking up employment in Switzerland for more than three months must register in person with the municipality of residence and apply for a residence permit within 14 days of their arrival in Switzerland AND before taking up work. Both limits apply at the same time.",
      "evidence_ids": [
        "e-sem-faq-en",
        "e-sem-faq-de",
        "e-aig-art12"
      ]
    },
    {
      "fact_id": "f-period-starts-at-arrival",
      "statement": "The 14-day period starts on the day of arrival in Switzerland (moving in), not on the first working day. The first working day does not define the arrival date.",
      "evidence_ids": [
        "e-sem-faq-en",
        "e-vzae-art10"
      ]
    },
    {
      "fact_id": "f-register-before-work",
      "statement": "Work may only be taken up after the personal registration and the submission of the residence application at the residents' registration office. Registration therefore has to be completed before the first working day, even if fewer than 14 days have passed since arrival.",
      "evidence_ids": [
        "e-aig-art12",
        "e-zh-weisung-fza"
      ]
    },
    {
      "fact_id": "f-documents",
      "statement": "Bring a valid identity card or passport and the employer's written confirmation of employment (for example the employment contract stating duration and working hours).",
      "evidence_ids": [
        "e-sem-faq-en"
      ]
    },
    {
      "fact_id": "f-zh-canton-14-days",
      "statement": "The canton of Zurich instructs EU/EFTA nationals who will work longer than 90 days to register in person with their municipality within 14 days.",
      "evidence_ids": [
        "e-zh-eu-efta"
      ]
    },
    {
      "fact_id": "f-zh-city-appointment",
      "statement": "In the City of Zurich, registration is possible only from the actual move-in date, and registration after arriving from abroad requires a booked appointment at the Personenmeldeamt (in person).",
      "evidence_ids": [
        "e-stadt-zh-zuzug"
      ]
    }
  ],
  "required_user_facts": [
    {
      "name": "arrival_date",
      "status": "NOT_PROVIDED_BY_SERVICE",
      "instruction": "Ask the user for the date on which they arrive (or arrived) in Switzerland. Never assume the arrival date equals the first working day; people usually arrive earlier. Without the arrival date the 14-day limit cannot be computed."
    },
    {
      "name": "first_working_day",
      "status": "NOT_PROVIDED_BY_SERVICE",
      "instruction": "Confirm the exact first working day; registration must be completed before it."
    },
    {
      "name": "employment_duration",
      "status": "UNKNOWN",
      "instruction": "If unknown, confirm that the contract exceeds three months; otherwise the short-term notification procedure applies instead of this rule."
    }
  ],
  "decision_rule": {
    "description": "The binding deadline is the EARLIER of two limits: (A) 14 days after the arrival date and (B) before the first working day.",
    "steps": [
      "1. Obtain arrival_date and first_working_day from the user; do not guess them.",
      "2. Compute limit A = arrival_date + 14 days.",
      "3. Limit B = registration completed before the first working day, i.e. at the latest on the last working day of the office before the first working day.",
      "4. If limit B falls before limit A, tell the user to register before the first working day and name that date. Otherwise tell the user to register within 14 days of arrival and name the date of limit A.",
      "5. State both limits so the user understands which one binds, and note that registration is only possible after the actual move-in."
    ]
  },
  "citations": [
    {
      "evidence_id": "e-sem-faq-en",
      "source_title": "SEM - FAQ: EU/EFTA citizens in Switzerland (English)",
      "url": "https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
      "language": "en",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-sem-faq-de",
      "source_title": "SEM - FAQ: EU/EFTA-Buergerinnen und -Buerger in der Schweiz (Deutsch)",
      "url": "https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-aig-art12",
      "source_title": "AIG (SR 142.20) Art. 12 Anmeldepflicht",
      "url": "https://www.fedlex.admin.ch/eli/cc/2007/758/de",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-vzae-art10",
      "source_title": "VZAE (SR 142.201) Art. 10 Aufenthalt mit Anmeldung",
      "url": "https://www.fedlex.admin.ch/eli/cc/2007/759/de",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-zh-weisung-fza",
      "source_title": "Kanton Zuerich - Weisung Freizuegigkeitsabkommen EU-26, EFTA-Staaten, Ziff. 2.3 und 3.4.4",
      "url": "https://www.zh.ch/content/dam/zhweb/bilder-dokumente/themen/migration-integration/einreise-aufenthalt/weisungen/Freiz%C3%BCgigkeitsabkommen%20EU-26,%20EFTA-Staaten_IW.pdf",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-zh-eu-efta",
      "source_title": "Kanton Zuerich - Aufenthalt fuer EU/EFTA-Staatsangehoerige",
      "url": "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    },
    {
      "evidence_id": "e-stadt-zh-zuzug",
      "source_title": "Stadt Zuerich - Zuzug anmelden",
      "url": "https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html",
      "language": "de",
      "retrieved_on": "2026-09-11"
    }
  ],
  "limitations": [
    "Mock server: hardcoded content for this one concept, taken from official pages saved on 2026-09-11. It is not the SwissTIP knowledge base and not legal advice.",
    "Office opening hours and appointment availability are not covered."
  ]
}
```

Assistant:

```text
Here's what I found for your situation - Czech citizen (EU/EFTA), taking up employment in **Zurich (CH-ZH)**:

---

### The Key Rule: Two Deadlines, Whichever Comes First

As an EU/EFTA national taking up employment in Switzerland for **more than three months**, you face **two simultaneous deadlines**:

1. **Within 14 days of your arrival** in Switzerland (the clock starts on move-in day, *not* your first working day).
2. **Before your first working day** - you may not take up work until you have personally registered and submitted your residence application.

**The binding deadline is the earlier of the two.** So if your first working day falls within 14 days of arrival, you must register *before* that first day - not 14 days after it.

### Zurich-Specific Details

- Registration in the City of Zurich is only possible **from your actual move-in date**, and requires a **booked appointment** at the **Personenmeldeamt** (residents' registration office) in person.
- You'll need a valid ID/passport and your **employer's written confirmation of employment** (e.g., employment contract stating duration and hours).

---

### To Give You an Exact Deadline, I Need a Few More Details

The system requires these to compute your specific date:

- **What is your arrival/move-in date** in Switzerland?
- **What is your exact first working day?**
- **Is your employment contract longer than 3 months?** (If unsure, I can confirm - but the rule above assumes >3 months.)

Since you mentioned starting work "next week," it's very likely that **registering before your first working day** is the binding constraint rather than the 14-day window. Please share the dates and I can give you the precise deadline!
```

#### Turn 2

User:

```text
I already arrived in Zurich on Tuesday 1 September 2026. My first working day is Friday 18 September 2026 and the contract is for two years.
```

Assistant:

```text
Now I have all the facts. Let me compute your deadlines precisely:

---

### Your Deadlines

| Deadline | Date |
|---|---|
| **Limit A** - 14 days after arrival (1 Sep 2026 + 14 days) | **Tuesday, 15 September 2026** |
| **Limit B** - Before first working day (last possible day to register before 18 Sep) | **Thursday, 17 September 2026** |

**The binding deadline is Tuesday, 15 September 2026** - because the 14-day limit falls *before* the first-working-day limit.

That means you must have registered in person at the **Personenmeldeamt** in Zurich **no later than Tuesday, 15 September 2026** - and you've actually had a window to do so since your arrival on Tuesday, 1 September.

### What You Need to Bring
- Valid **ID card or passport**
- Your **employer's written confirmation** of employment (employment contract with duration and working hours)

### Important Reminder for Zurich
Registration is only possible **from your actual move-in date** (which you've already hit), and requires a **booked appointment** in person. If you haven't yet booked one, you should do so immediately - the 15 September deadline is approaching fast.

---

**In short:** Register by **Tuesday, 15 September 2026** at the latest - that's 14 days after your arrival. Don't wait until the last day; book your appointment at the Personenmeldeamt as soon as possible.

> Sources: [SEM FAQ (EN)](https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html), [AIG Art. 12](https://www.fedlex.admin.ch/eli/cc/2007/758/de), [Canton Zurich - EU/EFTA](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html), [City of Zurich - Zuzug](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html)
```

## Limitations

- One model, one question, two date scenarios, two runs. Not a qualification of Ling or of
  the tool descriptions in general.
- The mock's `resolve` result spells out the required user facts and the
  decision rule. The real release would have to carry equivalent guidance for
  the calling LLM to behave the same way; the corpus pages alone do not. The
  [real-server test](2026-09-11-opencode-real-mcp-caller-test.md) follows up on
  this.
- The system prompt says that the SwissTIP tools exist. A run with an empty
  prompt (`--prompt-file`) or with the default OpenCode agent was not made.
