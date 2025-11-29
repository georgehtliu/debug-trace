"""Pytest configuration and shared fixtures."""

import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app import database
from app.database import Base, get_db
from app.main import app
from app.models import QAResult as QAResultModel
from app.models import Trace, Event, QAResult  # noqa: F401


@pytest.fixture(scope="function")
def mock_qa_pipeline():
    """Mock QA pipeline to avoid Docker/LLM calls in tests."""

    async def mock_run_qa_pipeline(trace, db):
        """Return a mock QA result."""
        existing = (
            db.query(QAResultModel)
            .filter(QAResultModel.trace_id == trace.trace_id)
            .first()
        )
        if existing:
            return existing

        qa_result = QAResultModel(
            trace_id=trace.trace_id,
            tests_passed=1,
            reasoning_score=3.5,
            judge_comments="Mock QA result for testing",
            test_output="Mock test output",
            qa_timestamp=datetime.now().isoformat(),
        )
        db.add(qa_result)
        db.commit()
        db.refresh(qa_result)
        return qa_result

    with patch("app.routers.traces.run_qa_pipeline", side_effect=mock_run_qa_pipeline):
        yield


@pytest.fixture(scope="function")
def client(mock_qa_pipeline):
    """Create a test client with isolated SQLite DB and mocked QA pipeline."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    db_path = temp_db.name

    test_engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    tables = inspect(test_engine).get_table_names()
    assert "traces" in tables
    assert "events" in tables
    assert "qa_results" in tables

    original_engine = database.engine
    original_session_local = database.SessionLocal

    database.engine = test_engine
    database.SessionLocal = TestingSessionLocal

    def override_get_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    with patch("app.database.init_db", lambda: None):
        app.dependency_overrides[get_db] = override_get_db
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()
            database.engine = original_engine
            database.SessionLocal = original_session_local
            Base.metadata.drop_all(bind=test_engine)
            test_engine.dispose()
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass


@pytest.fixture
def sample_trace_data():
    """Sample trace data for testing."""
    return {
        "developer_id": "dev_001",
        "repo_url": "https://github.com/octocat/Hello-World",
        "bug_description": "The login button does not respond when clicked",
        "events": [
            {
                "type": "reasoning",
                "timestamp": "2024-01-15T10:00:00Z",
                "details": {
                    "text": "I suspect the issue is in the event handler",
                    "reasoning_type": "hypothesis",
                    "confidence": "high",
                },
            },
            {
                "type": "command",
                "timestamp": "2024-01-15T10:05:00Z",
                "details": {
                    "command": "grep -r login-button src/",
                    "output": "src/components/Login.jsx:15",
                    "working_directory": "/project",
                },
            },
            {
                "type": "edit",
                "timestamp": "2024-01-15T10:10:00Z",
                "details": {
                    "file": "src/components/Login.jsx",
                    "change": "Added event listener",
                    "diff": '@@ -15,6 +15,8 @@\n+document.getElementById("login-button").addEventListener("click", handleLogin);\n+',
                },
            },
        ],
    }
