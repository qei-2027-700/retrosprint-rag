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
    assert response.json() == {
        "status": "insufficient_evidence",
        "mode": "fake",
        "answer": None,
        "citations": [],
    }


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
