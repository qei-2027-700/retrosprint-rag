"""Business data independent of HTTP and adapters."""

from dataclasses import dataclass
from typing import Literal

RetrievalMode = Literal["monthly_reflection", "related_search"]
Status = Literal[
    "answered", "no_documents", "insufficient_evidence", "stale_evidence", "input_limit_exceeded"
]


@dataclass(frozen=True)
class Document:
    document_id: str
    content_version: str
    reflection_month: str | None
    document_name: str | None
    content: str


@dataclass(frozen=True)
class Locator:
    start: int
    end: int


@dataclass(frozen=True)
class Citation:
    id: str
    document_id: str
    document_name: str | None
    content_version: str
    reflection_month: str | None
    heading: str | None
    quote: str
    original_text: str | None
    locator: Locator
    page: int | None = None
    drive_url: None = None


@dataclass(frozen=True)
class Answer:
    text: str
    citation_ids: list[str]


@dataclass(frozen=True)
class Evidence:
    documents: list[Document]
    citations: list[Citation]
    checked_at: str
    stale: bool = False
    omitted: bool = False


@dataclass(frozen=True)
class Coverage:
    scope: Literal["month_documents", "search_matches"]
    complete: bool
    omitted: bool
    documents_retrieved: int
    documents_used: int
    checked_at: str
    last_sync_at: str | None = None
