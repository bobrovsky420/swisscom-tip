# Repository instructions

## Python environment

- Use the repository-local `.venv` for every Python command, including scripts,
  package installation, formatting, linting, and tests.
- On Windows, invoke `.venv\Scripts\python.exe` directly. On macOS/Linux, invoke
  `.venv/bin/python` directly. Do not rely on an activated shell or a system
  `python`/`pip` executable.
- Run pip as `.venv\Scripts\python.exe -m pip` (or the macOS/Linux equivalent).
- If `.venv` is absent, create it at the repository root with Python 3.11 or
  newer, then install the editable workspace packages:
  `.venv\Scripts\python.exe -m pip install -e packages/ingestion -e apps/knowledge-builder`.
- Never commit `.venv`; it is intentionally excluded by the root `.gitignore`.
