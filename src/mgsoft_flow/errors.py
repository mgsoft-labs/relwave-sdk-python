"""Typed exceptions for the MGSoft Flow SDK."""

from __future__ import annotations

from typing import Dict, List, Optional

__all__ = [
    "FlowError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
]

# Errors map shape: { "field": ["message", ...], ... }
ErrorsMap = Dict[str, List[str]]


class FlowError(Exception):
    """Base error raised when the API returns ``HTTP >= 400`` or a populated
    ``errors`` envelope.

    Attributes:
        status: The HTTP status code returned by the API.
        errors: A mapping of ``field -> [messages]`` extracted from the response
            envelope's ``errors`` key.
        retry_after: Number of seconds to wait before retrying, parsed from the
            ``Retry-After`` header on ``429`` responses (``None`` otherwise).
        meta: The ``meta`` object from the response envelope, if any.
    """

    def __init__(
        self,
        status: int,
        errors: Optional[ErrorsMap] = None,
        retry_after: Optional[int] = None,
        meta: Optional[Dict[str, object]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.status = status
        self.errors: ErrorsMap = errors or {}
        self.retry_after = retry_after
        self.meta: Dict[str, object] = meta or {}
        super().__init__(message or self._build_message())

    def _build_message(self) -> str:
        if self.errors:
            parts = [
                f"{field}: {'; '.join(messages)}"
                for field, messages in self.errors.items()
            ]
            return f"[{self.status}] " + " | ".join(parts)
        return f"[{self.status}] request failed"

    @property
    def first_message(self) -> Optional[str]:
        """Return the first error message across all fields, if present."""
        for messages in self.errors.values():
            if messages:
                return messages[0]
        return None

    @classmethod
    def from_response(
        cls,
        status: int,
        errors: Optional[ErrorsMap] = None,
        retry_after: Optional[int] = None,
        meta: Optional[Dict[str, object]] = None,
    ) -> "FlowError":
        """Build the most specific error subclass for the given HTTP status."""
        error_cls = _STATUS_MAP.get(status, cls)
        return error_cls(status=status, errors=errors, retry_after=retry_after, meta=meta)


class AuthenticationError(FlowError):
    """Raised on ``401`` — missing or invalid API key."""


class PermissionError(FlowError):  # noqa: A001 - intentional public name
    """Raised on ``403`` — authenticated but not allowed (e.g. suspended account)."""


class NotFoundError(FlowError):
    """Raised on ``404`` — the requested resource does not exist."""


class ValidationError(FlowError):
    """Raised on ``422`` — the request body failed validation."""


class RateLimitError(FlowError):
    """Raised on ``429`` — too many requests. Inspect :attr:`retry_after`."""


_STATUS_MAP = {
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}
