# OpenCode caller test with the real MCP server - 11 September 2026

Follow-up to the [mock server test](2026-09-11-opencode-mock-mcp-caller-test.md):
the same question, model, agent prompt and two date scenarios, but the tools come
from the real SwissTIP MCP server (`swisstip.mcp_server.server`, runtime BUILD-03)
serving the assistant-curated residence pilot release. The goal was to reach the
same result as the mock: both limits stated, the arrival date not assumed, the
binding deadline chosen correctly once the dates are known.

Outcome: reached on the second attempt, after two changes on our side. The first
attempt on the unchanged pilot release and the original tool descriptions missed
"before starting work" in one session and produced no supported facts at all in the
other. An ablation shows which change mattered.

## Setup

- Harness: [run_opencode_test.py](../../scripts/test/mock-mcp/run_opencode_test.py)
  with `--server real`; OpenCode 1.18.29, model `opencode/ling-3.0-flash-fin-free`,
  the same `residence-assistant` agent and system prompt as the mock test, all
  built-in tools disabled. OpenCode's tool-output cap was raised from the default
  51,200 bytes to 400,000 bytes because topic-level discovery returns 120 to 145 KB
  (59 coverage profiles and context schemas inline).
- Release: `hackathon-residence-semantic-2026-09-11-v1` (81 facts, 34 concepts)
  for the first attempt and the ablation; `...-v2` (83 facts, 35 concepts) for the
  successful attempt. Both are assistant-curated experimental releases built by
  [build_residence_mvp.py](../../scripts/corpora/build_residence_mvp.py) from the
  frozen 2026-09-10 corpus; no human or legal review.
- Server behaviour verified beforehand with a standalone client: initialization
  1.8 s, calls 0.1 to 0.2 s; exact jurisdiction matching (federal concepts with the
  country only, Zurich concepts with `CH-ZH`, the city concept with municipality
  `261`); one concept per resolve; `as_of` inside the frozen window 2026-09-10 to
  2026-09-11; `population: eu_efta` required for the Zurich EU/EFTA concepts.
- Runs (Git-ignored transcripts and summaries under `.local/mock-mcp/runs/`):
  `run-20260911-193545-real` (attempt 1), `run-20260911-194507-real` (attempt 2),
  `run-20260911-194823-real` (ablation).

## Attempt 1: v1 release, original tool descriptions

| Scenario | Turn 1 tool calls | Turn 1 answer | Turn 2 answer |
| --- | --- | --- | --- |
| work-first | 17 calls, 50 s: 8 typed errors (invented space, domain and topic IDs; child listing without `release_id`; canton written as `ZH`; `intent` not matching the ID pattern), 3 `OUT_OF_COVERAGE` (three concepts in one call; city concept without municipality; federal short-employment concept with a canton), 2 supported (`residence-zh-eu-registration`, `residence-zh-eu-b`) | Within 14 days of entry; the clock starts at entry, not at the first working day; no mention of "before starting work"; arrival date not asked | 27 September 2026 (14 days after arrival): wrong, the work-start limit was missed |
| fourteen-days-first | 27 calls, 97 s: 0 supported, 7 `OUT_OF_COVERAGE`, errors for retrieval terms (`UNSUPPORTED_LANGUAGE`), `max_evidence` 10, `scope_mode` descendants, invented evidence IDs | Generic answer; says the system "returned limited extractable evidence text" and supplements from "the general Swiss immigration framework"; lists documents that are not in the release; asks for the arrival date only at the end | 15 September 2026 (correct) with the rule "within 14 days of arrival or before starting work, whichever comes first", which came from the model's own knowledge, not from a resolved fact; 15 September labelled a Wednesday |

Neither session resolved `residence-aig-registration`, the federal concept that
carries "before starting work". The `OUT_OF_COVERAGE` limitation text ("No evaluated
profile covers this combination and date.") does not say which part of the request
mismatched, so the model could not correct itself.

## Changes made

1. **Tool descriptions of the real server**
   ([server.py](../../apps/mcp-server/src/swisstip/mcp_server/server.py)). They now
   say to start discovery without arguments, walk the catalog with the pinned
   release, build a resolve request by copying one coverage profile's scope,
   intent, jurisdiction and required context, resolve one concept per call
   including federal ones, keep `as_of` inside the profile's temporal coverage,
   leave retrieval terms empty, and what `NEEDS_CONTEXT` and `OUT_OF_COVERAGE`
   mean; `get_evidence` states that rule, fact and concept IDs are not evidence
   IDs. The four server unit tests pass.
2. **Curated release v2.** [residence_mvp_curated.py](../../scripts/corpora/residence_mvp_curated.py)
   gained the concept `residence-eu-employment-registration-deadline` from the SEM
   free-movement FAQ (German page, intermediate document `doc-094ef42324485ec86493`,
   blocks 98 to 100): "Innert 14 Tagen nach ihrer Ankunft in der Schweiz und vor
   Stellenantritt, muessen sich die Buergerinnen und Buerger der EU/EFTA bei ihrer
   Wohngemeinde anmelden und eine Aufenthaltsbewilligung beantragen." Federal
   jurisdiction, selector `population = eu_efta`, applicability note that both
   limits apply together and the 14 days run from arrival. The builder took a new
   `--release-id`; v2 was built into `.local/mvp/residence-semantic-2026-09-11-v2/`
   (release SHA-256 `43a50b52...`, validated, 83 facts, 83 evidence objects, 20
   rules, 35 concepts, 60 coverage profiles, 12 documents). v1 is unchanged.
3. **Harness.** `--server real`, `--release-file`, `--release-id`, the raised
   tool-output cap, and a tighter heuristic for "computed a date before knowing the
   arrival date" (the snapshot-window note "valid through 2026-09-11" had counted as
   a computed date).

## Attempt 2: v2 release, new tool descriptions

| Scenario | Turn 1 tool calls | Turn 1 answer | Turn 2 answer |
| --- | --- | --- | --- |
| work-first | 6 calls, 25 s: root, knowledge space, one error (child listing without `release_id`), topic listing (121 KB), `residence-eu-employment-registration-deadline` supported, `residence-zh-eu-registration` supported | Within 14 days of arrival and before starting work; both limits apply together; the clock starts at arrival, not at the first working day; documents; SEM and Canton Zurich citations; no date computed; arrival date not asked | Before the first working day: effective deadline Wednesday 16 September 2026, 27 September shown as the non-binding 14-day limit; City of Zurich appointment and documents after two more resolves (the first two city requests lacked the municipality and returned `OUT_OF_COVERAGE`) |
| fourteen-days-first | 8 calls, 22 s: same walk, both registration concepts supported, two errors (`topic_id` missing on city-concept requests) | Both limits with the German SEM sentence and the Zurich sentence quoted; L versus B permit by contract length; no date computed; arrival date not asked | Tuesday 15 September 2026 (14 days after arrival), three days before the first working day, "both conditions are met"; B permit for the two-year contract |

Every fact and citation in the answers comes from the resolved evidence (SEM
free-movement FAQ, Canton Zurich EU/EFTA page, City of Zurich move-in page). The
decision between the two limits was correct in both scenarios and the weekdays were
right. Turn 1 did not ask for the arrival date in either session; the mock server's
result had listed the required user facts explicitly, the real release has no such
field. Answering the rule without a date is still correct for the question as
asked, and the follow-up was handled correctly.

## Ablation: v1 release, new tool descriptions

`run-20260911-194823-real`. Tool use was as efficient as in attempt 2 (13 and 11
calls in turn 1, no invented catalog IDs), but the model again resolved only the
Zurich concepts (`residence-zh-eu-registration`, `residence-city-zurich-arrival`,
`residence-zh-eu-b`) and never `residence-aig-registration`. Work-first ended with
27 September 2026 again; fourteen-days-first gave 15 September, which is right for
that scenario, but stated as the 14-day rule alone. The description change removed
the guessing and the dead ends; the SEM FAQ concept, whose single fact states both
limits, is what made the answers complete.

## Findings for the service

- **Discovery payload.** Every topic-level `get_coverage` returns all coverage
  profiles and context schemas inline, 120 to 145 KB for 60 profiles. A default
  OpenCode installation truncates this at 51,200 bytes. Profiles per entry or a
  compact profile summary would help callers with small context windows.
- **`OUT_OF_COVERAGE` diagnostics.** `unsupported_combination` should name the
  mismatching element (for example "profile mvp-profile-city-zurich-arrival requires
  municipality_id 261" or "scope_mode descendants not offered"); the model only
  recovered by trial and error.
- **Exact jurisdiction matching.** Callers naturally add the user's canton to every
  request; federal profiles reject it. Either accept a more specific jurisdiction
  for federal profiles or make the rule prominent in discovery output.
- **Cross-level facts.** Without a fact that states both limits, the caller did not
  combine the federal AIG Article 12 concept with the cantonal 14-day concept. Facts
  that cite both levels, or explicit related-concept references, are needed for
  deadline questions.
- **Required user facts.** The mock's `required_user_facts` made Ling ask for the
  arrival date; the real contract has no equivalent. The V3 concept format already
  carries questions; a "facts the caller must collect" field on facts or profiles
  would give the same effect.

## Limitations

- One model, one question, two date scenarios, three runs. Not a qualification of
  Ling, the contract or the release in general.
- The curated release is assistant-authored from saved official pages; the new
  concept follows the same process and has no independent review.
- The harness assessment is heuristic string matching; the transcripts and the
  message exchange below are the evidence.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py --output .local/mvp/residence-semantic-2026-09-11-v2 --release-id hackathon-residence-semantic-2026-09-11-v2
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --check-connection
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --live
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --live --release-file .local/mvp/residence-semantic-2026-09-11-v1/release.json --release-id hackathon-residence-semantic-2026-09-11-v1
```

## Full message exchange

Run `.local/mock-mcp/runs/run-20260911-194507-real/`, model `opencode/ling-3.0-flash-fin-free`,
real server on release `hackathon-residence-semantic-2026-09-11-v2`. User messages, tool
inputs, tool outputs and assistant texts are reproduced from the JSONL transcripts in the
order they occurred. The only edit is the replacement of em and en dashes in the model's
answers by hyphens, following the repository convention. Tool outputs are the exact JSON
returned by the server; the two topic-level get_coverage outputs (about 120 KB each) are
shortened to their catalog entries and one coverage profile, marked with `[...]`.

### Scenario work-first

#### Turn 1

User:

```text
I'm a Czech citizen and starting my work in Zurich next week. By when latest should I register my stay on the municipal authority?
```

Tool call 1: `swisstip_get_coverage`, status completed

Input:

```json
{
  "limit": 20
}
```

Output:

```json
{"schema_version":"get-coverage-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"knowledge_space_id":null,"parent":null,"entries":[{"schema_version":"catalog-entry/v1","entry_id":"hackathon","kind":"knowledge_space","parent_ids":[],"labels":{"en":{"label":"Experimental residence MVP","aliases":[],"description":"Assistant-curated experimental MVP data; no independent human or legal review.","provenance":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"}]}},"lifecycle":"CURATED","replacement_ids":[]}],"coverage_profiles":[],"context_schemas":[],"next_cursor":null,"default_limit":20,"maximum_limit":100,"ordering":"entry_id_ascending"}
```

Tool call 2: `swisstip_get_coverage`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "limit": 20
}
```

Output:

```json
{"schema_version":"get-coverage-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"knowledge_space_id":"hackathon","parent":null,"entries":[{"schema_version":"catalog-entry/v1","entry_id":"immigration","kind":"domain","parent_ids":["hackathon"],"labels":{"en":{"label":"Immigration","aliases":[],"description":"Assistant-curated experimental MVP data; no independent human or legal review.","provenance":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"}]}},"lifecycle":"CURATED","replacement_ids":[]}],"coverage_profiles":[],"context_schemas":[],"next_cursor":null,"default_limit":20,"maximum_limit":100,"ordering":"entry_id_ascending"}
```

Tool call 3: `swisstip_get_coverage`, status error

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "parent_id": "immigration",
  "limit": 20
}
```

Error returned to the model:

```json
{"schema_version":"tool-error/v1","code":"INVALID_ARGUMENT","issues":[{"path":"request","reason_code":"value_error","message":"Value error, child_and_continuation_requests_require_release","allowed_values":[]}],"release_id":null,"active_release_id":null}
```

Tool call 4: `swisstip_get_coverage`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "parent_id": "immigration",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "limit": 20
}
```

Output:

```json
{
  "schema_version": "get-coverage-result/v1",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "parent": {
    "schema_version": "catalog-entry/v1",
    "entry_id": "immigration",
    "kind": "domain",
    "parent_ids": [
      "hackathon"
    ],
    "labels": {
      "en": {
        "label": "Immigration",
        "aliases": [],
        "description": "Assistant-curated experimental MVP data; no independent human or legal review.",
        "provenance": [
          {
            "artifact_id": "mvp-curation-source",
            "version": "1",
            "sha256": "2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"
          }
        ]
      }
    },
    "lifecycle": "CURATED",
    "replacement_ids": []
  },
  "entries": [
    {
      "entry_id": "residence",
      "kind": "topic",
      "parent_ids": [
        "immigration"
      ],
      "label": "Residence permits in Switzerland"
    }
  ],
  "next_cursor": null,
  "default_limit": 20,
  "maximum_limit": 100,
  "ordering": "entry_id_ascending",
  "coverage_profiles": [
    {
      "schema_version": "coverage-profile/v1",
      "coverage_profile_id": "mvp-profile-eu-employment-registration-deadline",
      "release_id": "hackathon-residence-semantic-2026-09-11-v2",
      "catalog_ref": {
        "artifact_id": "mvp-catalog",
        "version": "1",
        "sha256": "a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"
      },
      "knowledge_space_id": "hackathon",
      "domain_id": "immigration",
      "topic_id": "residence",
      "concept_ids": [
        "residence-eu-employment-registration-deadline"
      ],
      "intent": "requirements",
      "concept_selection_required": true,
      "jurisdiction": {
        "country_code": "CH",
        "canton_code": null,
        "municipality_id": null
      },
      "context_schema_ref": {
        "artifact_id": "mvp-context-eu-employment-registration-deadline",
        "version": "1",
        "sha256": "744c08c553d36034ae976186d5bbec4e9bdb771ac7296cb35fddea8becc29867"
      },
      "scope_modes": [
        "exact"
      ],
      "max_descendant_depth": 0,
      "max_concepts": 1,
      "source_ids": [
        "ch-sem-free-movement-faq"
      ],
      "source_languages": [
        "de"
      ],
      "temporal_coverage": {
        "valid_from": "2026-09-10",
        "valid_through": "2026-09-11"
      },
      "term_routes": [],
      "projection_languages_complete": [],
      "evaluation_ref": {
        "artifact_id": "mvp-experimental-test-policy",
        "version": "1",
        "sha256": "d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"
      },
      "rule_refs": [
        {
          "artifact_id": "mvp-rule-eu-employment-registration-deadline",
          "version": "1",
          "sha256": "b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"
        }
      ],
      "exclusions": [
        "Assistant-curated experimental MVP data; no independent human or legal review.",
        "Frozen snapshot test window only; not complete Swiss legal coverage.",
        "Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work."
      ],
      "freshness_policy": {
        "max_age_days": 30,
        "policy_ref": {
          "artifact_id": "mvp-experimental-test-policy",
          "version": "1",
          "sha256": "d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"
        }
      },
      "approval_status": "APPROVED"
    },
    "[...] 60 profiles in total"
  ],
  "context_schemas": "[...] 60 context schemas omitted"
}
```

Tool call 5: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-eu-employment-registration-deadline"
  ],
  "context": {
    "population": "eu_efta"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-eu-employment-registration-deadline"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-eu-employment-registration-deadline"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-eu-employment-registration-deadline"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-eu-employment-registration-deadline-1","version":"1","sha256":"8ef7c24120b0cdc35996599a6e3b97450523f266f43879c58a3e5eccf730d3e8"},"fact_id":"mvp-fact-eu-employment-registration-deadline-1","statement":"SEM states that EU/EFTA nationals taking up employment of more than three months must register with their municipality of residence and apply for a residence permit within 14 days of their arrival in Switzerland and before starting work. A valid identity card or passport and the employer's written confirmation of employment (for example the contract with its duration and workload) must be presented; the contract duration determines whether a short-stay permit L or a residence permit B is issued.","language":"en","evidence_ids":["mvp-evidence-eu-employment-registration-deadline-1"],"rule_refs":[{"artifact_id":"mvp-rule-eu-employment-registration-deadline","version":"1","sha256":"b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"}],"applicability_conditions":["Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work.","population=eu_efta"]},{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-eu-employment-registration-deadline-2","version":"1","sha256":"3f3a6c389339798a734d984fe5f2e88897ec3e88f0516bbead5aa949a07c6df3"},"fact_id":"mvp-fact-eu-employment-registration-deadline-2","statement":"SEM states that the steps needed to obtain the residence permit can be completed after arrival in Switzerland.","language":"en","evidence_ids":["mvp-evidence-eu-employment-registration-deadline-2"],"rule_refs":[{"artifact_id":"mvp-rule-eu-employment-registration-deadline","version":"1","sha256":"b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"}],"applicability_conditions":["Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work.","population=eu_efta"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-eu-employment-registration-deadline-1","version":"1","sha256":"858729eef684d85d6e3e073ec0ac8be755642b26b4a38c113d81e67adc9bf744"},"evidence_id":"mvp-evidence-eu-employment-registration-deadline-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-094ef42324485ec86493","version":"1","sha256":"23d63f2e62afba6b7b55fc49ae58c4b46909fd17a58d0cc440f637d84b7413fc"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-094ef42324485ec86493","version":"1","sha256":"81f991c06bc103b0414cd6c92c41477127c97b19ba8013a712eed9c8b53b23ea"},"section_id":"full-document","start_offset":3701,"end_offset":4356,"original_excerpt":"Erwerbstätigkeit ab 3 Monaten:\n\nInnert 14 Tagen nach ihrer Ankunft in der Schweiz und vor Stellenantritt, müssen sich die Bürgerinnen und Bürger der EU/EFTA bei ihrer Wohngemeinde anmelden und eine Aufenthaltsbewilligung beantragen. Eine gültige Identitätskarte (oder Pass) sowie eine schriftliche Einstellungserklärung des Arbeitgebers (z.B. Arbeitsvertrag mit angegebener Dauer der Anstellung und Arbeitspensum) sind vorzuweisen. Je nach Dauer des Arbeitsverhältnisses wird eine Kurzaufenthaltsbewilligung (Ausweis L, Arbeitsvertrag bis 364 Tage) oder eine Aufenthaltsbewilligung B (Vertragsdauer von mindestens einem Jahr oder unbefristet) ausgestellt.","citation":{"source_id":"ch-sem-free-movement-faq","authority":"State Secretariat for Migration (SEM)","url":"https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html","title":"FAQ - Fragen zur Personenfreizügigkeit","accessed_at":"2026-09-10T20:05:56Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-eu-employment-registration-deadline"],"jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]},{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-eu-employment-registration-deadline-2","version":"1","sha256":"2333898924ed358629a32d745b08999792dfbd99630f6043ad0a86f126bb3474"},"evidence_id":"mvp-evidence-eu-employment-registration-deadline-2","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-094ef42324485ec86493","version":"1","sha256":"23d63f2e62afba6b7b55fc49ae58c4b46909fd17a58d0cc440f637d84b7413fc"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-094ef42324485ec86493","version":"1","sha256":"81f991c06bc103b0414cd6c92c41477127c97b19ba8013a712eed9c8b53b23ea"},"section_id":"full-document","start_offset":4358,"end_offset":4479,"original_excerpt":"Die notwendigen Schritte zur Erlangung der Aufenthaltsbewilligung können nach der Ankunft in der Schweiz erledigt werden.","citation":{"source_id":"ch-sem-free-movement-faq","authority":"State Secretariat for Migration (SEM)","url":"https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html","title":"FAQ - Fragen zur Personenfreizügigkeit","accessed_at":"2026-09-10T20:05:56Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-eu-employment-registration-deadline"],"jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:45:40Z","oldest_source_at":"2026-09-10T20:05:56Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["State Secretariat for Migration (SEM)"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage.","Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":2,"evidence_count":2,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-eu-employment-registration-deadline-1","mvp-evidence-eu-employment-registration-deadline-2"],"selections":[],"selection_policy":null}}
```

Tool call 6: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-zh-eu-registration"
  ],
  "context": {
    "population": "eu_efta"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-zh-eu-registration"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-zh-eu-registration"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-zh-eu-registration"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-zh-eu-registration-1","version":"1","sha256":"a5cd0a4a6fdcb6c5483a232ce291acb687a58ac44730a36342faeb9bf4722109"},"fact_id":"mvp-fact-zh-eu-registration-1","statement":"Zurich states that EU/EFTA nationals entering Switzerland need a valid passport or identity card. After entry they apply personally through the residents registration office for the longer stays described on the page; the office forwards the application to the cantonal migration office.","language":"en","evidence_ids":["mvp-evidence-zh-eu-registration-1"],"rule_refs":[{"artifact_id":"mvp-rule-zh-eu-registration","version":"1","sha256":"1030d4c4dbd61f7d9b81710b7dcb8a66d8a5f645f2620c2a1741110f039b4a60"}],"applicability_conditions":["population=eu_efta"]},{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-zh-eu-registration-2","version":"1","sha256":"418684e78756aa4cec7ed44384436670bd4efb7a3fec503e80c4fd5e4e201fe4"},"fact_id":"mvp-fact-zh-eu-registration-2","statement":"For EU/EFTA nationals wishing to work in Switzerland for longer than 90 days, Zurich specifies personal registration with the municipality within fourteen days. The page also describes an alternative three-month stay to look for work without a permit.","language":"en","evidence_ids":["mvp-evidence-zh-eu-registration-2"],"rule_refs":[{"artifact_id":"mvp-rule-zh-eu-registration","version":"1","sha256":"1030d4c4dbd61f7d9b81710b7dcb8a66d8a5f645f2620c2a1741110f039b4a60"}],"applicability_conditions":["population=eu_efta"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-zh-eu-registration-1","version":"1","sha256":"014e54ad9ce9fd99b5c9c3654a9f5c86a8752b261360eb899e9eefa57447436b"},"evidence_id":"mvp-evidence-zh-eu-registration-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-6fc4e12e684157ef4978","version":"1","sha256":"e2262490fc097664c7bf536b1648f9abe5744c616f7df2483fa8e461874bcf16"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-6fc4e12e684157ef4978","version":"1","sha256":"f37f12c5d44782b6d42e676b7e83ae9d4bac26a5661dac863d091225c52b7d12"},"section_id":"full-document","start_offset":1990,"end_offset":2959,"original_excerpt":"Anmeldung bei der Wohngemeinde\n\nEU/EFTA-Staatsangehörige geniessen die volle geographische Mobilität. Das heisst, sie können ihren Wohnsitz jederzeit in die Schweiz bzw. in den Kanton Zürich verlegen. Für die Einreise wird ein gültiger Reisepass oder eine gültige Identitätskarte benötigt.\n\nNach der Einreise in die Schweiz müssen sie sich persönlich bei der zuständigen Einwohnerkontrolle melden und ein Aufenthaltsgesuch einreichen, wenn der Aufenthalt länger als drei Monate oder 90 Arbeitstage dauern soll. Ein Umzug innerhalb des Kantons sowie in einen anderen Kanton muss innert 14 Tagen bei der Einwohnerkontrolle der neuen Wohngemeinde gemeldet werden.\n\nDas Aufenthaltsgesuch mit dem gewünschten Aufenthaltszweck wird von der Einwohnerkontrolle direkt ans Migrationsamt Kanton Zürich weitergeleitet. Wenn die Voraussetzungen für die Erteilung einer ausländerrechtlichen Bewilligung erfüllt sind, stellt das Migrationsamt den entsprechenden Ausländerausweis aus.","citation":{"source_id":"zh-eu-efta","authority":"Canton Zurich - Migration Office","url":"https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html","title":"Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich","accessed_at":"2026-09-10T20:07:37Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-zh-eu-registration"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]},{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-zh-eu-registration-2","version":"1","sha256":"b44b800a2ac88aa947f47235278b992e201fbd0bbcf497097071caa42dbea937"},"evidence_id":"mvp-evidence-zh-eu-registration-2","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-6fc4e12e684157ef4978","version":"1","sha256":"e2262490fc097664c7bf536b1648f9abe5744c616f7df2483fa8e461874bcf16"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-6fc4e12e684157ef4978","version":"1","sha256":"f37f12c5d44782b6d42e676b7e83ae9d4bac26a5661dac863d091225c52b7d12"},"section_id":"full-document","start_offset":3217,"end_offset":3630,"original_excerpt":"EU/EFTA-Staatsangehörige können in der Schweiz eine Erwerbstätigkeit aufnehmen. Hier erfahren Sie, wie Sie genau vorzugehen haben. Als EU/EFTA-Angehörige, die länger als 90 Tage in der Schweiz arbeiten möchten, müssen Sie sich innerhalb von 14 Tagen persönlich bei Ihrer Wohngemeinde anmelden. Alternativ haben Sie die Möglichkeit sich ohne Bewilligung für drei Monate zur Stellensuche in der Schweiz aufzuhalten.","citation":{"source_id":"zh-eu-efta","authority":"Canton Zurich - Migration Office","url":"https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html","title":"Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich","accessed_at":"2026-09-10T20:07:37Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-zh-eu-registration"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:45:40Z","oldest_source_at":"2026-09-10T20:07:37Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["Canton Zurich - Migration Office"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":2,"evidence_count":2,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-zh-eu-registration-1","mvp-evidence-zh-eu-registration-2"],"selections":[],"selection_policy":null}}
```

Assistant:

```text
Based on the official sources I retrieved, here is the answer:

## Registration Deadline for Czech Citizens Starting Work in Zurich

**You must register your stay at the municipal authority (your local *Einwohnerkontrolle* / residents' registration office) within 14 days of your arrival in Switzerland, and before you start working.**

Both limits apply together and are critical:

1. **14-day deadline**: The clock starts from the **date of your arrival in Switzerland** - not from your first working day.
2. **Before starting work**: Registration and the residence permit application must be completed **before you begin employment**, even if the 14-day window hasn't expired yet.

### What you need to bring:
- A valid **passport or identity card** (Czech EU ID card is sufficient)
- **Written confirmation of employment** from your employer (e.g., employment contract stating duration and workload)

### What happens next:
After you personally register at the municipal residents' registration office in Zurich, they will forward your application to the **Cantonal Migration Office (*Migrationsamt Kanton Zürich*)**. If your circumstances are met, the cantonal office will issue the appropriate residence permit (typically a **B permit** for employment of 1+ year or indefinite, or a **short-stay L permit** for contracts up to 364 days).

### Source:
- [State Secretariat for Migration (SEM) - FAQ on Free Movement of Persons](https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html)
- [Canton Zurich Migration Office - EU/EFTA nationals](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html)

> **Important note**: These facts come from an experimental snapshot of Swiss data (valid through 2026-09-11) curated from official SEM and Canton Zurich sources. For legal certainty, also verify the latest requirements on the [SEM website](https://www.sem.admin.ch) and the [City of Zurich immigration page](https://www.zh.ch).
```

#### Turn 2

User:

```text
I will arrive in Zurich on Sunday 13 September 2026 and my first working day is Wednesday 16 September 2026. My contract is open-ended.
```

Tool call 1: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH",
    "municipality_id": "261"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-city-zurich-arrival",
    "residence-city-zurich-arrival-documents"
  ],
  "context": {
    "arrival_origin": "abroad"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-city-zurich-arrival","residence-city-zurich-arrival-documents"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":null,"coverage_profile_ids":[],"status":"OUT_OF_COVERAGE","supported_portions":[],"unresolved_portions":[{"concept_ids":["residence-city-zurich-arrival","residence-city-zurich-arrival-documents"],"reason_code":"unsupported_combination","limitation":"No evaluated profile covers this combination and date."}],"evidence":[],"missing_context":[],"freshness":{"status":"UNKNOWN","checked_at":"2026-09-11T19:45:57Z","oldest_source_at":null,"policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":[],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"NONE","limitations":[]},"trace":null}
```

Tool call 2: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-zh-eu-b",
    "residence-zh-eu-nonworking"
  ],
  "context": {
    "population": "eu_efta"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-zh-eu-b","residence-zh-eu-nonworking"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":null,"coverage_profile_ids":[],"status":"OUT_OF_COVERAGE","supported_portions":[],"unresolved_portions":[{"concept_ids":["residence-zh-eu-b","residence-zh-eu-nonworking"],"reason_code":"unsupported_combination","limitation":"No evaluated profile covers this combination and date."}],"evidence":[],"missing_context":[],"freshness":{"status":"UNKNOWN","checked_at":"2026-09-11T19:46:02Z","oldest_source_at":null,"policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":[],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"NONE","limitations":[]},"trace":null}
```

Tool call 3: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH",
    "municipality_id": "261"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-city-zurich-arrival"
  ],
  "context": {
    "arrival_origin": "abroad"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-city-zurich-arrival"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-city-zurich-arrival"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-city-zurich-arrival"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-city-zurich-arrival-1","version":"1","sha256":"653458faedd1e3cab38cabfa0fba8f8ca487afafb7d002ba70f6d8fff714adb8"},"fact_id":"mvp-fact-city-zurich-arrival-1","statement":"For arrival from abroad, the City of Zurich requires an appointment and personal registration at Personenmeldeamt Zurich Sud. Without an appointment registration is not possible; for family registration every family member must attend in person.","language":"en","evidence_ids":["mvp-evidence-city-zurich-arrival-1"],"rule_refs":[{"artifact_id":"mvp-rule-city-zurich-arrival","version":"1","sha256":"0c281bf6c70b576c53b3213cdc8683da3f4388ff8ad8533942f5fcc15cfc9fca"}],"applicability_conditions":["arrival_origin=abroad"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-city-zurich-arrival-1","version":"1","sha256":"f8b18ebe223c1f6770bde640204fcf601931175d15f02ec1661a1729afc502d4"},"evidence_id":"mvp-evidence-city-zurich-arrival-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-34ef0ec737a996b68d08","version":"1","sha256":"214b9204bd23205e9c76fd2e035d314b16a7cd61a8f7a091563cc363a230ac26"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-34ef0ec737a996b68d08","version":"1","sha256":"cc8dbd21cd0670fc8c794011fb091e77abe1b96412d189746bbc708c158f3f31"},"section_id":"full-document","start_offset":2700,"end_offset":3178,"original_excerpt":"Zuzug aus dem Ausland\n\nSie sind aus dem Ausland nach Zürich gezogen? Für die Anmeldung aus dem Ausland müssen Sie einen Termin vereinbaren. Die Anmeldung findet persönlich beim Personenmeldeamt Zürich Süd statt. Termin für Zuzug aus dem Ausland buchen\n\nHinweis: Für die Anmeldung ist eine Terminvereinbarung zwingend notwendig. Ohne Termin können wir Ihre Anmeldung nicht vornehmen. Zudem müssen bei Familienanmeldungen alle Familienmitglieder persönlich beim Termin erscheinen.","citation":{"source_id":"zurich-city-arrival","authority":"City of Zurich - Population Office","url":"https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html","title":"Zuzug in die Stadt Zürich | Stadt Zürich","accessed_at":"2026-09-10T20:10:21Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-city-zurich-arrival"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:46:06Z","oldest_source_at":"2026-09-10T20:10:21Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["City of Zurich - Population Office"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":1,"evidence_count":1,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-city-zurich-arrival-1"],"selections":[],"selection_policy":null}}
```

Tool call 4: `swisstip_resolve`, status completed

Input:

```json
{
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH",
    "municipality_id": "261"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "concept_ids": [
    "residence-city-zurich-arrival-documents"
  ],
  "context": {
    "arrival_origin": "abroad"
  },
  "max_evidence": 5
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-city-zurich-arrival-documents"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-city-zurich-arrival-documents"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-city-zurich-arrival-documents"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-city-zurich-arrival-documents-1","version":"1","sha256":"a94637dd17434569225390e29a3b1113d74098b0028d9780370f7959c7454982"},"fact_id":"mvp-fact-city-zurich-arrival-documents-1","statement":"The City of Zurich lists a passport (an identity card suffices for EU/EFTA nationals), rental or housing documentation, permit assurance and visa authorisation if available, an employment contract or study confirmation, applicable migration fees, and original civil-status documents for registration from abroad.","language":"en","evidence_ids":["mvp-evidence-city-zurich-arrival-documents-1"],"rule_refs":[{"artifact_id":"mvp-rule-city-zurich-arrival-documents","version":"1","sha256":"8e518498dd60e2d163e0f53a95d2f987698aff36b4a282c6b42aa5a80990cdf2"}],"applicability_conditions":["arrival_origin=abroad"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-city-zurich-arrival-documents-1","version":"1","sha256":"acc924101b3c4ab680c4e41c3cabe9c5d0ea287bf5864e320d486c43230afd1a"},"evidence_id":"mvp-evidence-city-zurich-arrival-documents-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-34ef0ec737a996b68d08","version":"1","sha256":"214b9204bd23205e9c76fd2e035d314b16a7cd61a8f7a091563cc363a230ac26"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-34ef0ec737a996b68d08","version":"1","sha256":"cc8dbd21cd0670fc8c794011fb091e77abe1b96412d189746bbc708c158f3f31"},"section_id":"full-document","start_offset":3180,"end_offset":3716,"original_excerpt":"Vorbereitung für Zuzug aus dem Ausland\n\nFür die Anmeldung aus dem Ausland benötigen Sie folgende Dokumente:\n\nReisepass (bei EU/EFTA Staatsangehörigen genügt auch der Personalausweis)\n\nMietvertrag, Wohnungsausweis oder Untermietvertrag\n\nZusicherung der Aufenthaltsbewilligung (sofern vorhanden)\n\nErmächtigung der Visumserteilung (sofern vorhanden)\n\nArbeitsvertrag oder Studienbestätigung\n\nMigrationsamtliche Gebühren (je nach Art der Bewilligung unterschiedlich)\n\nZivilstandspapiere im Original (Ehepapiere und Geburtsscheine der Kinder)","citation":{"source_id":"zurich-city-arrival","authority":"City of Zurich - Population Office","url":"https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html","title":"Zuzug in die Stadt Zürich | Stadt Zürich","accessed_at":"2026-09-10T20:10:21Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-city-zurich-arrival-documents"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":"261"},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:46:11Z","oldest_source_at":"2026-09-10T20:10:21Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["City of Zurich - Population Office"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":1,"evidence_count":1,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-city-zurich-arrival-documents-1"],"selections":[],"selection_policy":null}}
```

Assistant:

```text
Great, now I can give you a fully personalized answer based on the official sources.

## Your Specific Registration Deadline

**You must register at the municipal authority *before your first working day* - that is, before Wednesday, 16 September 2026.**

Here's why this is the binding constraint:

| Rule | Deadline |
|------|----------|
| 14 days from arrival (13 Sep 2026) | Sunday, **27 September 2026** |
| Before starting work | Wednesday, **16 September 2026** |
| **Effective deadline (earlier of both)** | **Wednesday, 16 September 2026** |

Under both the federal SEM rule and the Canton Zurich rule, **the 14-day clock runs from the date of arrival in Switzerland - not from your first working day** - but **registration must also precede the start of work**. Since your first day (16 Sep) falls *before* the 14-day window expires (27 Sep), the **before-starting-work rule is what binds you**.

## What You Need (for Zurich specifically)

**Appointment is mandatory.** The City of Zurich requires you to book an appointment at the **Personenmeldeamt Zürich Süd** (no walk-ins). Without an appointment, registration is not possible.

**Documents to bring** (per the City of Zurich):

- **Valid passport** or - as an EU/EFTA national - **a valid Czech national ID card** suffices
- **Employment contract** (your open-ended Arbeitsvertrag)
- **Rental agreement / housing documentation** (Mietvertrag or Wohnungsausweis)
- **Migration fees** (amount varies by permit type)
- Original **civil-status documents** if applicable (e.g., marriage/birth certificates)

## What Permit You'll Get

With an **open-ended (unbefristet) contract**, you'll receive a **residence permit B** (Aufenthaltsbewilligung B), which is the standard permit for long-term employment. The registration office (*Einwohnerkontrolle*) will forward your application to the **Cantonal Migration Office (*Migrationsamt Kanton Zürich*)**, which issues the permit if requirements are met.

## Sources

- **Federal**: [SEM - FAQ Personenfreizügigkeit](https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html) - "Innert 14 Tagen nach ihrer Ankunft in der Schweiz und vor Stellenantritt müssen sich EU/EFTA-Bürger bei ihrer Wohngemeinde anmelden"
- **Canton Zurich**: [Aufenthalt für EU/EFTA-Staatsangehörige](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html) - "innerhalb von 14 Tagen persönlich bei Ihrer Wohngemeinde anmelden"
- **City of Zurich**: [Zuzug aus dem Ausland](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html) - Terminvereinbarung zwingend erforderlich

> **Note**: These facts are drawn from an experimental snapshot of Swiss official data (valid through 11 September 2026), curated from SEM, Canton Zurich, and City of Zurich sources. For full legal certainty, also verify on the [SEM website](https://www.sem.admin.ch) and the [City of Zurich immigration page](https://www.zh.ch).
```

### Scenario fourteen-days-first

#### Turn 1

User:

```text
I'm a Czech citizen and starting my work in Zurich next week. By when latest should I register my stay on the municipal authority?
```

Tool call 1: `swisstip_get_coverage`, status completed

Input:

```json
{
  "limit": 20
}
```

Output:

```json
{"schema_version":"get-coverage-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"knowledge_space_id":null,"parent":null,"entries":[{"schema_version":"catalog-entry/v1","entry_id":"hackathon","kind":"knowledge_space","parent_ids":[],"labels":{"en":{"label":"Experimental residence MVP","aliases":[],"description":"Assistant-curated experimental MVP data; no independent human or legal review.","provenance":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"}]}},"lifecycle":"CURATED","replacement_ids":[]}],"coverage_profiles":[],"context_schemas":[],"next_cursor":null,"default_limit":20,"maximum_limit":100,"ordering":"entry_id_ascending"}
```

Assistant:

```text
I'll look up the official Swiss rules on residence registration for foreign nationals in Zurich.
```

Tool call 2: `swisstip_get_coverage`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "limit": 20
}
```

Output:

```json
{"schema_version":"get-coverage-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"knowledge_space_id":"hackathon","parent":null,"entries":[{"schema_version":"catalog-entry/v1","entry_id":"immigration","kind":"domain","parent_ids":["hackathon"],"labels":{"en":{"label":"Immigration","aliases":[],"description":"Assistant-curated experimental MVP data; no independent human or legal review.","provenance":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"}]}},"lifecycle":"CURATED","replacement_ids":[]}],"coverage_profiles":[],"context_schemas":[],"next_cursor":null,"default_limit":20,"maximum_limit":100,"ordering":"entry_id_ascending"}
```

Tool call 3: `swisstip_get_coverage`, status error

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "parent_id": "immigration",
  "limit": 20
}
```

Error returned to the model:

```json
{"schema_version":"tool-error/v1","code":"INVALID_ARGUMENT","issues":[{"path":"request","reason_code":"value_error","message":"Value error, child_and_continuation_requests_require_release","allowed_values":[]}],"release_id":null,"active_release_id":null}
```

Tool call 4: `swisstip_get_coverage`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "parent_id": "immigration",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "limit": 20
}
```

Output:

```json
{
  "schema_version": "get-coverage-result/v1",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "parent": {
    "schema_version": "catalog-entry/v1",
    "entry_id": "immigration",
    "kind": "domain",
    "parent_ids": [
      "hackathon"
    ],
    "labels": {
      "en": {
        "label": "Immigration",
        "aliases": [],
        "description": "Assistant-curated experimental MVP data; no independent human or legal review.",
        "provenance": [
          {
            "artifact_id": "mvp-curation-source",
            "version": "1",
            "sha256": "2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"
          }
        ]
      }
    },
    "lifecycle": "CURATED",
    "replacement_ids": []
  },
  "entries": [
    {
      "entry_id": "residence",
      "kind": "topic",
      "parent_ids": [
        "immigration"
      ],
      "label": "Residence permits in Switzerland"
    }
  ],
  "next_cursor": null,
  "default_limit": 20,
  "maximum_limit": 100,
  "ordering": "entry_id_ascending",
  "coverage_profiles": [
    {
      "schema_version": "coverage-profile/v1",
      "coverage_profile_id": "mvp-profile-eu-employment-registration-deadline",
      "release_id": "hackathon-residence-semantic-2026-09-11-v2",
      "catalog_ref": {
        "artifact_id": "mvp-catalog",
        "version": "1",
        "sha256": "a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"
      },
      "knowledge_space_id": "hackathon",
      "domain_id": "immigration",
      "topic_id": "residence",
      "concept_ids": [
        "residence-eu-employment-registration-deadline"
      ],
      "intent": "requirements",
      "concept_selection_required": true,
      "jurisdiction": {
        "country_code": "CH",
        "canton_code": null,
        "municipality_id": null
      },
      "context_schema_ref": {
        "artifact_id": "mvp-context-eu-employment-registration-deadline",
        "version": "1",
        "sha256": "744c08c553d36034ae976186d5bbec4e9bdb771ac7296cb35fddea8becc29867"
      },
      "scope_modes": [
        "exact"
      ],
      "max_descendant_depth": 0,
      "max_concepts": 1,
      "source_ids": [
        "ch-sem-free-movement-faq"
      ],
      "source_languages": [
        "de"
      ],
      "temporal_coverage": {
        "valid_from": "2026-09-10",
        "valid_through": "2026-09-11"
      },
      "term_routes": [],
      "projection_languages_complete": [],
      "evaluation_ref": {
        "artifact_id": "mvp-experimental-test-policy",
        "version": "1",
        "sha256": "d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"
      },
      "rule_refs": [
        {
          "artifact_id": "mvp-rule-eu-employment-registration-deadline",
          "version": "1",
          "sha256": "b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"
        }
      ],
      "exclusions": [
        "Assistant-curated experimental MVP data; no independent human or legal review.",
        "Frozen snapshot test window only; not complete Swiss legal coverage.",
        "Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work."
      ],
      "freshness_policy": {
        "max_age_days": 30,
        "policy_ref": {
          "artifact_id": "mvp-experimental-test-policy",
          "version": "1",
          "sha256": "d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"
        }
      },
      "approval_status": "APPROVED"
    },
    "[...] 60 profiles in total"
  ],
  "context_schemas": "[...] 60 context schemas omitted"
}
```

Tool call 5: `swisstip_resolve`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "concept_ids": [
    "residence-eu-employment-registration-deadline"
  ],
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "context": {
    "population": "eu_efta"
  }
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-eu-employment-registration-deadline"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-eu-employment-registration-deadline"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-eu-employment-registration-deadline"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-eu-employment-registration-deadline-1","version":"1","sha256":"8ef7c24120b0cdc35996599a6e3b97450523f266f43879c58a3e5eccf730d3e8"},"fact_id":"mvp-fact-eu-employment-registration-deadline-1","statement":"SEM states that EU/EFTA nationals taking up employment of more than three months must register with their municipality of residence and apply for a residence permit within 14 days of their arrival in Switzerland and before starting work. A valid identity card or passport and the employer's written confirmation of employment (for example the contract with its duration and workload) must be presented; the contract duration determines whether a short-stay permit L or a residence permit B is issued.","language":"en","evidence_ids":["mvp-evidence-eu-employment-registration-deadline-1"],"rule_refs":[{"artifact_id":"mvp-rule-eu-employment-registration-deadline","version":"1","sha256":"b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"}],"applicability_conditions":["Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work.","population=eu_efta"]},{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-eu-employment-registration-deadline-2","version":"1","sha256":"3f3a6c389339798a734d984fe5f2e88897ec3e88f0516bbead5aa949a07c6df3"},"fact_id":"mvp-fact-eu-employment-registration-deadline-2","statement":"SEM states that the steps needed to obtain the residence permit can be completed after arrival in Switzerland.","language":"en","evidence_ids":["mvp-evidence-eu-employment-registration-deadline-2"],"rule_refs":[{"artifact_id":"mvp-rule-eu-employment-registration-deadline","version":"1","sha256":"b96ab8116d0d336fece405469980f3bb6a147a777923c4062e05dc6341bc0fdc"}],"applicability_conditions":["Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work.","population=eu_efta"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-eu-employment-registration-deadline-1","version":"1","sha256":"858729eef684d85d6e3e073ec0ac8be755642b26b4a38c113d81e67adc9bf744"},"evidence_id":"mvp-evidence-eu-employment-registration-deadline-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-094ef42324485ec86493","version":"1","sha256":"23d63f2e62afba6b7b55fc49ae58c4b46909fd17a58d0cc440f637d84b7413fc"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-094ef42324485ec86493","version":"1","sha256":"81f991c06bc103b0414cd6c92c41477127c97b19ba8013a712eed9c8b53b23ea"},"section_id":"full-document","start_offset":3701,"end_offset":4356,"original_excerpt":"Erwerbstätigkeit ab 3 Monaten:\n\nInnert 14 Tagen nach ihrer Ankunft in der Schweiz und vor Stellenantritt, müssen sich die Bürgerinnen und Bürger der EU/EFTA bei ihrer Wohngemeinde anmelden und eine Aufenthaltsbewilligung beantragen. Eine gültige Identitätskarte (oder Pass) sowie eine schriftliche Einstellungserklärung des Arbeitgebers (z.B. Arbeitsvertrag mit angegebener Dauer der Anstellung und Arbeitspensum) sind vorzuweisen. Je nach Dauer des Arbeitsverhältnisses wird eine Kurzaufenthaltsbewilligung (Ausweis L, Arbeitsvertrag bis 364 Tage) oder eine Aufenthaltsbewilligung B (Vertragsdauer von mindestens einem Jahr oder unbefristet) ausgestellt.","citation":{"source_id":"ch-sem-free-movement-faq","authority":"State Secretariat for Migration (SEM)","url":"https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html","title":"FAQ - Fragen zur Personenfreizügigkeit","accessed_at":"2026-09-10T20:05:56Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-eu-employment-registration-deadline"],"jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]},{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-eu-employment-registration-deadline-2","version":"1","sha256":"2333898924ed358629a32d745b08999792dfbd99630f6043ad0a86f126bb3474"},"evidence_id":"mvp-evidence-eu-employment-registration-deadline-2","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-094ef42324485ec86493","version":"1","sha256":"23d63f2e62afba6b7b55fc49ae58c4b46909fd17a58d0cc440f637d84b7413fc"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-094ef42324485ec86493","version":"1","sha256":"81f991c06bc103b0414cd6c92c41477127c97b19ba8013a712eed9c8b53b23ea"},"section_id":"full-document","start_offset":4358,"end_offset":4479,"original_excerpt":"Die notwendigen Schritte zur Erlangung der Aufenthaltsbewilligung können nach der Ankunft in der Schweiz erledigt werden.","citation":{"source_id":"ch-sem-free-movement-faq","authority":"State Secretariat for Migration (SEM)","url":"https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html","title":"FAQ - Fragen zur Personenfreizügigkeit","accessed_at":"2026-09-10T20:05:56Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-eu-employment-registration-deadline"],"jurisdiction":{"country_code":"CH","canton_code":null,"municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:46:47Z","oldest_source_at":"2026-09-10T20:05:56Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["State Secretariat for Migration (SEM)"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage.","Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":2,"evidence_count":2,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-eu-employment-registration-deadline-1","mvp-evidence-eu-employment-registration-deadline-2"],"selections":[],"selection_policy":null}}
```

Assistant:

```text
I found several relevant profiles. Let me now resolve the key ones for your situation - a Czech (EU) citizen starting work in Zurich. I'll check both the general EU employment registration deadline and the Zurich-specific EU registration rules.
```

Tool call 6: `swisstip_resolve`, status completed

Input:

```json
{
  "knowledge_space_id": "hackathon",
  "domain_id": "immigration",
  "topic_id": "residence",
  "concept_ids": [
    "residence-zh-eu-registration"
  ],
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH"
  },
  "as_of": "2026-09-11",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "context": {
    "population": "eu_efta"
  }
}
```

Output:

```json
{"schema_version":"structured-grounding-result/v1","release_id":"hackathon-residence-semantic-2026-09-11-v2","release_ref":{"artifact_id":"hackathon-residence-semantic-2026-09-11-v2","version":"1","sha256":"77a9a311b198dac10d6948041a9d981e1702ea81269f4c80d81bd0b834a0380f"},"catalog_ref":{"artifact_id":"mvp-catalog","version":"1","sha256":"a9b6d73fd5fec997750f0511e339b0ac01b91f1aa770fc4edf50b13465c5b59c"},"requested_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-zh-eu-registration"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"executed_scope":{"knowledge_space_id":"hackathon","domain_id":"immigration","topic_id":"residence","concept_ids":["residence-zh-eu-registration"],"intent":"requirements","jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"as_of":"2026-09-11","scope_mode":"exact"},"coverage_profile_ids":["mvp-profile-zh-eu-registration"],"status":"SUPPORTED","supported_portions":[{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-zh-eu-registration-1","version":"1","sha256":"a5cd0a4a6fdcb6c5483a232ce291acb687a58ac44730a36342faeb9bf4722109"},"fact_id":"mvp-fact-zh-eu-registration-1","statement":"Zurich states that EU/EFTA nationals entering Switzerland need a valid passport or identity card. After entry they apply personally through the residents registration office for the longer stays described on the page; the office forwards the application to the cantonal migration office.","language":"en","evidence_ids":["mvp-evidence-zh-eu-registration-1"],"rule_refs":[{"artifact_id":"mvp-rule-zh-eu-registration","version":"1","sha256":"1030d4c4dbd61f7d9b81710b7dcb8a66d8a5f645f2620c2a1741110f039b4a60"}],"applicability_conditions":["population=eu_efta"]},{"schema_version":"published-fact/v1","identity":{"artifact_id":"mvp-fact-zh-eu-registration-2","version":"1","sha256":"418684e78756aa4cec7ed44384436670bd4efb7a3fec503e80c4fd5e4e201fe4"},"fact_id":"mvp-fact-zh-eu-registration-2","statement":"For EU/EFTA nationals wishing to work in Switzerland for longer than 90 days, Zurich specifies personal registration with the municipality within fourteen days. The page also describes an alternative three-month stay to look for work without a permit.","language":"en","evidence_ids":["mvp-evidence-zh-eu-registration-2"],"rule_refs":[{"artifact_id":"mvp-rule-zh-eu-registration","version":"1","sha256":"1030d4c4dbd61f7d9b81710b7dcb8a66d8a5f645f2620c2a1741110f039b4a60"}],"applicability_conditions":["population=eu_efta"]}],"unresolved_portions":[],"evidence":[{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-zh-eu-registration-1","version":"1","sha256":"014e54ad9ce9fd99b5c9c3654a9f5c86a8752b261360eb899e9eefa57447436b"},"evidence_id":"mvp-evidence-zh-eu-registration-1","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-6fc4e12e684157ef4978","version":"1","sha256":"e2262490fc097664c7bf536b1648f9abe5744c616f7df2483fa8e461874bcf16"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-6fc4e12e684157ef4978","version":"1","sha256":"f37f12c5d44782b6d42e676b7e83ae9d4bac26a5661dac863d091225c52b7d12"},"section_id":"full-document","start_offset":1990,"end_offset":2959,"original_excerpt":"Anmeldung bei der Wohngemeinde\n\nEU/EFTA-Staatsangehörige geniessen die volle geographische Mobilität. Das heisst, sie können ihren Wohnsitz jederzeit in die Schweiz bzw. in den Kanton Zürich verlegen. Für die Einreise wird ein gültiger Reisepass oder eine gültige Identitätskarte benötigt.\n\nNach der Einreise in die Schweiz müssen sie sich persönlich bei der zuständigen Einwohnerkontrolle melden und ein Aufenthaltsgesuch einreichen, wenn der Aufenthalt länger als drei Monate oder 90 Arbeitstage dauern soll. Ein Umzug innerhalb des Kantons sowie in einen anderen Kanton muss innert 14 Tagen bei der Einwohnerkontrolle der neuen Wohngemeinde gemeldet werden.\n\nDas Aufenthaltsgesuch mit dem gewünschten Aufenthaltszweck wird von der Einwohnerkontrolle direkt ans Migrationsamt Kanton Zürich weitergeleitet. Wenn die Voraussetzungen für die Erteilung einer ausländerrechtlichen Bewilligung erfüllt sind, stellt das Migrationsamt den entsprechenden Ausländerausweis aus.","citation":{"source_id":"zh-eu-efta","authority":"Canton Zurich - Migration Office","url":"https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html","title":"Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich","accessed_at":"2026-09-10T20:07:37Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-zh-eu-registration"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]},{"schema_version":"evidence-object/v1","identity":{"artifact_id":"mvp-evidence-zh-eu-registration-2","version":"1","sha256":"b44b800a2ac88aa947f47235278b992e201fbd0bbcf497097071caa42dbea937"},"evidence_id":"mvp-evidence-zh-eu-registration-2","release_id":"hackathon-residence-semantic-2026-09-11-v2","snapshot_ref":{"artifact_id":"mvp-snapshot-doc-6fc4e12e684157ef4978","version":"1","sha256":"e2262490fc097664c7bf536b1648f9abe5744c616f7df2483fa8e461874bcf16"},"normalized_document_ref":{"artifact_id":"mvp-normalized-doc-6fc4e12e684157ef4978","version":"1","sha256":"f37f12c5d44782b6d42e676b7e83ae9d4bac26a5661dac863d091225c52b7d12"},"section_id":"full-document","start_offset":3217,"end_offset":3630,"original_excerpt":"EU/EFTA-Staatsangehörige können in der Schweiz eine Erwerbstätigkeit aufnehmen. Hier erfahren Sie, wie Sie genau vorzugehen haben. Als EU/EFTA-Angehörige, die länger als 90 Tage in der Schweiz arbeiten möchten, müssen Sie sich innerhalb von 14 Tagen persönlich bei Ihrer Wohngemeinde anmelden. Alternativ haben Sie die Möglichkeit sich ohne Bewilligung für drei Monate zur Stellensuche in der Schweiz aufzuhalten.","citation":{"source_id":"zh-eu-efta","authority":"Canton Zurich - Migration Office","url":"https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html","title":"Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich","accessed_at":"2026-09-10T20:07:37Z"},"declared_language":["de"],"detected_language":null,"effective_source_language":"de","language_detection_method":"declared-metadata-or-source-registry","language_confidence":0.0,"reviewed_language_override_ref":null,"canonical_concept_ids":["residence-zh-eu-registration"],"jurisdiction":{"country_code":"CH","canton_code":"CH-ZH","municipality_id":null},"temporal_coverage":{"valid_from":"2026-09-10","valid_through":"2026-09-11"},"provenance_refs":[{"artifact_id":"mvp-curation-source","version":"1","sha256":"2326e42654168a2f5daaf44c5a94707164564598ce71f639fc09ed4eff9c335e"},{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}]}],"missing_context":[],"freshness":{"status":"FRESH","checked_at":"2026-09-11T19:46:47Z","oldest_source_at":"2026-09-10T20:07:37Z","policy_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"}},"trust":{"source_authorities":["Canton Zurich - Migration Office"],"evaluation_ref":{"artifact_id":"mvp-experimental-test-policy","version":"1","sha256":"d24dad3e0a8e5ab3938c696b6684bf107e5444a92b04e6f708e00e79cdfdc261"},"fact_support":"PUBLISHED_FACTS_OR_RULES","limitations":["Legacy identifier/lexical release; no hybrid retrieval assets.","Assistant-curated experimental MVP data; no independent human or legal review.","Frozen snapshot test window only; not complete Swiss legal coverage."]},"trace":{"term_routes":[],"effective_source_languages":["de"],"channels":["concept"],"index_refs":[],"provider_configuration_ref":{"artifact_id":"mvp-no-providers","version":"1","sha256":"b9d22a733b382e7b65a4e695bbf408ca49c55583648d0e10343fdc9f3949ef2f"},"ranking_configuration_ref":{"artifact_id":"mvp-baseline-ranking","version":"1","sha256":"affad36e20a45977ee3c45e41949e3986a6b92fa19f5904706cff494c61e4f72"},"candidate_count":2,"evidence_count":2,"degradations":[],"language_policy_ref":{"artifact_id":"mvp-language-policy","version":"1","sha256":"9b25526860082e0abfbf3ad22944a2db50aff57622f92c706052dbe07d6bed9b"},"projection_refs":[],"candidate_ids":["mvp-evidence-zh-eu-registration-1","mvp-evidence-zh-eu-registration-2"],"selections":[],"selection_policy":null}}
```

Tool call 7: `swisstip_resolve`, status error

Input:

```json
{
  "as_of": "2026-09-11",
  "concept_ids": [
    "residence-city-zurich-arrival"
  ],
  "context": {
    "arrival_origin": "abroad"
  },
  "domain_id": "immigration",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH",
    "municipality_id": "261"
  },
  "knowledge_space_id": "hackathon",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1"
}
```

Error returned to the model:

```json
{"schema_version":"tool-error/v1","code":"INVALID_ARGUMENT","issues":[{"path":"topic_id","reason_code":"missing","message":"Field required","allowed_values":[]}],"release_id":null,"active_release_id":null}
```

Tool call 8: `swisstip_resolve`, status error

Input:

```json
{
  "as_of": "2026-09-11",
  "concept_ids": [
    "residence-city-zurich-arrival-documents"
  ],
  "context": {
    "arrival_origin": "abroad"
  },
  "domain_id": "immigration",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH",
    "municipality_id": "261"
  },
  "knowledge_space_id": "hackathon",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1"
}
```

Error returned to the model:

```json
{"schema_version":"tool-error/v1","code":"INVALID_ARGUMENT","issues":[{"path":"topic_id","reason_code":"missing","message":"Field required","allowed_values":[]}],"release_id":null,"active_release_id":null}
```

Assistant:

```text
Let me also check the Zurich city-specific arrival information for additional detail
```

Assistant:

```text
I now have all the information I need from both the federal and cantonal levels. Here's the answer based on official sources:

---

**As a Czech (EU/EFTA) citizen starting work in Zurich, you must register your stay with the municipal authority (Wohngemeinde / Einwohnerkontrolle) within 14 days of your arrival in Switzerland, and importantly - before you start working.**

Here are the key facts from official sources:

### Federal Rule (State Secretariat for Migration - SEM):
> *"Innert 14 Tagen nach ihrer Ankunft in der Schweiz und vor Stellenantritt, müssen sich die Bürgerinnen und Bürger der EU/EFTA bei ihrer Wohngemeinde anmelden und eine Aufenthaltsbewilligung beantragen."*

- **Deadline**: 14 days from **arrival in Switzerland** (not from your first working day)
- **Must happen before starting work** - registration must precede the start of employment
- You'll need a valid **ID card or passport** and your **employer's written confirmation** (e.g., employment contract showing duration and workload)
- Depending on your contract length, you'll receive either a **short-stay permit L** (contract up to 364 days) or a **residence permit B** (contract of at least one year or indefinite)

### Canton Zurich Rule (Canton Zurich Migration Office):
> *"Als EU/EFTA-Angehörige, die länger als 90 Tage in der Schweiz arbeiten möchten, müssen Sie sich innerhalb von 14 Tagen persönlich bei Ihrer Wohngemeinde anmelden."*

- Zurich specifies **personal registration** with the municipality within **14 days**
- You must appear **in person** at the residents' registration office (*Einwohnerkontrolle*)
- The office will forward your application to the Cantonal Migration Office (*Migrationsamt Kanton Zürich*)
- You also need to register a change of address within the canton within **14 days** if moving within Zurich

### Practical summary:
| Requirement | Deadline |
|---|---|
| Register at municipal authority | **Within 14 days of arrival** in Switzerland |
| Must be done | **Before starting work** |
| Where | Your local *Wohngemeinde* / *Einwohnerkontrolle* in Zurich |
| Documents | Valid passport/ID + employer's written employment confirmation |

**Sources:**
- State Secretariat for Migration (SEM) FAQ on free movement: https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html
- Canton Zurich Migration Office: https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html

> **Note**: This information comes from an official snapshot of SEM and Canton Zurich sources. The data is current as of September 10-11, 2026. For the most up-to-date and personalized guidance, you may also want to contact the Zurich Migration Office or the Citizens' Registration Office (*Einwohmerkontrolle*) of your specific district in Zurich.
```

#### Turn 2

User:

```text
I already arrived in Zurich on Tuesday 1 September 2026. My first working day is Friday 18 September 2026 and the contract is for two years.
```

Tool call 1: `swisstip_resolve`, status error

Input:

```json
{
  "as_of": "2026-09-11",
  "concept_ids": [
    "residence-zh-eu-b"
  ],
  "context": {
    "population": "eu_efta"
  },
  "domain_id": "immigration",
  "intent": "requirements",
  "jurisdiction": {
    "country_code": "CH",
    "canton_code": "CH-ZH"
  },
  "knowledge_space_id": "hackathon",
  "release_id": "hackathon-residence-semantic-2026-09-11-v2",
  "scope_mode": "exact",
  "schema_version": "structured-grounding/v1"
}
```

Error returned to the model:

```json
{"schema_version":"tool-error/v1","code":"INVALID_ARGUMENT","issues":[{"path":"topic_id","reason_code":"missing","message":"Field required","allowed_values":[]}],"release_id":null,"active_release_id":null}
```

Assistant:

```text
With those specific dates, I can now give you a precise answer. Let me also check the Zurich-specific B permit details since your contract is for two years.
```

Assistant:

```text
Good - you've provided the critical details. I now have all the information needed to give you a precise answer. Here it is:

---

## Your Specific Situation: Key Dates & Deadline

Based on what I've already confirmed from both SEM and the Canton Zurich Migration Office, here's how the rules apply to you:

### The 14-Day Clock Starts from Arrival

| Event | Date |
|---|---|
| **Arrival in Switzerland** | Tuesday, 1 September 2026 |
| **14-day registration deadline** | **Tuesday, 15 September 2026** |
| First working day | Friday, 18 September 2026 |
| Today | Friday, 11 September 2026 |

**The critical rule (from SEM)**: *"Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work."*

This means:

- ✅ Your deadline is **Tuesday, 15 September 2026** (14 days after arrival), **not** based on your 18 September start date.
- ✅ The 15 September deadline also happens to be **3 days before** your first working day - so both conditions are met simultaneously.
- ⚠️ **You have only 4 days left (today through 15 September)** to complete registration.

### Your Permit Type: **B Permit** (Residence Permit B)

Since your contract is for **two years** (at least one year), the SEM confirms you would receive a **residence permit B** (Aufenthaltsbewilligung B), rather than a short-stay permit L (which applies to contracts up to 364 days).

### What You Need to Bring

1. **Valid passport or identity card** (Czech national ID card is valid for EU/EFTA citizens)
2. **Employer's written confirmation of employment** - your employment contract showing duration (2 years) and workload
3. **Personal appearance** - you must register in person at your local *Einwohnerkontrolle* / *Wohngemeinde* in Zurich

### What Happens After Registration

The Zurich *Einwohnerkontrolle* will forward your application to the **Cantonal Migration Office** (*Migrationsamt Kanton Zürich*), which will issue the B permit if all conditions are met.

---

### Summary of Actions You Should Take

| Step | Action | By When |
|---|---|---|
| 1 | Contact/visit your local Zurich *Einwohnerkontrolle* to schedule registration | **As soon as possible - today or tomorrow** |
| 2 | Gather documents: ID/passport + signed employment contract | Before appointment |
| 3 | Register in person & submit application | **By Tuesday, 15 September 2026** |
| 4 | Receive B permit (after processing) | Ongoing - can continue working once registered |

> **Sources**:
> - SEM FAQ on EU/EFTA free movement: https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html
> - Canton Zurich Migration Office: https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html
> - This information is based on official source snapshots dated 10-11 September 2026.
```
