# Extraction prompts

These UTF-8 Markdown files are package resources used as model system prompts.
The files contain the actual instructions, without a Markdown wrapper added by
the loader. Source data and response schemas are assembled separately in Python.

| Profile | Extraction files, in order | Review file |
| --- | --- | --- |
| `concept_extraction_v1` | `concept_extraction_v1.md` | None |
| `concept_extraction_v2` | `concept_extraction_v2.md` | None |
| `concept_extraction_v3` | `concept_extraction_v2.md` + `concept_extraction_v3_extension.md` | `concept_review_v3.md` |
| `concept_extraction_v4` (repository default; `--structured`) | `structured_claim_extraction_v4.md` + `structured_claim_example_v4.md` | `structured_claim_review_v4.md` |

The v3 extraction files are concatenated exactly, with no added separator. The
extension starts with a newline. Changes to the v2 base also affect the v3
prompt. The original prompts are frozen by hash assertions in
`tests/test_prompt_templates.py`; intentional changes need corresponding updates.
The v4 example is also appended exactly and begins with a newline. It illustrates
connected conditions and separate authority actions with synthetic visitor-badge
facts; it is never source evidence. V4 reviews now use the versioned
`swisstip.structured-review/v2` contract, including condition logic and every
scope field on each claim. Custom v4 review prompts must request that full shape.

For local customization, copy the complete effective prompt from a dry-run
report's `effective_prompts.extraction.text` or `effective_prompts.review.text`
to an external file. The extraction entry contains all components for its profile.
Configure the copy through `extraction_prompt_file` or `review_prompt_file` in
the model configuration's `[extraction]` table. An override replaces the complete
prompt for that role, including any bundled composition. It applies to the
selected profile, including when `--structured` selects v4, so use a separate
configuration for each profile's custom prompts.

Only the bundled files belong in this package directory. Keep operator-specific
copies outside the installed package so application updates do not overwrite them.
See the knowledge-builder README for configuration and dry-run commands.
