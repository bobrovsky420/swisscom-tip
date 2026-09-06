"""Export deterministic JSON Schema contracts, without running any service.

Usage: python -m swisstip.core.schemas --output packages/core/schemas
Pass --check to compare existing exports without writing files.
"""

import argparse
import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from .contracts import CONTRACT_MODELS


def schema_documents() -> dict[str, str]:
    roots, schema = models_json_schema(
        [(model, "validation") for model in CONTRACT_MODELS],
        title="SwissTIP contract bundle v1",
        description="Structural schemas. Canonicalization, cross-field invariants and catalog-aware validation additionally apply.",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:swisstip:contracts:v1"
    schema["x-contracts"] = {model.__name__: roots[(model, "validation")] for model in CONTRACT_MODELS}
    schema["anyOf"] = list(schema["x-contracts"].values())
    return {"contracts-v1.schema.json": json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=True) + "\n"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    documents = schema_documents()
    if args.check:
        mismatched = [name for name, content in documents.items() if not (args.output / name).is_file() or (args.output / name).read_text(encoding="utf-8") != content]
        if mismatched:
            print("Missing or stale schemas: " + ", ".join(mismatched))
            return 1
        print(f"Verified {len(documents)} contract schemas.")
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in documents.items():
        (args.output / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"Exported {len(documents)} contract schemas to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
