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
  status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
  created_at TEXT NOT NULL,  -- ISO8601 timestamp
  updated_at TEXT NOT NULL   -- ISO8601 timestamp
);

-- Events table
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT NOT NULL,
  event_type TEXT NOT NULL,  -- 'edit', 'command', 'reasoning'
  event_timestamp TEXT NOT NULL,  -- ISO8601 timestamp
  details TEXT NOT NULL,  -- JSON string
  FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);

-- QA Results table (Enhanced with detailed evaluation fields)
CREATE TABLE qa_results (
  trace_id TEXT PRIMARY KEY,
  tests_passed INTEGER NOT NULL,  -- 0/1 (SQLite boolean)
  reasoning_score REAL NOT NULL,  -- 1.0-5.0
  judge_comments TEXT,
  test_output TEXT,  -- Store test logs for debugging
  qa_timestamp TEXT NOT NULL,  -- ISO8601 timestamp
  -- Enhanced fields for detailed evaluation
  detailed_scores TEXT,  -- JSON string with per-criterion scores
  strengths TEXT,  -- JSON string array of strengths
  weaknesses TEXT,  -- JSON string array of weaknesses
  recommendations TEXT,  -- JSON string array of recommendations
  FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);
```

### 4. Scope & Trade-offs

**MVP (Must Have):**
- ✅ API endpoint accepts JSON traces.
- ✅ Persistence to database.
- ✅ Docker test validation.
- ✅ Enhanced LLM reasoning scoring (1-5) with detailed rubric.
- ✅ QA results updated with comprehensive feedback.
- ✅ One-command startup with Docker Compose.
- ✅ E2E example and comprehensive test suite.
- ✅ README with plan/instructions.
- ✅ Incremental ingestion (bonus feature - implemented!).
- ✅ Comprehensive pytest test suite (36 tests).

**Nice-to-Have (De-scoped):**
- ⏭️ Auth/RBAC.
- ⏭️ Analytics dashboard.
- ⏭️ Webhooks.
- ⏭️ Async task queue (Celery/RQ).

**Key Trade-offs:**
- Simplicity over Scale: Synchronous processing; no queues for MVP.
- Basic Judging: Fixed rubric.
- Local Storage: SQLite for ease.

## Setup and Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults shown)
DATABASE_URL=sqlite:///./traces.db
HOST=0.0.0.0
PORT=8000
```

**Required variables:**
- `OPENAI_API_KEY`: Your OpenAI API key for LLM judging (required for QA pipeline)

**Optional variables:**
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `HOST`: Server host (defaults to `0.0.0.0`)
- `PORT`: Server port (defaults to `8000`)

> **Note:** The `.env` file is gitignored for security. Never commit API keys.

### Running the Application

**One-command startup:**
```bash
docker compose up
```

Note: On modern Docker installations (especially Apple Silicon), use `docker compose` (with space) instead of `docker-compose` (with hyphen).

The API will be available at `http://localhost:8000`

**API Documentation:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

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

### Health & Status

#### `GET /`
Root health check endpoint.
```json
{
  "status": "ok",
  "message": "Debug Trace Data Collection Pipeline API",
  "version": "0.1.0"
}
```

#### `GET /health`
Health check endpoint.
```json
{
  "status": "healthy"
}
```

### Trace Management

#### `POST /api/traces`
Submit a complete trace for processing. Automatically triggers QA pipeline.

**Request Body:** See `example_trace.json` for a complete example.

**Response:** `201 Created` - Returns `TraceResponseSchema` with QA results included.

**Features:**
- Validates input schema
- Generates UUID trace_id
- Stores trace and events in database
- Automatically triggers QA pipeline (Docker tests + LLM judge)
- Returns enhanced QA results with detailed scores, strengths, weaknesses, recommendations

#### `GET /api/traces/{trace_id}`
Retrieve a trace by ID, including all events and QA results.

**Path Parameters:**
- `trace_id` (string): UUID of the trace

**Response:** `200 OK` - Returns `TraceResponseSchema` with:
- Full trace metadata
- All events (reasoning, command, edit)
- Complete QA results (if available)

**Error Responses:**
- `404 Not Found`: Trace not found

#### `POST /api/traces/{trace_id}/events` (Bonus Feature)
Add an event to an existing trace (incremental ingestion).

**Path Parameters:**
- `trace_id` (string): UUID of the trace

**Request Body:**
```json
{
  "type": "reasoning|command|edit",
  "timestamp": "ISO8601",
  "details": { ... }
}
```

**Response:** `201 Created`
```json
{
  "message": "Event added successfully",
  "event_id": <integer>
}
```

**Error Responses:**
- `404 Not Found`: Trace not found
- `400 Bad Request`: Missing required fields (type or timestamp)

#### `POST /api/traces/{trace_id}/finalize`
Finalize a trace and trigger the QA pipeline. Used for incremental ingestion workflow.

**Path Parameters:**
- `trace_id` (string): UUID of the trace

**Response:** `200 OK` - Returns `TraceResponseSchema` with updated status and QA results

**Error Responses:**
- `404 Not Found`: Trace not found
- `400 Bad Request`: Trace is not in 'pending' status

### Workflow Examples

**Full Submission Workflow:**
1. `POST /api/traces` → Creates trace, triggers QA, returns results

**Incremental Ingestion Workflow:**
1. `POST /api/traces` → Create trace with initial events (status: "pending")
2. `POST /api/traces/{trace_id}/events` → Add more events as they occur
3. `POST /api/traces/{trace_id}/finalize` → Finalize and trigger QA
4. `GET /api/traces/{trace_id}` → Retrieve final trace with QA results

## Testing

### Running Tests

**Run all tests:**
```bash
docker compose exec api pytest tests/ -v
```

**Run specific test file:**
```bash
docker compose exec api pytest tests/test_traces.py -v
```

**Run with coverage:**
```bash
docker compose exec api pytest tests/ --cov=app --cov-report=term-missing
```

### Test Coverage

The project includes comprehensive pytest tests (36 tests passing):

- ✅ **Unit tests** for each endpoint (`test_traces.py`)
- ✅ **Error handling tests** (`test_error_handling.py`)
- ✅ **Event type validation** (`test_event_types.py`)
- ✅ **QA pipeline integration** (`test_qa_pipeline.py`)
- ✅ **Incremental ingestion workflow** (`test_incremental.py`)
- ✅ **Health check endpoints** (`test_api.py`)

All tests use isolated SQLite databases and mock external dependencies (Docker, OpenAI API) for fast, reliable execution.

### End-to-End Example

See `example_trace.json` for a complete example trace. You can submit it using:

```bash
curl -X POST http://localhost:8000/api/traces \
  -H "Content-Type: application/json" \
  -d @example_trace.json
```

Or use the one-liner commands in `TEST_COMMANDS.md` for quick testing.

## Architecture

### System Components

```
┌─────────────┐
│   Client    │
│  (IDE/App)  │
└──────┬──────┘
       │ HTTP/JSON
       ▼
┌─────────────────────────────────────┐
│      FastAPI Application            │
│  ┌───────────────────────────────┐  │
│  │   API Endpoints              │  │
│  │   - POST /api/traces         │  │
│  │   - GET /api/traces/{id}     │  │
│  │   - POST /api/traces/{id}/   │  │
│  │     events                   │  │
│  │   - POST /api/traces/{id}/   │  │
│  │     finalize                 │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      SQLite Database                 │
│  ┌──────────┐  ┌──────────┐        │
│  │  Traces  │  │  Events  │        │
│  └──────────┘  └──────────┘        │
│  ┌──────────┐                       │
│  │QA Results│                       │
│  └──────────┘                       │
└──────────────────────────────────────┘
               │
               ▼ (on finalize/submit)
┌─────────────────────────────────────┐
│         QA Pipeline                  │
│  ┌───────────────────────────────┐  │
│  │  1. Docker Test Runner        │  │
│  │     - Clone repo              │  │
│  │     - Apply diffs             │  │
│  │     - Run tests               │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  2. LLM Judge (GPT-4o)       │  │
│  │     - Evaluate reasoning      │  │
│  │     - Score (1.0-5.0)        │  │
│  │     - Provide feedback        │  │
│  └───────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Key Components

- **API Layer**: FastAPI application handling HTTP requests with automatic validation
- **Data Layer**: SQLite database with SQLAlchemy ORM (upgradeable to PostgreSQL)
- **QA Pipeline**: Synchronous processing of test validation and LLM judging
- **Docker Integration**: Isolated test execution environment for safety
- **LLM Integration**: OpenAI GPT-4o for reasoning quality evaluation

## Enhanced AI Judge

The system includes an enhanced AI judge that evaluates developer reasoning quality using a comprehensive rubric. See `ENHANCED_AI_JUDGE.md` for detailed documentation.

### Key Features

- **Weighted Rubric**: 6 evaluation criteria with specific weights
  - Hypothesis Quality (20%)
  - Reasoning Chain Quality (25%)
  - Alternative Exploration (15%)
  - Action-Reasoning Alignment (20%)
  - Confidence Calibration (10%)
  - Efficiency (10%)

- **Temporal Reasoning Chains**: Tracks how reasoning events lead to actions
- **Test-Aware Evaluation**: Considers test results in scoring
- **Structured Output**: Detailed scores, strengths, weaknesses, and recommendations

### Example QA Result

```json
{
  "tests_passed": true,
  "reasoning_score": 4.2,
  "judge_comments": "The developer demonstrated strong reasoning...",
  "detailed_scores": {
    "hypothesis_quality": 4.5,
    "reasoning_chain": 4.3,
    "alternative_exploration": 3.8,
    "action_reasoning_alignment": 4.5,
    "confidence_calibration": 4.0,
    "efficiency": 4.2
  },
  "strengths": [
    "Clear hypothesis formation",
    "Systematic approach to testing"
  ],
  "weaknesses": [
    "Limited consideration of edge cases"
  ],
  "recommendations": [
    "Consider edge cases earlier in the process"
  ]
}
```

## Error Handling

The API implements comprehensive error handling:

- **Validation Errors** (`422 Unprocessable Entity`): Invalid request schema
- **Not Found** (`404 Not Found`): Trace or resource not found
- **Bad Request** (`400 Bad Request`): Invalid operation (e.g., finalizing non-pending trace)
- **Internal Server Error** (`500`): Unexpected errors (logged for debugging)

All errors return structured JSON responses with descriptive messages.

## Production Considerations

### Current Limitations (MVP)

- **Synchronous Processing**: QA pipeline runs synchronously (may take 30-60 seconds)
- **SQLite Database**: Suitable for development/testing, consider PostgreSQL for production
- **No Authentication**: All endpoints are public (add auth middleware for production)
- **No Rate Limiting**: Consider adding rate limiting for production use
- **CORS**: Currently allows all origins (restrict in production)

### Recommended Production Upgrades

1. **Database**: Migrate to PostgreSQL for better concurrency and scalability
2. **Task Queue**: Use Celery/RQ for async QA pipeline processing
3. **Authentication**: Add JWT or OAuth2 authentication
4. **Rate Limiting**: Implement rate limiting middleware
5. **Monitoring**: Add logging, metrics, and health checks
6. **Caching**: Cache LLM responses for similar traces
7. **Backup**: Implement database backup strategy
8. **Security**: Review and harden security settings

### Environment-Specific Configuration

Use environment variables for configuration:
- `DATABASE_URL`: Database connection string
- `OPENAI_API_KEY`: OpenAI API key (required)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)

## Project Status

✅ **MVP Complete**: All core features implemented and tested
- API endpoints fully functional
- QA pipeline with Docker tests and LLM judge
- Comprehensive test suite (36 tests)
- Enhanced AI judge with detailed evaluation
- Incremental ingestion support
- Complete documentation

🚀 **Ready for**: Development, testing, and evaluation use cases

📋 **Future Enhancements**: See `ENHANCED_AI_JUDGE.md` for potential improvements

