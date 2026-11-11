"""Typed exceptions for Zoho integration failures."""

from __future__ import annotations


class ZohoError(Exception):
    """Base class for all Zoho integration errors."""


class ZohoAuthError(ZohoError):
    """Raised when OAuth flow fails (invalid code, bad client, expired token)."""

    def __init__(self, message: str, *, zoho_error: str | None = None) -> None:
        super().__init__(message)
        self.zoho_error = zoho_error


class ZohoAPIError(ZohoError):
    """Raised when a Zoho CRM API call fails after retries."""

    def __init__(self, message: str, *, status_code: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body

    @property
    def retryable(self) -> bool:
        return self.status_code == 429 or self.status_code >= 500
