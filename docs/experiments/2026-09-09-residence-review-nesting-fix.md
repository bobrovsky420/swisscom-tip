# Residence extraction: review nesting correction and live rerun

The saved `ch-sem-residence-en` page now retains one usable **Residence permits**
draft. A fresh DeepSeek V4 Pro run completed in 19.332 seconds with two model
requests, no provider retries, no checkpoint reuse and no failed revisions.
The only warning is the standard human-review requirement.

## Failure and correction

GUI job `a3eba5ef2158488696ba603de42433c5` made four model calls in about 39 seconds
and retained zero candidates. Both reviews contained all six scope assessments
for each of three claims, but nested `scope_fields` inside `condition_logic`.
The canonical review contract requires these objects to be siblings.

The earlier prompt example and review-validation feedback were already active
in this job. They did not prevent the repeated error. The extraction proposals
themselves represented the source's six substantive assertions faithfully.

The review parser now corrects this one known nesting error when the claim and
condition objects otherwise have exactly the expected keys and no sibling
`scope_fields` already exists. It moves the existing object without changing any
assessment, then runs the unchanged closed schema, reference and semantic checks.
Missing assessments, conflicting copies, unknown fields, duplicate JSON keys,
invalid condition logic and negative verdicts still prevent acceptance.

The report preserves the original raw completion and every corrected JSON path
under `review_normalizations`. Canonical provider responses need no correction.
The canonical schema and human promotion requirements remain unchanged.

## Reproduce from the command line

```shell
./.venv/Scripts/python.exe scripts/admin/extract.py --job-dir .local/admin/jobs/a3eba5ef2158488696ba603de42433c5 --dry-run
./.venv/Scripts/python.exe scripts/admin/extract.py --job-dir .local/admin/jobs/a3eba5ef2158488696ba603de42433c5
```

The [script guide](../../scripts/admin/README.md) describes credentials, output
paths and exit codes. This calls the same builder as the GUI with copied original
page bytes, saved model settings, current code and fresh checkpoints. It writes
new local artifacts without creating a GUI database job or modifying the old job.

## Observed result

| Metric | Original GUI job | Corrected live CLI run |
| --- | --- | --- |
| Retained candidates | 0 | 1 |
| Structured claims in retained draft | 0 | 3 |
| Model requests | 4 | 2 |
| Failed review revisions | 2 | 0 |
| Corrected scope objects | 0 | 3 |
| Elapsed seconds | About 39 | 19.332 |
| Reported input tokens | 18659 | 8918 |
| Reported output tokens | 4918 | 2515 |
| Provider retries | 0 | 0 |

The live reviewer repeated the exact nesting defect on all three claims. The
local correction recovered the complete assessments on the first review, so no
repair extraction was needed. The retained draft contains the permit requirement
with work OR a strict greater-than-three-month stay condition, the issuing
authority as actor, the complete three-category permit taxonomy, exact evidence
and three source-answerable questions. Assistant source inspection found all
six rubric assertions represented and no invented procedure or exception.

The report still has `coverage_complete=false`: five ancillary blocks (brochure
label, further-information label, modification date, URL and footer authority
name) are model-assessed `not_substantive` and remain for human review. The six
assertions above are source-fidelity checks, not an adjudicated completeness score.

This establishes recovery of the observed formatting failure and fidelity to
this saved page. One known-page run and model self-review do not establish general
accuracy or current legal correctness. The candidate remains `CANDIDATE` with
`publication_eligible=false`.

The script reports `extraction_status=draft_ready`, exit code 0 and
`gui_equivalent_status=needs_attention`. The GUI currently maps any report warning,
including the standard human-review warning, to **Needs attention**. That status
alone cannot distinguish a valid draft from the original zero-candidate failure.

## Artifacts and verification

Successful live artifacts are under
`.local/admin/cli-extractions/residence-a3eba5ef-live-network-20260909/`:
`result.json`, `summary.json`, `progress.log`, `manifest.json`, copied inputs,
configuration and two model checkpoints. The dry-run is in the adjacent
`residence-a3eba5ef-plan-20260909/` directory and planned four calls with zero sent.
An earlier sandbox attempt in `residence-a3eba5ef-live-20260909/` could not connect
to DeepSeek; it produced no completion and is retained separately. The successful
run used approved network access.

| Artifact | SHA-256 |
| --- | --- |
| Original report, unchanged | `4b2fcccb0b95572fdfad5cedab03bf30aacaa519297121aa9d1a614cf628f019` |
| Original and copied source | `4e24815fa1ac301c1d0e3c4cd7c4f63eec1802e3af00529526774c7515d578bb` |
| Successful live report | `1fe9b02e766f0b6beea4afc9c5f69ad90d15dfb3f173cb0d929ce1a6059a5bc0` |

All 123 ingestion tests, 158 existing knowledge-builder tests and seven new
script tests passed (288 total). Tests cover lossless normalization, rejection
of incomplete/conflicting data and negative assessments, unchanged canonical
behavior, review repair feedback, dry-run isolation, credential handling,
original-file preservation and useful CLI exit statuses. Both original failed
review revisions also passed direct offline replay with three recorded moves each.

Next: review the retained draft against its citations. Then distinguish
**Draft ready - review required** from extraction failures in the GUI, and run
the same checks on the German Residence and Zurich pages to test beyond this
known source.
