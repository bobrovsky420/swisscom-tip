from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("poc01_packet", ROOT / "scripts/test/poc01/prepare_packet.py")
packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packet)


class Poc01PacketTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name) / "repo"
        self.repo.mkdir()
        (self.repo / "config").mkdir()
        (self.repo / "config/semantic-models.toml").write_text('active_profile = "fixture"\n', encoding="utf-8")
        (self.repo / "config/model-profiles.toml").write_text('schema_version = "swisstip.model-profiles/v1"\n', encoding="utf-8")
        (self.repo / ".env").write_text("DO_NOT_COPY_SECRET", encoding="utf-8")
        (self.repo / "config/private.toml").write_text("DO_NOT_COPY_SECRET", encoding="utf-8")
        self.source = Path(self.directory.name) / "historical"
        (self.source / "pages/de").mkdir(parents=True)
        (self.source / "runs/failed").mkdir(parents=True)
        (self.source / "checkpoints/v1").mkdir(parents=True)
        (self.source / "runs/failed/run.log").write_bytes(b"FAILED_LOG_SENTINEL\x00\xff")
        (self.source / "checkpoints/v1/opaque.json").write_bytes(b"UNPARSEABLE_MODEL_PROPOSAL_SENTINEL")
        (self.source / "concept-proposals.json").write_bytes(b"UNPARSEABLE_MODEL_PROPOSAL_SENTINEL")
        pages = []
        for index in (1, 2):
            raw = (f'<html lang="de"><title>Fixture {index}</title><h1>Heading {index}</h1>'
                   '<p>Exact source wording and conditions.</p>'
                   '<script src="https://invalid.example/remote.js">alert("source")</script>'
                   '<img src="https://invalid.example/remote.png"></html>').encode("utf-8")
            path = self.source / f"pages/de/page-{index}.html"
            path.write_bytes(raw)
            pages.append({"url": f"https://invalid.example/de/page-{index}.html",
                          "relative_path": f"de/page-{index}.html", "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()})
        self.manifest = {"page_count": len(pages), "total_bytes": sum(p["bytes"] for p in pages),
                         "pages": pages, "historical_absolute_path": "C:/old-temporary/location"}
        self.write_manifest()
        self.destination = self.repo / ".local/experiments/poc-01"

    def write_manifest(self):
        (self.source / "download-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def prepare(self):
        return packet.prepare_packet(self.source, self.destination, repo=self.repo)

    def read_rows(self):
        with (self.destination / "reviewer/gold.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            return reader.fieldnames, list(reader)

    def write_rows(self, columns, rows):
        with (self.destination / "reviewer/gold.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def label_rows(self):
        columns, rows = self.read_rows()
        required = packet.load_json(packet.SUPPORT / "review-schema.json")["required_for_labeled_row"]
        for row in rows:
            if int(row["gold_id"].rsplit("-", 1)[-1]) > 5:
                continue
            for field in required:
                row[field] = "Synthetic reviewed value"
            normalized = packet.load_json(self.destination / f"reviewer/sources/{row['page_id']}/normalized.json")
            section = normalized["sections"][0]
            quote = section["evidence_text"]
            row["evidence_refs_json"] = json.dumps([{"section_id": section["section_id"],
                                                    "start": 0, "end": len(quote), "quote": quote}])
            row["first_batch"] = "yes"
            row["risk_reason"] = "Synthetic high-risk selection"
            row["review_minutes"] = "2.5"
        self.write_rows(columns, rows)
        return columns, rows

    def test_preserves_every_original_byte_and_historical_manifest_paths(self):
        before = {p.relative_to(self.source): p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        result = self.prepare()
        self.assertEqual(result["artifact_count"], len(before))
        for relative, value in before.items():
            self.assertEqual((self.source / relative).read_bytes(), value)
            self.assertEqual((self.destination / "archive" / relative).read_bytes(), value)
        mapping = packet.load_json(self.destination / "metadata/source-map.json")
        self.assertEqual(mapping["original_root"], str(self.source.resolve()))
        self.assertTrue(mapping["sources"][0]["archived_relative_path"].startswith("archive/pages/"))
        original = packet.load_json(self.destination / "archive/download-manifest.json")
        self.assertEqual(original["historical_absolute_path"], "C:/old-temporary/location")

    def test_reviewer_sees_no_proposal_contents_and_no_prefilled_gold(self):
        self.prepare()
        for path in (self.destination / "reviewer").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"MODEL_PROPOSAL_SENTINEL", path.read_bytes())
                self.assertNotIn(b"FAILED_LOG_SENTINEL", path.read_bytes())
        _, rows = self.read_rows()
        self.assertEqual(len(rows), 20)
        for row in rows:
            self.assertEqual(row["label"], "")
            self.assertEqual(row["evidence_refs_json"], "")
            self.assertEqual(row["first_batch"], "")
            self.assertEqual(row["primary_reviewer"], "user")
            self.assertEqual(row["same_person_rereviewer"], "user")
            self.assertEqual(row["independent_adjudication"], "")
        raw = (self.destination / "reviewer/sources/source-01/raw-source.html").read_text(encoding="utf-8")
        self.assertNotIn('<script src="https:', raw)
        self.assertNotIn('<img src="https:', raw)
        self.assertIn("&lt;script", raw)
        self.assertIn("Content-Security-Policy", raw)

    def test_rejects_corrupt_source_before_creating_destination(self):
        (self.source / "pages/de/page-1.html").write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_rejects_manifest_path_traversal(self):
        self.manifest["pages"][0]["relative_path"] = "../../outside.html"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_nonempty_destination_preserves_existing_annotations(self):
        self.prepare()
        worksheet = self.destination / "reviewer/gold.csv"
        worksheet.write_text("Human annotation must survive", encoding="utf-8")
        before = worksheet.read_bytes()
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.prepare()
        self.assertEqual(worksheet.read_bytes(), before)
        self.assertEqual(packet.verify_packet(self.destination)["status"], "VERIFIED_PRESERVATION_ONLY")

    def test_verify_detects_archive_corruption_and_unexpected_files(self):
        self.prepare()
        archive = self.destination / "archive/runs/failed/run.log"
        before = archive.read_bytes()
        archive.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Preserved file differs"):
            packet.verify_packet(self.destination)
        archive.write_bytes(before)
        (self.destination / "reviewer/unexpected-model.json").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            packet.verify_packet(self.destination)

    def test_freezes_only_safe_configuration_and_current_metadata(self):
        self.prepare()
        files = list((self.destination / "metadata/frozen").rglob("*"))
        self.assertTrue(any(p.name == "semantic-models.toml" for p in files))
        self.assertTrue(any(p.name == "model-profiles.toml" for p in files))
        self.assertFalse(any(p.name in (".env", "private.toml") for p in files))
        for path in files:
            if path.is_file():
                self.assertNotIn(b"DO_NOT_COPY_SECRET", path.read_bytes())

    def test_blank_or_forged_evidence_cannot_be_frozen(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "10-15"):
            packet.freeze_review(self.destination)
        columns, rows = self.label_rows()
        refs = json.loads(rows[0]["evidence_refs_json"])
        refs[0]["quote"] = "Fabricated evidence"
        rows[0]["evidence_refs_json"] = json.dumps(refs)
        self.write_rows(columns, rows)
        with self.assertRaisesRegex(ValueError, "Evidence span mismatch"):
            packet.freeze_review(self.destination)
        self.assertFalse((self.destination / "review-freezes").exists())

    def test_review_freezes_are_versioned_and_corruption_is_detected(self):
        self.prepare()
        columns, rows = self.label_rows()
        first = packet.freeze_review(self.destination)
        first_path = Path(first["freeze"])
        first_bytes = (first_path / "gold.csv").read_bytes()
        rows[0]["notes"] = "Later human revision"
        self.write_rows(columns, rows)
        second = packet.freeze_review(self.destination, stage="full-gold")
        self.assertNotEqual(first["freeze"], second["freeze"])
        self.assertEqual((first_path / "gold.csv").read_bytes(), first_bytes)
        frozen = packet.load_json(first_path / "freeze-manifest.json")
        self.assertEqual(frozen["independent_adjudication"], "PENDING")
        self.assertEqual(frozen["status"], "GOLD_SNAPSHOT_NOT_EVALUATION_PASS")
        self.assertEqual(first["selected_count"], 10)
        packet.verify_packet(self.destination)
        (first_path / "gold.csv").write_text("corrupt", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Frozen gold"):
            packet.verify_packet(self.destination)

    def test_same_person_cannot_be_reported_as_independent_adjudication(self):
        self.prepare()
        columns, rows = self.label_rows()
        rows[0]["independent_adjudicator"] = "user"
        rows[0]["independent_adjudication"] = "approved"
        self.write_rows(columns, rows)
        with self.assertRaisesRegex(ValueError, "Independent adjudication"):
            packet.freeze_review(self.destination)

    def test_unique_quotes_derive_offsets_without_rewriting_worksheet(self):
        self.prepare()
        columns, rows = self.label_rows()
        for row in rows:
            if row["label"]:
                refs = json.loads(row["evidence_refs_json"])
                row["evidence_refs_json"] = json.dumps([
                    {"section_id": ref["section_id"], "quote": ref["quote"]} for ref in refs])
        self.write_rows(columns, rows)
        before = (self.destination / "reviewer/gold.csv").read_bytes()
        frozen = packet.freeze_review(self.destination)
        validated = packet.load_json(Path(frozen["freeze"]) / "validated-gold.json")
        ref = validated["rows"][0]["validated_evidence_refs"][0]
        self.assertEqual(ref["start"], 0)
        self.assertEqual(ref["end"], len(ref["quote"]))
        self.assertEqual((self.destination / "reviewer/gold.csv").read_bytes(), before)
        packet.verify_packet(self.destination)

    def test_ambiguous_quote_requires_unique_text_or_explicit_offsets(self):
        self.prepare()
        columns, rows = self.label_rows()
        ref = json.loads(rows[0]["evidence_refs_json"])[0]
        # The letter e appears repeatedly in the fixture's section heading/body.
        rows[0]["evidence_refs_json"] = json.dumps([{"section_id": ref["section_id"], "quote": "e"}])
        self.write_rows(columns, rows)
        with self.assertRaisesRegex(ValueError, "Ambiguous.*explicit start/end"):
            packet.freeze_review(self.destination)

    def test_destination_must_remain_internal(self):
        with self.assertRaisesRegex(ValueError, "ignored .local"):
            packet.prepare_packet(self.source, self.repo / "public-output", repo=self.repo)


if __name__ == "__main__":
    unittest.main()
