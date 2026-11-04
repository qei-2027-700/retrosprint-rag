"""Contracts required by the question use case."""

from typing import Protocol

from retrosprint_rag.domain.models import Answer, Coverage, Evidence


class ProcessingFailed(Exception):
    """Legacy fake failure."""


class RetrievalFailed(Exception):
    """Evidence could not be retrieved."""


class GenerationFailed(Exception):
    """Generation or citation validation failed."""


class Search(Protocol):
    def search(self, question: str, reflection_month: str | None) -> Evidence: ...


class MonthDocuments(Protocol):
    def fetch_month(self, reflection_month: str) -> Evidence: ...


class Generation(Protocol):
    def generate(self, question: str, evidence: Evidence, coverage: Coverage) -> Answer | None: ...
