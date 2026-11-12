# relwave

Official Python SDK for the **Relwave** API (`/api/v1`). Send
transactional email, manage subscribers, and read your lists and campaigns —
with a typed, idiomatic, envelope-aware client.

- PyPI package: **`relwave`**
- Import package: **`relwave`**
- Python **3.9+**, built on [`requests`](https://pypi.org/project/requests/)

## Installation

```bash
pip install relwave
```

## Quickstart

```python
from relwave import Client

client = Client(
    api_key="nl_live_xxxxx.secret",
    base_url="https://app.example.com/api/v1",
)

# Send a transactional message
message = client.messages.send({
    "to": "user@example.com",
    "subject": "Welcome aboard",
    "html": "<h1>Hello!</h1><p>Thanks for joining.</p>",
})
print(message.id, message.status)        # 42 sent
print(message.message_id)                # uuid@app.example.com

# Look up a message later
fetched = client.messages.get(message.id)
print(fetched.status, fetched.delivered_at)
```

### Authentication

Every request is authenticated with your API key via the
`Authorization: Bearer <API_KEY>` header (the SDK also supports the
`X-Api-Key` alternative server-side). Keys look like `nl_xxxxx.secret`.

```python
client = Client(api_key="nl_live_xxxxx.secret",
                base_url="https://app.example.com/api/v1")
```

The `base_url` defaults to `https://relwave.com/api/v1`;
set it to your application's `/api/v1` URL in production.

## Subscribers

```python
# Create (or upsert) a subscriber
subscriber = client.subscribers.create({
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "status": "confirmed",          # pending | confirmed | unsubscribed
    "attributes": {"plan": "pro"},
})

# Fetch one
jane = client.subscribers.get(subscriber.id)

# Soft-unsubscribe (DELETE)
client.subscribers.delete(subscriber.id)

# List (paginated) — returns a Page you can iterate
page = client.subscribers.list({"page": 1, "per_page": 50})
for sub in page:
    print(sub.email, sub.status)

print(page.pagination.current_page, page.pagination.total, page.pagination.has_more)
```

## Lists & campaigns

```python
for mailing_list in client.lists.list():
    print(mailing_list.id, mailing_list.name)

for campaign in client.campaigns.list():
    print(campaign.name, campaign.status, campaign.sent_at)
```

## Sending messages

`to`, `subject`, and at least one of `html` / `text` are required. Optional
fields: `from`, `from_name`, `reply_to`, `stream_id`, `variables`,
`metadata`, and up to **10** `tags`.

```python
client.messages.send({
    "to": "user@example.com",
    "from": "team@example.com",
    "from_name": "The Team",
    "reply_to": "support@example.com",
    "subject": "Hi {{ first_name }}",
    "html": "<p>Hello {{ first_name }}!</p>",
    "variables": {"first_name": "Jane"},
    "tags": ["welcome", "onboarding"],
    "metadata": {"campaign": "spring"},
})
```

### Attachments and templates

```python
import base64

with open("invoice.pdf", "rb") as f:
    pdf = base64.b64encode(f.read()).decode()

client.messages.send({
    "to": "jane@example.com",
    "subject": "Your invoice",
    "template_id": 12,  # the body fills the template's {{content}} slot
    "markdown": "Thanks for your order, **{{ first_name }}**.",
    "variables": {"first_name": "Jane"},
    "attachments": [{"filename": "invoice.pdf", "content": pdf}],
})
```

Up to 10 files, 10 MB in total. Executable and script types are rejected.

## Error handling

The API returns a `{ data, meta, errors }` envelope. On success the SDK returns
the deserialized `data` (and exposes `meta` for paginated lists). When the
response has `HTTP >= 400` or a populated `errors` map, the SDK raises a typed
`RelwaveError` (or a subclass) carrying the `status` and an `errors`
mapping of `field -> [messages]`.

```python
from relwave import (
    RelwaveError,
    AuthenticationError,   # 401
    PermissionError,       # 403
    NotFoundError,         # 404
    ValidationError,       # 422
    RateLimitError,        # 429
)

try:
    client.subscribers.create({"first_name": "NoEmail"})
except ValidationError as err:
    print(err.status)            # 422
    print(err.errors)            # {"email": ["The email field is required."]}
    print(err.first_message)     # "The email field is required."
except RelwaveError as err:
    # Catch-all base for any API error
    print(err.status, err.errors)
```

### Rate limiting (429)

On `429 Too Many Requests`, the SDK raises `RateLimitError` and surfaces the
`Retry-After` header value (seconds) via `retry_after`:

```python
import time
from relwave import RateLimitError

try:
    client.messages.send({"to": "u@example.com", "subject": "Hi", "text": "yo"})
except RateLimitError as err:
    wait = err.retry_after or 1
    time.sleep(wait)
    # ...then retry
```

## Idempotency

`create` and `send` accept an optional `idempotency_key`, sent as the
`X-Idempotency-Key` header so retries never duplicate a write:

```python
client.messages.send(
    {"to": "user@example.com", "subject": "Receipt", "html": "<p>Thanks</p>"},
    idempotency_key="order-1001-receipt",
)
```

## Sandbox

API keys prefixed with `nl_test_` route to the **sandbox**: messages are
recorded and return a realistic `sent` response, but no real email is
delivered. Check `client.is_sandbox` to detect the mode:

```python
client = Client(api_key="nl_test_xxxxx.secret",
                base_url="https://app.example.com/api/v1")
assert client.is_sandbox is True
```

## API reference

| Method | HTTP | Returns |
| --- | --- | --- |
| `client.subscribers.list(params?)` | `GET /subscribers` | `Page[Subscriber]` (paginated) |
| `client.subscribers.create(body, idempotency_key?)` | `POST /subscribers` (201) | `Subscriber` |
| `client.subscribers.get(id)` | `GET /subscribers/{id}` | `Subscriber` |
| `client.subscribers.delete(id)` | `DELETE /subscribers/{id}` | `Subscriber` (unsubscribed) |
| `client.lists.list()` | `GET /lists` | `list[MailingList]` |
| `client.campaigns.list()` | `GET /campaigns` | `list[Campaign]` |
| `client.messages.send(body, idempotency_key?)` | `POST /messages` (201) | `Message` |
| `client.messages.get(id)` | `GET /messages/{id}` | `Message` |

## Development

```bash
pip install -e ".[test]"
pytest
```

Tests run fully offline using [`responses`](https://pypi.org/project/responses/)
— no network access required.

## License

MIT
