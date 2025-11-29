# Debug Trace Data Collection Pipeline

Backend service for collecting high-fidelity developer debugging traces to improve AI coding capabilities.

## Project Plan

### 1. Clarifying Questions and Answers

**How granular are we looking? Keystrokes? Diff-based?**
- Diff-based is an easier start plus provides more insight, since the changes are more complete.

**How many devs should be using this at once? How many per session?**
- 100s for experimentation (probably many more in prod).

**How long is the debug session?**
- Several hours to a day (average time to fix simple to moderate bugs).

**Do we need real-time or can we collect it per commit/add etc?**
- We don't need to do it real-time, since what matters is the final result. Eventual consistency is ok.

**How detailed should the "chain-of-thought" be? What should we include?**
- Hypotheses about the bug, alternative approaches, reasoning behind change, notes about what worked or failed.

**Other assumptions:**
- One file per edit (probably different in Prod) since easier to parse/process; simplifies QA diff application.
- Data is internal-only, so storing raw code is allowed in the json.
- Chronological ordering is the most important; all events timestamped.

### 2. Proposed Data Schema

**High level structure:**

```json
{
  "trace_id": "uuid",
  "developer_id": "string",
  "repo_url": "string",
  "bug_description": "string",
  "events": [
    {
      "type": "edit|command|reasoning",
      "timestamp": "ISO8601",
      "details": {
        // For edit: { "file": "...", "change": "...", "diff": "..." }
        // For command: { "command": "...", "output": "...", "working_directory": "..." }
        // For reasoning: { "text": "...", "reasoning_type": "hypothesis", "confidence": "low|medium|high" }
      }
    }
  ],
  "qa_results": {
    "tests_passed": true,
    "reasoning_score": 4.5,
    "judge_comments": "..."
  }
}
```

**Justification:**
- Single chronological event list (simple and flexible for new event types).
- ML-friendly: diff, commands, reasoning all contained.
- Metadata (repo, bug description, tests) gives researchers full context.

### 3. High-Level Technical Plan

**Architecture Overview:**
```
Client/IDE → API Service (FastAPI) → SQLite Database → QA Pipeline (synchronous on submit) → Updated Trace
                                                              ↓
                                        QA branches: Docker Test Runner + LLM Judge
```

**Tech Stack:**
- **API Framework**: Python + FastAPI – Fast, async-ready, built-in JSON validation.
- **Database**: SQLite + SQLAlchemy – Lightweight, no external setup, sufficient for 100s of traces.
- **Containerization**: Docker + Docker Compose – Reproducible, one-command startup.
- **Code Execution**: Docker containers – Isolated for tests.
- **LLM Integration**: OpenAI API (GPT-4o) – High-quality reasoning eval, easy integration.
- **Testing**: pytest – Standard for Python.

**Why This Stack:**
- FastAPI: Lightweight for ingestion API.
- SQLite: Simple for MVP; queryable without complexity (upgrade to PostgreSQL for prod).
- Docker: Safety and isolation.
- OpenAI: Reliable for judging hypotheses/alternatives.
- No task queue (e.g., Celery): Synchronous QA is fine per "eventual consistency" answer; keeps MVP lean.

**Data Flow:**
1. Ingestion: Client sends JSON → FastAPI validates → stored in SQLite.
2. Processing: On final submit, QA runs synchronously (tests in Docker, LLM scoring).
3. Storage: Results merged into trace.

**Database Schema:**
```sql
-- Traces table
CREATE TABLE traces (
  trace_id TEXT PRIMARY KEY,
  developer_id TEXT NOT NULL,
  repo_url TEXT NOT NULL,
  bug_description TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Events table
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_timestamp TEXT NOT NULL,
  details TEXT NOT NULL,  -- JSON string
  FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);

-- QA Results table
CREATE TABLE qa_results (
  trace_id TEXT PRIMARY KEY,
  tests_passed INTEGER NOT NULL,  -- 0/1 for bool
  reasoning_score REAL NOT NULL,
  judge_comments TEXT,
  test_output TEXT,
  qa_timestamp TEXT NOT NULL,
  FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);
```

### 4. Scope & Trade-offs

**MVP (Must Have):**
- ✅ API endpoint accepts JSON traces.
- ✅ Persistence to database.
- ✅ Docker test validation.
- ✅ LLM reasoning scoring (1-5).
- ✅ QA results updated.
- ✅ One-command startup.
- ✅ E2E example.
- ✅ README with plan/instructions.

**Nice-to-Have (De-scoped):**
- ⏭️ Incremental ingestion (add if time).
- ⏭️ Auth/RBAC.
- ⏭️ Analytics dashboard.
- ⏭️ Webhooks.

**Key Trade-offs:**
- Simplicity over Scale: Synchronous processing; no queues for MVP.
- Basic Judging: Fixed rubric.
- Local Storage: SQLite for ease.

## Setup and Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `OPENAI_API_KEY`: Your OpenAI API key for LLM judging

### Running the Application

**One-command startup:**
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python -c "from app.database import init_db; init_db()"
```

4. Run the development server:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### `POST /api/traces`
Submit a complete trace for processing.

### `GET /api/traces/{trace_id}`
Retrieve a trace by ID, including all events and QA results.

### `POST /api/traces/{trace_id}/events` (Bonus)
Add an event to an existing trace (incremental ingestion).

### `POST /api/traces/{trace_id}/finalize`
Finalize a trace and trigger the QA pipeline.

## Testing

TODO: Add E2E test example

## Architecture

The system consists of:
- **API Layer**: FastAPI application handling HTTP requests
- **Data Layer**: SQLite database with SQLAlchemy ORM
- **QA Pipeline**: Synchronous processing of test validation and LLM judging
- **Docker Integration**: Isolated test execution environment

## Next Steps

1. Implement trace creation endpoint
2. Implement QA pipeline (Docker test runner + LLM judge)
3. Add E2E test example
4. Add error handling and validation
5. Implement incremental ingestion (bonus)

