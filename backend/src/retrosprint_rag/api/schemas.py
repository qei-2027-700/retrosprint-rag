"""Question HTTP request and response contracts."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

QuestionText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)
]


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: QuestionText
    retrieval_mode: Literal["monthly_reflection", "related_search"] = "related_search"
    reflection_month: (
        Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")] | None
    ) = None

    @model_validator(mode="after")
    def require_month(self) -> "QuestionRequest":
        if self.reflection_month is not None and self.reflection_month.startswith("0000"):
            raise ValueError("Year must be between 0001 and 9999")
        if self.retrieval_mode == "monthly_reflection" and self.reflection_month is None:
            raise ValueError("reflection_month is required for monthly_reflection")
        return self


class Locator(BaseModel):
    start: int
    end: int


class Coverage(BaseModel):
    scope: Literal["month_documents", "search_matches"]
    complete: bool
    omitted: bool
    documents_retrieved: int
    documents_used: int
    checked_at: str
    last_sync_at: str | None = None


class ResultBase(BaseModel):
    mode: Literal["fake"] = "fake"
    retrieval_mode: Literal["monthly_reflection", "related_search"]
    reflection_month: str | None
    coverage: Coverage
    message: str | None = None


class Citation(BaseModel):
    id: str
    document_id: str
    document_name: str | None
    content_version: str
    reflection_month: str | None
    heading: str | None
    page: int | None = None
    quote: str
    original_text: str | None
    locator: Locator
    drive_url: None = None


class Answer(BaseModel):
    text: str
    citation_ids: list[str]


class Answered(ResultBase):
    status: Literal["answered"] = "answered"
    mode: Literal["fake"] = "fake"
    answer: Answer
    citations: list[Citation]


class InsufficientEvidence(ResultBase):
    status: Literal[
        "insufficient_evidence", "no_documents", "stale_evidence", "input_limit_exceeded"
    ] = "insufficient_evidence"
    mode: Literal["fake"] = "fake"
    answer: None = None
    citations: list[Citation] = []


class QuestionError(BaseModel):
    code: Literal["question_processing_failed"] = "question_processing_failed"
    message: str = "回答処理に失敗しました。もう一度送信してください。"


class RetrievalError(BaseModel):
    code: Literal["retrieval_failed", "generation_failed"]
    message: str
    request_id: str
