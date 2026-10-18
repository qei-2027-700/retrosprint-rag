import pytest
from fastapi.testclient import TestClient

from retrosprint_rag.main import Settings, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, enable_dev_api=True)))


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    schema = client.get("/openapi.json").json()
    assert (
        schema["components"]["schemas"]["HealthResponse"]["properties"]["status"]["const"] == "ok"
    )


@pytest.mark.parametrize("message", ["疎通確認", " x ", "あ" * 200, " " + "x" * 200 + " "])
def test_echo(client: TestClient, message: str) -> None:
    response = client.post("/api/v1/dev/echo", json={"message": message})
    assert response.status_code == 200
    assert response.json() == {"message": message.strip()}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"message": 1},
        {"message": True},
        {"message": None},
        {"message": ""},
        {"message": " \t\n　"},
        {"message": "a" * 201},
    ],
)
def test_invalid_echo(client: TestClient, body: dict[str, object]) -> None:
    response = client.post("/api/v1/dev/echo", json=body)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_public_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RETROSPRINT_ENABLE_DEV_API", raising=False)
    client = TestClient(create_app(Settings(_env_file=None)))
    assert client.get("/health").status_code == 200
    assert client.post("/api/v1/dev/echo", json={"message": "test"}).status_code == 404
    assert "/api/v1/dev/echo" not in client.get("/openapi.json").json()["paths"]


def test_cors(client: TestClient) -> None:
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/v1/dev/echo", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    headers["Origin"] = "https://untrusted.example"
    assert client.options("/api/v1/dev/echo", headers=headers).status_code == 400
    headers["Origin"] = "http://localhost:3000"
    headers["Access-Control-Request-Method"] = "DELETE"
    assert client.options("/api/v1/dev/echo", headers=headers).status_code == 400
