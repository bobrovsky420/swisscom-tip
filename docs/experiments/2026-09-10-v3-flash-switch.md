# V3 extraction and DeepSeek Flash switch - 10 September 2026

The user selected `concept_extraction_v3` after reviewing the cost and complexity
of the V4 extraction experiment, then selected `deepseek_v4_1_flash` as the default
extraction/review model. Both defaults are active in `config/semantic-models.toml`.
The local GUI API and worker were restarted while idle. No live extraction or
human review decision was submitted for this switch.

## Prepared resume point

Refresh **http://127.0.0.1:8000**. In **Builds & review**, the **Extraction plan**
created at **21:42 Zurich time on 10 September** is the V3/Flash preview for
**Aufenthalt fuer EU/EFTA-Staatsangehoerige, Kanton Zuerich** (`zh-eu-efta`).
In **Saved pages**, select only that page and confirm the extraction model is
`deepseek_v4_1_flash` before the next operator-triggered extraction.

| Item | Verified value |
| --- | --- |
| Offline plan job | `11599a3070c34a86bc1bcf5a9ba52ad9` |
| Source asset | `6be69747eebc489294932bc1d8d3c770` |
| Workflow | `concept_extraction_v3` |
| Model profile / provider identifier | `deepseek_v4_1_flash` / `deepseek-flash` |
| Source normalization | 32 sections, 13689 characters |
| Filtered source preview | 15 sections, 10747 characters; 17 excluded sections |
| Planned model requests | 4: extraction and review for each of two chunks |
| Model requests sent | 0 |
| Limits | 8192 output tokens, 180 seconds, 12 calls/page and 30/run; GUI automatic retries disabled |

Flash uses the existing catalog alias and adapter, JSON-object output and disabled
thinking. The [recorded provider mapping](../../config/README.md#deepseek-v41-flash)
explains the alias's version-pinning limits. Ranking and embeddings retain their
independent settings.

V3 selects source spans, attaches exact quotations locally, and proposes concepts
with textual scope and questions. It excludes generic contacts, navigation,
feedback and embedded news. It does not produce V4 condition trees or perform
block-by-block coverage audits and structured repair. Its normalization and
content scope differ from V4, so the four-request plan is not a quality-equivalent
replacement for the previous twelve-request V4 plan. Live quality remains to be
reviewed against the source, especially applicability and omitted conditions.

## Implementation and validation

The GUI worker now follows the frozen job configuration instead of forcing
`--structured`. The parsed-source preview uses the configured workflow's actual
normalization and filters. Catalog/preview responses identify that workflow;
omitted API model selections resolve to the configured default and are frozen
in the saved request. Explicit model selections remain available.

V3 plans display page/request estimates; V3 candidate cards display scope,
questions and source evidence. Saved V4 results retain claim/condition display
and source inventories. The comment dialogs for needs changes and rejection
remain available on both kinds of candidate.

- Builder suite: 177 tests exercised; one old V4-default expectation was updated
  and its seven-test DeepSeek module passed on rerun. All other tests passed.
- Control API/worker: all 21 tests passed, including disposable PostgreSQL
  integration and real offline CLI jobs using frozen V3 and V4 configurations.
- OpenAPI/SDK regenerated; TypeScript and production frontend build passed.
- Both API-mocked browser suites passed V3/Flash display, historical V4 rendering,
  comment dialogs, save/retry/focus behavior and mobile layout.
- The real local worker completed the saved Zurich plan with zero model calls.
- A fresh browser session verified the real Flash default, V3 source preview and
  saved four-request plan. The check allowed reads only and attempted no mutations.

The [V4 pause checkpoint](2026-09-10-extraction-pause-checkpoint.md) remains the
historical reference. Its latest result `891e31a3...` still has zero reviews;
`b5ec2579...` still has 14. Both result hashes and full review records matched
before and after preparing this plan. No prompts or historical result files
were changed.

## Local artifacts and identities

The verification script, filtered preview, plan response, previous review
snapshots and manifest are under `.local/admin/v3-flash-switch-20260910/`.
The plan's frozen inputs/configuration and progress log are under
`.local/admin/jobs/11599a3070c34a86bc1bcf5a9ba52ad9/`. These local artifacts are
Git-ignored; this document preserves their identities, not their contents.

| Identity | SHA-256 |
| --- | --- |
| Original source HTML | `b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4` |
| Frozen configuration | `1f92a6bfd389c6b7daf6d7e7bda712dd2c8c775359045c39c1dc2e9f4fe18818` |
| V3 extraction prompt | `ccd968b7b59b7ef144255483d42cda016872c0c82b49d00deb384578b234ee83` |
| V3 review prompt | `893394d896520067767f1c69eaeefd8efad780658710b99fde64112d8390c78e` |
| Canonical GUI plan result | `ef69d4ae0df199702b7765bfa1eae5d18fc40dac898e9917a37c24e782a98731` |
