"""Refresh derived source index and draft contract hashes, without network access."""

from __future__ import annotations

import argparse
from pathlib import Path

from swisstip.builder.source_catalog import load_source_catalog
from swisstip.core.contracts import ArtifactRef, KnowledgeCatalog, LanguagePolicy
from swisstip.core.identity import json_content_hash, seal_artifact


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "config/catalogs"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report stale outputs without writing")
    args = parser.parse_args()
    data = load_source_catalog(DIRECTORY / "hackathon.sources.json")
    reference = ArtifactRef(artifact_id=data["artifact_id"], version=data["version"], sha256=json_content_hash(data))
    policy = seal_artifact(LanguagePolicy.model_validate_json((DIRECTORY / "hackathon.language-policy.json").read_bytes()))
    seed = KnowledgeCatalog.model_validate_json((DIRECTORY / "hackathon.seed.json").read_bytes())
    seed.language_policy_ref = policy.identity
    for entry in seed.entries:
        for metadata in entry.labels.values():
            metadata.provenance = [reference if ref.artifact_id == reference.artifact_id else ref for ref in metadata.provenance]
    seed = seal_artifact(seed)
    directory_url = next(source["definition"]["start_url"] for source in data["sources"]
                         if source["definition"]["source_id"] == "ch-sem-authorities")
    lines = ["# Residence in Switzerland - source catalogue", "",
             "Operator-authored source references only. Discovery dates and references are recorded",
             "per source in the registry. Authority discovery includes the",
             f"[SEM cantonal authority directory]({directory_url}).",
             "These are future scan targets, not legal evidence or confirmed crawler coverage.", "",
             "The machine-readable [registry](hackathon.sources.json) contains exact allowlists,",
             "discovery references, topic hints, scan sets, limits and per-source caveats.",
             "`ready` means eligible for a test; access and robots policy are checked at run time.", "",
             "| ID | Official source | Jurisdiction | Seed language hint | Priority | Scan status |",
             "| --- | --- | --- | --- | --- | --- |"]
    for source in sorted(data["sources"], key=lambda item: item["definition"]["source_id"]):
        definition = source["definition"]
        jurisdiction = definition["jurisdiction"]
        if source["authority_level"] == "municipal":
            jurisdiction += " / city " + source["municipality"]["name"]
        lines.append(f"| `{definition['source_id']}` | [{source['title']}]({definition['start_url']}) | "
                     f"{jurisdiction} | {definition['language']} | {source['priority']} | {source['scan_status']} |")
    outputs = {
        "hackathon.sources.md": "\n".join(lines) + "\n",
        "hackathon.language-policy.json": policy.model_dump_json(indent=2) + "\n",
        "hackathon.seed.json": seed.model_dump_json(indent=2) + "\n",
    }
    stale = []
    for filename, content in outputs.items():
        path = DIRECTORY / filename
        if path.read_text(encoding="utf-8") != content:
            stale.append(filename)
            if not args.check:
                path.write_text(content, encoding="utf-8", newline="\n")
    if args.check and stale:
        print("Stale generated catalogue files: " + ", ".join(stale))
        return 1
    print(f"Validated {len(data['sources'])} source references; draft identities and source index are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
