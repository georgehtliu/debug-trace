"""Tests for QA pipeline functionality."""
import pytest
from fastapi import status


class TestQAPipeline:
    """Tests for QA pipeline evaluation."""
    
    def test_qa_pipeline_high_quality_reasoning(self, client):
        """Test QA pipeline with high-quality reasoning."""
        payload = {
            "developer_id": "dev_good_reasoning",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Null pointer exception in data processing",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "text": "The error occurs when data is null. I need to check where data comes from and add null checks at the entry point.",
                        "reasoning_type": "hypothesis",
                        "confidence": "high"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:01:00Z",
                    "details": {
                        "text": "Alternative approaches: 1) Add null check at entry point, 2) Use optional chaining, 3) Provide default value. I'll go with option 1 as it's the most explicit.",
                        "reasoning_type": "alternative",
                        "confidence": "medium"
                    }
                },
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:05:00Z",
                    "details": {
                        "file": "src/processor.js",
                        "change": "Added null check with early return",
                        "diff": "@@ -10,5 +10,7 @@\n function process(data) {\n+  if (!data) return null;\n   return data.map(...);\n }"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "qa_results" in data
        qa_results = data["qa_results"]
        assert "reasoning_score" in qa_results
        assert "judge_comments" in qa_results
        assert 1.0 <= qa_results["reasoning_score"] <= 5.0
        # High quality reasoning should score well (but may vary based on LLM)
        # We just check it's a valid score
    
    def test_qa_pipeline_low_quality_reasoning(self, client):
        """Test QA pipeline with low-quality reasoning."""
        payload = {
            "developer_id": "dev_poor_reasoning",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Something is broken",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "text": "Maybe it works now?",
                        "reasoning_type": "hypothesis",
                        "confidence": "low"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "qa_results" in data
        qa_results = data["qa_results"]
        assert "reasoning_score" in qa_results
        assert 1.0 <= qa_results["reasoning_score"] <= 5.0
    
    def test_qa_pipeline_no_reasoning_events(self, client):
        """Test QA pipeline with no reasoning events."""
        payload = {
            "developer_id": "dev_no_reasoning",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Bug fix without reasoning",
            "events": [
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "file": "src/file.js",
                        "change": "Fixed typo",
                        "diff": "@@ -1,1 +1,1 @@\n-consol.log(\"test\");\n+console.log(\"test\");"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "qa_results" in data
        # Should still return QA results even without reasoning events
        qa_results = data["qa_results"]
        assert "reasoning_score" in qa_results
    
    def test_qa_pipeline_multiple_reasoning_events(self, client):
        """Test QA pipeline with multiple reasoning events."""
        payload = {
            "developer_id": "dev_multi_reasoning",
            "repo_url": "https://github.com/octocat/Hello-World",
            "bug_description": "Performance issue in data processing",
            "events": [
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "details": {
                        "text": "The function is too slow. Need to optimize by reducing iterations or using memoization.",
                        "reasoning_type": "hypothesis",
                        "confidence": "high"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:01:00Z",
                    "details": {
                        "text": "Options: 1) Use memoization, 2) Reduce iterations, 3) Use more efficient algorithm. Memoization requires minimal code changes.",
                        "reasoning_type": "alternative",
                        "confidence": "medium"
                    }
                },
                {
                    "type": "reasoning",
                    "timestamp": "2024-01-15T10:02:00Z",
                    "details": {
                        "text": "Chose memoization as it requires minimal code changes and has good performance characteristics.",
                        "reasoning_type": "note",
                        "confidence": "high"
                    }
                },
                {
                    "type": "edit",
                    "timestamp": "2024-01-15T10:05:00Z",
                    "details": {
                        "file": "src/optimizer.js",
                        "change": "Added memoization cache",
                        "diff": "@@ -5,6 +5,8 @@\n+const cache = new Map();\n function expensive(data) {\n+  if (cache.has(data)) return cache.get(data);\n   const result = compute(data);\n+  cache.set(data, result);\n   return result;\n }"
                    }
                }
            ]
        }
        response = client.post("/api/traces", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "qa_results" in data
        qa_results = data["qa_results"]
        assert "reasoning_score" in qa_results
        assert "judge_comments" in qa_results
        # Multiple reasoning events should be evaluated together

