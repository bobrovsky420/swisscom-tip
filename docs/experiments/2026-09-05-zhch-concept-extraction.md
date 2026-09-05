# zh.ch concept extraction experiment: Apertus 8B and 70B

Experiment date: 2026-09-05. Status: completed POC runs, not a validated quality benchmark.

## Outcome

Both models completed extraction from the same six downloaded German-language
zh.ch pages. Apertus 8B retained 47 candidate concepts; Apertus 70B retained 55.
Exact evidence references and primary-section constraints passed verification
for all retained candidates. Checkpoint reuse prevented repeated inference for
completed work after provider failures.

Semantic completeness remains a significant weakness. Both models omitted an
important condition from a close-relative concept, and their model reviewers
accepted it. Matching source text is not proof that a description is complete,
correctly scoped or entailed by its citations. These proposals are not legal
guidance or approved knowledge-base content.

70B retained more overview and employment-procedure concepts, but this does not
establish greater accuracy. The models also chose different topics and different
levels of detail. No human-review worksheet rows had been completed at the time
of verification; the findings below include targeted assistant spot-checks, not
an independently labelled evaluation.

## Inputs, configuration and evidence

The fixture consists of the following pages beneath
`https://www.zh.ch/de/migration-integration/`:

| Page | Relative path |
|---|---|
| Residence overview | `aufenthalt.html` |
| EU/EFTA residence | `aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html` |
| Third-country residence with employment | `aufenthalt/aufenthalt-mit-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html` |
| Third-country residence without employment | `aufenthalt/aufenthalt-ohne-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html` |
| Biometric residence documents | `aufenthalt/biometrische-auslaenderausweise.html` |
| Family reunification | `aufenthalt/familiennachzug-von-drittstaatsangehoerigen.html` |

Final comparison runs:

- 8B: `8b-v3-02`, model `swiss-ai/Apertus-8B-Instruct-2509`.
- 70B: `70b-v3-05`, model `swiss-ai/Apertus-70B-Instruct-2509`.
- Both used the HF router with explicitly selected provider `publicai`.

Shared generation/extraction settings were `concept_extraction_v3`, temperature
0.0, 4096 maximum output tokens, 6400-character chunks, 400-character overlap,
and at most six proposed concepts per chunk. The limits were 12 model attempts
per page and 30 per invocation. Configured request timeouts differed: 120 seconds
for 8B and 180 seconds for 70B. The 8B final run additionally had the new review
fallback setting, but did not exercise that fallback.

The final reports have identical generation and extraction settings, matching
normalized input hashes for all six pages, and byte-identical download manifests.
The SHA-256 of the shared `download-manifest.json` is:

```text
4f9e854e4325c25e193e8ce2a9281999521cb2bc1d08dad3bb928eecf6f79869
```

Evidence is in `<system-temp>/swisstip-zhch-poc/runs/<run-name>/`:

- `concept-proposals.json`: candidates, evidence, diagnostics and effective settings.
- `run.log`: progress, failures, retry waits and execution accounting.
- `review.csv`: retained candidates and human-review fields.
- `download-manifest.json`: fixture identity and downloaded-file hashes.

On Windows, `<system-temp>` is normally `%TEMP%`. These artifacts are local and
are not committed with this report. Keep the downloaded fixture and raw responses
internal unless reuse is permitted by the source's usage terms. Preserve the
artifacts before temporary-directory cleanup; this document is an analysis
summary, not a replacement for the source snapshots or a self-contained dataset.

## Quantitative comparison

| Measure | Apertus 8B | Apertus 70B |
|---|---:|---:|
| Pages with retained concepts | 6 | 6 |
| Proposed candidates | 59 | 57 |
| Retained candidates | 47 | 55 |
| Primary-section violations rejected | 11 | 2 |
| Semantic-review rejections | 1 | 0 |
| Total rejected | 12 | 2 |
| Rejection rate | 20.34% | 3.51% |
| Retained evidence spans checked | 95 | 120 |
| Evidence-offset / primary-section errors found | 0 | 0 |
| Retained candidates without questions | 0 | 0 |
| Excluded sections | 105 | 105 |
| Generic link-only chunks skipped | 1 | 1 |
| Logical generation + review requests | 22 | 22 |
| Logical review requests | 11 | 11 |
| Conservative consolidated concepts | 47 | 55 |
| Possible duplicate pairs suggested | 5 | 3 |
| Populated human-review worksheet rows | 0 | 0 |

No exact consolidation reduced the candidate count. Duplicate pairs are review
suggestions, not automatically merged concepts. The 8B semantic reviewer rejected
one UK/FZA proposal because its selected evidence did not support the stated
quota details. Its issue code was `insufficient_context`.

### Usage and recovery accounting

| Measure | `8b-v3-02` | `70b-v3-05` |
|---|---:|---:|
| Reused responses | 19 | 14 |
| New model attempts in the final invocation | 3 | 8 |
| Transient retries in the final invocation | 0 | 0 |
| Smaller-review fallback in the final invocation | Not used | Not used |
| New successful input tokens | 8624 | 21988 |
| New successful output tokens | 2570 | 6644 |
| Full logical-result input tokens, including reused responses | 65832 | 70773 |
| Full logical-result output tokens, including reused responses | 21574 | 21685 |
| Final invocation elapsed seconds | 41.849 | 117.944 |

These elapsed times are not end-to-end model-speed measurements: the invocations
resumed different amounts of cached work. Full-result token totals describe
successful responses contributing to the result, not all work across failed
attempts. Earlier timeouts and truncated completions may incur additional usage;
neither table is a billing receipt or a reliable cost comparison.

## Retained concept comparison

The following tables align shortened labels by topic, not by identical claims.
`Yes` means a separate retained candidate. `Included` means content inside
another candidate. `-` means no retained standalone candidate on that page,
not necessarily that the model never proposed the topic. Scope and classification
can differ even where both columns say `Yes`.

### 1. Residence overview: 8B 2, 70B 5

| Concept | 8B | 70B |
|---|---|---|
| Aufenthalt mit Erwerbstätigkeit für Drittstaatsangehörige | - | Yes |
| Aufenthalt ohne Erwerbstätigkeit für Drittstaatsangehörige | - | Yes |
| Familiennachzug von Drittstaatsangehörigen | - | Yes |
| Kurzaufenthaltsbewilligung (L) | Yes | Yes |
| Aufenthaltsbewilligung (B) | Yes | Yes |

8B proposed the first three topics too, but their evidence crossed the required
primary-section boundary and they were rejected.

### 2. EU/EFTA residence: 8B 10, 70B 10

| Concept | 8B | 70B |
|---|---|---|
| Freizügigkeitsabkommen / Personenfreizügigkeit | Yes | Yes |
| Meldeverfahren für Erwerbstätigkeit bis 90 Arbeitstage | Yes | Yes |
| Kurzaufenthaltsbewilligung (L) | Yes | Yes |
| Aufenthaltsbewilligung (B) | Yes | Yes |
| Grenzgängerbewilligung (G) | Yes | Yes |
| Aufnahme einer selbständigen Erwerbstätigkeit | Yes | Yes |
| Aufenthalt ohne Erwerbstätigkeit | Yes | Yes |
| Familiennachzug: Anspruch und berechtigte Angehörige | Yes | - |
| Familiennachzug: Zulassungsvoraussetzungen und Nachweise | - | Yes |
| Brexit-Auswirkungen auf das Freizügigkeitsabkommen | Yes | Yes |
| Freizügigkeitsrechte für liechtensteinische Staatsangehörige | Yes | Yes |

8B classified self-employment as a `DOCUMENT`; 70B classified it as a `PROCESS`.
Their family-reunification candidates emphasize different aspects, despite equal
page-level candidate counts.

### 3. Third-country residence with employment: 8B 8, 70B 11

| Concept | 8B | 70B |
|---|---|---|
| Arbeitsbewilligung beantragen | - | Yes |
| Kontingente für Drittstaatsangehörige | - | Yes |
| Bewilligungspflicht für Drittstaatsangehörige | - | Yes |
| EasyGov für Arbeitsbewilligungen | Yes | Yes |
| Erwerbstätigkeit von Familienangehörigen | Yes | Yes |
| Einverständnis: Wohnsitz ausserhalb Zürichs, Arbeit in Zürich | Yes | Yes |
| Einverständnis: Wohnsitz in Zürich, Arbeit in anderem Kanton | Yes | Yes |
| Kurzaufenthaltsbewilligung für befristete Arbeitsverträge | Yes | Yes |
| Aufenthaltsbewilligung für unbefristete/überjährige Arbeitsverträge | Yes | Yes |
| Model label: Kurzfristige Erwerbstätigkeit ohne Bewilligung (bis 4 Monate) | Yes | Yes |
| Einreiseerlaubnis statt Ausländerausweis bei Viermonatsregel | Yes | Yes |

Both models labelled the family-members' employment concept "Familiennachzug für
Drittstaatsangehörige", although its description concerns employment rights.
The "ohne Bewilligung" label is an unverified model claim: a quota exemption does
not by itself establish a permit exemption. Do not promote it based only on the
matching quota-exemption citation.

### 4. Third-country residence without employment: 8B 12, 70B 11

| Concept | 8B | 70B |
|---|---|---|
| Aufenthalt als Rentner/in aus Drittstaaten | Yes | Yes |
| Voraussetzungen für Einreisebewilligung als Rentner/in | Yes | Included above |
| Einreisebewilligung für nahe Verwandte / Familiennachzug | Yes | Yes |
| Einreise zur Vorbereitung der Heirat | Yes | Yes |
| Einreise/Aufenthalt zur medizinischen Behandlung | Yes | Yes |
| Einreise/Aufenthalt im Konkubinat | Yes | Yes |
| Einreisegesuch für Aus- und Weiterbildung | Yes | Yes |
| Finanzielle Mittel für Aus- und Weiterbildung | Yes | Yes |
| Sprachliche und bildungsmässige Voraussetzungen | Yes | Yes |
| Detailliertes Studienprogramm | Yes | Yes |
| Begründungspflicht für über 30-Jährige | Yes | Yes |
| Begründung der Studienplatzwahl Zürich | Yes | Yes |

The main count difference is granularity: 8B split retirement residence and its
conditions into two concepts. Both close-relative descriptions omit the source's
special care/support-needs condition; see the quality findings below.

### 5. Biometric residence documents: 8B 5, 70B 8

| Concept | 8B | 70B |
|---|---|---|
| Ausländerausweis für EU/EFTA-Staatsangehörige | Yes | - |
| Ausländerausweis für Personen im Asylprozess, F/N | Yes | - |
| Sicherheit biometrischer Ausweise | Yes | - |
| Ausstellung biometrischer Ausweise für Drittstaatsangehörige | - | Yes |
| Biometrische Daten auf dem Ausländerausweis | - | Yes |
| Speicherung biometrischer Daten | - | Yes |
| Persönliche Anwesenheit zur Datenerfassung | - | Yes |
| Online-Verschiebung des Biometrietermins | - | Yes |
| Fristen für die Verschiebung des Biometrietermins | - | Yes |
| Verlustmeldung für Ausweiskategorien C, B, L, N oder F | Yes | Yes |
| Unterlagen für ein Ausweisduplikat | Yes | Yes |

Only two retained topics clearly overlap. The higher 70B count does not mean it
covers all the topics retained by 8B.

### 6. Family reunification: 8B 10, 70B 10

| Concept | 8B | 70B |
|---|---|---|
| Familiennachzug durch EU/EFTA-Staatsangehörige | Yes | Yes |
| Visumspflicht für nachzuziehende Familienangehörige | Yes | Yes |
| Prüfung auf Rechtsmissbrauch und Widerrufsgründe | Yes | Yes |
| Kein Neubeginn der Nachzugsfristen bei Einbürgerung | Yes | Yes |
| Nachzugsfristen bei Familiennachzug durch Schweizer Staatsangehörige | - | Yes |
| Nachzugsfristen für Familienangehörige anerkannter Flüchtlinge | Yes | Yes |
| Deutschkenntnisse / Kursanmeldung für nachzuziehende Ehegatten | Yes | Included below |
| Angemessene gemeinsame Wohnung | Yes | Yes |
| Sozialhilfeunabhängigkeit | Yes | Included below |
| Gebündelte Voraussetzungen für Familiennachzug anerkannter Flüchtlinge | - | Yes |
| Opferhilfe-Nummer 142 | Yes | Yes |
| Schutzbrief gegen Mädchenbeschneidung | Yes | Yes |

8B scoped its housing concept to recognized refugees, whereas 70B stated all
family-reunification applications. This is a scope difference requiring review,
not an equivalent claim merely because the topic matches.

## Quality findings and limitations

1. **Exact evidence location works, but completeness does not follow.** All 95
   retained 8B spans and 120 retained 70B spans matched their normalized source
   offsets and primary sections. Both models nevertheless omitted the condition
   "besondere Betreuungs- oder Pflegebedürfnisse" from the close-relative concept
   in `section-0009` of the non-employment page. Both model reviewers accepted
   the descriptions. This is a concrete false negative in model review.
2. **Scope remains fragile.** Family-reunification housing scopes differ. The
   short-employment concept also illustrates the risk of extending a statement
   about quotas into a broader statement about permits. Primary-section checks
   prevent cross-section citations, not every incorrect inference within a section.
3. **Duplicate suggestions are noisy.** 70B suggested residence with employment
   and residence without employment as a possible pair. 8B suggested family
   reunification and a foreign-national identity document because their labels
   share EU/EFTA wording. These must not be merged merely on lexical similarity.
4. **Coverage is uneven.** The biometric page has markedly different topic
   selection. A six-candidate-per-chunk cap and model choice can affect which
   topics survive. A missing-topic benchmark is needed to measure recall.
5. **Rejection rate is not accuracy.** 8B violated the single-primary-section
   contract more often in this fixture. Some multi-section proposals may describe
   useful topics, but they do not meet the current extraction contract. More
   rejections can reduce retained coverage without proving worse factual accuracy.
6. **Same-model review is not independent validation.** Zero semantic rejections
   in 70B is not evidence of zero errors. Confidence values are uncalibrated, and
   no human-labelled precision, recall or model-quality ranking is available.

## Failure history and recovery lessons

| Run | Observation | Outcome / lesson |
|---|---|---|
| `70b-v3-01` | HTTP 504 during page 3, chunk 2 generation | Before response checkpoints; completed model work was not recoverable from the log. |
| `70b-v3-02` | HTTP 504 on page 4, chunk 1; Retry-After exceeded the then-30s wait cap | Ten responses were checkpointed. The original retry wait cap was too short for this provider response. |
| `70b-v3-03` | Reused ten responses, saved four more; HTTP 504 on page 4, chunk 3 | Checkpointing worked; fourteen completed responses remained reusable. |
| `70b-v3-04` | `finish_reason=length` on page 4, chunk 3 | The input was only 190 characters: a generic links heading and two link labels. Truncated content was rejected. |
| `70b-v3-05` | Reused fourteen responses and made eight new calls | Link-only chunk skipped; all six pages completed. |
| `8b-v3-01` | Final-page review returned HTTP 504 with Retry-After 120s; retry then returned `length` | The wait and heartbeat worked. The truncated review reported 2189 input tokens, 4096 output tokens and 7119 content characters for four verdicts. Nineteen successful responses survived. |
| `8b-v3-02` | Reused nineteen responses and made three new calls | Full pending review succeeded normally; no live smaller-batch fallback was needed. |

Implemented recovery safeguards include generation/review checkpoints, bounded
transient retries, a separate provider-wait cap with progress, generic link-only
chunk skipping, and safe truncation metadata. A truncated multi-proposal review
can now split into smaller checkpointed batches within the same request budgets.
That last mechanism passed simulated regression tests but was **not exercised
by either successful live comparison run**. No partial completion is accepted.

Unchanged chunks retain their original prompt numbering and checkpoint identity.
Structural validation is rerun over reused responses; matching model-review
verdicts can themselves be reused from checkpoints. Tests
also cover interrupted child batches, singleton truncation, invalid verdicts,
and budget exhaustion. These tests establish implementation behavior, not model
accuracy or immunity to future provider outages.

## Earlier v2 exploration

The exploratory `8b-v2-01`, `8b-v2-02` and `8b-v2-03` runs each retained 71
candidates with no rejections. Their candidate outputs were identical, while
reported durations were 311.383s, 9.026s and 7.257s. Upstream caching was suspected
but not established; these runs do not demonstrate independent sampling or
reliable cold/warm performance. `70b-v2-01` retained 70 candidates with one
rejection in 277.405s.

Earlier analysis exposed numeric scopes incorrectly rejected as breadcrumbs,
embedded News content, abbreviation splitting, cross-section condition leakage
and unsupported expansions of cited text. V3 and subsequent fixes addressed
input structure, scoping, diagnostics and recovery. Its lower candidate counts
cannot be interpreted as a quality gain by themselves: selection and review
changed between versions, and some semantic omissions still remain.

## Recommended next evaluation

1. Populate both `review.csv` worksheets for 10-15 matched concepts first,
   prioritizing close relatives, permit/quota exemptions, EU/EFTA conditions and
   family-reunification scopes. Mark support as yes/no/uncertain; record missing
   conditions, exceptions and classification errors in notes.
2. Define 5-10 expected concepts per page with source evidence independently of
   either model's output. Use this to measure missing topics, not just retained
   candidate counts. Distinguish a proposed-but-rejected topic from one never
   proposed and from a condition included in another candidate.
3. Turn the known semantic failures into labelled regression examples. Evaluate
   explicit condition/exception checks and, if useful, an independent reviewer;
   do not treat a change of reviewer as proof that the problem is solved.
4. Refine duplicate review to account for topic, applicability and contrasts such
   as with/without employment. Keep automatic merging conservative.
5. Only then compare independent fresh runs for quality, full elapsed time and
   complete attempt/usage accounting. Use `-FreshInference` for an independent
   experiment and omit it when resuming. Do not compare a resumed invocation's
   duration directly with a fresh invocation.

See the [experiment workflow and recovery options](../../scripts/test/zhch/README.md)
and the [knowledge-builder setup](../../apps/knowledge-builder/README.md).
