"""
Anthropic (Claude) adapter, using the official `anthropic` SDK.
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


class AnthropicProvider(LLMProvider):
    default_model = 'claude-opus-5-5'

    # A full landing page is a lot of markup; leave room rather than risk a
    # draft that stops mid-section.
    max_tokens = 32000

    def _client(self):
        import anthropic

        return anthropic.Anthropic(api_key=self.api_key)

    def generate_json(self, *, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        import anthropic

        client = self._client()
        try:
            # Streaming because `max_tokens` is large and a non-streaming
            # request at that size risks an HTTP timeout. `cache_control` on
            # the system prompt matters here: it is the same several-KB block
            # of house style on every generation, so it should be read from
            # cache rather than re-billed each time.
            with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking={'type': 'adaptive'},
                system=[{
                    'type': 'text',
                    'text': system,
                    'cache_control': {'type': 'ephemeral'},
                }],
                output_config={
                    'format': {
                        'type': 'json_schema',
                        'schema': schema,
                    },
                },
                messages=[{'role': 'user', 'content': user}],
            ) as stream:
                message = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise AIAuthError('Anthropic rejected the API key.') from exc
        except anthropic.PermissionDeniedError as exc:
            raise AIAuthError('This Anthropic key is not allowed to use that model.') from exc
        except anthropic.NotFoundError as exc:
            raise AIError(f'Anthropic does not recognise the model "{self.model}".') from exc
        except anthropic.RateLimitError as exc:
            raise AIRateLimitError(
                'Anthropic is rate limiting this key. Try again in a moment.'
            ) from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise AIError('Anthropic had a server error. Try again shortly.') from exc
            raise AIError(f'Anthropic rejected the request: {exc.message}') from exc
        except anthropic.APIConnectionError as exc:
            raise AIError('Could not reach Anthropic. Check network access.') from exc

        # A safety decline comes back as a normal 200, so it has to be checked
        # before the content is read.
        if message.stop_reason == 'refusal':
            raise AIResponseError(
                'Claude declined to generate this page. Try describing it differently.'
            )
        if message.stop_reason == 'max_tokens':
            raise AIResponseError(
                'The page was longer than the limit and came back incomplete. '
                'Try asking for a simpler page.'
            )

        text = ''.join(block.text for block in message.content if block.type == 'text')
        if not text.strip():
            raise AIResponseError('Claude returned an empty response.')

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIResponseError('Claude returned something that was not valid JSON.') from exc

        usage = {
            'input_tokens': getattr(message.usage, 'input_tokens', 0) or 0,
            'output_tokens': getattr(message.usage, 'output_tokens', 0) or 0,
        }
        return payload, usage

    def validate(self) -> None:
        import anthropic

        try:
            # Cheapest call that proves the key and the model name: one token
            # of output, no thinking budget to speak of.
            self._client().messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{'role': 'user', 'content': 'ok'}],
            )
        except anthropic.AuthenticationError as exc:
            raise AIAuthError('Anthropic rejected the API key.') from exc
        except anthropic.PermissionDeniedError as exc:
            raise AIAuthError('This Anthropic key is not allowed to use that model.') from exc
        except anthropic.NotFoundError as exc:
            raise AIError(f'Anthropic does not recognise the model "{self.model}".') from exc
        except anthropic.RateLimitError as exc:
            raise AIRateLimitError('Anthropic is rate limiting this key.') from exc
        except anthropic.APIConnectionError as exc:
            raise AIError('Could not reach Anthropic. Check network access.') from exc
        except anthropic.APIStatusError as exc:
            raise AIError(f'Anthropic rejected the request: {exc.message}') from exc
