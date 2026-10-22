"""Question HTTP request and response contracts."""

from typing import Annotated, Literal

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


class QuestionError(BaseModel):
    code: Literal["question_processing_failed"] = "question_processing_failed"
    message: str = "回答処理に失敗しました。もう一度送信してください。"
