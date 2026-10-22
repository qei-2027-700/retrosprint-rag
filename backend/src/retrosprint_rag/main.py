"""Composition root: configure HTTP and assemble concrete dependencies."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

from retrosprint_rag.adapters.fake import FakeGeneration, FakeSearch
from retrosprint_rag.api.connectivity import create_echo_router, create_health_router
from retrosprint_rag.api.questions import create_question_router
from retrosprint_rag.application.questions import AskQuestion


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RETROSPRINT_", env_file=".env", extra="ignore")

    enable_dev_api: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]


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
    app.include_router(create_health_router())
    if config.enable_dev_api:
        app.include_router(create_echo_router())
        usecase = AskQuestion(search=FakeSearch(), generation=FakeGeneration())
        app.include_router(create_question_router(usecase))
    return app
