"""Respect concept capacity without splitting ownership or hiding skipped input."""
import json
import unittest

from swisstip.ingestion.structured_extraction import StructuredExtraction
import test_structured_extraction as helpers


class PacketScopeLimitTests(unittest.TestCase):
    def setUp(self):
        self.helper = helpers.StructuredTests()

    def page(self, count, text="Apply online."):
        return self.helper.page("".join(
            f"<section><h2>Topic {i}</h2><p>{text}</p><ul><li>Attach proof.</li></ul></section>"
            for i in range(count)))

    def test_scope_capacity_keeps_every_group_whole_and_every_block_once(self):
        page = self.page(7)
        engine = self.helper.engine(None, max_concepts_per_chunk=6)
        packets, inventory = StructuredExtraction(engine).plan(page)
        self.assertEqual([len({b.scope_id for b in p}) for p in packets], [6, 1])
        eligible = [b for b in page.sections if b.block_kind not in {"heading", "navigation"}]
        self.assertEqual([b for p in packets for b in p], eligible)
        for block in eligible:
            owners = [p for p in packets if any(b.scope_id == block.scope_id for b in p)]
            self.assertEqual(len(owners), 1)
            self.assertEqual([b for b in owners[0] if b.scope_id == block.scope_id],
                             [b for b in eligible if b.scope_id == block.scope_id])
        self.assertEqual(sum(r["status"] == "pending" for r in inventory), len(eligible))

    def test_character_limit_can_split_before_scope_capacity(self):
        page = self.page(3, text="word " * 60)
        engine = self.helper.engine(None, max_concepts_per_chunk=6,
                                   chunk_content_characters=500, chunk_overlap_characters=0)
        packets, _ = StructuredExtraction(engine).plan(page)
        self.assertEqual(len(packets), 3)
        self.assertTrue(all(sum(len(b.evidence_text) for b in p) <= 500 for p in packets))

    def test_budget_omissions_remain_explicit_after_scope_split(self):
        page = self.page(7)
        engine = self.helper.engine(None, max_concepts_per_chunk=2, max_model_requests_per_page=5)
        packets, inventory = StructuredExtraction(engine).plan(page)
        self.assertEqual(len(packets), 2)
        self.assertEqual(engine.planned_request_count(page), 4)
        self.assertEqual(sum(r["status"] == "not_processed_budget" for r in inventory), 6)
        planned_ids = {b.section_id for p in packets for b in p}
        self.assertTrue(all(r["section_id"] not in planned_ids
                            for r in inventory if r["status"] == "not_processed_budget"))

    def test_later_packets_get_initial_audits_before_repairs_spend_budget(self):
        page = self.page(7)
        provider = helpers.Provider(generate=lambda result, payload: result.update(concepts=[]))
        engine = self.helper.engine(provider, max_concepts_per_chunk=2, max_model_requests_per_page=12)
        report = engine.extract(page)
        self.assertEqual(len(provider.calls), 12)
        initial = [call for call in provider.calls
                   if "concepts" not in (payload := json.loads(call["user_prompt"]))
                   and payload["repair"] is None]
        self.assertEqual(len(initial), 4)
        self.assertEqual(report.quality_metrics["review_request_count"], 6)
        self.assertEqual(report.quality_metrics["repair_request_count"], 2)
        self.assertFalse(report.candidates)
        self.assertFalse(any(r["status"].startswith("not_processed") for r in report.source_inventory))


if __name__ == "__main__":
    unittest.main()
