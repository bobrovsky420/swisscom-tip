# Repeat a saved extraction from the command line

Run with the repository interpreter. This repeats the builder operation behind
the GUI's **Run extraction**, using the saved job's page bytes and model settings,
the current extraction code, fresh checkpoints and zero provider retries.

```shell
./.venv/Scripts/python.exe scripts/admin/extract.py --job-dir .local/admin/jobs/a3eba5ef2158488696ba603de42433c5 --dry-run
./.venv/Scripts/python.exe scripts/admin/extract.py --job-dir .local/admin/jobs/a3eba5ef2158488696ba603de42433c5
```

That job contains the `ch-sem-residence-en` snapshot and selects
`deepseek_v4_pro`. Replace `--job-dir` to repeat another saved extraction or plan.
The selected profile's API credential comes from the process environment first,
then `.env.dev` (override with `--env-file`). The script reads values without
executing shell expressions and does not print the credential. A dry-run needs
no credential and makes no model calls.

Each invocation creates a new ignored directory under
`.local/admin/cli-extractions/`. Override it with `--output path/to/new-directory`.
Artifacts include copied inputs, resolved configuration, a manifest with source
hashes, `result.json`, `progress.log`, `summary.json` and successful model
checkpoints. The report records the effective prompts and review history. The
original job's files and GUI status remain unchanged; this script runs the same
builder directly, without creating a database job or requiring the GUI server.

Exit code 0 means planning succeeded, or each page retained a draft. Exit code 2
means at least one page has no usable draft (or arguments were invalid); builder
failures propagate their nonzero code. Inspect `extraction_status`, candidate
labels, review history and warnings in the summary. `gui_equivalent_status` can
remain `needs_attention` for a successfully extracted draft because human review
is still required. A retained draft is not approved or published knowledge.

For the API and worker launcher, see the
[control API guide](../../apps/control-api/README.md).
