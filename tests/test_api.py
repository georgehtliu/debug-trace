"""E2E tests for the API."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# TODO: Add E2E test for full trace submission and QA pipeline
# def test_full_trace_submission():
#     """Test complete trace submission with QA pipeline."""
#     pass

