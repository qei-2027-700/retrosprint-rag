"""Health and development echo HTTP handlers."""

from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


Message = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]


class EchoRequest(BaseModel):
    message: Message


class EchoResponse(BaseModel):
    message: str


def create_health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse, operation_id="get_health")
    def health() -> HealthResponse:
        return HealthResponse()

    return router


def create_echo_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/dev/echo", response_model=EchoResponse, operation_id="echo_message")
    def echo(body: EchoRequest) -> EchoResponse:
        return EchoResponse(message=body.message)

    return router
