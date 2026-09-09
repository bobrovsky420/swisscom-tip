"""Local response checkpoints and bounded hosted-provider retries for extraction runs.

Checkpoints contain model output and usage, never credentials. They are an
internal trusted cache, not an import format or authoritative reviewed data.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from swisstip.ingestion.concepts import ModelCompletion, NormalizedPage, SemanticModelError, SemanticModelProvider
from swisstip.ingestion.concept_review import REVIEW_SYSTEM_PROMPT, parse_verdicts, review_schema
from swisstip.core.deepseek import DeepSeekHTTPError, DeepSeekTransportError, DeepSeekIncompleteCompletionError
from .deepseek_provider import DeepSeekProviderError
from .groq_provider import GroqHTTPError, GroqTransportError, GroqIncompleteCompletionError
from .huggingface_provider import (
    HuggingFaceHTTPError, HuggingFaceTransportError, HuggingFaceIncompleteCompletionError,
    is_approved_model_identity,
)
from .model_profiles import SemanticModelConfig


# v1 discarded the observed HF model. Keep old files, but never reuse them.
CHECKPOINT_VERSION = "swisstip.model-response-checkpoint/v2"
TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}
WAIT_PROGRESS_SECONDS = 15.0


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


class RecoverableProvider:
    def __init__(self, provider: SemanticModelProvider, config: SemanticModelConfig, *,
                 checkpoint_dir: Path | None = None, fresh: bool = False,
                 progress: Callable[[str], None] = lambda message: None,
                 sleep: Callable[[float], None] = time.sleep,
                 now: Callable[[], datetime] = lambda: datetime.now(UTC),
                 review_system_prompt: str | None = REVIEW_SYSTEM_PROMPT) -> None:
        self.provider, self.config = provider, config
        self.review_system_prompt = review_system_prompt
        self.directory = Path(checkpoint_dir).resolve() if checkpoint_dir is not None else None
        self.fresh, self.progress, self.sleep = fresh, progress, sleep
        self.now = now
        self.attempts = self.retry_attempts = self.hits = self.page_attempts = 0
        self.new_completions: list[ModelCompletion] = []
        self.incomplete_completions: list[dict[str, object]] = []
        self.review_fallbacks: list[dict[str, object]] = []
        self.context: str | None = None
        self.last_path: Path | None = None
        if self.directory is not None:
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise SemanticModelError("Cannot create model checkpoint directory") from exc
            self.progress(f"Model checkpoints: {self.directory}; reuse={'disabled' if fresh else 'enabled'}")

    def begin_page(self, page: NormalizedPage) -> None:
        self.page_attempts = 0
        self.last_path = None
        # Include the full normalized page as well as its original input hash.
        # Token values and recovery timing do not affect response identity.
        page_data = asdict(page)
        page_data["sections"] = tuple(section.content_dict() for section in page.sections)
        if page.normalization_version == "legacy":
            # Preserve v1-v3 checkpoint identity after adding optional v4 fields.
            page_data.pop("normalization_version", None)
            page_data.pop("source_sha256", None)
        self.context = _digest({
            "version": CHECKPOINT_VERSION, "page": page_data,
            "profile": asdict(self.config.active_profile),
            "generation": asdict(self.config.generation),
            "extraction": {field: getattr(self.config.extraction, field) for field in (
                "prompt_profile", "chunk_content_characters", "chunk_overlap_characters", "max_concepts_per_chunk"
            )},
        })

    def _budget_available(self) -> bool:
        limits = self.config.extraction
        return (self.attempts < limits.max_model_requests_per_run
                and self.page_attempts < limits.max_model_requests_per_page)

    def generate_structured(self, *, system_prompt: str, user_prompt: str,
                            response_schema: Mapping[str, object]) -> ModelCompletion:
        request = {"system_prompt": system_prompt, "user_prompt": user_prompt,
                   "response_schema": dict(response_schema)}
        if self.context is None:
            raise SemanticModelError("Checkpoint provider requires a page context")
        key = _digest({"context": self.context, "request": request})
        self.last_path = None
        path = self.directory / f"{key}.json" if self.directory is not None else None
        review = self._review_payload(request)
        if path is not None and path.exists() and not self.fresh:
            completion = self._read(path, key)
            if completion is not None:
                self.last_path = path
                if review is not None:
                    try:
                        parse_verdicts(completion.content, len(review["proposals"]))
                    except ValueError:
                        self.discard_last_checkpoint()
                        raise
                self.hits += 1
                self.progress(f"Reused model checkpoint {key[:12]}; network_attempts={self.attempts}")
                return completion
        marker = self.directory / f"{key}.split.json" if self.directory is not None else None
        if review is not None and len(review["proposals"]) > 1 and not self.fresh and marker is not None:
            resume_split = False
            try:
                saved = json.loads(marker.read_text(encoding="utf-8"))
                resume_split = saved == {"version": "swisstip.review-split/v1", "key": key}
            except (OSError, ValueError):
                pass
            if resume_split:
                self.progress(f"Resuming smaller review batches for {key[:12]}")
                return self._split_review(request, review, key)
        recovery = self.config.recovery
        for retry in range(recovery.max_retries + 1):
            if not self._budget_available():
                raise SemanticModelError("Model request budget exhausted (includes failed attempts and retries); checkpoints retained")
            self.attempts += 1
            self.page_attempts += 1
            self.retry_attempts += int(retry > 0)
            limits = self.config.extraction
            self.progress(
                f"Provider attempt {self.attempts}/{limits.max_model_requests_per_run} "
                f"(page {self.page_attempts}/{limits.max_model_requests_per_page}, retry {retry}/{recovery.max_retries})"
            )
            try:
                completion = self.provider.generate_structured(**request)
            except (HuggingFaceIncompleteCompletionError, HuggingFaceHTTPError,
                    HuggingFaceTransportError, DeepSeekProviderError, GroqHTTPError,
                    GroqTransportError, GroqIncompleteCompletionError) as exc:
                failure = exc.failure if isinstance(exc, DeepSeekProviderError) else exc
                if isinstance(failure, (HuggingFaceIncompleteCompletionError, DeepSeekIncompleteCompletionError, GroqIncompleteCompletionError)):
                    self.incomplete_completions.append(failure.diagnostics)
                    self.progress(f"Rejected incomplete completion: {json.dumps(failure.diagnostics, ensure_ascii=True)}; "
                                  "partial content not checkpointed; identical request not retried")
                    if (failure.diagnostics["finish_reason"] == "length" and review is not None
                            and len(review["proposals"]) > 1):
                        if marker is not None:
                            self._write_document(marker, {"version": "swisstip.review-split/v1", "key": key})
                        return self._split_review(request, review, key)
                    raise
                if not isinstance(failure, (HuggingFaceHTTPError, HuggingFaceTransportError,
                                            DeepSeekHTTPError, DeepSeekTransportError, GroqHTTPError, GroqTransportError)):
                    raise
                transient = isinstance(failure, (HuggingFaceTransportError, DeepSeekTransportError, GroqTransportError)) or failure.status_code in TRANSIENT_HTTP
                delay = self._retry_delay(failure, retry) if transient else None
                if not transient or retry == recovery.max_retries or not self._budget_available():
                    self.progress("Provider failure; no further retry permitted; successful checkpoints retained")
                    raise
                if delay is None:
                    self.progress("Provider Retry-After exceeds max_retry_after_seconds; stopping with checkpoints retained")
                    raise
                self.progress(f"Transient provider failure ({exc}); retrying in {delay:g}s; "
                              f"run_attempts_remaining={limits.max_model_requests_per_run - self.attempts}")
                self._wait_for_retry(delay)
                continue
            self._validate_model_identity(completion)
            self.new_completions.append(completion)
            if review is not None:
                # Invalid schemas/verdicts are fatal, not another fallback trigger.
                parse_verdicts(completion.content, len(review["proposals"]))
            if path is not None:
                self._write(path, key, completion)
                self.last_path = path
                self.progress(f"Saved model checkpoint {key[:12]}")
            return completion
        raise SemanticModelError("Invalid model retry configuration")

    def _review_payload(self, request: dict[str, object]) -> dict[str, object] | None:
        if request["system_prompt"] != self.review_system_prompt:
            return None
        try:
            review = json.loads(request["user_prompt"])["untrusted_review"]
            proposals = review["proposals"]
            if not isinstance(proposals, list) or not proposals:
                return None
            if request["response_schema"] != review_schema(len(proposals)):
                return None
            if any(type(p["review_id"]) is not int or p["review_id"] != index
                   for index, p in enumerate(proposals, 1)):
                return None
            return review
        except (ValueError, TypeError, KeyError):
            return None

    def _split_review(self, request: dict[str, object], review: dict[str, object], key: str) -> ModelCompletion:
        proposals = review["proposals"]
        size = min(self.config.recovery.review_fallback_batch_size, max(1, len(proposals) // 2))
        self.progress(f"Review fallback {key[:12]}: {len(proposals)} proposals in batches of at most {size}; existing budgets apply")
        event = {"request_key": key[:12], "proposal_count": len(proposals), "batch_size": size,
                 "status": "incomplete", "child_request_ids": [], "child_model_identities": []}
        self.review_fallbacks.append(event)
        completions = []
        verdicts = []
        for start in range(0, len(proposals), size):
            batch = proposals[start:start + size]
            ids = {p["candidate"]["primary_section_id"] for p in batch}
            child = {**review,
                     "primary_sections": [s for s in review["primary_sections"] if s["section_id"] in ids],
                     "proposals": [{**p, "review_id": index} for index, p in enumerate(batch, 1)]}
            completion = self.generate_structured(
                system_prompt=request["system_prompt"],
                user_prompt=json.dumps({"untrusted_review": child}, ensure_ascii=False, separators=(",", ":")),
                response_schema=review_schema(len(batch)),
            )
            completions.append(completion)
            event["child_model_identities"].append({
                "provider": completion.provider, "model": completion.model,
                "requested_model": completion.requested_model,
                "observed_model": completion.observed_model, "request_id": completion.request_id,
            })
            if completion.request_id is not None:
                event["child_request_ids"].append(completion.request_id)
            for verdict in parse_verdicts(completion.content, len(batch)):
                verdicts.append({**verdict, "review_id": batch[verdict["review_id"] - 1]["review_id"]})
        first = completions[0]
        if any((c.provider, c.model, c.requested_model) !=
               (first.provider, first.model, first.requested_model) for c in completions):
            raise SemanticModelError("Inconsistent model identity across smaller review batches")
        content = json.dumps({"verdicts": verdicts}, ensure_ascii=False)
        parse_verdicts(content, len(proposals))
        def total(field):
            values = [getattr(c, field) for c in completions]
            return None if any(v is None for v in values) else sum(values)
        self.last_path = None  # No synthetic provider response is checkpointed.
        event["status"] = "complete"
        self.progress(f"Review fallback {key[:12]} completed: {len(verdicts)} verdicts validated")
        return ModelCompletion(content, first.provider, first.model,
                               prompt_tokens=total("prompt_tokens"), output_tokens=total("output_tokens"),
                               requested_model=first.requested_model,
                               observed_model=(first.observed_model if all(
                                   c.observed_model == first.observed_model for c in completions
                               ) else None))

    def _retry_delay(self, exc: HuggingFaceHTTPError | HuggingFaceTransportError | DeepSeekHTTPError | DeepSeekTransportError | GroqHTTPError | GroqTransportError,
                     retry: int) -> float | None:
        recovery = self.config.recovery
        delay = min(recovery.max_backoff_seconds, recovery.backoff_seconds * 2 ** retry)
        header = getattr(exc, "retry_after", None)
        if header is not None:
            # Quote/escape external header text so it cannot inject log lines.
            displayed = repr(header[:512]) + (" [truncated]" if len(header) > 512 else "")
            self.progress(f"Provider Retry-After={displayed}; "
                          f"max_retry_after_seconds={recovery.max_retry_after_seconds:g}")
            try:
                wait = int(header)
                if wait < 0:
                    raise ValueError("negative delay")
            except (ValueError, TypeError):
                try:
                    date = parsedate_to_datetime(header)
                    wait = max(0.0, (date - self.now()).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    self.progress(f"Invalid Retry-After; using ordinary backoff of {delay:g}s")
                    return delay
            if wait > recovery.max_retry_after_seconds:
                self.progress(f"Provider requested wait exceeds {recovery.max_retry_after_seconds:g}s")
                return None
            self.progress(f"Provider requested wait={wait:g}s; ordinary_backoff={delay:g}s")
            delay = max(delay, wait)
        return delay

    def _wait_for_retry(self, delay: float) -> None:
        remaining = delay
        while remaining > 0:
            interval = min(WAIT_PROGRESS_SECONDS, remaining)
            self.sleep(interval)
            remaining = max(0.0, remaining - interval)
            self.progress(f"Retry wait: {delay - remaining:g}/{delay:g}s elapsed; "
                          f"{remaining:g}s remaining; no new provider attempt yet")

    def _validate_model_identity(self, completion: ModelCompletion) -> None:
        profile = self.config.active_profile
        provider = profile.provider if profile.adapter == "huggingface" else profile.adapter
        requested = f"{profile.model}:{provider}" if profile.adapter == "huggingface" else profile.model
        if (completion.provider != provider or completion.model != profile.model
                or completion.requested_model != requested):
            raise SemanticModelError("Completion model identity does not match the selected profile")
        if profile.adapter == "huggingface":
            approved = is_approved_model_identity(provider, profile.model, completion.observed_model)
        else:
            approved = completion.observed_model == profile.model
        if not approved:
            raise SemanticModelError("Completion has an unverifiable observed model identity")

    def _read(self, path: Path, key: str) -> ModelCompletion | None:
        try:
            if path.stat().st_size > 2_000_000:
                raise ValueError("oversized checkpoint")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (payload["version"] != CHECKPOINT_VERSION or payload["key"] != key
                    or payload["completion_hash"] != _digest(payload["completion"])):
                raise ValueError("checkpoint identity/integrity mismatch")
            completion = ModelCompletion(**payload["completion"])
            if not all(isinstance(getattr(completion, f), str) and getattr(completion, f)
                       for f in ("content", "provider", "model")):
                raise ValueError("invalid completion")
            for field in ("prompt_tokens", "output_tokens"):
                value = getattr(completion, field)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("invalid usage")
            if completion.request_id is not None and not isinstance(completion.request_id, str):
                raise ValueError("invalid request ID")
            # Integrity alone cannot establish attribution. Apply today's policy
            # to every cache hit, including the configured provider and model.
            self._validate_model_identity(completion)
            return completion
        except (OSError, ValueError, KeyError, TypeError, SemanticModelError):
            self.progress(f"Ignoring unreadable or invalid checkpoint {key[:12]}")
            return None

    def _write(self, path: Path, key: str, completion: ModelCompletion) -> None:
        data = asdict(completion)
        self._write_document(path, {"version": CHECKPOINT_VERSION, "key": key, "completion": data,
                                    "completion_hash": _digest(data)})

    def _write_document(self, path: Path, payload: dict[str, object]) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=".checkpoint-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            raise SemanticModelError("Cannot save model checkpoint; stopping to avoid losing further paid work") from exc
        finally:
            if temporary is not None and temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass  # Preserve the original write failure; .tmp files are never reused.

    def discard_last_checkpoint(self) -> None:
        """Do not perpetually reuse a completion rejected by structural validation."""
        if self.last_path is not None:
            try:
                self.last_path.unlink(missing_ok=True)
                self.progress("Removed structurally invalid model checkpoint; earlier checkpoints retained")
            except OSError as exc:
                raise SemanticModelError("Cannot remove invalid model checkpoint") from exc

    def statistics(self) -> dict[str, object]:
        def tokens(field: str) -> int | None:
            values = [getattr(c, field) for c in self.new_completions]
            return None if any(v is None for v in values) else sum(values)
        return {
            "network_attempts": self.attempts, "retry_attempts": self.retry_attempts,
            "checkpoint_hits": self.hits, "fresh_inference": self.fresh,
            "new_completion_prompt_tokens": tokens("prompt_tokens"),
            "new_completion_output_tokens": tokens("output_tokens"),
            "incomplete_completions": self.incomplete_completions,
            "review_fallbacks": self.review_fallbacks,
            "usage_note": "New completion usage excludes cached responses; failed-attempt billing is unknown. Report usage includes reused completions.",
        }
