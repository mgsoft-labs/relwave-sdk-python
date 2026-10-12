"""Synchronous client for the MGSoft Flow ``/api/v1`` API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import requests

from .errors import FlowError
from .models import (
    Campaign,
    MailingList,
    Message,
    Page,
    Pagination,
    Subscriber,
)

__all__ = ["Client"]

DEFAULT_BASE_URL = "https://app.test/api/v1"
DEFAULT_TIMEOUT = 30.0
_USER_AGENT = "mgsoft-flow-python/0.1.0"


class Client:
    """Entry point for the MGSoft Flow API.

    Args:
        api_key: An API key in the form ``nl_xxxxx.secret``. Keys prefixed with
            ``nl_test_`` route to the sandbox and never send real email.
        base_url: The API base URL, e.g. ``https://app.example.com/api/v1``.
        timeout: Per-request timeout in seconds.
        session: An optional pre-configured :class:`requests.Session`.

    Example:
        >>> client = Client(api_key="nl_live_abc.secret",
        ...                  base_url="https://app.example.com/api/v1")
        >>> client.subscribers.list()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

        # Resource groups.
        self.subscribers = SubscribersResource(self)
        self.lists = ListsResource(self)
        self.campaigns = CampaignsResource(self)
        self.messages = MessagesResource(self)

    @property
    def is_sandbox(self) -> bool:
        """Whether this key targets the sandbox (``nl_test_`` prefix)."""
        return self.api_key.startswith("nl_test_")

    # ------------------------------------------------------------------ #
    # Low-level transport
    # ------------------------------------------------------------------ #

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Issue a request and unwrap the ``{ data, meta, errors }`` envelope.

        Returns a ``(data, meta)`` tuple on success. Raises
        :class:`~mgsoft_flow.errors.FlowError` (or a subclass) when the
        response has ``HTTP >= 400`` or a populated ``errors`` map.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        response = self._session.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=self._headers(idempotency_key),
            timeout=self.timeout,
        )

        return self._parse(response)

    def _parse(self, response: requests.Response) -> Tuple[Any, Dict[str, Any]]:
        try:
            body = response.json()
        except ValueError:
            body = {}

        if not isinstance(body, dict):
            body = {"data": body}

        data = body.get("data")
        meta = _as_dict(body.get("meta"))
        errors = _as_dict(body.get("errors"))

        if response.status_code >= 400 or errors:
            raise FlowError.from_response(
                status=response.status_code,
                errors=_normalize_errors(errors),
                retry_after=_parse_retry_after(response.headers.get("Retry-After")),
                meta=meta,
            )

        return data, meta


# ---------------------------------------------------------------------- #
# Resource groups
# ---------------------------------------------------------------------- #


class _Resource:
    def __init__(self, client: Client) -> None:
        self._client = client


class SubscribersResource(_Resource):
    """Operations on subscribers — ``/subscribers``."""

    def list(self, params: Optional[Dict[str, Any]] = None) -> Page:
        """List subscribers (paginated).

        Args:
            params: Optional query params, e.g. ``{"page": 2, "per_page": 50}``.

        Returns:
            A :class:`~mgsoft_flow.models.Page` of
            :class:`~mgsoft_flow.models.Subscriber` with ``.pagination``.
        """
        data, meta = self._client.request("GET", "subscribers", params=params)
        items = [Subscriber.from_dict(row) for row in (data or [])]
        return Page(items=items, pagination=Pagination.from_dict(meta))

    def create(
        self,
        body: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Subscriber:
        """Create (or upsert) a subscriber — ``POST /subscribers`` (201).

        Args:
            body: Must include ``email``. Optional: ``first_name``,
                ``last_name``, ``phone``, ``language``, ``status``
                (``pending`` | ``confirmed`` | ``unsubscribed``), ``attributes``.
            idempotency_key: Optional ``X-Idempotency-Key`` value.
        """
        data, _ = self._client.request(
            "POST", "subscribers", json=body, idempotency_key=idempotency_key
        )
        return Subscriber.from_dict(data)

    def get(self, subscriber_id: int) -> Subscriber:
        """Fetch a single subscriber — ``GET /subscribers/{id}``."""
        data, _ = self._client.request("GET", f"subscribers/{subscriber_id}")
        return Subscriber.from_dict(data)

    def delete(self, subscriber_id: int) -> Subscriber:
        """Soft-unsubscribe a subscriber — ``DELETE /subscribers/{id}``.

        Returns the updated subscriber (status ``unsubscribed``).
        """
        data, _ = self._client.request("DELETE", f"subscribers/{subscriber_id}")
        return Subscriber.from_dict(data)


class ListsResource(_Resource):
    """Operations on mailing lists — ``/lists``."""

    def list(self) -> List[MailingList]:
        """List all mailing lists — ``GET /lists``."""
        data, _ = self._client.request("GET", "lists")
        return [MailingList.from_dict(row) for row in (data or [])]


class CampaignsResource(_Resource):
    """Operations on campaigns — ``/campaigns``."""

    def list(self) -> List[Campaign]:
        """List all campaigns — ``GET /campaigns``."""
        data, _ = self._client.request("GET", "campaigns")
        return [Campaign.from_dict(row) for row in (data or [])]


class MessagesResource(_Resource):
    """Transactional messages — ``/messages``."""

    def send(
        self,
        body: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Message:
        """Send a transactional message — ``POST /messages`` (201).

        Args:
            body: Must include ``to``, ``subject`` and at least one of ``html``
                / ``text``. Optional: ``from``, ``from_name``, ``reply_to``,
                ``stream_id``, ``variables``, ``metadata``, ``tags`` (<= 10),
                ``markdown``, ``template_id`` and ``attachments`` — a list of
                ``{"filename", "content" (base64), "content_type"?}``, up to 10
                files / 10 MB in total.
            idempotency_key: Optional ``X-Idempotency-Key`` value.
        """
        data, _ = self._client.request(
            "POST", "messages", json=body, idempotency_key=idempotency_key
        )
        return Message.from_dict(data)

    def get(self, message_id: int) -> Message:
        """Fetch a sent message and its events — ``GET /messages/{id}``."""
        data, _ = self._client.request("GET", f"messages/{message_id}")
        return Message.from_dict(data)


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_errors(errors: Dict[str, Any]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {}
    for key, messages in errors.items():
        if isinstance(messages, list):
            normalized[key] = [str(m) for m in messages]
        else:
            normalized[key] = [str(messages)]
    return normalized


def _parse_retry_after(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
