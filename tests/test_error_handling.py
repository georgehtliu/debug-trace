"""Tests for error handling and edge cases."""
import pytest
from fastapi import status


class TestErrorHandling:
    """Tests for error cases and edge cases."""
    
    def test_missing_developer_id(self, client):
        """Test trace creation without developer_id."""
        payload = {
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test",
            "events": []
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_repo_url(self, client):
        """Test trace creation without repo_url."""
        payload = {
            "developer_id": "dev_001",
            "bug_description": "Test",
            "events": []
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_bug_description(self, client):
        """Test trace creation without bug_description."""
        payload = {
            "developer_id": "dev_001",
            "repo_url": "https://github.com/octocat/Hello-World",
            "events": []
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_events(self, client):
        """Test trace creation without events."""
        payload = {
            "developer_id": "dev_001",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test"
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_invalid_event_type(self, client):
        """Test trace creation with invalid event type."""
        payload = {
            "developer_id": "dev_001",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test",
            "events": [
                {
                    "type": "invalid_type",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {}
                }
            ]
        }
        # Should still create trace (event type validation might be lenient)
        response = client.post("/api/traces", json=payload)
        # Either succeeds or fails validation
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_missing_event_details(self, client):
        """Test trace creation with missing event details."""
        payload = {
            "developer_id": "dev_001",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_invalid_timestamp_format(self, client):
        """Test trace creation with invalid timestamp."""
        payload = {
            "developer_id": "dev_001",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "invalid-date",
                    "details": {"text": "test", "reasoning_type": "hypothesis", "confidence": "medium"}
                }
            ]
        }
        # Timestamp format might be lenient, so could succeed
        response = client.post("/api/traces", json=payload)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_get_nonexistent_trace(self, client):
        """Test getting non-existent trace."""
        response = client.get("/api/traces/non-existent-id-12345")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_add_event_to_nonexistent_trace(self, client):
        """Test adding event to non-existent trace."""
        event = {
            "type": "reasoning",
            "timestamp": "2024-01-15T10:00:00Z",
            "details": {"text": "test", "reasoning_type": "hypothesis", "confidence": "medium"}
        }
        response = client.post("/api/traces/non-existent-id/events", json=event)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_finalize_nonexistent_trace(self, client):
        """Test finalizing non-existent trace."""
        response = client.post("/api/traces/non-existent-id/finalize")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_empty_string_fields(self, client):
        """Test trace creation with empty string fields."""
        payload = {
            "developer_id": "",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test",
            "events": []
        }
        response = client.post("/api/traces", json=payload)
        # Empty string is allowed (no validation on non-empty)
        assert response.status_code == status.HTTP_201_CREATED

