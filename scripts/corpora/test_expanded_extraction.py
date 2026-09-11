import io
import unittest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from extract_expanded import extract_pdf, extract_rtf


class ExpandedPdfTests(unittest.TestCase):
    def test_rtf_formatting_and_embedded_picture_are_not_source_text(self):
        raw=br'{\rtf1\ansi Permit \b documents\b0\par {\pict\pngblip 89504e47}Required: passport.}'
        value=extract_rtf(raw)
        self.assertEqual([b['text'] for b in value['blocks']],['Permit documents','Required: passport.'])

    def test_native_text_and_blank_pages_are_distinguished(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=300,height=300)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),
                                 NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 10 100 Td (Permit application) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        writer.add_blank_page(width=300,height=300)
        raw = io.BytesIO()
        writer.write(raw)
        value = extract_pdf(raw.getvalue())
        self.assertEqual(value['pdf_page_count'],2)
        self.assertEqual(value['blocks'][0]['text'],'Permit application')
        self.assertEqual(value['pages_without_text'],[2])


if __name__=='__main__':
    unittest.main()
