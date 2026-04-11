from fastapi.testclient import TestClient
import pytest
from backend.app.main import app

client = TestClient(app)

def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_missions():
    response = client.get("/api/missions")
    assert response.status_code == 200
    assert "missions" in response.json()

def test_leaderboard():
    response = client.get("/api/leaderboard")
    assert response.status_code == 200
    assert "entries" in response.json()
