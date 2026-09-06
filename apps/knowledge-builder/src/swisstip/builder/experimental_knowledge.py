"""Build and query extractor candidates directly for hackathons and local tests."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

SCHEMA = "swisstip.experimental-knowledge/v1"
MANIFEST_SCHEMA = "swisstip.experimental-knowledge-manifest/v1"
TRUST = {"mode": "EXPERIMENTAL_UNREVIEWED", "human_review": "not_required",
         "publication_eligible": False, "verified_coverage": False}
MAX_BYTES = 100_000_000


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"file exceeds {MAX_BYTES} bytes: {path}")
    return raw


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=invalid)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid {name}")
    return value


def _reports(document):
    if not isinstance(document, dict):
        raise ValueError("expected an extractor report or batch")
    reports = document.get("reports") if document.get("schema_version") == "swisstip.concept-proposal-batch/v1" else [document]
    if not isinstance(reports, list) or not reports or len(reports) > 1000:
        raise ValueError("expected 1-1000 reports")
    for report in reports:
        if not isinstance(report, dict) or report.get("schema_version") not in {
            "swisstip.concept-proposal-report/v1", "swisstip.concept-proposal-report/v2"
        } or report.get("prompt_profile") not in {f"concept_extraction_v{i}" for i in range(1, 5)}:
            raise ValueError("unsupported extractor report schema or prompt profile")
        for key in ("document_id", "source", "input_hash", "output_hash"):
            _text(report.get(key), key)
        if report.get("language") is not None:
            _text(report["language"], "language")
        if not isinstance(report.get("candidates"), list):
            raise ValueError("report candidates must be an array")
    return reports


def _candidate(value, report):
    if not isinstance(value, dict) or value.get("validation_state") != "CANDIDATE":
        raise ValueError("experimental input must contain extractor CANDIDATE records")
    for key in ("candidate_id", "preferred_label", "description", "scope", "concept_type", "granularity"):
        _text(value.get(key), key)
    for key in ("alternative_labels", "user_questions"):
        if not isinstance(value.get(key), list) or any(not isinstance(v, str) for v in value[key]):
            raise ValueError(f"candidate {key} must be a string array")
    spans = value.get("evidence")
    if not isinstance(spans, list) or not spans:
        raise ValueError("candidate requires source evidence")
    inventory = {row["section_id"]: row for row in report.get("source_inventory", [])}
    for span in spans:
        if not isinstance(span, dict):
            raise ValueError("invalid evidence span")
        _text(span.get("section_id"), "section_id")
        quote = _text(span.get("quote"), "quote")
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or start < 0 or end - start != len(quote):
            raise ValueError("invalid evidence offsets")
        if report["prompt_profile"] == "concept_extraction_v4":
            block = inventory.get(span["section_id"], {})
            text = block.get("evidence_text")
            if not isinstance(text, str) or text[start:end] != quote:
                raise ValueError("v4 citation does not match the source inventory")


def build_bundle(report_paths, output_dir):
    """Materialize retained candidates; never read human decisions or call a model."""
    paths = list(report_paths)
    if not 1 <= len(paths) <= 100:
        raise ValueError("provide 1-100 extractor report files")
    raw_inputs = {}
    for path in paths:
        raw = _read(path)
        raw_inputs.setdefault(_sha(raw), raw)
    if sum(map(len, raw_inputs.values())) > 200_000_000:
        raise ValueError("combined reports exceed 200 MB")
    concepts, evidence, sources = [], [], []
    for digest, raw in sorted(raw_inputs.items()):
        for report_index, report in enumerate(_reports(_decode(raw))):
            source_id = "exp-source-" + _sha(_bytes([digest, report_index]))[:24]
            sources.append({"source_id": source_id, "report_file": f"reports/{digest}.json",
                            "report_sha256": digest, "report_index": report_index,
                            **{key: report.get(key) for key in (
                                "source", "document_id", "title", "language", "input_hash", "output_hash",
                                "source_sha256", "normalization_version", "provider", "model", "prompt_profile",
                                "quality_metrics", "warnings", "source_inventory", "semantic_reviews",
                                "rejected_candidates", "skipped_chunks", "excluded_sections")}})
            seen = set()
            for candidate in report["candidates"]:
                _candidate(candidate, report)
                if candidate["candidate_id"] in seen:
                    raise ValueError("duplicate candidate ID within a source report")
                seen.add(candidate["candidate_id"])
                concept_id = "exp-concept-" + _sha(_bytes([source_id, candidate["candidate_id"]]))[:24]
                evidence_ids = []
                for index, span in enumerate(candidate["evidence"]):
                    evidence_id = "exp-evidence-" + _sha(_bytes([concept_id, index, span]))[:24]
                    evidence_ids.append(evidence_id)
                    evidence.append({"evidence_id": evidence_id, "concept_id": concept_id,
                                     "source_id": source_id, "source": report["source"],
                                     "input_hash": report["input_hash"], "report_sha256": digest,
                                     "location_validation": "matched_source_inventory" if report["prompt_profile"] == "concept_extraction_v4"
                                     else "extractor_report_only", **span})
                concepts.append({"concept_id": concept_id, "source_id": source_id,
                                 "language": report.get("language"), "evidence_ids": evidence_ids,
                                 "candidate": copy.deepcopy(candidate)})
                if len(concepts) > 20_000:
                    raise ValueError("experimental bundle exceeds 20000 candidates")
    knowledge = {"schema_version": SCHEMA, **TRUST, "concepts": concepts, "evidence": evidence,
                 "sources": sources, "selection_policy": "retained_candidates_only; preserve_model_outputs_without_human_review",
                 "consolidation_policy": "preserve_each_source_and_model_revision; no_automatic_merge"}
    knowledge["bundle_id"] = "experiment-" + _sha(_bytes(knowledge))[:24]
    encoded = _bytes(knowledge)
    if len(encoded) > MAX_BYTES:
        raise ValueError("experimental knowledge exceeds 100 MB")
    manifest = {"schema_version": MANIFEST_SCHEMA, **TRUST, "bundle_id": knowledge["bundle_id"],
                "concept_count": len(concepts), "evidence_count": len(evidence), "source_count": len(sources),
                "files": {"knowledge.json": _sha(encoded), **{f"reports/{key}.json": key for key in raw_inputs}}}
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "reports").mkdir()
    for digest, raw in raw_inputs.items():
        (directory / "reports" / f"{digest}.json").write_bytes(raw)
    (directory / "knowledge.json").write_bytes(encoded)
    # Written last: an interrupted build cannot load as a completed bundle.
    (directory / "manifest.json").write_bytes(_bytes(manifest))
    return manifest


def _terms(text):
    return set(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


class ExperimentalKnowledge:
    """Small dependency-free catalog/search/evidence adapter for experimental apps."""
    def __init__(self, directory):
        directory = Path(directory).resolve()
        manifest = _decode(_read(directory / "manifest.json"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA or any(manifest.get(k) != v for k, v in TRUST.items()):
            raise ValueError("not an experimental unreviewed bundle")
        files = manifest.get("files")
        if not isinstance(files, dict) or "knowledge.json" not in files:
            raise ValueError("bundle manifest lacks knowledge.json")
        knowledge = None
        for name, digest in files.items():
            if name != "knowledge.json" and not re.fullmatch(r"reports/[a-f0-9]{64}\.json", name):
                raise ValueError("invalid bundle artifact path")
            path = (directory / name).resolve()
            if not path.is_relative_to(directory):
                raise ValueError("bundle artifact escapes its directory")
            raw = _read(path)
            if _sha(raw) != digest:
                raise ValueError(f"bundle artifact hash mismatch: {name}")
            if name == "knowledge.json":
                knowledge = _decode(raw)
        if not isinstance(knowledge, dict) or knowledge.get("schema_version") != SCHEMA or any(knowledge.get(k) != v for k, v in TRUST.items()):
            raise ValueError("invalid experimental knowledge metadata")
        payload = {k: v for k, v in knowledge.items() if k != "bundle_id"}
        identity = "experiment-" + _sha(_bytes(payload))[:24]
        if knowledge.get("bundle_id") != identity or manifest.get("bundle_id") != identity:
            raise ValueError("experimental bundle identity mismatch")
        self._data = knowledge
        self._concepts = {c["concept_id"]: c for c in knowledge["concepts"]}
        self._evidence = {e["evidence_id"]: e for e in knowledge["evidence"]}

    def _result(self, **values):
        return copy.deepcopy({"schema_version": "swisstip.experimental-result/v1",
                              "bundle_id": self._data["bundle_id"], **TRUST, **values})

    def list_concepts(self, *, limit=20, offset=0, language=None):
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError("limit must be 1-100 and offset must be nonnegative")
        items = [c for c in self._data["concepts"] if language is None or c["language"] == language]
        return self._result(total=len(items), concepts=items[offset:offset + limit],
                            next_offset=offset + limit if offset + limit < len(items) else None)

    def search(self, query, *, limit=10, language=None):
        if not isinstance(query, str) or not 1 <= len(query) <= 1000 or not _terms(query):
            raise ValueError("query must contain words and be at most 1000 characters")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1-100")
        terms, matches = _terms(query), []
        for item in self._data["concepts"]:
            if language is not None and item["language"] != language:
                continue
            candidate = item["candidate"]
            label = _terms(" ".join([candidate["preferred_label"], *candidate["alternative_labels"]]))
            body = _terms(" ".join([candidate["description"], candidate["scope"], *candidate["user_questions"]]))
            score = 3 * len(terms & label) + len(terms & body)
            if score:
                matches.append({"score": score, **item})
        matches.sort(key=lambda item: (-item["score"], item["concept_id"]))
        return self._result(query=query, total=len(matches), matches=matches[:limit],
                            ranking="lexical_term_overlap; not_entailment_or_eligibility")

    def get_concept(self, concept_id):
        if concept_id not in self._concepts:
            raise ValueError("unknown experimental concept ID")
        item = self._concepts[concept_id]
        source = next(s for s in self._data["sources"] if s["source_id"] == item["source_id"])
        return self._result(concept=item, evidence=[self._evidence[e] for e in item["evidence_ids"]], source=source)

    def get_evidence(self, evidence_id):
        if evidence_id not in self._evidence:
            raise ValueError("unknown experimental evidence ID")
        return self._result(evidence=self._evidence[evidence_id])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="use retained extractor output without human review")
    build.add_argument("reports", type=Path, nargs="+")
    build.add_argument("--output-dir", type=Path, required=True)
    for name in ("list", "search", "get", "evidence"):
        command = commands.add_parser(name)
        command.add_argument("bundle", type=Path)
        if name == "search":
            command.add_argument("query")
        if name in {"get", "evidence"}:
            command.add_argument("id")
        else:
            command.add_argument("--limit", type=int, default=10)
            command.add_argument("--language")
        if name == "list":
            command.add_argument("--offset", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_bundle(args.reports, args.output_dir)
        else:
            knowledge = ExperimentalKnowledge(args.bundle)
            if args.command == "list":
                result = knowledge.list_concepts(limit=args.limit, offset=args.offset, language=args.language)
            elif args.command == "search":
                result = knowledge.search(args.query, limit=args.limit, language=args.language)
            elif args.command == "get":
                result = knowledge.get_concept(args.id)
            else:
                result = knowledge.get_evidence(args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"experimental-knowledge: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
