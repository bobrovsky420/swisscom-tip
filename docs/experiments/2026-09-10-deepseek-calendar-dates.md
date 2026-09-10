# DeepSeek calendar-date extraction experiment

This experiment follows GUI extraction `9210329deaa64ef49abc26cef7bfc7a9`,
whose [source review](2026-09-10-deepseek-zh-gui-extraction.md) retained 12 drafts.
Alex accepted five and marked seven needs changes. Those decisions and all
source/report/checkpoint files remain unchanged. This change addresses date
representation; it does not resolve the seven semantic corrections or the
remaining contact ownership failure.

## Observed failure

Packet 3 repeated four valid ISO-date comparisons across three proposals:

| Proposal | Boundary | Source meaning to assess |
| --- | --- | --- |
| Brexit | `lte 2020-12-31` | End of the stated transition phase; its start is not explicitly dated. |
| Brexit | `gte 2021-01-01` | When non-application of the FZA begins. |
| Citizens' rights agreement | `lte 2020-12-31` | When UK citizens exercised free-movement rights, not today's or application date. |
| Liechtenstein | `gte 2005-01-01` | When the stated grant applies, not an individual's residence deadline. |

Every value uses `unit="date"` and its condition text is an exact source excerpt.
The former validator converted ordered-comparison values to floats and rejected
these dates. Valid date strings do not settle the interpretation: subjects such
as `FZA` or `Freizügigkeit` do not identify the compared temporal quantity clearly.
The source's reference to a document also does not establish that document's
unprovided rights or requirements.

## Prepared change

Claim contract `swisstip.structured-claims/v2` adds a strictly validated date
domain without changing the JSON shape. Exact `unit="date"` requires a canonical
ASCII `YYYY-MM-DD` value representing a real calendar date for every operator.
No compact dates, week dates, timestamps, partial dates, invalid leap days,
Unicode-digit formats or invented calendar components are accepted. Other ordered
comparisons retain the finite-numeric-value requirement; non-date categorical
and `stated` values retain their existing behavior. No value or operator is
converted, and source quotation, ownership, condition-tree and review checks
remain enforced.

Both packaged prompts now distinguish historical facts, assertion-applicability
periods and person-specific cutoff events. They require the comparison subject
to identify the evidenced temporal quantity and preserve comparison boundaries.
Unclear or incomplete dates retain exact source wording with `stated`, unspecified
typed value/unit and a limitation. The prompts forbid invented transition starts,
eligibility prerequisites and substitution of an unrelated event date.

The prompt profile remains `concept_extraction_v4`; the review contract remains
`swisstip.structured-review/v2`. The authoring-contract version changes candidate
and review-revision identities, even for otherwise identical proposals. Earlier
human decisions remain bound to their old report and candidate; they are not
automatically copied to new IDs. Changed default prompt bytes produce new model
checkpoint keys. Unchanged custom prompts can still reuse raw completions, which
undergo current local validation.

| Prompt | New SHA-256 |
| --- | --- |
| Extraction | `b8683871a251a5d14498d95db4758fdf5fed875bec48072061aa752ba51d56e7` |
| Review | `d2478d3ac3c84104941e47293fe315c2cf350f98bf0e81345829ac9aef3f698b` |

## Offline verification

`deepseek_v4_zh_9210329d_dates.json` preserves the exact packet 3 evidence,
original and repaired completion bytes, original v1 rejection records and hashes.
Both saved four-proposal packets now reach review without changing evidence,
dates, operators or subjects. Synthetic uncertain reviews retain zero candidates;
this tests admission to review, not semantic approval or a successful live repair.
Negative controls still reject malformed dates, altered quotations and evidence
crossing ownership scopes. A separate synthetic control confirms that contract v2
changes candidate/revision identity without rewriting the claim content.

All 157 ingestion tests and 177 builder tests passed (334 total). Tests include
all seven operators, leap-year/year boundaries, invalid formats, explicit-unit
requirements, finite-number controls, unchanged categorical conditions and the
saved-proposal replay. Prompt snapshots pin the reviewed default bytes.

The audit in `.local/admin/zh-date-contract-9210329d-20260910/` preserves the
offline replay, requests, new GUI-resolved configuration, plan and hash checks.
Dry planning sends zero model requests and keeps the same source hashes,
inventory, four packets and 12-call ceiling. Provider construction was blocked.
Source size, 8192 output-token limit, 64000 review/repair-input allowances,
180-second timeout and disabled GUI provider retries are unchanged.

## Prepared GUI checkpoint

Fresh preview `4f38eaaa2cab4414b7f625e96e439474` is the **Extraction plan**
created at **10:22 Zurich time** on 10 September. The next user-controlled run
selects only **Aufenthalt für EU/EFTA-Staatsangehörige | Kanton Zürich**
(`zh-eu-efta`) in **Saved pages**, chooses **DeepSeek V4 Pro**, and uses
**Run extraction > Confirm extraction**. At preparation no live extraction of
this change had been performed. Saved human notes remain an audit trail; GUI extraction does
not automatically feed those notes into the new model requests.

## Live follow-up: b5ec2579

The user ran job `b5ec257972d849da9ddceb0cdb975b2c` with the prepared prompts
and contract v2. It took 359.071 seconds and made 11 calls: four initial
extractions, three repairs and four reviews. It retained 14 proposals and reported
98488 input and 50821 output tokens. There was no truncation, input-size failure,
provider retry or checkpoint hit. Source/configuration hashes match the previous
snapshot; both effective prompt hashes match the prepared date experiment.

Three actual retained conditions exercise the new date domain: transition
`lte 2020-12-31`, FZA non-application `gte 2021-01-01`, and the Liechtenstein
grant `gte 2005-01-01`. These ISO values would fail the old numeric-only check.
Their exact excerpts and inclusive operators match the source. Packet 3 now
reaches review in two calls without repair and retains Brexit/UK, Liechtenstein
and the address/opening-hours draft. This is evidence that the validator change
was used; the semantic completeness issues below remain separate.

Packet 1 again needed repair after its first reviewer described the entry-document
assertion as unconditional while approving added conditions. Packet 2 repaired
exact-quotation failures and retained six proposals; nine misplaced `scope_fields`
objects were normalized without changing judgments. Its 24 blocks remain flagged
for saturation. Packet 4 spent its available repair but still combined unrelated
contact ownership scopes, retaining nothing from that packet.

Final inventory statuses are 37 policy exclusions, 24 saturated-review blocks,
19 model-assessed not-substantive blocks, 18 covered blocks and seven invalid-response
blocks. The unresolved count is 50, down from 56. No block is labeled missing,
but source review still finds omitted content. Coverage judgments therefore do
not establish complete or correct extraction.

## Review of the fourteen retained drafts

All cited quotations and offsets match the source inventory. The introductory
residence and FZA structured claims are unchanged from the v1 job despite new
candidate IDs. Some other claims improved: registration now names its procedure
branches, job search regains `Stellensuche`, self-employment preserves active
business in the shorter value, and non-employment restores purpose-dependent
additional requirements in both the statement and a limitation.

Recommended **accept draft**, within the saved source scope:

- **Aufenthalt für EU/EFTA-Staatsangehörige** (`527faef8`): introductory summary.
- **Kurzaufenthaltsbewilligung (L)** (`9d24d5ad`): correct three cumulative thresholds.
- **Grenzgängerbewilligung (G)** (`6835617d`): correct conjunction and source modality.
- **Selbständige Erwerbstätigkeit** (`92b8b66a`): cumulative examination requirements and filing duty.
- **Aufenthalt ohne Erwerbstätigkeit** (`70b961ae`): the previously missing purpose-dependent qualification is restored.
- **Kontakt Migrationsamt** (`68c535f6`): address and onsite opening hours only, not telephone availability.

Recommended **needs changes**:

| Draft | Concrete review note |
| --- | --- |
| Personenfreizügigkeit (`07cf6d2f`) | Structure the specialized AND qualified restriction without implying sufficient entitlement. |
| Anmeldung bei der Wohngemeinde (`3167f1e0`) | Keep the restored move scope and explicitly represent within-canton OR across-canton applicability with the 14-day notification duty. The alternatives remain only in prose. |
| Zulassung zur unselbständigen Erwerbstätigkeit (`6f325c0c`) | Keep the restored job-search branch; do not require a stay of exactly three months. |
| Meldeverfahren (90 Tage) (`3479cb9e`) | Leave the reporting actor unspecified unless the cited evidence identifies who submits the notification. |
| Aufenthaltsbewilligung (B) (`67d7f7bc`) | Explicitly represent (unbefristet OR überjährig) AND more than 15 hours/week. |
| Familiennachzug (`804dc0a6`) | Separate branch-specific document requirements; structure the existing-permit prerequisite and retain the spouse-nationality wording. Leave the document recipient unspecified unless supported. The new limitation acknowledging alternatives does not correct the definite six-way AND, and family members are not evidenced recipients of the documents. |
| Brexit und UK-Bürger (`7cbf082a`) | Structure the UK-citizen cutoff in `weisung-uk-buerger`: the date of exercising free-movement rights is at or before 2020-12-31. It currently remains only in the statement and population. |
| Personen aus dem Fürstentum Liechtenstein (`fcb3a3bb`) | Restore the omitted assertion that Switzerland and Liechtenstein have a dense network of bilateral treaties and agreements. The 1923 treaty is only the following example. Preserve year-only wording without inventing a complete date. |

The brief date subjects could be clearer, but are not the sole basis for either
date draft's needs-changes recommendation. The new comparisons do not invent a
transition start or turn the Liechtenstein grant into a personal residence deadline.

The read-only audit in `.local/admin/zh-date-live-b5ec2579-20260910/` verifies
the three live date predicates, unchanged source, exact quotations and original
file hashes. It records all 14 recommended decisions. No inference, review mutation,
additional engine change or validation relaxation was performed during this audit.

Live report SHA-256:
`ea4b01cc7cd110110fbb159eed93dc64092e5531028fb89c51d57899be3bad55`.
Frozen configuration SHA-256:
`ffa3bbdc8018dd5312c2afe621546057ea6196147148431bca4e7a92e1912ac3`.

## Current GUI resume checkpoint

Open **Builds & review**, select **Concept extraction** from 10 September at
**10:25 Zurich time** (job `b5ec257972d849da9ddceb0cdb975b2c`), and record the
six accept-draft and eight needs-changes decisions above. Prior reviews remain
bound to their original reports. Review this result before another experiment.
