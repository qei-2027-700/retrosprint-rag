"""Register question routes and translate application results to HTTP."""

from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from retrosprint_rag.api.schemas import (
    Answer,
    Answered,
    Citation,
    Coverage,
    InsufficientEvidence,
    QuestionError,
    QuestionRequest,
    RetrievalError,
)
from retrosprint_rag.application.ports import GenerationFailed, ProcessingFailed, RetrievalFailed
from retrosprint_rag.application.questions import AskQuestion


def create_question_router(usecase: AskQuestion) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/questions",
        response_model=Answered | InsufficientEvidence,
        responses={
            500: {"model": QuestionError},
            503: {"model": RetrievalError},
            502: {"model": RetrievalError},
        },
        operation_id="ask_question",
    )
    def question(body: QuestionRequest) -> Answered | InsufficientEvidence | JSONResponse:
        try:
            result = usecase.execute(body.question, body.retrieval_mode, body.reflection_month)
        except ProcessingFailed:
            return JSONResponse(status_code=500, content=QuestionError().model_dump())
        except (RetrievalFailed, GenerationFailed) as exc:
            retrieval = isinstance(exc, RetrievalFailed)
            error = RetrievalError(
                code="retrieval_failed" if retrieval else "generation_failed",
                message="資料を取得できませんでした。"
                if retrieval
                else "回答を生成できませんでした。",
                request_id=uuid4().hex,
            )
            return JSONResponse(status_code=503 if retrieval else 502, content=error.model_dump())
        coverage = Coverage.model_validate(result.coverage, from_attributes=True)
        common = dict(
            retrieval_mode=body.retrieval_mode,
            reflection_month=body.reflection_month,
            coverage=Coverage.model_validate(result.coverage, from_attributes=True),
            message=result.message,
        )
        if result.answer is None:
            return InsufficientEvidence.model_validate(dict(status=result.status, **common))
        return Answered(
            retrieval_mode=body.retrieval_mode,
            reflection_month=body.reflection_month,
            coverage=coverage,
            message=result.message,
            answer=Answer.model_validate(result.answer, from_attributes=True),
            citations=[
                Citation.model_validate(citation, from_attributes=True)
                for citation in result.citations
            ],
        )

    return router
