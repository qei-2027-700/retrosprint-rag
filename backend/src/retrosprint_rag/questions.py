"""Local-only question use case and deterministic synthetic adapters."""

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, StringConstraints

QuestionText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)
]


class QuestionRequest(BaseModel):
    question: QuestionText


class Citation(BaseModel):
    id: str
    document_id: str
    document_name: str
    content_version: str
    reflection_month: str
    heading: str
    page: int | None = None
    quote: str
    original_text: str


class Answer(BaseModel):
    text: str
    citation_ids: list[str]


class Answered(BaseModel):
    status: Literal["answered"] = "answered"
    mode: Literal["fake"] = "fake"
    answer: Answer
    citations: list[Citation]


class InsufficientEvidence(BaseModel):
    status: Literal["insufficient_evidence"] = "insufficient_evidence"
    mode: Literal["fake"] = "fake"
    answer: None = None
    citations: list[Citation] = []


class ProcessingFailed(Exception):
    """A deterministic failure used only in the local demo."""


class QuestionError(BaseModel):
    code: Literal["question_processing_failed"] = "question_processing_failed"
    message: str = "回答処理に失敗しました。もう一度送信してください。"


class Search(Protocol):
    def search(self, question: str) -> list[Citation]: ...


class Generation(Protocol):
    def generate(self, question: str, citations: list[Citation]) -> Answer: ...


SAMPLE_TEXT = (
    "2026年9月の振り返り（合成資料）\n\n"
    "うまくいったこと\n"
    "作業を小さく分けたら、着手しやすくなった。\n"
    "次の日に取り組む作業を前日に一つ決めておいた。\n\n"
    "次に試すこと\n週末に進み具合を振り返る。"
)


class FakeSearch:
    def search(self, question: str) -> list[Citation]:
        if question == "処理失敗の確認":
            raise ProcessingFailed
        if question != "最近うまくいったことは？":
            return []
        return [
            Citation(
                id="c1",
                document_id="reflection-2026-09",
                document_name="2026年9月の振り返り（合成資料）",
                content_version="v1",
                reflection_month="2026-09",
                heading="うまくいったこと",
                quote="作業を小さく分けたら、着手しやすくなった。",
                original_text=SAMPLE_TEXT,
            )
        ]


class FakeGeneration:
    def generate(self, question: str, citations: list[Citation]) -> Answer:
        return Answer(
            text="作業を小さく分けることで、着手しやすくなっています。",
            citation_ids=[citation.id for citation in citations],
        )


def ask(question: str, search: Search, generation: Generation) -> Answered | InsufficientEvidence:
    citations = search.search(question)
    if not citations:
        return InsufficientEvidence()
    return Answered(answer=generation.generate(question, citations), citations=citations)
