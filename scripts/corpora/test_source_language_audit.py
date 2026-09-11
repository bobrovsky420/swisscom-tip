import unittest

from audit_source_languages import normalize, scan


class LanguageAuditTests(unittest.TestCase):
    def test_published_languages_are_candidates_not_invented_translations(self):
        result = scan(b'<html lang="de"><head><link rel="alternate" hreflang="fr" href="/fr/permis"/>'
                      b'</head><body><a href="/de/aufenthalt">DE</a></body></html>',
                      'https://example.gov/de/aufenthalt', ['example.gov'])
        self.assertEqual({x['advertised_language'] for x in result['language_links']}, {'de', 'fr'})
        self.assertEqual(result['declared_language'], 'de')

    def test_federal_json_translation_slugs_are_read_without_executing_scripts(self):
        result = scan(b'<html><script id="__NUXT_DATA__" type="application/json">'
                      b'[{"lang":1,"slug":2},"fr","permis-sejour"]</script></html>',
                      'https://example.gov/de/aufenthalt', ['example.gov'])
        self.assertEqual(result['language_links'][0]['url'], 'https://example.gov/fr/permis-sejour')

    def test_generic_labour_office_does_not_imply_every_descendant_is_in_scope(self):
        result = scan(b'<html><title>Office of work</title><a href="/government/economy/office/climate">Climate</a>'
                      b'<a href="/government/economy/office/work-permits">Work permits</a></html>',
                      'https://example.gov/government/economy/office', ['example.gov'])
        self.assertEqual(len(result['topic_links']), 1)
        self.assertEqual(len(result['deferred_links']), 1)

    def test_valais_language_action_normalizes_to_public_content_url(self):
        self.assertEqual(normalize('https://www.vs.ch/c/portal/update_language?redirect=%2Fweb%2Fspm&languageId=fr_FR'),
                         'https://www.vs.ch/fr/web/spm')
        self.assertEqual(normalize('https://example.gov/../it'), 'https://example.gov/it')

    def test_published_unicode_and_space_urls_are_encoded_once(self):
        url = 'https://example.gov/Merkblatt f\u00fcr Kinder.pdf'
        expected = 'https://example.gov/Merkblatt%20f%C3%BCr%20Kinder.pdf'
        self.assertEqual(normalize(url), expected)
        self.assertEqual(normalize(expected), expected)

    def test_recursive_plone_entity_encoding_does_not_create_an_infinite_frontier(self):
        url='https://www.bern.ch/migration/@@news_portlet_listing?portlet=news&amp;amp;amp;manager=plone.rightcolumn'
        self.assertEqual(normalize(url),'https://www.bern.ch/migration/@@news_portlet_listing?portlet=news&manager=plone.rightcolumn')

    def test_anonymous_form_sessions_resolve_to_the_published_entry_point(self):
        url='https://eforms.sh.ch:443/migrationsamt_passbuero/start.do?txid=abc&vid=def&wfjs_orig_req=%2Fstart.do%3Fgeneralid%3DFNZ_EU'
        self.assertEqual(normalize(url),'https://eforms.sh.ch/migrationsamt_passbuero/start.do?generalid=FNZ_EU')

    def test_published_language_roots_do_not_require_an_english_language_name(self):
        result=scan('<a role="menuitem" href="/ja">こんにちは</a>'.encode(), 'https://www.hallo-baselland.ch/', ['www.hallo-baselland.ch'])
        self.assertEqual(result['language_links'][0]['advertised_language'],'ja')


if __name__ == '__main__':
    unittest.main()
