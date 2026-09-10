"""Compatibility entry point for the standard catalogue downloader."""
from swisstip.builder.download_cli import main
from swisstip.ingestion.acquisition import (  # Backward-compatible helper imports.
    catalogue_targets, now, saved_and_intact, snapshot, summary, write_json,
)

if __name__ == "__main__":
    raise SystemExit(main())
