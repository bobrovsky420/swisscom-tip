from __future__ import annotations

import unittest

from swisstip.core.contracts import (
    ArtifactRef, CatalogEntry, KnowledgeCatalog, LanguagePolicy, LocalizedMetadata,
)
from swisstip.core.contracts import ArtifactRef, KnowledgeCatalog
from swisstip.core.identity import artifact_hash, json_content_hash, seal_artifact, verify_artifact


class ArtifactIdentityTests(unittest.TestCase):
    def policy(self) -> LanguagePolicy:
        return LanguagePolicy(
            identity=ArtifactRef(artifact_id="policy-test", version="1", sha256="0" * 64),
            term_languages=[], source_languages=[], projection_languages=[], routes=[],
        )

    def test_sealing_is_stable_and_not_approval(self) -> None:
        original = self.policy()
        sealed = seal_artifact(original)
        self.assertTrue(verify_artifact(sealed))
        self.assertEqual(sealed, seal_artifact(sealed))
        self.assertEqual(original.identity.sha256, "0" * 64)
        self.assertEqual(sealed.approval_status, "DRAFT")
        self.assertEqual(artifact_hash(original), artifact_hash(sealed))

    def test_content_version_and_dependency_changes_invalidate_hash(self) -> None:
        policy = seal_artifact(self.policy())
        policy.identity = policy.identity.model_copy(update={"version": "2"})
        self.assertFalse(verify_artifact(policy))
        policy = seal_artifact(self.policy())
        policy.projection_languages.append("en")
        self.assertFalse(verify_artifact(policy))

        reference = seal_artifact(self.policy()).identity
        catalog = seal_artifact(KnowledgeCatalog(
            identity=ArtifactRef(artifact_id="catalog-test", version="1", sha256="0" * 64),
            release_id="release-test",
            entries=[CatalogEntry(entry_id="space-test", kind="knowledge_space", labels={
                "en": LocalizedMetadata(label="Test", description="Synthetic fixture.", provenance=[reference])
            })],
            language_policy_ref=reference,
        ))
        catalog.language_policy_ref = reference.model_copy(update={"sha256": "f" * 64})
        self.assertFalse(verify_artifact(catalog))

    def test_json_roundtrip_preserves_hash(self) -> None:
        policy = seal_artifact(self.policy())
        roundtrip = LanguagePolicy.model_validate_json(policy.model_dump_json(indent=2))
        self.assertTrue(verify_artifact(roundtrip))


if __name__ == "__main__":
    unittest.main()


class ExtensionFieldTests(unittest.TestCase):
    """Optional fields added later must not change the hash of earlier artifacts."""

    @staticmethod
    def catalog(**extra):
        ref = ArtifactRef(artifact_id="source", version="1", sha256="a" * 64)
        return KnowledgeCatalog(
            identity=ArtifactRef(artifact_id="catalog", version="1", sha256="0" * 64), release_id="release-a",
            entries=[dict(entry_id="space", kind="knowledge_space",
                          labels={"en": dict(label="Space", description="Synthetic.", provenance=[ref])})],
            language_policy_ref=ref, **extra)

    def test_null_scope_hashes_as_before_the_field_existed(self) -> None:
        sealed = seal_artifact(self.catalog())
        document = sealed.model_dump(mode="json")
        del document["scope"]
        del document["identity"]["sha256"]
        self.assertEqual(sealed.identity.sha256, json_content_hash(document))
        self.assertTrue(verify_artifact(sealed))
        self.assertTrue(verify_artifact(KnowledgeCatalog.model_validate({**document, "identity": sealed.identity.model_dump()})))

    def test_published_scope_is_part_of_the_hash(self) -> None:
        scope = dict(statements={"en": dict(in_scope="Residence permits.", out_of_scope=["Taxes."])},
                     provenance=[ArtifactRef(artifact_id="source", version="1", sha256="a" * 64)])
        with_scope = seal_artifact(self.catalog(scope=scope))
        self.assertTrue(verify_artifact(with_scope))
        self.assertNotEqual(with_scope.identity.sha256, seal_artifact(self.catalog()).identity.sha256)
        with_scope.scope.statements["en"].out_of_scope.append("Fees.")
        self.assertFalse(verify_artifact(with_scope))


if __name__ == "__main__":
    unittest.main()
