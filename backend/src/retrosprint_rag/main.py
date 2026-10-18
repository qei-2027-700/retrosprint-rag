"""HTTP entry point; constructing the app requires no external connections."""

from typing import Annotated, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RETROSPRINT_", env_file=".env", extra="ignore")

    enable_dev_api: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


Message = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]


class EchoRequest(BaseModel):
    message: Message


class EchoResponse(BaseModel):
    message: str


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    app = FastAPI(title="Retrosprint RAG API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.get("/health", response_model=HealthResponse, operation_id="get_health")
    def health() -> HealthResponse:
        return HealthResponse()

    if config.enable_dev_api:

        @app.post("/api/v1/dev/echo", response_model=EchoResponse, operation_id="echo_message")
        def echo(body: EchoRequest) -> EchoResponse:
            return EchoResponse(message=body.message)

    return app
