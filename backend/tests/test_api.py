from fastapi.testclient import TestClient
from app.main import app


def test_models_no_key():
    client = TestClient(app)
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert data["embedding_model"] is None

