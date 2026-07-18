"""Application-specific errors for local AI providers."""

from __future__ import annotations


class FoundryLocalError(RuntimeError):
    """Base error for Microsoft Foundry Local integration failures."""


class FoundryCatalogError(FoundryLocalError):
    """Raised when the Foundry Local model catalog cannot be inspected."""


class FoundryModelUnavailableError(FoundryLocalError):
    """Raised when a configured model alias is not available."""


class FoundryProviderError(FoundryLocalError):
    """Raised when a Foundry Local provider operation fails."""
