"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class EventDetailEdit(BaseModel):
    """Details for an edit event."""
    file: str
    change: str
    diff: str


class EventDetailCommand(BaseModel):
    """Details for a command event."""
    command: str
    output: str
    working_directory: Optional[str] = None


class EventDetailReasoning(BaseModel):
    """Details for a reasoning event."""
    text: str
    reasoning_type: str = Field(..., description="e.g., 'hypothesis', 'alternative', 'note'")
    confidence: str = Field(..., description="'low', 'medium', or 'high'")


class EventSchema(BaseModel):
    """Schema for a single event."""
    type: str = Field(..., description="'edit', 'command', or 'reasoning'")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    details: Dict[str, Any]  # Flexible to handle different event types


class QAResultSchema(BaseModel):
    """Schema for QA results with enhanced evaluation details."""
    tests_passed: bool
    reasoning_score: float = Field(..., ge=1.0, le=5.0, description="Score from 1.0 to 5.0")
    judge_comments: Optional[str] = None
    detailed_scores: Optional[Dict[str, float]] = Field(None, description="Per-criterion scores (1.0-5.0)")
    strengths: Optional[List[str]] = Field(None, description="List of identified strengths")
    weaknesses: Optional[List[str]] = Field(None, description="List of identified weaknesses")
    recommendations: Optional[List[str]] = Field(None, description="List of improvement recommendations")


class TraceCreateSchema(BaseModel):
    """Schema for creating a new trace."""
    developer_id: str
    repo_url: str
    bug_description: str
    events: List[EventSchema]


class TraceResponseSchema(BaseModel):
    """Schema for trace response."""
    trace_id: str
    developer_id: str
    repo_url: str
    bug_description: str
    status: str
    created_at: str
    updated_at: str
    events: List[EventSchema]
    qa_results: Optional[QAResultSchema] = None

    class Config:
        from_attributes = True

