"""
OpenAI adapter, using the official `openai` SDK.

Uses the Responses API, which is what OpenAI's current model documentation
directs new code to (not Chat Completions).
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


class OpenAIProvider(LLMProvider):
    # OpenAI's models page names this as the place to start for complex
    # reasoning work. Overridable per organization; cheaper siblings in the
    # same family (gpt-6.1-sol, gpt-6-luna) drop straight in.
    default_model = 'gpt-6-astra'

    def _client(self):
        import openai

        return openai.OpenAI(api_key=self.api_key)

    def _call(self, **kwargs):
        import openai

        try:
            return self._client().responses.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise AIAuthError('OpenAI rejected the API key.') from exc
        except openai.PermissionDeniedError as exc:
            raise AIAuthError('This OpenAI key is not allowed to use that model.') from exc
        except openai.NotFoundError as exc:
            raise AIError(f'OpenAI does not recognise the model "{self.model}".') from exc
        except openai.RateLimitError as exc:
            raise AIRateLimitError(
                'OpenAI is rate limiting this key, or the account is out of quota.'
            ) from exc
        except openai.APIConnectionError as exc:
            raise AIError('Could not reach OpenAI. Check network access.') from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise AIError('OpenAI had a server error. Try again shortly.') from exc
            raise AIError(f'OpenAI rejected the request: {exc}') from exc

    def generate_json(self, *, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        response = self._call(
            model=self.model,
            input=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            text={
                'format': {
                    'type': 'json_schema',
                    'name': 'landing_page',
                    'schema': schema,
                    'strict': True,
                },
            },
        )

        text = getattr(response, 'output_text', '') or ''
        if not text.strip():
            raise AIResponseError('OpenAI returned an empty response.')

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIResponseError('OpenAI returned something that was not valid JSON.') from exc

        usage = getattr(response, 'usage', None)
        return payload, {
            'input_tokens': getattr(usage, 'input_tokens', 0) or 0,
            'output_tokens': getattr(usage, 'output_tokens', 0) or 0,
        }

    def validate(self) -> None:
        self._call(
            model=self.model,
            input='ok',
            max_output_tokens=16,
        )
