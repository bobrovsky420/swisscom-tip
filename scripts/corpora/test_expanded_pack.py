import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from lingua import LanguageDetectorBuilder
from build_expanded_pack import build_part, pieces
from audit_source_languages import sha, allowed
from extract_source_assertions import identify_language, annotate
from office_text import extract_openxml


class ExpandedPackTests(unittest.TestCase):
    def test_published_language_survives_confident_wrong_classifier(self):
        d=dict(source_url='https://www.sem.admin.ch/sem/fr/data/example.pdf',language_hint='fr')
        result=identify_language(d,'French PDF with damaged font mapping. '*20,None,
            dict(detected_language='tl',confidence=1.0))
        self.assertEqual(result['effective_language'],'fr')
        self.assertTrue(result['review_flags'])

    def test_named_language_requires_word_boundaries(self):
        d=dict(source_url='https://www.ag.ch/tuerkische-staatsangehoerige',language_declared='de')
        cached=dict(detected_language='de',confidence=1.0)
        self.assertEqual(identify_language(d,'Text',None,cached)['effective_language'],'de')
        d['source_url']='https://www.ag.ch/elterninformation-vietnamesisch.pdf'
        self.assertEqual(identify_language(d,'Text',None,cached)['effective_language'],'vi')

    def test_long_assertion_fragments_retain_every_character_and_qualification(self):
        text=('A permit requires the listed documents. '*100)+'Unless an exception applies, submit them together.'
        result=list(pieces(text))
        self.assertEqual(''.join(result),text)
        self.assertTrue(all(len(p)<=1900 for p in result))
        self.assertTrue(annotate(text,'Permit application','https://www.ge.ch/permit')['condition_or_exception_sentences'])

    def test_declared_italian_is_not_replaced_by_navigation_language(self):
        detector=LanguageDetectorBuilder.from_all_languages().build()
        d=dict(source_url='https://www.sem.admin.ch/sem/it/home/themen/arbeit.html',language_declared='it',language_hint='it')
        result=identify_language(d,'Non-cittadini dell’UE/AELS. Basi per l’ammissione sul mercato del lavoro. Iter procedurale.',detector)
        self.assertEqual(result['effective_language'],'it')
        self.assertEqual(result['detected_language'],'it')

    def test_government_subdomains_are_allowed_without_allowing_lookalikes(self):
        self.assertTrue(allowed('https://media.bs.ch/form.pdf',[]))
        self.assertTrue(allowed('https://prestations.vd.ch/law',[]))
        self.assertFalse(allowed('https://vd.ch.example.com/law',[]))

    def test_office_xml_keeps_inline_text_and_formula_without_executing_it(self):
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as z:
            z.writestr('xl/workbook.xml','<workbook/>')
            z.writestr('xl/worksheets/sheet1.xml','<worksheet><row r="1"><c r="A1" t="inlineStr"><is><t>Permit fee</t></is></c><c r="B1"><f>1+2</f><v>3</v></c></row></worksheet>')
        result=extract_openxml(raw.getvalue())
        self.assertEqual(result['blocks'][0]['text'],'Permit fee | 3 [formula: 1+2]')
        self.assertEqual(result['blocks'][0]['cells'][1]['formula'],'1+2')

    def test_extended_language_assertion_is_exact_in_serialized_serving_fixture(self):
        text='Документи для дозволу на проживання. Подайте заяву до відповідного органу.'
        raw=text.encode()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'source.html').write_bytes(raw)
            doc=dict(document_id='doc-example',source_url='https://www.ge.ch/permit',document_url='https://www.ge.ch/permit',
                title='Permit documents',language_declared='uk',content_text=text,content_sha256=sha(raw),
                acquisition=dict(path='source.html',raw_sha256=sha(raw),retrieved_at='2026-09-11T07:00:00+00:00'))
            assertion=dict(assertion_id='assertion-example',original_text=text,start_offset=0,end_offset=len(text),
                language=dict(effective_language='uk',detected_language='uk',confidence=1.0,method='source-language-metadata'),
                source_locator={},source_block_ids=['b1'],semantic_annotations={})
            output=root/'pack'; output.mkdir()
            with patch('build_expanded_pack.OUT',root):
                report=build_part(output,[(doc,[assertion]),
                    (doc|{'document_id':'doc-second'},[assertion|{'assertion_id':'assertion-second'}])],1,1)
            bundle=json.loads((output/'release.json').read_text(encoding='utf-8'))
            self.assertTrue(report['validated'])
            self.assertEqual(bundle['evidence'][0]['original_excerpt'],text)
            self.assertEqual(bundle['facts'][0]['statement'],text)
            self.assertEqual(bundle['evidence'][0]['effective_source_language'],'uk')
            self.assertEqual(len(bundle['catalog']['coverage_profiles']),1)
            scope=bundle['catalog']['scope']
            self.assertIn('read-source-assertions',scope['statements']['en']['in_scope'])
            self.assertTrue(any('verbatim' in item for item in scope['statements']['en']['out_of_scope']))
            self.assertEqual(scope['provenance'][0]['artifact_id'],'expanded-build-source')
            self.assertEqual(len(bundle['graph']['plans'][0]['portions']),2)
            first,second=bundle['graph']['plans'][0]['portions']
            self.assertTrue(set(first['concept_ids']).isdisjoint(second['concept_ids']))
            self.assertTrue(set(first['fact_ids']).isdisjoint(second['fact_ids']))


if __name__=='__main__': unittest.main()
