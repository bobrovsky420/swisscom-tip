from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

APP_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages" / "ingestion" / "src"))

from swisstip.builder.concept_cli import (  # noqa: E402
    PageInputDiscoveryError,
    main,
    resolve_page_inputs,
)
from swisstip.ingestion.concepts import (  # noqa: E402
    ModelCompletion,
    SemanticModelError,
)


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Mapping[str, object],
    ) -> ModelCompletion:
        self.calls += 1
        request = json.loads(user_prompt)
        if "untrusted_review" in request:
            return ModelCompletion(
                content=json.dumps({"verdicts": [
                    {"review_id": item["review_id"], "decision": "supported",
                     "issue": "none", "reason": "Supported by the test evidence."}
                    for item in request["untrusted_review"]["proposals"]
                ]}),
                provider="publicai",
                model="swiss-ai/Apertus-8B-Instruct-2509",
                requested_model="swiss-ai/Apertus-8B-Instruct-2509:publicai",
                observed_model="swiss-ai/Apertus-8B-Instruct-2509",
                request_id=f"request-{self.calls}",
            )
        payload = {
            "concepts": [
                {
                    "preferred_label": "Residence permit",
                    "alternative_labels": [],
                    "concept_type": "DOCUMENT",
                    "granularity": "ANSWERABLE",
                    "description": "A required residence document.",
                    "scope": "Residents",
                    "user_questions": ["Do I need a permit?"],
                    "confidence": 0.9,
                    "evidence": [
                        {
                            "section_id": "section-0001",
                            "quote": "A residence permit is required.",
                        }
                    ],
                    "relations": [],
                }
            ]
        }
        page = json.loads(user_prompt)["untrusted_page"]
        if "evidence_spans" in page:
            span = next(s for s in page["evidence_spans"]
                        if "A residence permit is required." in s["text"])
            payload["concepts"][0]["evidence"] = [{"evidence_id": span["evidence_id"]}]
            if "primary_section_id" in response_schema["properties"]["concepts"]["items"]["properties"]:
                payload["concepts"][0]["primary_section_id"] = span["section_id"]
        return ModelCompletion(
            content=json.dumps(payload),
            provider="publicai",
            model="swiss-ai/Apertus-8B-Instruct-2509",
            requested_model="swiss-ai/Apertus-8B-Instruct-2509:publicai",
            observed_model="swiss-ai/Apertus-8B-Instruct-2509",
            request_id=f"request-{self.calls}",
        )


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Mapping[str, object],
    ) -> ModelCompletion:
        self.calls += 1
        raise SemanticModelError("Hugging Face router returned HTTP 504")


class ConceptCliTests(unittest.TestCase):
    def test_custom_prompts_are_sent_and_saved_in_reports_and_dry_run(self):
        directory = self.config_path.parent
        extraction = directory / "extract.md"
        review = directory / "review.md"
        extraction.write_text("Custom extraction instructions.\n", encoding="utf-8")
        review.write_text("Custom review instructions.\n", encoding="utf-8")
        document = self.config_path.read_text(encoding="utf-8").replace(
            "[extraction]", '[extraction]\nextraction_prompt_file = "extract.md"\nreview_prompt_file = "review.md"')
        self.config_path.write_text(document, encoding="utf-8")
        page = directory / "page.md"
        page.write_text("# Requirements\nA residence permit is required.\n", encoding="utf-8")
        provider = FakeProvider()
        with (patch("swisstip.builder.concept_cli.create_semantic_model_provider", return_value=provider),
              patch.object(provider, "generate_structured", wraps=provider.generate_structured) as generate,
              redirect_stdout(io.StringIO()) as stdout):
            self.assertEqual(main([str(page), "--config", str(self.config_path)]), 0)
        output = json.loads(stdout.getvalue())
        report = output["reports"][0]
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual([call.kwargs["system_prompt"] for call in generate.call_args_list],
                         [extraction.read_text(), review.read_text()])
        effective = report["effective_prompts"]
        self.assertEqual(effective["extraction"]["text"], extraction.read_text())
        self.assertEqual(effective["review"]["text"], review.read_text())
        self.assertEqual(output["effective_config"]["extraction"]["extraction_prompt_file"], str(extraction.resolve()))
        with (patch("swisstip.builder.concept_cli.create_semantic_model_provider") as factory,
              redirect_stdout(io.StringIO()) as stdout):
            self.assertEqual(main([str(page), "--config", str(self.config_path), "--dry-run"]), 0)
        factory.assert_not_called()
        self.assertEqual(json.loads(stdout.getvalue())["effective_prompts"], effective)

    def test_missing_override_fails_before_provider_creation(self):
        document = self.config_path.read_text(encoding="utf-8").replace(
            "[extraction]", '[extraction]\nextraction_prompt_file = "missing.md"')
        self.config_path.write_text(document, encoding="utf-8")
        with (patch("swisstip.builder.concept_cli.create_semantic_model_provider") as factory,
              redirect_stderr(io.StringIO()) as stderr):
            self.assertEqual(main(["unused.md", "--config", str(self.config_path)]), 2)
        factory.assert_not_called()
        self.assertIn("cannot read UTF-8 prompt file", stderr.getvalue())

    def setUp(self) -> None:
        self.config_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.config_directory.cleanup)
        self.config_path = Path(self.config_directory.name) / "semantic-models.toml"
        document = (REPOSITORY_ROOT / "config" / "semantic-models.toml").read_text(encoding="utf-8")
        # Fake completions identify HF Apertus 8B, regardless of the operator's
        # current profile. Preserve the real file and exercise the normal loader.
        document = re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "apertus_8b"', document)
        self.config_path.write_text(document, encoding="utf-8")

    def test_empty_input_is_rejected_in_cli_and_direct_resolution(self) -> None:
        stderr = io.StringIO()
        with (
            patch(
                "swisstip.builder.concept_cli.create_semantic_model_provider"
            ) as provider_factory,
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main([""])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("input path or wildcard must not be empty", stderr.getvalue())
        provider_factory.assert_not_called()
        with self.assertRaisesRegex(PageInputDiscoveryError, "at least one"):
            resolve_page_inputs([], max_pages=1)

    def test_emits_one_candidate_report_per_explicit_input(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.md"
            second = Path(directory) / "second.txt"
            first.write_text(
                "# Requirements\nA residence permit is required.\n",
                encoding="utf-8",
            )
            second.write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(first),
                        str(second),
                        "--config",
                        str(self.config_path),
                        "--compact",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["schema_version"], "swisstip.concept-proposal-batch/v1")
        self.assertEqual(
            payload["model_config_schema_version"],
            "swisstip.semantic-model-profiles/v1",
        )
        self.assertEqual(payload["active_profile"], "apertus_8b")
        self.assertEqual(payload["report_count"], 2)
        self.assertEqual(len(payload["reports"]), 2)
        self.assertEqual(provider.calls, 4)
        for report in payload["reports"]:
            self.assertEqual(report["provider"], "publicai")
            self.assertEqual(report["model"], "swiss-ai/Apertus-8B-Instruct-2509")
            self.assertEqual(len(report["model_identities"]), 2)
            for identity in report["model_identities"]:
                self.assertEqual(identity["provider"], "publicai")
                self.assertEqual(identity["model"], "swiss-ai/Apertus-8B-Instruct-2509")
                self.assertEqual(
                    identity["requested_model"],
                    "swiss-ai/Apertus-8B-Instruct-2509:publicai",
                )
                self.assertEqual(
                    identity["observed_model"],
                    "swiss-ai/Apertus-8B-Instruct-2509",
                )
            self.assertEqual(
                report["candidates"][0]["validation_state"],
                "CANDIDATE",
            )

    def test_verbose_mode_reports_live_extraction_milestones(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.txt"
            page.write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(page),
                        "--config",
                        str(self.config_path),
                        "--compact",
                        "--verbose",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["report_count"], 1)
        progress = stderr.getvalue()
        self.assertIn("Selected profile=", progress)
        self.assertIn("Discovered 1 supported page(s)", progress)
        self.assertIn("Normalizing page 1/1", progress)
        self.assertIn("Planned 2 model request(s) for this run", progress)
        self.assertIn("Semantic review for chunk 1/1 completed", progress)
        self.assertIn("Model request 1/1 started", progress)
        self.assertIn("Model request 1/1 completed", progress)
        self.assertIn("accepted_candidates=1", progress)
        self.assertIn("Concept extraction completed successfully", progress)

    def test_verbose_mode_identifies_request_active_when_provider_fails(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FailingProvider()
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.txt"
            page.write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(page),
                        "--config",
                        str(self.config_path),
                        "--verbose",
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(provider.calls, 1)
        progress = stderr.getvalue()
        started = progress.index("Model request 1/1 started")
        failed = progress.index("Hugging Face router returned HTTP 504")
        self.assertLess(started, failed)
        self.assertNotIn("Model request 1/1 completed", progress)

    def test_invalid_input_fails_before_provider_is_created(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.pdf"
            page.write_text("not supported", encoding="utf-8")

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider"
                ) as provider_factory,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(page),
                        "--config",
                        str(self.config_path),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("unsupported page extension", stderr.getvalue())
        provider_factory.assert_not_called()

    def test_run_request_budget_fails_before_any_model_call(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.txt"
            second = Path(directory) / "second.txt"
            first.write_text("First useful page.", encoding="utf-8")
            second.write_text("Second useful page.", encoding="utf-8")
            config_path = Path(directory) / "semantic-models.toml"
            config_document = self.config_path.read_text(encoding="utf-8")
            config_document = config_document.replace(
                "max_model_requests_per_page = 12",
                "max_model_requests_per_page = 2",
            ).replace(
                "max_model_requests_per_run = 30",
                "max_model_requests_per_run = 2",
            )
            config_path.write_text(config_document, encoding="utf-8")

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(Path(directory) / "*.txt"),
                        "--config",
                        str(config_path),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("run requires 4 model requests", stderr.getvalue())
        self.assertEqual(provider.calls, 0)

    def test_page_and_total_character_budgets_fail_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.txt"
            second_page = Path(directory) / "second.txt"
            page.write_text("A useful page with enough text.", encoding="utf-8")
            second_page.write_text(
                "A second useful page with enough text.",
                encoding="utf-8",
            )
            original_config = self.config_path.read_text(encoding="utf-8")

            cases = {
                "page limit": (
                    original_config.replace("max_pages_per_run = 10", "max_pages_per_run = 1"),
                    [str(Path(directory))],
                    "configured page limit of 1",
                ),
                "character limit": (
                    original_config.replace(
                        "max_total_input_characters = 120000",
                        "max_total_input_characters = 10",
                    ),
                    [str(Path(directory) / "*.txt")],
                    "normalized input characters",
                ),
            }
            for name, (config_document, page_arguments, expected_error) in cases.items():
                with self.subTest(name=name):
                    config_path = Path(directory) / f"{name.replace(' ', '-')}.toml"
                    config_path.write_text(config_document, encoding="utf-8")
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with (
                        patch(
                            "swisstip.builder.concept_cli.create_semantic_model_provider"
                        ) as provider_factory,
                        redirect_stdout(stdout),
                        redirect_stderr(stderr),
                    ):
                        exit_code = main(
                            [*page_arguments, "--config", str(config_path)]
                        )

                    self.assertEqual(exit_code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn(expected_error, stderr.getvalue())
                    provider_factory.assert_not_called()

    def test_directory_input_recurses_and_filters_supported_extensions(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            input_directory = Path(directory) / "pages"
            supported_pages = [
                input_directory / "01.HTML",
                input_directory / "02.HtM",
                input_directory / "nested" / "03.TXT",
                input_directory / "nested" / "04.Md",
                input_directory / "nested" / "deeper" / "05.MARKDOWN",
            ]
            for page in supported_pages:
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text(
                    "A residence permit is required.\n",
                    encoding="utf-8",
                )
            (input_directory / "ignored.pdf").write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )
            (input_directory / "nested" / "ignored.json").write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(input_directory),
                        "--config",
                        str(self.config_path),
                        "--compact",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        expected_sources = [
            str(path)
            for path in sorted(supported_pages, key=lambda item: str(item).casefold())
        ]
        self.assertEqual(
            [report["source"] for report in payload["reports"]],
            expected_sources,
        )
        self.assertEqual(payload["report_count"], len(supported_pages))
        self.assertEqual(provider.calls, 2 * len(supported_pages))

    def test_quoted_glob_is_expanded_sorted_and_deduplicated(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            input_directory = Path(directory) / "pages"
            input_directory.mkdir()
            first = input_directory / "a.html"
            last = input_directory / "z.html"
            nested = input_directory / "nested" / "ignored.html"
            nested.parent.mkdir()
            for page in (first, last, nested):
                page.write_text(
                    "<p>A residence permit is required.</p>\n",
                    encoding="utf-8",
                )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(last),
                        str(input_directory / "*.html"),
                        "--config",
                        str(self.config_path),
                        "--compact",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            [report["source"] for report in payload["reports"]],
            [str(first), str(last)],
        )
        self.assertEqual(payload["report_count"], 2)
        self.assertEqual(provider.calls, 4)

    def test_wildcard_syntax_precedes_an_existing_magic_literal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            literal = root / "page[1].html"
            pattern_match = root / "page1.html"
            for page in (literal, pattern_match):
                page.write_text(
                    "<p>A residence permit is required.</p>\n",
                    encoding="utf-8",
                )

            unescaped = resolve_page_inputs([literal], max_pages=10)
            escaped = resolve_page_inputs(
                [root / "page[[]1].html"],
                max_pages=10,
            )

        self.assertEqual(unescaped, [pattern_match])
        self.assertEqual(escaped, [literal])

    def test_recursive_glob_expands_nested_pages(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            input_directory = Path(directory) / "pages"
            pages = [
                input_directory / "01.html",
                input_directory / "nested" / "02.html",
                input_directory / "nested" / "deeper" / "03.html",
            ]
            for page in pages:
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text(
                    "<p>A residence permit is required.</p>\n",
                    encoding="utf-8",
                )
            (input_directory / "nested" / "ignored.txt").write_text(
                "A residence permit is required.\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(input_directory / "**" / "*.html"),
                        "--config",
                        str(self.config_path),
                        "--compact",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            [report["source"] for report in payload["reports"]],
            [str(page) for page in pages],
        )
        self.assertEqual(payload["report_count"], len(pages))
        self.assertEqual(provider.calls, 2 * len(pages))

    def test_directory_symlinks_are_not_traversed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_directory = root / "pages"
            linked_directory = input_directory / "linked"
            linked_directory.mkdir(parents=True)
            visible = input_directory / "visible.html"
            hidden = linked_directory / "hidden.html"
            visible.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )
            hidden.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )
            real_is_symlink = Path.is_symlink

            def is_symlink(path: Path) -> bool:
                return path == linked_directory or real_is_symlink(path)

            inputs = {
                "directory": str(input_directory),
                "recursive glob": str(input_directory / "**" / "*.html"),
            }
            for name, page_input in inputs.items():
                with self.subTest(name=name):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    provider = FakeProvider()
                    with (
                        patch.object(
                            Path,
                            "is_symlink",
                            autospec=True,
                            side_effect=is_symlink,
                        ),
                        patch(
                            "swisstip.builder.concept_cli.create_semantic_model_provider",
                            return_value=provider,
                        ),
                        redirect_stdout(stdout),
                        redirect_stderr(stderr),
                    ):
                        exit_code = main(
                            [
                                page_input,
                                "--config",
                                str(self.config_path),
                                "--compact",
                            ]
                        )

                    self.assertEqual(exit_code, 0)
                    self.assertEqual(stderr.getvalue(), "")
                    payload = json.loads(stdout.getvalue())
                    self.assertEqual(payload["report_count"], 1)
                    self.assertEqual(payload["reports"][0]["source"], str(visible))
                    self.assertEqual(provider.calls, 2)

    def test_link_in_explicit_root_path_is_treated_as_deliberate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected_root = root / "selected"
            selected_root.mkdir()
            page = selected_root / "page.html"
            page.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )
            real_is_symlink = Path.is_symlink

            def is_symlink(path: Path) -> bool:
                return path == selected_root or real_is_symlink(path)

            with patch.object(
                Path,
                "is_symlink",
                autospec=True,
                side_effect=is_symlink,
            ):
                directory_result = resolve_page_inputs(
                    [selected_root],
                    max_pages=10,
                )
                glob_result = resolve_page_inputs(
                    [selected_root / "**" / "*.html"],
                    max_pages=10,
                )

        self.assertEqual(directory_result, [page])
        self.assertEqual(glob_result, [page])

    def test_unmatched_glob_and_empty_directory_fail_before_provider_creation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unsupported_directory = root / "unsupported"
            (unsupported_directory / "nested").mkdir(parents=True)
            (unsupported_directory / "nested" / "page.pdf").write_text(
                "not supported",
                encoding="utf-8",
            )
            cases = {
                "unmatched glob": (
                    str(root / "missing-*.html"),
                    "wildcard matched no supported page files",
                ),
                "directory without supported pages": (
                    str(unsupported_directory),
                    "directory tree contains no supported page files",
                ),
            }
            for name, (page_input, expected_error) in cases.items():
                with self.subTest(name=name):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with (
                        patch(
                            "swisstip.builder.concept_cli.create_semantic_model_provider"
                        ) as provider_factory,
                        redirect_stdout(stdout),
                        redirect_stderr(stderr),
                    ):
                        exit_code = main(
                            [
                                page_input,
                                "--config",
                                str(self.config_path),
                            ]
                        )

                    self.assertEqual(exit_code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn(expected_error, stderr.getvalue())
                    provider_factory.assert_not_called()

    def test_discovery_budget_and_hidden_recursive_glob_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            visible = root / "visible.html"
            hidden = root / ".hidden" / "hidden.html"
            visible.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )
            hidden.parent.mkdir()
            hidden.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )

            resolved = resolve_page_inputs(
                [root / "**" / "*.html"],
                max_pages=10,
            )

            self.assertEqual(resolved, [visible])
            with self.assertRaisesRegex(
                PageInputDiscoveryError,
                "filesystem entries",
            ):
                resolve_page_inputs(
                    [root],
                    max_pages=10,
                    max_discovery_entries=2,
                )

    def test_page_limit_counts_canonically_deduplicated_expanded_pages(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_directory = root / "pages"
            nested_directory = input_directory / "nested"
            nested_directory.mkdir(parents=True)
            page = input_directory / "page.html"
            page.write_text(
                "<p>A residence permit is required.</p>\n",
                encoding="utf-8",
            )
            lexical_alias = nested_directory / ".." / page.name
            config_path = root / "semantic-models.toml"
            config_document = self.config_path.read_text(encoding="utf-8")
            config_path.write_text(
                config_document.replace(
                    "max_pages_per_run = 10",
                    "max_pages_per_run = 1",
                ),
                encoding="utf-8",
            )

            with (
                patch(
                    "swisstip.builder.concept_cli.create_semantic_model_provider",
                    return_value=provider,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        str(lexical_alias),
                        str(input_directory),
                        str(input_directory / "*.html"),
                        str(page),
                        "--config",
                        str(config_path),
                        "--compact",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["report_count"], 1)
        self.assertEqual(Path(payload["reports"][0]["source"]).resolve(), page.resolve())
        self.assertEqual(provider.calls, 2)


if __name__ == "__main__":
    unittest.main()
