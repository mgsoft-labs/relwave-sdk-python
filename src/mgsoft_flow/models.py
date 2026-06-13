"""Data models mirroring the MGSoft Flow ``/api/v1`` response shapes.

Each dataclass exposes a :meth:`from_dict` constructor that tolerates extra
keys and missing optional fields, so forward-compatible API additions never
break deserialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "Subscriber",
    "MailingList",
    "Campaign",
    "Stream",
    "Message",
    "Pagination",
    "Page",
]


@dataclass
class Subscriber:
    id: int
    email: str
    status: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None
    engagement_tier: Optional[str] = None
    created_at: Optional[str] = None
    unsubscribed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subscriber":
        return cls(
            id=data["id"],
            email=data["email"],
            status=data.get("status", ""),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            language=data.get("language"),
            engagement_tier=data.get("engagement_tier"),
            created_at=data.get("created_at"),
            unsubscribed_at=data.get("unsubscribed_at"),
        )


@dataclass
class MailingList:
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MailingList":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            created_at=data.get("created_at"),
        )


@dataclass
class Campaign:
    id: int
    name: str
    status: str
    subject: Optional[str] = None
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        return cls(
            id=data["id"],
            name=data["name"],
            status=data.get("status", ""),
            subject=data.get("subject"),
            scheduled_at=data.get("scheduled_at"),
            sent_at=data.get("sent_at"),
            created_at=data.get("created_at"),
        )


@dataclass
class Stream:
    id: int
    name: str
    type: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stream":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type=data.get("type"),
        )


@dataclass
class Message:
    id: int
    message_id: str
    status: str
    to: Optional[str] = None
    subject: Optional[str] = None
    stream: Optional[Stream] = None
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    failure_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        stream_data = data.get("stream")
        return cls(
            id=data["id"],
            message_id=data["message_id"],
            status=data.get("status", ""),
            to=data.get("to"),
            subject=data.get("subject"),
            stream=Stream.from_dict(stream_data) if stream_data else None,
            sent_at=data.get("sent_at"),
            delivered_at=data.get("delivered_at"),
            failure_reason=data.get("failure_reason"),
        )


@dataclass
class Pagination:
    """The ``meta`` object returned by paginated list endpoints."""

    current_page: int = 1
    last_page: int = 1
    per_page: int = 0
    total: int = 0

    @property
    def has_more(self) -> bool:
        """Whether another page exists after the current one."""
        return self.current_page < self.last_page

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pagination":
        return cls(
            current_page=int(data.get("current_page", 1)),
            last_page=int(data.get("last_page", 1)),
            per_page=int(data.get("per_page", 0)),
            total=int(data.get("total", 0)),
        )


@dataclass
class Page:
    """A single page of subscribers plus its pagination metadata.

    Iterating over a :class:`Page` iterates over its :attr:`items`.
    """

    items: List[Subscriber] = field(default_factory=list)
    pagination: Pagination = field(default_factory=Pagination)

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)
