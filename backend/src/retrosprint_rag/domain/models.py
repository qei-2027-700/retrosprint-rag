"""Business data, independent of HTTP and concrete service adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    id: str
    document_id: str
    document_name: str
    content_version: str
    reflection_month: str
    heading: str
    quote: str
    original_text: str
    page: int | None = None


@dataclass(frozen=True)
class Answer:
    text: str
    citation_ids: list[str]
