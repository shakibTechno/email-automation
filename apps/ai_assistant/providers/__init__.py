"""
Provider registry.

Adapters are imported lazily so a missing SDK for one vendor cannot stop the
app from booting — the failure surfaces when that provider is actually used,
with a message naming what to install.
"""
from .base import (  # noqa: F401
    AIAuthError,
    AIError,
    AIRateLimitError,
    AIResponseError,
    LLMProvider,
)

PROVIDERS = {
    'anthropic': ('apps.ai_assistant.providers.anthropic_provider', 'AnthropicProvider'),
    'openai': ('apps.ai_assistant.providers.openai_provider', 'OpenAIProvider'),
    'google': ('apps.ai_assistant.providers.google_provider', 'GoogleProvider'),
    'local': ('apps.ai_assistant.providers.local_provider', 'LocalProvider'),
}

#: Providers that take a server address instead of (or as well as) a key.
SELF_HOSTED = {'local'}


def get_provider(
    name: str, api_key: str, model: str = '', base_url: str = ''
) -> LLMProvider:
    """Build the adapter for `name`, or raise AIError if it cannot be loaded."""
    import importlib

    try:
        module_path, class_name = PROVIDERS[name]
    except KeyError:
        raise AIError(f'Unknown AI provider "{name}".') from None

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise AIError(
            f'The SDK for {name} is not installed on the server. '
            'Install the project requirements and rebuild the backend image.'
        ) from exc

    cls = getattr(module, class_name)
    if name in SELF_HOSTED:
        return cls(api_key=api_key, model=model, base_url=base_url)
    return cls(api_key=api_key, model=model)


def default_model_for(name: str) -> str:
    """The model used when an organization has not pinned one."""
    import importlib

    try:
        module_path, class_name = PROVIDERS[name]
        return getattr(importlib.import_module(module_path), class_name).default_model
    except (KeyError, ImportError):
        return ''
