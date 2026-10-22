"""Contracts required by the question use case."""

from typing import Protocol

from retrosprint_rag.domain.models import Answer, Citation


class ProcessingFailed(Exception):
    """Search or generation could not complete the requested operation."""


class Search(Protocol):
    def search(self, question: str) -> list[Citation]: ...


class Generation(Protocol):
    def generate(self, question: str, citations: list[Citation]) -> Answer: ...
