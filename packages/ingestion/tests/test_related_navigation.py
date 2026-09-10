from __future__ import annotations

import unittest
from pathlib import Path

from swisstip.ingestion.concepts import CandidateConceptExtractor, STRUCTURED_PROMPT_PROFILE
from swisstip.ingestion.source_structure import normalize_blocks
from swisstip.ingestion.structured_extraction import StructuredExtraction


class RelatedNavigationTests(unittest.TestCase):
    def page(self, html):
        return normalize_blocks(Path("fixture.html"), html, html.encode("utf-8"))

    def plan(self, page):
        engine = CandidateConceptExtractor(None, active_profile="fixture", prompt_profile=STRUCTURED_PROMPT_PROFILE)
        return StructuredExtraction(engine).plan(page)

    def test_zurich_related_cards_are_audited_but_not_planned_as_evidence(self):
        page = self.page('''<main><h1>Residence</h1><p>Apply at your municipality.</p>
            <div class="mdl-related-content" data-init="relatedContent">
              <h2 id="relatedcontent">Das koennte Sie auch interessieren</h2>
              <div class="mdl-content_nav mdl-content_nav--two-columns" data-init="contentNav">
                <ul class="mdl-content_nav__list">
                  <li class="mdl-content_nav__item"><a class="atm-content_teaser" href="/work">
                    <span>EU/EFTA workers</span> Labour market, work permits</a></li>
                  <li class="mdl-content_nav__item"><a class="atm-content_teaser" href="/settlement">
                    <span>Settlement</span> Language skills, requirements</a></li>
                </ul>
              </div>
            </div>
            <div class="mdl-tag-group"><h2>Responsible authority</h2>
              <ul class="mdl-tag-group__tags"><li><a href="/migration-office">Migration office</a></li></ul>
            </div></main>''')
        jobs, inventory = self.plan(page)
        evidence = "\n".join(block.evidence_text for job in jobs for block in job)
        self.assertNotIn("Labour market", evidence)
        self.assertNotIn("Language skills", evidence)
        self.assertIn("Apply at your municipality.", evidence)
        self.assertIn("Responsible authority\nMigration office", evidence)
        related = next(row for row in inventory if "Labour market" in row["text"])
        self.assertEqual((related["kind"], related["status"], related["reason"]),
                         ("navigation", "excluded_policy", "navigation"))
        self.assertIn("Language skills", related["evidence_text"])

    def test_classification_preserves_block_identity_ownership_and_evidence(self):
        for tag, marker in (("div", "mdl-related-content"), ("div", "mdl-content_nav"),
                            ("ul", "mdl-content_nav__list")):
            with self.subTest(marker=marker):
                links = '<li><a href="/other">Other topic</a></li>'
                if tag == "div":
                    links = f"<ul>{links}</ul>"
                baseline = (f'<main><h1>Residence</h1><h2>Related pages</h2><{tag}>{links}</{tag}>'
                            '<h2>Contact</h2><address>Migration office</address></main>')
                marked = baseline.replace(f"<{tag}>", f'<{tag} class="{marker}">', 1)
                before, after = self.page(baseline), self.page(marked)
                self.assertEqual(len(before.sections), len(after.sections))
                for original, classified in zip(before.sections, after.sections):
                    original_data, classified_data = original.content_dict(), classified.content_dict()
                    original_data.pop("block_kind")
                    classified_data.pop("block_kind")
                    self.assertEqual(original_data, classified_data)
                    self.assertEqual(original.evidence_text, classified.evidence_text)
                navigation = next(block for block in after.sections if block.text == "Other topic")
                self.assertEqual(navigation.block_kind, "navigation")
                contact = next(block for block in after.sections if block.text == "Migration office")
                self.assertEqual(contact.block_kind, "address")
                self.assertEqual(after.normalization_version, "swisstip.logical-blocks/v3")

    def test_link_heavy_contacts_downloads_and_nested_conditions_remain_eligible(self):
        page = self.page('''<main><h1>Residence</h1>
            <div class="mdl-content_nav__wrapper"><h2>Application conditions</h2>
              <p>Provide the following documents.</p>
              <ul><li><a href="/income">Proof of income</a>
                <ul><li><a href="/bank">Bank statement</a></li></ul></li>
                <li><a href="/housing">Proof of housing</a></li></ul>
            </div>
            <div class="mdl-related-content-guidance"><p>Keep this similarly named prose.</p></div>
            <h2>Downloads</h2><div class="mdl-download_list"><ul class="mdl-download_list__list">
              <li><a href="/instructions.pdf" download>Permit instructions, PDF, 6 pages</a></li>
              <li><a href="/form.pdf" download>Application form, PDF, 2 pages</a></li></ul></div>
            <h2>Contact</h2><ul class="mdl-tag-group__tags">
              <li><a href="/migration-office">Migration office</a></li>
              <li><a href="mailto:office@example.test">Email</a></li>
              <li><a href="tel:+41000000000">Telephone</a></li></ul>
            </main>''')
        jobs, inventory = self.plan(page)
        evidence = "\n".join(block.evidence_text for job in jobs for block in job)
        for text in ("Provide the following documents.", "Proof of income", "Bank statement", "Proof of housing",
                     "Keep this similarly named prose.", "Permit instructions, PDF, 6 pages", "Application form",
                     "Migration office", "mailto:office@example.test", "tel:+41000000000"):
            self.assertIn(text, evidence)
        conditions = next(row for row in inventory if "Bank statement" in row["text"])
        self.assertEqual((conditions["kind"], conditions["status"]), ("list", "pending"))
        self.assertIn("Proof of income", conditions["text"])
        self.assertIn("Proof of housing", conditions["text"])


if __name__ == "__main__":
    unittest.main()
