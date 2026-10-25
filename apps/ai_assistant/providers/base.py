"""
The provider seam.

Three vendors, one interface. Each adapter speaks its own vendor's official SDK
— no cross-provider compatibility shims — and converts that vendor's errors
into the small set below, so callers and the UI never have to know three
exception hierarchies.
"""
from abc import ABC, abstractmethod


class AIError(Exception):
    """Base for every provider failure, carrying a message fit to show a user."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AIAuthError(AIError):
    """The key was rejected. The user fixes this in Settings."""


class AIRateLimitError(AIError):
    """The provider is throttling or the account is out of quota. Retry later."""


class AIResponseError(AIError):
    """A response came back but was unusable — wrong shape, truncated, refused."""


class LLMProvider(ABC):
    """
    What the generation service needs from a provider, and nothing more.

    Kept deliberately narrow: one call that returns parsed JSON matching a
    schema, and one cheap call to check credentials. Anything a particular
    vendor does better lives inside its own adapter.
    """

    #: Used when the organization has not pinned a model.
    default_model: str = ''

    def __init__(self, api_key: str, model: str = ''):
        self.api_key = api_key
        self.model = model or self.default_model

    @abstractmethod
    def generate_json(self, *, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        """
        Run one generation and return ``(parsed_payload, usage)``.

        ``usage`` is ``{"input_tokens": int, "output_tokens": int}``; providers
        that do not report token counts return zeros rather than guessing.
        """

    @abstractmethod
    def validate(self) -> None:
        """
        Confirm the credentials work. Returns None, raises on failure.

        Must be cheap — this sits behind a "Test connection" button.
        """
