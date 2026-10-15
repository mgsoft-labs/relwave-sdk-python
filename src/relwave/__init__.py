"""Relwave — official Python SDK for the ``/api/v1`` API.

Quickstart::

    from relwave import Client

    client = Client(
        api_key="nl_live_xxxxx.secret",
        base_url="https://app.example.com/api/v1",
    )
    message = client.messages.send({
        "to": "user@example.com",
        "subject": "Welcome",
        "html": "<h1>Hello!</h1>",
    })
"""

from .client import Client
from .errors import (
    AuthenticationError,
    RelwaveError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ValidationError,
)
from .models import (
    Campaign,
    MailingList,
    Message,
    Page,
    Pagination,
    Stream,
    Subscriber,
)

__version__ = "0.1.0"

__all__ = [
    "Client",
    "RelwaveError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "Subscriber",
    "MailingList",
    "Campaign",
    "Stream",
    "Message",
    "Page",
    "Pagination",
    "__version__",
]
