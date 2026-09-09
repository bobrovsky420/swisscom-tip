"""DeepSeek JSON chat adapter for locally validated concept extraction/review."""

from swisstip.core.deepseek import DeepSeekClient, DeepSeekError
from swisstip.ingestion.concepts import ModelCompletion, SemanticModelError


class DeepSeekProviderError(SemanticModelError):
    def __init__(self, failure: DeepSeekError):
        super().__init__(str(failure))
        self.failure = failure


class DeepSeekSemanticModelProvider:
    def __init__(self, *, max_tokens, temperature, **kwargs):
        self._client = DeepSeekClient(**kwargs)
        self._max_tokens, self._temperature = max_tokens, temperature

    def generate_structured(self, *, system_prompt, user_prompt, response_schema):
        try:
            result = self._client.complete(system_prompt=system_prompt, user_prompt=user_prompt,
                                           response_schema=dict(response_schema), max_tokens=self._max_tokens,
                                           temperature=self._temperature)
        except DeepSeekError as exc:
            raise DeepSeekProviderError(exc) from exc
        return ModelCompletion(content=result.content, provider="deepseek", model=result.model,
                               requested_model=result.model, observed_model=result.model,
                               prompt_tokens=result.prompt_tokens, output_tokens=result.output_tokens,
                               request_id=result.request_id)
