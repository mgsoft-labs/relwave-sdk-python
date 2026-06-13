"""Offline tests for the AVVA Newsletter SDK using the ``responses`` library.

No real network access happens; every HTTP call is mocked.
"""

import pytest
import responses

from newsletter import (
    Client,
    NewsletterError,
    RateLimitError,
    ValidationError,
)

BASE_URL = "https://app.test/api/v1"


def make_client() -> Client:
    return Client(api_key="nl_test_abc.secret", base_url=BASE_URL)


@responses.activate
def test_send_message_returns_message_and_sets_auth_header():
    responses.add(
        responses.POST,
        f"{BASE_URL}/messages",
        json={
            "data": {
                "id": 42,
                "message_id": "uuid@app.test",
                "to": "user@example.com",
                "subject": "Welcome",
                "status": "sent",
                "stream": {"id": 1, "name": "Transactional", "type": "transactional"},
                "sent_at": "2026-06-13T10:00:00+00:00",
                "delivered_at": None,
                "failure_reason": None,
            },
            "meta": {},
            "errors": {},
        },
        status=201,
    )

    client = make_client()
    message = client.messages.send(
        {
            "to": "user@example.com",
            "subject": "Welcome",
            "html": "<h1>Hello!</h1>",
        },
        idempotency_key="welcome-42",
    )

    assert message.id == 42
    assert message.message_id == "uuid@app.test"
    assert message.status == "sent"
    assert message.stream is not None
    assert message.stream.type == "transactional"

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer nl_test_abc.secret"
    assert request.headers["X-Idempotency-Key"] == "welcome-42"


@responses.activate
def test_create_subscriber_returns_subscriber():
    responses.add(
        responses.POST,
        f"{BASE_URL}/subscribers",
        json={
            "data": {
                "id": 7,
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "status": "confirmed",
                "language": "en",
                "engagement_tier": "active",
                "created_at": "2026-06-13T09:00:00+00:00",
                "unsubscribed_at": None,
            },
            "meta": {},
            "errors": {},
        },
        status=201,
    )

    client = make_client()
    subscriber = client.subscribers.create(
        {"email": "jane@example.com", "first_name": "Jane", "last_name": "Doe"}
    )

    assert subscriber.id == 7
    assert subscriber.email == "jane@example.com"
    assert subscriber.status == "confirmed"
    assert subscriber.first_name == "Jane"


@responses.activate
def test_create_subscriber_422_raises_validation_error():
    responses.add(
        responses.POST,
        f"{BASE_URL}/subscribers",
        json={
            "data": None,
            "meta": {},
            "errors": {"email": ["The email field is required."]},
        },
        status=422,
    )

    client = make_client()
    with pytest.raises(ValidationError) as exc_info:
        client.subscribers.create({"first_name": "NoEmail"})

    err = exc_info.value
    assert isinstance(err, NewsletterError)
    assert err.status == 422
    assert err.errors["email"] == ["The email field is required."]
    assert err.first_message == "The email field is required."


@responses.activate
def test_list_subscribers_exposes_pagination_meta():
    responses.add(
        responses.GET,
        f"{BASE_URL}/subscribers",
        json={
            "data": [
                {"id": 1, "email": "a@example.com", "status": "confirmed"},
                {"id": 2, "email": "b@example.com", "status": "pending"},
            ],
            "meta": {
                "current_page": 1,
                "last_page": 3,
                "per_page": 2,
                "total": 6,
            },
            "errors": {},
        },
        status=200,
    )

    client = make_client()
    page = client.subscribers.list({"per_page": 2})

    assert len(page) == 2
    assert page.items[0].email == "a@example.com"
    assert page.pagination.total == 6
    assert page.pagination.last_page == 3
    assert page.pagination.has_more is True


@responses.activate
def test_rate_limit_429_carries_retry_after():
    responses.add(
        responses.POST,
        f"{BASE_URL}/messages",
        json={
            "data": None,
            "meta": {},
            "errors": {"rate": ["too many requests"]},
        },
        status=429,
        headers={"Retry-After": "30"},
    )

    client = make_client()
    with pytest.raises(RateLimitError) as exc_info:
        client.messages.send({"to": "x@example.com", "subject": "Hi", "text": "yo"})

    assert exc_info.value.status == 429
    assert exc_info.value.retry_after == 30
