# DeepSeek concept-ownership extraction experiment

This follows the completed human review of Zurich GUI job
`b5ec257972d849da9ddceb0cdb975b2c`: six accepted drafts and eight needs-changes
decisions. The [calendar-date validation record](2026-09-10-deepseek-calendar-dates.md)
preserves those findings. This experiment addresses the separate contact-content
failure and keeps the eight semantic corrections visible for the next review.

## Observed failure

Packet 4's initial and repaired proposals are equal as parsed JSON. They place four
claims in one concept, anchored to the telephone section. Each claim cites one
ownership scope, but the entire concept spans three. The existing concept-level
validator rejects both revisions before semantic review:
`evidence crosses unrelated source ownership groups`.

| Ownership scope | Source sections | Assertions absent from retained candidates |
| --- | --- | --- |
| `scope-0047` | 0088, 0090 | Telephone number and telephone hours, including the midday gap. |
| `scope-0048` | 0092, 0093 | Contact form for electronic inquiries and absence of an email address. |
| `scope-0050` | 0098 | The Migrationsamt is responsible for the page's topic. |

The accepted contact draft covers the address and onsite hours in scope 0046.
It does not establish telephone availability. The failed contact claims also
assign an EU/EFTA population from page context; structural separation alone
does not validate that population or the other claim meanings.

## Prepared correction

Only the bundled V4 extraction system prompt changes. It now states that the
entire concept must use evidence from its primary section's supplied `scope_id`,
across claims, scope fields, conditions, groups and exceptions. Different source
ownership scopes require separate concepts even when the authority is the same.
Each concept needs a cited primary section within its own group. Source ownership
metadata remains distinct from the semantic fields inside `claim.scope`.

Repair guidance explicitly requires separating complete claims by source ownership.
It preserves evidence IDs, valid conditions, and appropriately scoped questions
and limitations. If an individual claim crosses groups, its support must be
reassessed; duplicating the mixed claim, cutting its condition tree or deleting
valid conditions is not a correction.

No output is automatically split or rewritten. The claim/review contracts,
validators, review prompt, worked example, source normalization and request limits
stay unchanged. This is a prompt experiment, not evidence that a model will obey
the clarified instruction or resolve the eight earlier semantic findings.

| Effective prompt | SHA-256 |
| --- | --- |
| Previous extraction | `b8683871a251a5d14498d95db4758fdf5fed875bec48072061aa752ba51d56e7` |
| Prepared extraction | `caadc95fed4a5736b179e9f9b7a480bd78fbc052b2d718f53a9ea6381c8f84de` |
| Unchanged review | `d2478d3ac3c84104941e47293fe315c2cf350f98bf0e81345829ac9aef3f698b` |

The changed extraction prompt yields a different extraction checkpoint key.
Earlier source/report/checkpoint files and human decisions remain bound to their
saved jobs. Reviews are not transferred to a new result or automatically included
in new model requests.

## Offline verification

The fixture `deepseek_v4_zh_b5ec2579_contacts.json` preserves all seven packet
blocks, exact evidence, both raw completions, original rejection records and
source/report/configuration/checkpoint provenance. The two raw completion hashes
also match: `3420114db7d32d3e05ff7b102b2aaed8c56df0b74c4b5f149eea822e56d8cfcd`.

Saved-output replay still rejects the initial proposal and repeated repair,
making two synthetic extraction calls and no semantic-review call. A separately
identified, hand-authored three-concept repair preserves every original claim and
evidence reference and reaches review in three synthetic calls. Uncertain and
unsupported population assessments each retain zero candidates despite the other
synthetic assessments being supported. This verifies that structural admission
does not bypass a failed semantic field; it does not measure prompt effectiveness.

Six adversarial variants retain the existing rejections for cross-scope claim,
scope, condition, group or exception evidence and for an uncited primary section.
The four new replay tests pass, along with the existing ingestion tests: 161
ingestion and 177 builder tests passed in total (338). Prompt snapshots pin the
new extraction bytes and the unchanged review bytes.

The provider-blocked local dry run and fresh GUI preview preserve the exact source
and inventory, four whole-ownership packets, 68 eligible blocks and 37 policy
exclusions. Packet character counts remain 5015, 5765, 3780 and 852. The resolved
configuration is unchanged from the live baseline: 8192 output tokens, 64000
review/repair-input characters, 180-second timeout, no automatic provider retries,
and a 12-call page/run plan ceiling within the configured run limit of 30.
Planning sends zero model requests. No model checkpoints are created by the preview.

The repeatable local audit under
`.local/admin/zh-concept-ownership-b5ec2579-20260910/` contains `plan-verify.py`,
the dry and GUI plans, the baseline snapshot and `plan-audit.json`. Original live
and earlier preview files retain their hashes, and all 14 human reviews are
unchanged. No live inference of this prompt change had been performed at preparation.

## Prepared GUI checkpoint and predeclared live success criteria

Fresh preview `4284a491de6f45a2b3eae900725e3047` is the **Extraction plan** created
at **13:50 Zurich time** on 10 September. Find it under **Builds & review**.
For the next user-controlled run, open **Saved pages**, select only
**Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich** (`zh-eu-efta`), choose
**DeepSeek V4 Pro**, then use **Run extraction > Confirm extraction**.

Inspect whether packet 4 produces ownership-separated concepts covering all five
assertions above and reaches semantic review without repeated cross-ownership
rejection. Check telephone hours independently from onsite hours, the conditional
electronic-contact instruction, and unsupported population or actor/recipient
assignments. A higher retained count or structural success is not sufficient.
Recheck the eight prior semantic findings and the previously accepted source
bounds on the new report. Changed extraction output can introduce regressions
elsewhere even though the source and limits are unchanged.

## Live follow-up: 891e31a3 did not meet the ownership target

The user ran job `891e31a32d0f4f09b16a6ab062eaae00`, created at **20:37 Zurich
time** on 10 September. Extraction took 355.874 seconds and made 11 calls: four
initial extractions, three repairs and four reviews. It reported 101376 input
and 55624 output tokens, with no output-token truncation, automatic retry or
checkpoint hit.
The effective extraction prompt matches `caadc95f...`; the review prompt, frozen
configuration, raw/normalized source, contracts and packet boundaries match the
prepared experiment.

Only seven candidates were retained, compared with fourteen in the baseline.
The targeted contact concept still crossed ownership groups and was rejected.
This run therefore does not demonstrate successful contact repair. The loss of
previously accepted source content is a coverage regression; one stochastic run
does not establish that the prompt change alone caused every other failure.

| Packet | Observed result |
| --- | --- |
| 1 | The first review again described entry documents as unconditional while approving added conditions. Local review validation rejected the contradiction. Repair and review retained five drafts. |
| 2 | Both revisions repeat five exact-quotation failures across B, self-employment and non-employment proposals. Review retained L and G and rejected the family-document logic. Four misplaced `scope_fields` objects were normalized without changing assessments. |
| 3 | Initial extraction emitted 15 concepts for 15 blocks, exceeding six and including interface text. Repair returned six concepts, but the final review assigned two unrelated download blocks to a UK-document concept that did not cite them. The entire review failed locally. |
| 4 | The four contact claims still combined scopes 0047, 0048 and 0050 in one concept. Eleven calls had been spent, leaving one slot; the remaining slot cannot fund the required repair-and-review pair. No usable contact proposal reached review. |

The final inventory has 37 policy exclusions, 24 saturated-review blocks, 22
invalid-response blocks, 12 model-assessed not-substantive blocks and 10 covered
blocks. The unresolved count is 58, compared with 50 in the baseline. These
statuses are not verified source recall. In particular, the 24 saturated blocks
retain that conservative status even where the model identifies missing content.

## Quotation and coverage findings

Packet 2 did not correct the five failing condition quotations during repair.
The B-permit condition reconstructs `unbefristeter Arbeitsvertrag` from a source
that says `unbefristeter oder überjähriger Arbeitsvertrag`. Self-employment drops
parenthetical evidence examples in two conditions and changes a comma to a period
in the SVA condition. Non-employment reconstructs
`ausreichende finanzielle Mittel nachgewiesen` from a longer coordinated clause.
These are failures of the exact-excerpt contract, not evidence that every
paraphrase is factually false. No source text or condition was silently rewritten.

The family reviewer correctly rejects the flat six-way AND for conditional
document requirements, as well as the resulting incomplete description and
misleading document question. This is a useful rejection of a previously
human-flagged issue. It does not mean the family content has been repaired or
retained, and the reviewer still approves an unsupported document-recipient role.

Packet 3's final review marks sections 0072 and 0076 covered by concept 2, whose
UK-document claim cites only section 0065. Section 0072 refers to the Liechtenstein
PDF; section 0076 lists other directives. The review's claim that these repeat
the UK download is not supported. The strict per-block citation check remains
appropriate. The repaired proposal also omits address and onsite hours from
sections 0085/0086, which its review explicitly marks missing.

An offline structural-capacity control removes only the three interface claims
from the initial packet 3 proposals and groups the remaining 21 unchanged claims
by ownership, splitting the Liechtenstein group at the existing eight-claim cap.
The resulting five concepts have 7, 8, 1, 3 and 2 claims and pass the unchanged
schema and ownership validator. This demonstrates available structural capacity,
not semantic correctness or a successful model repair. No control replaced the
saved output.

The initial invalid completion has 21864 characters, but repair feedback includes
only its first 6000 characters, ending inside the Brexit material. The complete
source is still supplied. This fixed prefix is a concrete next diagnostic target:
it may bias repair attention, but the saved run does not establish causation.
Another useful diagnostic improvement would identify the offending block, concept
index and actual citations when a coverage reference fails. Neither finding
justifies weakening validation or increasing the current request limits.

## Source review of the seven retained drafts

All 12 retained evidence spans match their exact source offsets, and the 18
claims remain within their respective concepts' ownership scopes. Recommended
**accept draft**:

- **Aufenthalt für EU/EFTA-Staatsangehörige** (`527faef8`): accept only as the
  introductory source summary; its claim is unchanged.
- **Kurzaufenthaltsbewilligung (L)** (`37056dc0`): preserves more than three
  months AND less than one year AND more than 15 hours/week. Nested AND groups
  remain equivalent to the earlier flat conjunction.
- **Grenzgängerbewilligung (G)** (`bcb00440`): preserves EU/EFTA residence AND
  Swiss employment. `kind=permission` matches the source's permission modality.

Recommended **needs changes**, with GUI comments:

| Draft | Comment |
| --- | --- |
| Personenfreizügigkeit (`0f26c28d`) | Structure the specialized AND qualified restriction without implying sufficient entitlement. |
| Anmeldung bei der Wohngemeinde (`a29f3dcd`) | Represent within-canton OR across-canton move applicability explicitly, retain the 14-day reporting duty, and restore the supported procedure branches. |
| Zulassung zur unselbständigen Erwerbstätigkeit (`90db79cd`) | Do not require a stay of exactly three months for job search. Restore the supported job-search and registration procedure branches. |
| Meldeverfahren (90 Tage) (`945782e4`) | Leave the reporting actor unspecified unless the cited source identifies who submits the notification. |

The job-search statement survives; the loss concerns its explicit procedure-branch
field, not the whole assertion. Registration likewise loses explicit entry,
registration, move, forwarding and card-issuance branch fields. The four retained
previous change requests remain unresolved. The other four previous change
requests concern B, family reunification, Brexit and Liechtenstein drafts, which
are no longer retained. Previously accepted self-employment, non-employment and
address/onsite contact drafts are also absent.

## Current GUI resume checkpoint

This experiment is now paused at the user's request. The
[pause checkpoint](2026-09-10-extraction-pause-checkpoint.md) records the active
configuration, preserved artifacts, pending review recommendations and the
architectural/evaluation discussion to resume before further live tuning.

Under **Builds & review**, select **Concept extraction** created at **20:37 Zurich
time**, job `891e31a32d0f4f09b16a6ab062eaae00`. Record the three accept-draft and
four needs-changes recommendations above. The audit found zero reviews on this
new result. All fourteen decisions on the earlier job remain unchanged; even an
identical candidate ID does not transfer a review to a new result revision.

The read-only audit in `.local/admin/zh-ownership-live-891e31a3-20260910/` contains
`verify.py`, `audit.json`, `quotation-failures.json`, `packet-failures.json`,
`retained-review.json` and `draft-review-notes.json`. It verifies the prepared
prompt, unchanged inputs/configuration, exact quotations, original file hashes,
and both results' review bindings. No further inference, review mutation,
prompt change or validation relaxation was performed during this audit.

Raw result SHA-256:
`5b2caebd29df8dda2052b3829ed8d8110b1056e187423d5fc587d924e52f13c7`.
Canonical GUI result SHA-256:
`6238166d7e7b9e79991db45dcce372ab967025c196331f888f12be5710cb9851`.
