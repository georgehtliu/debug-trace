"""Pytest configuration and shared fixtures."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
# Import models to ensure they're registered with Base
from app.models import Trace, Event, QAResult  # noqa: F401
from app.models import QAResult as QAResultModel
from datetime import datetime


# Use in-memory SQLite for testing
# Create a new engine for each test to ensure isolation
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    # Create a new in-memory database for each test
    test_engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    # Ensure models are imported and registered
    from app.models import Trace, Event, QAResult  # noqa: F401
    # Create all tables - must be done after models are imported
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture(scope="function")
def mock_qa_pipeline():
    """Mock QA pipeline to avoid Docker/LLM calls in tests."""
    async def mock_run_qa_pipeline(trace, db):
        """Return a mock QA result."""
        qa_result = QAResultModel(
            trace_id=trace.trace_id,
            tests_passed=1,  # True
            reasoning_score=3.5,
            judge_comments="Mock QA result for testing",
            test_output="Mock test output",
            qa_timestamp=datetime.now().isoformat()
        )
        db.add(qa_result)
        db.commit()
        db.refresh(qa_result)
        return qa_result
    
    with patch('app.routers.traces.run_qa_pipeline', side_effect=mock_run_qa_pipeline):
        yield


@pytest.fixture(scope="function")
def client(db_session, mock_qa_pipeline):
    """Create a test client with database override and mocked QA pipeline."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


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
                    "confidence": "high"
                }
            },
            {
                "type": "command",
                "timestamp": "2024-01-15T10:05:00Z",
                "details": {
                    "command": "grep -r login-button src/",
                    "output": "src/components/Login.jsx:15",
                    "working_directory": "/project"
                }
            },
            {
                "type": "edit",
                "timestamp": "2024-01-15T10:10:00Z",
                "details": {
                    "file": "src/components/Login.jsx",
                    "change": "Added event listener",
                    "diff": "@@ -15,6 +15,8 @@\n+document.getElementById(\"login-button\").addEventListener(\"click\", handleLogin);\n+"
                }
            }
        ]
    }
