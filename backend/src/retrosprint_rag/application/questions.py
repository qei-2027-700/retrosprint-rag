"""Coordinate evidence retrieval and answer generation."""

from dataclasses import dataclass

from retrosprint_rag.application.ports import Generation, Search
from retrosprint_rag.domain.models import Answer, Citation


@dataclass(frozen=True)
class QuestionResult:
    answer: Answer | None
    citations: list[Citation]


class AskQuestion:
    def __init__(self, search: Search, generation: Generation) -> None:
        self._search = search
        self._generation = generation

    def execute(self, question: str) -> QuestionResult:
        citations = self._search.search(question)
        if not citations:
            return QuestionResult(answer=None, citations=[])
        answer = self._generation.generate(question, citations)
        return QuestionResult(answer=answer, citations=citations)
