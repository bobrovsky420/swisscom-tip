import io
import unittest
from pypdf import PdfWriter
from extract_intermediate import extract_html, extract_pdf, attach_offsets


class IntermediateTests(unittest.TestCase):
    def test_headings_lists_footnotes_and_unicode_keep_source_context(self):
        raw = '''<html lang="de"><head><title>Bewilligung</title></head><body><main><h1>Aufenthalt</h1>
        <article id="art_1"><h2>Art. 1</h2><p>Die Bewilligung <b>ist erforderlich.</b><sup>1</sup></p>
        <ol start="3"><li><p>Pass mitbringen.</p><ul><li>Original vorlegen.</li></ul></li></ol>
        <div class="footnotes"><p id="fn-1">1 Geändert 2026.</p></div></article></main></body></html>'''.encode()
        result = extract_html(raw, 'https://example.gov/permit')
        blocks = result['blocks']
        paragraph = next(b for b in blocks if b['text'].startswith('Die Bewilligung'))
        self.assertEqual(paragraph['text'], 'Die Bewilligung ist erforderlich.1')
        self.assertEqual(paragraph['heading_path'], ['Aufenthalt', 'Art. 1'])
        self.assertEqual(paragraph['source_locator']['article_id'], 'art_1')
        nested = next(b for b in blocks if b['text'] == 'Original vorlegen.')
        self.assertEqual(len(nested['source_locator']['list_context']), 2)
        self.assertEqual(nested['source_locator']['list_context'][0]['start'], '3')
        self.assertTrue(blocks[-1]['source_locator']['is_footnote'])
        self.assertEqual(blocks[-1]['text'], '1 Geändert 2026.')

    def test_tables_preserve_cells_and_spans_without_duplicate_blocks(self):
        result = extract_html(b'<table><caption>Fees</caption><tr><th rowspan="2">Permit</th><td>10</td></tr>'
                              b'<tr><td><p>20</p><p>per year</p></td></tr></table>', 'https://example.gov/')
        self.assertEqual(len(result['blocks']), 1)
        table = result['blocks'][0]
        self.assertEqual(table['rows'][0][0]['rowspan'], '2')
        self.assertEqual(len(table['rows']), 2)
        self.assertEqual(table['caption'], 'Fees')
        self.assertEqual(table['rows'][1][0]['text'], '20 per year')

    def test_furniture_retained_with_labels_but_scripts_omitted(self):
        result = extract_html(b'<html><body><nav><a href="/help">Help</a></nav><main><p>Apply.</p>'
                              b'<div hidden><p>Alternate text.</p></div></main><footer>Contact us.</footer>'
                              b'<script>doNotInclude()</script></body></html>', 'https://example.gov/law')
        blocks = result['blocks']
        self.assertEqual(blocks[0]['source_locator']['region'], 'nav')
        self.assertEqual(blocks[0]['links'][0]['resolved_url'], 'https://example.gov/help')
        self.assertTrue(next(b for b in blocks if b['text'] == 'Alternate text.')['source_locator']['explicit_hidden'])
        self.assertEqual(blocks[-1]['source_locator']['region'], 'footer')
        self.assertNotIn('doNotInclude', ' '.join(b['text'] for b in blocks))

    def test_maintenance_is_identified_and_plain_unicode_not_corrupted(self):
        result = extract_html('<html><title>Wartungsarbeiten</title><body>Änderung bientôt.</body></html>'.encode(),
                              'https://example.gov/')
        self.assertEqual(result['page_kind'], 'maintenance_page')
        self.assertEqual(result['blocks'][0]['text'], 'Änderung bientôt.')

    def test_offsets_round_trip_and_stable_block_ids(self):
        document = {'document_id': 'doc-one', 'blocks': extract_html(b'<h1>Permit</h1><p>Apply now.</p>',
                                                                    'https://example.gov/')['blocks']}
        attach_offsets(document)
        self.assertEqual(document['blocks'][1]['block_id'], 'doc-one:b00002')
        for block in document['blocks']:
            self.assertEqual(document['content_text'][block['start']:block['end']], block['text'])

    def test_http_200_soft_404_is_not_substantive_evidence(self):
        result = extract_html(b'<html><body><nav>DE FR IT RM EN</nav><main><h1>Error Page (404)</h1>'
                              b'</main></body></html>', 'https://example.gov/residence')
        self.assertEqual(result['page_kind'], 'error_page')

    def test_unrendered_cms_navigation_is_not_content(self):
        raw=b'<html><script>window.CONTENT_ID="3454"; window.IS_FRONTEND=true;</script><body>Navigation Login Logout</body></html>'
        self.assertEqual(extract_html(raw,'https://sh.ch/CMS/page')['page_kind'],'application_shell')

    def test_blank_pdf_reports_missing_text_without_inventing_ocr(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        raw = io.BytesIO()
        writer.write(raw)
        result = extract_pdf(raw.getvalue())
        self.assertEqual(result['blocks'], [])
        self.assertEqual(result['pdf_page_count'], 1)
        self.assertEqual(result['pages_without_text'], [1])


if __name__ == '__main__':
    unittest.main()
