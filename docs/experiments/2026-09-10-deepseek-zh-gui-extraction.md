# DeepSeek Zurich GUI extraction: partial runs and bounded corrections

Latest live job `56850144d9a444129496dbfed6e9d45e` used four scope-bounded
packets without the earlier concept-count or enum errors. Four drafts were
retained from its first packet, but two later repairs exceeded the input cap.
An explicit repair-input allowance is now verified offline. See the latest
follow-up and current checkpoint below; earlier runs remain preserved.

GUI job `008afd0e4bb14328867ae790e945a880` retained zero candidates from the
saved `zh-eu-efta` page. Its first extraction response ended with
`finish_reason=length` at the configured 4096-token output limit. The adapter
rejected the incomplete response; no semantic review or repair ran. The report
took 29.742 seconds and records one network attempt, zero usable completions,
zero provider retries and no checkpoint hits. Reported zero usage excludes the
failed completion; it does not establish zero consumption or billing.

The progress line `requests=0` counts completed responses. It does not mean no
request was sent: `execution.network_attempts=1` and
`quality_metrics.request_attempt_count=1` record the attempt. The final
`Concept extraction completed successfully` message means the CLI wrote its
report, not that the page produced a usable draft. The GUI's **Needs attention**
therefore identifies an actual extraction failure in this run.

The saved page has 105 blocks and 20333 normalized characters. Planning packs
69 eligible blocks into three bundles of 26, 24 and 19 blocks (6005, 5989 and
3993 evidence characters); 36 navigation/heading blocks are excluded by policy.
The first bundle's 26 blocks became `provider_failure`; the remaining 43 were
`not_processed_provider_failure`. All remain unresolved. No partial response
was checkpointed or retained as a candidate.

## Initial adjustment and offline verification

`config/semantic-models.toml` now sets `generation.max_output_tokens=8192`.
This shared setting affects extraction and review for any selected semantic
profile. DeepSeek remains selected. Source packet size, concept limit, prompts,
validation, one-repair limit, 180-second timeout and 12-call page ceiling are
unchanged. GUI provider retries remain disabled. New GUI jobs read the current
configuration without restarting the server; old jobs retain their frozen
4096-token setting.

Doubling the allowance was prepared as a controlled experiment. The truncated
response did not reveal how much output was needed; the later result below
establishes no truncation in one run, not reliable extraction on this page.
Complete output must still fit the separate 25600-character source/proposal
review-input allowance and pass all existing checks. A larger limit permits
more output and potentially longer and more costly calls, even though the
request ceiling is unchanged.

Smaller source packets were considered offline. A 4800-character packet limit
plans four bundles, reserving eight initial extraction/review calls and leaving
four repair calls within the 12-call ceiling. At 3200, six bundles consume all
12 initial calls, leaving no repair capacity. At 2400, the budget omits 19
eligible blocks. Reducing this limit also reduces the review-input allowance.
The prepared output-only change preserves the original three-bundle plan.

Verification artifacts are in `.local/admin/zh-output-008afd0e-20260910/`:
the GUI-resolved configuration, `plan.json`, `progress.log`, `audit.json` and
the offline audit script. Provider construction was blocked. The plan sent
zero model requests and retained the same 12-call ceiling, source inventory,
source hashes and effective prompts. The only effective configuration change
from the failed job is the output limit. All six Control API configuration
tests and 13 builder profile tests passed. No live retry was performed during
that offline preparation.

| Preserved artifact | SHA-256 |
| --- | --- |
| Failed report | `3fae78064f63124a9d0a6313375914cbf574bc5580c8499e69b0c9e6af9bf1f1` |
| Original source | `b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4` |
| Original configuration | `4756246277094b08db46839ce7538c8a53e1d0eb4341584cdbf747a63ca5d6cf` |

All original job files retained their hashes during verification.

## Live follow-up at 8192 output tokens

Preview `f8161975084d4498a1835066a4eb0630` froze the larger output allowance,
same source hash and 12-request ceiling with zero requests sent. The user then
ran GUI extraction `e4f1f67a1f8a423baa40999cbc6f339e`. It took 271.607 seconds,
made seven model calls (three initial extractions, three repairs and one review),
and retained four candidates. No response was truncated; there were no provider
retries or checkpoint hits. Reported usage was 58646 input and 34561 output
tokens. All candidates have empty questions, which the schema permits.

| Bundle | Initial extraction | Repair and final outcome |
| --- | --- | --- |
| 1, 26 blocks | Seven concepts exceeded the six-concept schema limit. | Six structurally valid concepts with 17 claims; review input was 27011 characters, exceeding the 25600-character allowance. No review or retained draft. |
| 2, 24 blocks | A concept used unsupported concept type `FACT`. | Five structurally valid concepts with 10 claims; review input was 28634 characters, exceeding the same allowance. No review or retained draft. |
| 3, 19 blocks | One contact concept combined evidence from separate ownership groups. | Repair repeated that grouping. The invalid contact concept was rejected; the remaining four were reviewed and retained. |

The review-input sizes were reconstructed offline from the saved inventory and
repaired proposals using the pipeline's source payload and rendered descriptions.
Compact JSON alone would still exceed the limit (25864 and 27687 characters).
Increasing the output cap exposed this independent input-allowance constraint;
raising output again would not address it. No input limit or validator was
changed during this diagnosis, and no new model calls were made.

The report marks 50 source blocks `invalid_response`, seven `covered`, seven
`not_substantive`, five `missing` and 36 `excluded_policy`. Its 62 unresolved
blocks include the model's seven not-substantive assessments, which still need
human disposition. Retention is therefore not evidence of full page coverage.
The missing contact material includes address/opening hours, telephone details
and the contact-form instruction, which the rejected proposal grouped across
three ownership scopes. Those sections are related to the same office, but the
proposal does not satisfy the current single-scope concept contract.

Assistant inspection of the four retained drafts found:

- **Liechtenstein und Freizügigkeit:** all eight full statements match the saved
  substantive paragraphs. Nationality OR fixed-residence applicability survives
  in statement and population scope, but the corresponding claim has no
  condition tree and the reviewer calls it unconditional. Whether that
  applicability also requires explicit branches merits review; this is less
  clear-cut than the German Residence draft's missing work qualifier.
- **Weiterführende Informationen und Downloads:** accurately lists document
  titles and file metadata. It is a reference list, not extraction of the linked
  documents' substantive contents, and the candidate omits their target URLs.
- **Das könnte Sie auch interessieren:** copies related-page teaser keywords
  from `section-0096`. The original HTML explicitly wraps these links in
  `mdl-related-content` and `mdl-content_nav`. Normalization classified it as a
  list, and the reviewer marked it covered. Retaining it as substantive knowledge
  conflicts with the navigation exclusion policy. Recommend **reject**.
- **Zuständigkeit:** the source supports the Migrationsamt's responsibility.
  The wording `Für dieses Thema zuständig` should name the page's topic so that
  the claim can stand alone; this authority fact itself is supported.

These are saved-source assessments, not current legal verification. The report
remains immutable at `.local/admin/jobs/e4f1f67a1f8a423baa40999cbc6f339e/result.json`,
SHA-256 `e178ee6cac5e67a78332dadb985809820ad8211ce00df46dee436329af8fbc69`.
Its frozen configuration SHA-256 is
`0708f09107713c9d1b82edcd82bf82ed700d0212f3d00d84ebb14eae57889ec6`.
The source hash still matches the original run above.

## Review-input and navigation corrections

`extraction.max_review_input_characters` now independently bounds the complete
serialized review user payload, including evidence, proposals, rendered
descriptions and review-validation feedback. Its configured/default value is
64000 characters; older TOML files that omit it use the same default. The CLI
passes the setting to the extraction engine and records it in effective config.
Non-integer and non-positive values are rejected. Overflow errors show actual
and configured lengths before a review call. Source packet size and the
existing extraction/repair feedback allowance are unchanged; proposals are
neither truncated nor edited to fit. Prompts and acceptance checks are unchanged.

The normalizer now marks exact Zurich `mdl-related-content`, `mdl-content_nav`
and `mdl-content_nav__list` components as navigation while retaining their
blocks for audit. On the saved HTML, only `section-0096` changes classification
from list to navigation. All 105 block IDs, scopes, headings, text and evidence
remain identical. The next plan has 68 eligible and 37 excluded blocks. Contacts,
downloads and substantive linked lists remain eligible; a broad link-density
filter would lose useful material. Normalization version is now
`swisstip.logical-blocks/v3`, changing normalized source and checkpoint identity
while the original HTML SHA-256 stays unchanged.

`packages/ingestion/tests/fixtures/deepseek_v4_zh_e4f1f67a.json` preserves exact
source evidence and initial/repaired completions for the first two bundles,
with report/source provenance hashes. At the old explicit 25600-character cap,
offline replay still sends two extraction calls and zero reviews per bundle.
At 64000, each sends two extraction calls and one complete review. The supplied
review responses are synthetic uncertain controls, not new model output, so
they retain zero candidates. Every proposal and source block survives intact
into the review request. Both paths stay within the existing request ceiling.

Other tests cover exact size boundaries, rendered descriptions and diagnostic
feedback counting toward the limit, the unchanged extraction feedback cap,
strict/optional configuration, CLI forwarding and navigation identity/contacts.
All 131 ingestion tests, 175 builder tests and seven Control API configuration
tests passed (313 total). One factory test's old fixed 4096-token expectation
was replaced with an explicit custom-generation fixture, so it now verifies
forwarding without coupling to the repository's changing default.

Offline plan, replay reports, exact review requests, verification script and
audit are in `.local/admin/zh-review-input-e4f1f67a-20260910/`. The plan blocks
provider construction and sends zero model requests. Original job files,
including every saved checkpoint, retain their hashes. The new GUI preview also
loads the corrected code and freezes 8192 output tokens, the 64000-character
review cap, DeepSeek V4 Pro and zero retries.

## Assistant source review and pending semantics

The assistant review recommends keeping **Liechtenstein und Freizügigkeit**
as a faithful draft with the applicability-modeling question above, and keeping
the narrow **Zuständigkeit** responsibility assertion with explicit topic
wording. It recommends rejecting **Weiterführende Informationen und Downloads**
as a substantive concept (retain its document references separately) and
**Das könnte Sie auch interessieren** as navigation.

The database review history inspected during this step shows Alex accepting
Liechtenstein, downloads and related links, and rejecting Zuständigkeit. These
human decisions were preserved; the assistant's differing recommendations are
recorded here, not substituted into Alex's review history.

Inspection of repaired proposals that previously could not reach review found
two concrete issues for the next semantic assessment:

- Bundle 1, `ausweis-ausstellung`: the full statement preserves the source's
  `Wenn` prerequisite for issuing a permit, but the repair removes its explicit
  conditions and root. The initial proposal had a condition.
- Bundle 2, `unterlagen-familiennachzug`: one AND group combines documents with
  different applicability branches. In particular, proof of prior common
  residence loses the source's `falls ... bestand` prerequisite. Similar
  branching applies to non-employed people and supported relatives. The
  submission recipient `Familienangehörige` is not supported by that relation.

The input allowance correction lets a reviewer assess these proposals; it does
not fix or approve their meaning. A further live run must be inspected for
false approvals, omissions and source coverage. The German Residence work
qualifier issue also remains pending.

## Latest live follow-up: review reached, validation still failing

The user ran job `ed64c431b32f42129035a6bde9ff1330` after the corrected GUI
preview. It used 8192 output tokens, the 64000-character review cap, normalization
v3, the same source and the 12-call ceiling. It took 363.587 seconds and made
eight calls: three initial extractions, two repair extractions and three reviews.
There was no truncation, provider retry, checkpoint reuse or review-input overflow.
Related-link navigation remained excluded. Reported usage was 68597 input and
38043 output tokens. Two candidates were retained, both from the first bundle.

- Bundle 1 again exceeded the concept-array bound initially. Repair produced four
  proposals; two failed exact-quotation/ownership validation. The other two were
  reviewed and retained as **Aufenthalt für EU/EFTA-Staatsangehörige** and
  **Personenfreizügigkeit**.
- Bundle 2's reviewer called `finanzielle-mittel` unconditional while approving
  added conditions. Its prose also disputed that logic. The validator rejected
  this contradictory review; it did not infer a corrected verdict from prose.
  The next repair payload measured 25775 characters against the 25600-character
  source/feedback allowance, so no repair request was sent for this bundle.
- Bundle 3 repeated cross-ownership contact grouping after repair. Review of
  the valid subset then assigned `partial` coverage to seven contact blocks
  with no concept references. None of the valid proposals cites those blocks.
  Adding references would invent represented coverage; changing `partial` to
  `missing` would change the review judgment. This review remains invalid.

The inventory has 37 policy exclusions, three covered blocks, 14 model-assessed
not-substantive blocks, nine missing blocks and 42 invalid-response blocks.
The report's unresolved count is 65. Two retained introductory concepts do not
establish successful extraction of the page's detailed rules and procedures.

Assistant inspection found the introductory **Aufenthalt für
EU/EFTA-Staatsangehörige** sentence faithful to its bounded evidence. It is not
a substitute for the separate registration and permit requirements elsewhere
on the page. **Personenfreizügigkeit** preserves its three full sentences, but
`drittstaaten-begrenzt` leaves the restriction to specialized AND qualified
workers only in prose: conditions/groups/root are empty and population scope
only identifies third-country nationals. Recommend **needs changes** to preserve
that necessary restriction structurally without implying those attributes alone
guarantee permission. Empty questions are allowed and are not rejection grounds.

Live report SHA-256:
`e029162f5b4efb370c10231e897994bb9e6bfc7a5763798f640ff22d5ee29d5d`.
Frozen configuration SHA-256:
`60109f9fa691c17fff738fa90f8e4d0b1878d3c99d57692bef5c68ede7cdc2e8`.
The original source hash remains unchanged.

## Prepared correction: lossless JSON whitespace compaction

When serialized extraction/repair input exceeds its existing allowance, the
pipeline now retries serialization with compact separators. Every JSON value
is unchanged. For the saved bundle 2 repair this saves 1020 characters,
reducing 25775 to 24755 and fitting the same 25600-character cap. The raw invalid
review was already excluded from feedback; no additional source, proposal or
diagnostic is removed. No limit, prompt, request ceiling or verdict changed.
Normal-sized request bytes remain unchanged. A still-oversized compact payload
is rejected with its original/compact sizes and limit before any call.

`packages/ingestion/tests/fixtures/deepseek_v4_zh_ed64c431.json` preserves the
exact extraction completion, invalid review record, source evidence and hashes.
Offline replay now reaches the previously blocked repair and its review within
four calls. The replayed repair deliberately repeats the saved extraction;
it is a synthetic control, not a live correction. Repeating the actual invalid
review still retains zero candidates, and the next reviewer receives the
original validation diagnostic. Tests compare all source/feedback values and
exact sizes, reject a larger control payload without sending a partial repair,
and preserve serialization for requests that already fit.

All 134 ingestion tests and 12 builder structured-workflow tests passed.
The offline audit, replay report, repair request, progress and unchanged dry plan
are under `.local/admin/zh-compact-repair-ed64c431-20260910/`. The plan still
reserves at most 12 calls and sends zero; provider construction is blocked.
All original live job files and checkpoints retain their hashes. This removes
the observed whitespace overhead, not every possible repair-size failure or
the model's remaining extraction and review errors. No live rerun was performed.

## Previous GUI resume checkpoint after ed64c431

Review the two candidates in job `ed64c431b32f42129035a6bde9ff1330`. In
**Personenfreizügigkeit**, record **needs changes** with this note:
"Preserve the restriction to specialized AND qualified workers in structured
fields. Do not imply that those attributes alone guarantee permission."
The other draft is acceptable as a narrow source summary. No assistant review
decision has been written to the GUI. The whitespace correction is ready for
a subsequent fresh preview and user-controlled extraction step.

The earlier GUI decisions remain separate: Alex accepted the English Residence
draft from job `87ca1a63d46f49c7afa6343714fb4e8d`. The latest German decision for
job `7ed3c77f27fe4b5381957929a8093d11` is `needs_changes`, following an earlier
acceptance. Its work condition contains only `arbeitet`, dropping the source
qualification `während seines Aufenthaltes in der Schweiz`. The complete
statement retains that qualification, but the structured condition needs it
too. The review note records that correction; it does not edit or publish the
draft. No extraction/prompt correction for that semantic issue is included here.

## Live follow-up: 34170bf4 repeated schema failures

The user ran extraction from fresh preview `5b6abcc3f4c14b9abeae1b5190509f0d`.
Job `34170bf43ddf430fbf1396bd17f8d757` took 282.586 seconds and made seven
calls: three initial extractions, three repair extractions and one review. It
used the same source, normalization v3, 8192 output-token limit, 64000-character
review limit and 12-call ceiling. It reported 58154 input and 35772 output tokens,
with no truncation, provider retry or checkpoint hit. No payload required JSON
whitespace compaction, so this run did not exercise that previous correction.

- Bundle 1 returned seven concepts twice against the configured maximum of six.
  The labels stayed the same, though other response fields changed. Its packet
  contained eight ownership scopes, seven of which held substantive topics.
  Six concepts cannot represent all seven while obeying the cross-ownership rule.
- Bundle 2 returned five concepts twice, including Brexit with the invalid
  `concept_type` value `FACT`. The allowed types are `ENTITY`, `PROCESS`, `RULE`,
  `SERVICE`, `DOCUMENT`, and `OTHER`; claim kind `fact` is a separate field.
  The error only said `unknown value`. The offending value began around raw
  character 19714, beyond the 6000-character excerpt supplied to repair.
- Bundle 3 initially combined unrelated contact scopes in two proposals. Repair
  still left one such proposal invalid; the valid subset reached review and four
  candidates were retained. Cross-ownership rejection remained enforced.

The report has 37 policy exclusions, 50 invalid-response blocks, seven covered
blocks, four model-assessed not-substantive blocks and seven missing blocks.
Its unresolved count is 61. This remains a partial extraction.

| Retained draft | Source inspection |
| --- | --- |
| Liechtenstein und Freizügigkeit (`6d4217a4`) | Eight statements match sections 0068-0071. Nationality OR fixed-residence scope remains in the prose and population field. Suitable for review as a bounded source summary. |
| Dokumente und Downloads (`816cfc8e`) | Only title, language, page count and size of the Liechtenstein PDF. A document reference, not extracted requirements. |
| Weitere Dokumente (`046b581c`) | Three PDF listings, including the same Liechtenstein document. Duplicates part of the preceding draft. |
| Zuständigkeit (`e78988e4`) | Supports only the statement that the Migrationsamt is responsible for this topic. No actionable contact details. |

The schema permits document concepts, so PDF metadata is not a schema failure.
For substantive-rule extraction, those references do not establish coverage of
the linked PDFs or the page's detailed requirements. The actual address, office
hours, telephone, telephone hours and contact-form/no-email statement remain
missing (sections 0085, 0086, 0088, 0090 and 0093). Related navigation at 0096
remains excluded. No assistant review decision was posted.

Live report SHA-256:
`e5850f72a62c239a7a396cbcd102504cc766bda2067c78b870c5085ab4a27b73`.
Frozen configuration SHA-256:
`60109f9fa691c17fff738fa90f8e4d0b1878d3c99d57692bef5c68ede7cdc2e8`.

## Prepared correction: scope capacity and specific repair diagnostics

The planner now caps ownership scopes per packet at `max_concepts_per_chunk`,
alongside the existing character limit. Whole ownership groups and source
evidence remain unchanged. On this snapshot, every eligible block fits:

| Packet | Scopes | Blocks | Evidence characters |
| --- | ---: | ---: | ---: |
| 1 | 6 | 22 | 5015 |
| 2 | 6 | 24 | 5765 |
| 3 | 6 | 15 | 3780 |
| 4 | 3 | 7 | 852 |

All 68 eligible blocks are present exactly once; 37 remain policy exclusions.
Four initial extraction/review pairs reserve eight calls, leaving four calls
for repairs under the unchanged 12-call ceiling. In larger inputs, extra packets
may reach the budget; those blocks remain explicitly marked not processed.
The conservative saturation rule remains: exactly six proposed concepts can
still trigger repair and human review even when all six scopes appear covered.
Scope count does not guarantee that a topic needs only one concept.

Schema errors now include received array count/minimum/maximum, or the invalid
enum value and bounded allowed values. Saved bundle 1 now reports
`array bounds exceeded (received=7, min=0, max=6)`. Bundle 2's repair receives
`received="FACT"` plus every allowed concept type despite the unchanged truncated
raw excerpt. Replaying both actual invalid bundle 2 responses still retains zero
candidates. No value is mapped, discarded or approved to bypass validation.
The prompts, schema, concept limit, generation limits and request ceiling remain
unchanged; changed packet contents and repair feedback alter checkpoint keys.

All 143 ingestion tests and 175 builder tests passed. Tests cover whole-group
packing, explicit budget omissions, reserved initial calls, strict enum/array
rejection, bounded diagnostics and a late invalid field beyond the raw excerpt.
The historical review-size replay pins its original packet boundaries so it
continues testing the saved request without altering evidence or concept limits.
An independent source audit and CLI dry run are saved under
`.local/admin/zh-scope-packets-34170bf4-20260910/`. Provider construction was
blocked; zero model requests were sent. Original job files and checkpoints retain
their hashes. Offline verification establishes the mechanics, not model quality.

## Previous GUI resume checkpoint after 34170bf4

Fresh preview `5c36eab29d3c4459b814e3051f038557` uses DeepSeek V4 Pro and the
new four-packet plan. Open this preview in the GUI to inspect the unchanged
12-call ceiling before the next user-controlled extraction. The corrections
have not yet had a live extraction. The latest job's four drafts remain available
for human review; prior acceptance and needs-changes decisions were preserved.

## Live follow-up: 56850144 repair-input limits and draft review

Job `56850144d9a444129496dbfed6e9d45e` used the new four-packet plan on the
same Zurich source with DeepSeek V4 Pro. It made eight calls in 289.715 seconds:
four initial extractions, two repair extractions and two reviews. Reported usage
was 59688 input and 33647 output tokens. There was no truncation, provider retry
or checkpoint hit. No concept-array or concept-type error appeared in this run;
that does not establish reliable schema compliance in future runs.

- Packet 1's registration proposal repeated a non-verbatim condition excerpt
  after repair. The valid subset reached review and retained four drafts.
- Packet 2's L-permit and self-employment proposals failed exact-excerpt checks.
  Its repair input was 26731 characters, or 25642 after lossless whitespace
  compaction: 42 above the 25600-character cap. No repair call was sent.
- Packet 3 produced six proposals and a valid model review. The model reported
  `saturated=false`, but reaching the six-concept limit triggers the local
  saturation safeguard. Repair input measured 48219 characters, or 46345
  compacted. No repair call was sent. The failed final revision cleared the
  earlier proposals and review, so these six were not retained. This conservative
  final-revision policy was not changed to recover more drafts.
- Packet 4 combined telephone, contact-form and authority evidence across
  unrelated ownership scopes. Both initial and repaired proposals were rejected;
  no valid proposal remained for review.

Inventory statuses are 37 policy exclusions, 46 invalid-response blocks, seven
covered blocks, eight model-assessed not-substantive blocks and seven missing
blocks. The unresolved count remains 61, as in the preceding run. Retained
content changed, but the report does not show improved verified coverage.

## Review notes for the four retained drafts

These recommendations compare structured claims with this saved source. They
do not independently establish current legal requirements or publish knowledge.

| Draft | Suggested decision | Review note |
| --- | --- | --- |
| Aufenthalt für EU/EFTA-Staatsangehörige (`49ac92fe`) | Accept draft narrowly | Source-faithful introductory summary; not a complete statement of residence requirements. |
| Personenfreizügigkeit (`86c88499`) | Needs changes | Preserve the restriction to specialized AND qualified workers in structured fields. Do not imply that those attributes alone guarantee permission. |
| Zulassung zur unselbständigen Erwerbstätigkeit (`47d009a7`) | Needs changes | Represent the permitted job-search duration without requiring a stay of exactly three months. The source does not support Aufenthalt eq 3 Monate as an eligibility prerequisite. |
| Meldeverfahren (90 Tage) (`c2a41a01`) | Needs changes | The cited passive sentence does not identify who must submit the notification. Leave the reporting actor unspecified unless supported by evidence; retain the EU/EFTA population and Amt für Wirtschaft recipient. |

The employment draft otherwise preserves the longer-than-90-days work condition
and the 14-day personal registration statement. The reporting draft correctly
preserves at most 90 working days per calendar year. Its unsupported actor is a
separate issue. The FZA candidate repeats the previously reviewed omission with
the same candidate ID. Review decisions remain tied to their saved job/result;
earlier human decisions were not overwritten or copied to this run.

The rejected condition quotations illustrate the exact-excerpt requirement:
registration reconstructs `Umzug in einen anderen Kanton` from an elliptical
source clause; the L-permit proposal reconstructs `Arbeitsvertrag von weniger
als einem Jahr` from a shared noun phrase; self-employment conditions drop
parenthetical examples or change a final comma to a period. These are exactness
failures, not proof that every paraphrase is factually false. The pipeline keeps
the quotation check strict and does not silently substitute corrected excerpts.

## Prepared correction: explicit repair-input allowance

`extraction.max_repair_input_characters` now optionally bounds the complete
serialized repair user payload. The repository sets 64000 characters. Omitted
values retain the legacy `chunk_content_characters * 4` allowance, so old frozen
jobs keep their previous setting. The initial extraction allowance, 6400-character
source packets, 64000-character review limit, prompts, schema, output tokens,
one-repair limit and 12-call ceiling remain unchanged. An oversized initial
source request stops locally rather than using the larger repair allowance.

Both saved repair requests fit at their original serialization sizes of 26731
and 48219 characters. No source value, proposal, review judgment or diagnostic
is removed or shortened. Packet 2's compact payload contains 8947 source
characters and 16664 feedback characters plus the wrapper. Packet 3 contains
6009 source characters and 40305 feedback characters plus the wrapper. Its
feedback includes 11015 characters of proposals and 29209 of parsed review,
covering 18 claim assessments across six concepts. Raw review text and duplicate
proposal copies were already absent; additional whitespace removal cannot
resolve the 20745-character excess. The explicit cap addresses that observed
requirement instead of weakening review feedback.

The larger allowance can increase repair input tokens and permit calls that
previously stopped locally, within the same total ceiling. It does not correct
the model's quotation, ownership or semantic errors. The final-revision policy
and conservative saturation flag remain enforced.

The saved fixture `deepseek_v4_zh_56850144.json` preserves both exact source
packets, initial completions, packet 3's review, initial history and hashes.
Offline replay reproduces both old-limit failures and reaches both repairs with
the explicit 64000 limit. Post-repair responses deliberately repeat the initial
extraction and use uncertain review controls, retaining zero candidates. These
controls establish input handling and strict validation, not a successful live
correction. Boundary checks cover the exact compact size and one character below;
an oversized initial source still sends zero calls even with the larger repair
cap. GUI configuration tests preserve both omitted and explicit cap snapshots.
All 148 ingestion tests, 177 builder tests and eight control-API configuration
tests passed (333 total).

The frozen/current GUI-config dry-plan comparison is recorded under
`.local/admin/zh-repair-limit-56850144-20260910/`. Both plans reserve 12 calls
and send zero, with identical prompts, source inventory and four packets. All 68
eligible blocks remain planned, with 37 exclusions. Original live files and
checkpoints retain their hashes. No additional live extraction was performed.

Live report SHA-256:
`bbd516ad2a25548016722ed7b014cc144813920d40cbde7d6e8a9316a906d211`.
Frozen configuration SHA-256:
`60109f9fa691c17fff738fa90f8e4d0b1878d3c99d57692bef5c68ede7cdc2e8`.

## Current GUI resume checkpoint

In **Builds & review**, select **Concept extraction** from 10 September at
09:22 Zurich time (job `56850144d9a444129496dbfed6e9d45e`, **needs attention**).
Review its four candidates using the notes above. The introductory residence
draft is acceptable narrowly; the other three need changes. The assistant has
not submitted any review decision. New extraction jobs will use the explicit
64000-character repair allowance; this setting does not retroactively repair
the saved candidates or edit earlier reviews.
