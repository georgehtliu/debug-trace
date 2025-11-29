"""E2E tests for the API."""
import pytest
from fastapi import status


class TestHealthEndpoints:
    """Tests for health and root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root health check endpoint."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"
        assert "version" in response.json()
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"

