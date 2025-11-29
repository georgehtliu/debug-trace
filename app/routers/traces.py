"""API endpoints for trace management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import json
from datetime import datetime

from app.database import get_db
from app.models import Trace, Event, QAResult
from app.schemas import TraceCreateSchema, TraceResponseSchema
from app.services.qa_pipeline import run_qa_pipeline

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.post("", response_model=TraceResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_trace(
    trace_data: TraceCreateSchema,
    db: Session = Depends(get_db)
):
    """
    Submit a complete trace for processing.
    
    This endpoint accepts a full trace with all events and triggers
    the QA pipeline synchronously.
    """
    # 1. Generate trace_id (UUID)
    trace_id = str(uuid.uuid4())
    # 2. Create Trace record
    trace = Trace(
        trace_id=trace_id,
        developer_id=trace_data.developer_id,
        repo_url=trace_data.repo_url,
        bug_description=trace_data.bug_description,
        status="pending",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    # 3. Create Event records
    db.add(trace)
    for event_data in trace_data.events:
        event = Event(
            trace_id=trace_id,
            event_type=event_data.type,
            event_timestamp=event_data.timestamp,
            details=json.dumps(event_data.details) if isinstance(event_data.details, dict) else str(event_data.details)
        )
        db.add(event)
    db.commit()
    db.refresh(trace)
    # 4. Trigger QA pipeline
    qa_result = await run_qa_pipeline(trace, db)
    trace.status = "completed"
    trace.updated_at = datetime.now().isoformat()
    db.commit()
    # 5. Return trace with QA results
    return TraceResponseSchema(
        trace_id=trace_id,
        developer_id=trace_data.developer_id,
        repo_url=trace_data.repo_url,
        bug_description=trace_data.bug_description,
        status="completed",
        created_at=trace.created_at,
        updated_at=trace.updated_at,
        events=[{"type": e.type, "timestamp": e.timestamp, "details": e.details} for e in trace_data.events],
        qa_results=qa_result
    )


@router.get("/{trace_id}", response_model=TraceResponseSchema)
async def get_trace(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a trace by ID, including all events and QA results.
    """
    # 1. Query Trace by trace_id
    trace = db.query(Trace).filter(Trace.trace_id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found"
        )
    # 2. Load associated events
    events = db.query(Event).filter(Event.trace_id == trace_id).all()
    # Convert events to schema format
    event_schemas = []
    for event in events:
        import json
        event_schemas.append({
            "type": event.event_type,
            "timestamp": event.event_timestamp,
            "details": json.loads(event.details) if isinstance(event.details, str) else event.details
        })
    # 3. Load QA results if available
    qa_result = db.query(QAResult).filter(QAResult.trace_id == trace_id).first()
    qa_result_schema = None
    if qa_result:
        from app.schemas import QAResultSchema
        qa_result_schema = QAResultSchema(
            tests_passed=bool(qa_result.tests_passed),
            reasoning_score=qa_result.reasoning_score,
            judge_comments=qa_result.judge_comments
        )
    # 4. Return combined response
    return TraceResponseSchema(
        trace_id=trace_id,
        developer_id=trace.developer_id,
        repo_url=trace.repo_url,
        bug_description=trace.bug_description,
        status=trace.status,
        created_at=trace.created_at,
        updated_at=trace.updated_at,
        events=event_schemas,
        qa_results=qa_result_schema
    )

@router.post("/{trace_id}/events", status_code=status.HTTP_201_CREATED)
async def add_event(
    trace_id: str,
    event: dict,  # TODO: Use proper schema
    db: Session = Depends(get_db)
):
    """
    Add an event to an existing trace (incremental ingestion - bonus feature).
    
    This allows clients to continuously export events during a session
    rather than uploading everything at the end.
    """
    # 1. Verify trace exists
    trace = db.query(Trace).filter(Trace.trace_id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found"
        )
    # 2. Validate event schema
    event = Event(
        trace_id=trace_id,
        event_type=event.type,
        event_timestamp=event.timestamp,
        details=event.details
    )
    db.add(event)
    db.commit()
    # 3. Create Event record
    return {"message": "Event added successfully"}


@router.post("/{trace_id}/finalize", response_model=TraceResponseSchema)
async def finalize_trace(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """
    Finalize a trace and trigger the QA pipeline.
    
    This is used when incremental ingestion is enabled - it signals
    that the trace is complete and ready for QA processing.
    """
    # 1. Verify trace exists and is in 'pending' status
    trace = db.query(Trace).filter(Trace.trace_id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found"
        )
    if trace.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trace is not in 'pending' status"
        )
    # 2. Trigger QA pipeline
    qa_result = await run_qa_pipeline(trace, db)
    # 3. Update trace status
    trace.status = "completed"
    trace.updated_at = datetime.now().isoformat()
    db.commit()
    # 4. Return trace with QA results
    return TraceResponseSchema(
        trace_id=trace_id,
        developer_id=trace.developer_id,
        repo_url=trace.repo_url,
        bug_description=trace.bug_description,
        status="completed",
        created_at=trace.created_at,
        updated_at=trace.updated_at,
        events=trace.events,
        qa_results=qa_result
    )

