
Worked example (synthetic guidance, not evidence for the current extraction).
Use its representation pattern only where the actual source supports it. Never
copy its labels, IDs, values, questions or facts into an unrelated extraction.
Source section_id: section-example
Source evidence ID: section-example:0:124
Source text: If a visitor operates equipment or stays longer than five days, the visitor requires a badge. The Site Office issues badges.
The visitor bears the requirement; the office performs the separate issuing
act. Neither assertion identifies an application recipient or a permit status.
The OR and strict duration threshold belong in connected condition fields.

```json
{
  "concepts": [
    {
      "label": "Visitor badges",
      "concept_type": "RULE",
      "primary_section_id": "section-example",
      "claims": [
        {
          "claim_id": "badge-required",
          "kind": "requirement",
          "statement": "A visitor who operates equipment or stays longer than five days requires a badge.",
          "evidence_ids": [
            "section-example:0:124"
          ],
          "scope": {
            "population": "visitors",
            "jurisdiction": "unspecified",
            "permit_status": "unspecified",
            "actor": "visitor",
            "recipient": "unspecified",
            "procedure_branch": "unspecified"
          },
          "scope_evidence_ids": [
            "section-example:0:124"
          ],
          "conditions": [
            {
              "condition_id": "equipment",
              "text": "operates equipment",
              "evidence_ids": [
                "section-example:0:124"
              ],
              "subject": "visitor",
              "operator": "stated",
              "value": "operates equipment",
              "unit": "unspecified",
              "time_window": "unspecified"
            },
            {
              "condition_id": "duration",
              "text": "stays longer than five days",
              "evidence_ids": [
                "section-example:0:124"
              ],
              "subject": "visitor",
              "operator": "gt",
              "value": "5",
              "unit": "days",
              "time_window": "unspecified"
            }
          ],
          "condition_groups": [
            {
              "group_id": "either",
              "operator": "OR",
              "members": [
                "equipment",
                "duration"
              ],
              "evidence_ids": [
                "section-example:0:124"
              ]
            }
          ],
          "condition_root": "either",
          "exceptions": [],
          "limitations": []
        },
        {
          "claim_id": "badge-issued",
          "kind": "fact",
          "statement": "The Site Office issues badges.",
          "evidence_ids": [
            "section-example:0:124"
          ],
          "scope": {
            "population": "unspecified",
            "jurisdiction": "unspecified",
            "permit_status": "unspecified",
            "actor": "Site Office",
            "recipient": "unspecified",
            "procedure_branch": "unspecified"
          },
          "scope_evidence_ids": [
            "section-example:0:124"
          ],
          "conditions": [],
          "condition_groups": [],
          "condition_root": "",
          "exceptions": [],
          "limitations": []
        }
      ],
      "questions": [
        "When does a visitor require a badge?",
        "Who issues badges?"
      ],
      "limitations": []
    }
  ],
  "saturated": false
}
```

