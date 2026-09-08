# Local ingestion Control API

See the [knowledge studio guide](../admin-console/README.md) for setup and demo.
The API is available at `http://127.0.0.1:8000/api/`; its OpenAPI schema is exported
to `apps/admin-console/openapi.json` for the generated frontend SDK.

Run `scripts/admin/run.py` with the repository Python interpreter to start the
API and worker together. For separate processes, first apply storage migrations,
then run `-m swisstip.control.worker` and
`-m uvicorn swisstip.control.api:app --host 127.0.0.1 --port 8000` with the same
database configuration. Closing an API process does not cancel the separate worker.

All mutation endpoints require JSON and `X-Swisstip-Local: 1`. The GUI supplies
these automatically. The API offers no arbitrary shell command, filesystem read,
DSN editor or provider-secret editor. Catalog source definitions and semantic
profiles are loaded from the existing checked-in configuration.

Jobs run existing knowledge-builder CLIs with argument lists, retained inputs and
bounded output. They write operational results, not serving-release approvals.
