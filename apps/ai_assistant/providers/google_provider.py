"""
Google (Gemini) adapter, using the official `google-genai` SDK.

Uses the Interactions API, which is what Google's current model documentation
shows for new code.
"""
import json
import logging

from .base import (
    AIAuthError,
    AIError,
    AIRateLimitError,
    AIResponseError,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProvider):
    default_model = 'gemini-4-argon'

    def _client(self):
        from google import genai

        return genai.Client(api_key=self.api_key)

    def _call(self, **kwargs):
        from google.genai import errors as genai_errors

        try:
            return self._client().interactions.create(**kwargs)
        except genai_errors.ClientError as exc:
            status = getattr(exc, 'code', None) or getattr(exc, 'status_code', None)
            if status in (401, 403):
                raise AIAuthError('Google rejected the API key.') from exc
            if status == 404:
                raise AIError(f'Google does not recognise the model "{self.model}".') from exc
            if status == 429:
                raise AIRateLimitError(
                    'Google is rate limiting this key, or the quota is exhausted.'
                ) from exc
            raise AIError(f'Google rejected the request: {exc}') from exc
        except genai_errors.ServerError as exc:
            raise AIError('Google had a server error. Try again shortly.') from exc
        except genai_errors.APIError as exc:
            raise AIError(f'Google returned an error: {exc}') from exc

    def generate_json(self, *, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        # The Interactions API takes a single `input`, so the house-style rules
        # are prepended to the request rather than sent as a separate system
        # role the way the other two providers accept.
        interaction = self._call(
            model=self.model,
            input=f'{system}\n\n---\n\n{user}',
            response_format={
                'type': 'text',
                'mime_type': 'application/json',
                'schema': schema,
            },
        )

        text = getattr(interaction, 'output_text', '') or ''
        if not text.strip():
            raise AIResponseError('Gemini returned an empty response.')

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIResponseError('Gemini returned something that was not valid JSON.') from exc

        # Reported under a few different names across SDK versions; zeros
        # rather than a guess when it is not there.
        usage = getattr(interaction, 'usage', None) or getattr(interaction, 'usage_metadata', None)
        return payload, {
            'input_tokens': _first_int(usage, 'input_tokens', 'prompt_token_count'),
            'output_tokens': _first_int(usage, 'output_tokens', 'candidates_token_count'),
        }

    def validate(self) -> None:
        self._call(model=self.model, input='ok')


def _first_int(obj, *names: str) -> int:
    for name in names:
        value = getattr(obj, name, None)
        if isinstance(value, int):
            return value
    return 0
