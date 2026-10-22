"""Register question routes and translate application results to HTTP."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from retrosprint_rag.api.schemas import (
    Answer,
    Answered,
    Citation,
    InsufficientEvidence,
    QuestionError,
    QuestionRequest,
)
from retrosprint_rag.application.ports import ProcessingFailed
from retrosprint_rag.application.questions import AskQuestion


def create_question_router(usecase: AskQuestion) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/questions",
        response_model=Answered | InsufficientEvidence,
        responses={500: {"model": QuestionError}},
        operation_id="ask_question",
    )
    def question(body: QuestionRequest) -> Answered | InsufficientEvidence | JSONResponse:
        try:
            result = usecase.execute(body.question)
        except ProcessingFailed:
            return JSONResponse(status_code=500, content=QuestionError().model_dump())
        if result.answer is None:
            return InsufficientEvidence()
        return Answered(
            answer=Answer.model_validate(result.answer, from_attributes=True),
            citations=[
                Citation.model_validate(citation, from_attributes=True)
                for citation in result.citations
            ],
        )

    return router
