from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "postgres" in data
    assert "redis" in data
    assert "qdrant" in data
    assert "llm" in data
    assert "nvidia" in data["llm"]
    assert "groq" in data["llm"]
