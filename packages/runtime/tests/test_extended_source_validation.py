"""Pure release validation for opt-in source languages; no service invocation."""
import unittest

from swisstip.runtime.fixture import fixture
from swisstip.runtime.release import validate_release
from test_service import reseal


class ExtendedSourceValidationTests(unittest.TestCase):
    def test_v2_evidence_cannot_be_loaded_under_legacy_policy(self):
        bundle, _ = fixture()
        bundle.evidence[0].schema_version = 'evidence-object/v2'
        with self.assertRaisesRegex(ValueError, 'extended_evidence_requires_v4_language_policy'):
            validate_release(reseal(bundle))

    def test_explicit_extended_language_is_validated_against_its_profile(self):
        bundle, _ = fixture()
        bundle.language_policy.platform_catalog = 'tip-language-catalog/v4'
        bundle.language_policy.source_languages.append('uk')
        bundle.catalog.coverage_profiles[0].source_languages.append('uk')
        bundle.evidence[0].schema_version = 'evidence-object/v2'
        bundle.evidence[0].effective_source_language = 'uk'
        bundle.evidence[0].declared_language = ['uk']
        bundle.evidence[0].detected_language = None
        validate_release(reseal(bundle))
        bundle.catalog.coverage_profiles[0].source_languages.remove('uk')
        with self.assertRaisesRegex(ValueError, 'excerpt_outside_profile'):
            validate_release(reseal(bundle))


if __name__ == '__main__':
    unittest.main()
