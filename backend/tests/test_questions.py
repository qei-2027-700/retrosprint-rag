import pytest
from fastapi.testclient import TestClient

from retrosprint_rag.main import Settings, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, enable_dev_api=True)))


def test_answer_and_source(client: TestClient) -> None:
    response = client.post("/api/questions", json={"question": "  最近うまくいったことは？ "})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["mode"] == "fake"
    assert body["answer"]["citation_ids"] == [c["id"] for c in body["citations"]]
    for citation in body["citations"]:
        assert citation["quote"] in citation["original_text"]
        assert citation["heading"] in citation["original_text"]
        assert citation["content_version"] == "v1"


@pytest.mark.parametrize("question", ["根拠のない質問", "x" * 2000, "😀" * 2000])
def test_no_evidence(client: TestClient, question: str) -> None:
    response = client.post("/api/questions", json={"question": question})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_evidence"
    assert body["answer"] is None and body["citations"] == []
    assert body["retrieval_mode"] == "related_search"
    assert body["coverage"]["complete"] is False


@pytest.mark.parametrize("question", ["", " \n　", "x" * 2001, 42, True, None])
def test_invalid_question(client: TestClient, question: object) -> None:
    assert client.post("/api/questions", json={"question": question}).status_code == 422


def test_missing_question_and_failure(client: TestClient) -> None:
    assert client.post("/api/questions", json={}).status_code == 422
    response = client.post("/api/questions", json={"question": "処理失敗の確認"})
    assert response.status_code == 500
    assert response.json()["code"] == "question_processing_failed"


def test_disabled_by_default() -> None:
    client = TestClient(create_app(Settings(_env_file=None, enable_dev_api=False)))
    assert client.post("/api/questions", json={"question": "test"}).status_code == 404
    assert "/api/questions" not in client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    "fields",
    [
        {"retrieval_mode": "unknown"},
        {"retrieval_mode": None},
        {"retrieval_mode": "monthly_reflection"},
        *[
            {"reflection_month": m}
            for m in ["0000-01", "2026-13", "2026-00", "2026-1", "2026-09\n", 202609]
        ],
        {"sql": "SELECT"},
        {"owner_id": "other"},
    ],
)
def test_invalid_retrieval_input(client: TestClient, fields: dict[str, object]) -> None:
    assert client.post("/api/questions", json={"question": "test", **fields}).status_code == 422


@pytest.mark.parametrize(
    ("month", "status", "used"),
    [
        ("2026-09", "answered", 2),
        ("2025-01", "no_documents", 0),
        ("2026-08", "input_limit_exceeded", 0),
    ],
)
def test_month_states(client: TestClient, month: str, status: str, used: int) -> None:
    response = client.post(
        "/api/questions",
        json={
            "question": "この月の成果と悩みを整理して",
            "retrieval_mode": "monthly_reflection",
            "reflection_month": month,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == status and body["mode"] == "fake"
    assert body["reflection_month"] == month
    assert body["coverage"]["documents_used"] == used
    assert body["coverage"]["scope"] == "month_documents"


def test_retrieval_failure_is_not_insufficient(client: TestClient) -> None:
    response = client.post(
        "/api/questions",
        json={
            "question": "summary",
            "retrieval_mode": "monthly_reflection",
            "reflection_month": "2026-06",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "retrieval_failed"
    assert response.json()["request_id"]


def test_citation_failure_is_502() -> None:
    from unittest.mock import Mock

    from fastapi import FastAPI

    from retrosprint_rag.api.questions import create_question_router
    from retrosprint_rag.application.ports import GenerationFailed
    from retrosprint_rag.application.questions import AskQuestion

    usecase = Mock(spec=AskQuestion)
    usecase.execute.side_effect = GenerationFailed
    app = FastAPI()
    app.include_router(create_question_router(usecase))
    response = TestClient(app).post("/api/questions", json={"question": "test"})
    assert response.status_code == 502
    assert response.json()["code"] == "generation_failed"
    assert response.json()["request_id"]
