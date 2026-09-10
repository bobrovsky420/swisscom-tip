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
unchanged. No live inference of this prompt change has been performed.

## Prepared GUI checkpoint and live success criteria

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
