"""Tests for different event types."""
import pytest
from fastapi import status


class TestEventTypes:
    """Tests for various event types."""
    
    def test_reasoning_events(self, client):
        """Test trace with multiple reasoning events."""
        payload = {
            "developer_id": "dev_reasoning",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test reasoning events",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "text": "Hypothesis about the bug",
                        "reasoning_type": "hypothesis",
                        "confidence": "high"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:01:00Z",
                    "details": {
                        "text": "Alternative approach",
                        "reasoning_type": "alternative",
                        "confidence": "medium"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:02:00Z",
                    "details": {
                        "text": "Note about the solution",
                        "reasoning_type": "note",
                        "confidence": "high"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["events"]) == 3
        assert all(e["type"] == "reasoning" for e in data["events"])
    
    def test_command_events(self, client):
        """Test trace with command events."""
        payload = {
            "developer_id": "dev_commands",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test command events",
            "events": [
                {
                    "type": "command",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "command": "git log --oneline",
                        "output": "abc123 Fix bug",
                        "working_directory": "/project"
                    }
                },
                {
                    "type": "command",
                    "timestamp": "2024-01-15T10:05:00Z",
                    "details": {
                        "command": "npm test",
                        "output": "Tests passed",
                        "working_directory": "/project"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["events"]) == 2
        assert all(e["type"] == "command" for e in data["events"])
    
    def test_edit_events(self, client):
        """Test trace with edit events."""
        payload = {
            "developer_id": "dev_edits",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test edit events",
            "events": [
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "file": "src/file1.js",
                        "change": "Fixed bug",
                        "diff": "@@ -1,1 +1,1 @@\n-const x = 1;\n+const x = 2;"
                    }
                },
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:05:00Z",
                    "details": {
                        "file": "src/file2.js",
                        "change": "Added null check",
                        "diff": "@@ -5,6 +5,8 @@\n+if (!data) return;\n  return data.map(...);"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["events"]) == 2
        assert all(e["type"] == "edit" for e in data["events"])
    
    def test_mixed_event_types(self, client):
        """Test trace with mixed event types."""
        payload = {
            "developer_id": "dev_mixed",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Test mixed events",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "text": "Starting investigation",
                        "reasoning_type": "hypothesis",
                        "confidence": "medium"
                    }
                },
                {
                    "type": "command",
                    "timestamp": "2024-01-15T10:05:00Z",
                    "details": {
                        "command": "grep -r error src/",
                        "output": "src/file.js:10",
                        "working_directory": "/project"
                    }
                },
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:10:00Z",
                    "details": {
                        "file": "src/file.js",
                        "change": "Fixed error",
                        "diff": "@@ -10,5 +10,7 @@\n+try {\n   process();\n+} catch (e) {}\n"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:15:00Z",
                    "details": {
                        "text": "Fix applied successfully",
                        "reasoning_type": "note",
                        "confidence": "high"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["events"]) == 4
        event_types = [e["type"] for e in data["events"]]
        assert "reasoning" in event_types
        assert "command" in event_types
        assert "edit" in event_types

