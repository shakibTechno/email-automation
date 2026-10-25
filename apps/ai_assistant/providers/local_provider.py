"""
Self-hosted model server adapter.

Covers llama.cpp's `llama-server` and Ollama, which both expose an
OpenAI-compatible `/v1/chat/completions`. Uses the `openai` SDK as a plain
HTTP client pointed at the configured address — not as a route to OpenAI, and
not as a compatibility shim for a hosted provider.

Deliberately uses Chat Completions rather than the Responses API: these servers
implement the former and not the latter, which is why this cannot simply be the
OpenAI adapter with a different base URL.
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


class LocalProvider(LLMProvider):
    # Self-hosted servers run whatever was loaded at startup, so there is no
    # sensible default name — it is discovered from the server instead.
    default_model = ''

    # Generous: a local model reasons before it answers, and both halves come
    # out of this budget. Too small and the whole allowance is spent thinking,
    # leaving empty content.
    max_tokens = 16000

    # These are often large models on modest hardware; a full page can take
    # minutes. The SDK's 10-minute default is not always enough.
    timeout_seconds = 900

    def __init__(self, api_key: str, model: str = '', base_url: str = ''):
        super().__init__(api_key=api_key, model=model)
        self.base_url = (base_url or '').rstrip('/')

    def _client(self):
        import openai

        if not self.base_url:
            raise AIError('No server address configured for the local provider.')

        return openai.OpenAI(
            # These servers are usually unauthenticated; the SDK still insists
            # on a non-empty key, and the server ignores whatever is sent.
            api_key=self.api_key or 'not-required',
            base_url=f'{self.base_url}/v1',
            timeout=self.timeout_seconds,
            max_retries=1,
        )

    def _resolve_model(self, client) -> str:
        """
        Use the configured model, or whatever the server has loaded.

        A self-hosted server usually serves exactly one model, so making the
        user copy its filename into settings is friction for no benefit.
        """
        if self.model:
            return self.model
        try:
            listed = client.models.list()
            if listed.data:
                return listed.data[0].id
        except Exception as exc:
            raise AIError(
                f'Could not reach the model server at {self.base_url}. '
                'Check the address and that the server is running.'
            ) from exc
        raise AIError('The model server reported no loaded models.')

    def _call(self, *, messages, response_format=None, max_tokens=None):
        import openai

        client = self._client()
        model = self._resolve_model(client)
        self.model = model

        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                **({'response_format': response_format} if response_format else {}),
            )
        except openai.AuthenticationError as exc:
            raise AIAuthError('The model server rejected the credentials.') from exc
        except openai.NotFoundError as exc:
            raise AIError(
                f'The server has no model named "{model}". '
                'Leave the model blank to use whatever it has loaded.'
            ) from exc
        except openai.RateLimitError as exc:
            raise AIRateLimitError('The model server is busy. Try again shortly.') from exc
        except openai.APITimeoutError as exc:
            raise AIError(
                'The model server took too long to respond. A large model on '
                'modest hardware can exceed the time limit for a whole page.'
            ) from exc
        except openai.APIConnectionError as exc:
            raise AIError(
                f'Could not reach the model server at {self.base_url}. '
                'Check the address and that the server is running.'
            ) from exc
        except openai.APIStatusError as exc:
            raise AIError(f'The model server returned an error: {exc}') from exc

    def generate_json(self, *, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        response = self._call(
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'landing_page',
                    'strict': True,
                    'schema': schema,
                },
            },
        )

        choice = response.choices[0]
        text = (choice.message.content or '').strip()

        if not text:
            # These models think into a separate field first. An empty answer
            # with a length stop almost always means the budget went on
            # reasoning rather than on the page.
            if choice.finish_reason == 'length':
                raise AIResponseError(
                    'The model ran out of room before writing the page — it spent '
                    'the budget reasoning. Try a simpler description.'
                )
            raise AIResponseError('The model server returned an empty response.')

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIResponseError(
                'The model server returned something that was not valid JSON.'
            ) from exc

        usage = getattr(response, 'usage', None)
        return payload, {
            'input_tokens': getattr(usage, 'prompt_tokens', 0) or 0,
            'output_tokens': getattr(usage, 'completion_tokens', 0) or 0,
        }

    def validate(self) -> None:
        # Listing models proves the address is right, the server is up, and a
        # model is loaded — without waiting on a generation.
        client = self._client()
        model = self._resolve_model(client)
        logger.info(f'Local model server at {self.base_url} is serving {model}')
