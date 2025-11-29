"""Database models for traces, events, and QA results."""
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Trace(Base):
    """Trace model representing a complete debugging session."""
    __tablename__ = "traces"

    trace_id = Column(String, primary_key=True, index=True)
    developer_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    bug_description = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(String, nullable=False)  # ISO8601 timestamp
    updated_at = Column(String, nullable=False)  # ISO8601 timestamp

    # Relationships
    events = relationship("Event", back_populates="trace", cascade="all, delete-orphan")
    qa_result = relationship("QAResult", back_populates="trace", uselist=False, cascade="all, delete-orphan")


class Event(Base):
    """Event model representing individual events in a trace."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trace_id = Column(String, ForeignKey("traces.trace_id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)  # 'edit', 'command', 'reasoning'
    event_timestamp = Column(String, nullable=False)  # ISO8601 timestamp
    details = Column(Text, nullable=False)  # JSON string

    # Relationships
    trace = relationship("Trace", back_populates="events")


class QAResult(Base):
    """QA result model storing test and reasoning evaluation results."""
    __tablename__ = "qa_results"

    trace_id = Column(String, ForeignKey("traces.trace_id", ondelete="CASCADE"), primary_key=True)
    tests_passed = Column(Integer, nullable=False)  # 0/1 (SQLite doesn't have BOOLEAN)
    reasoning_score = Column(Float, nullable=False)  # 1.0-5.0
    judge_comments = Column(Text)
    test_output = Column(Text)  # Store test logs for debugging
    qa_timestamp = Column(String, nullable=False)  # ISO8601 timestamp

    # Relationships
    trace = relationship("Trace", back_populates="qa_result")

