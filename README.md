# Debug Trace Collector

A backend service that captures the full debugging process—not just code changes, but the reasoning, commands, and hypotheses behind each fix. Built to help train better AI coding assistants.

## The Idea

Most tools only track what changed. I wanted to capture *why* it changed. When you debug, you form hypotheses, run commands, explore alternatives. This project collects all of that, then automatically validates fixes and uses GPT-4o to evaluate the quality of your debugging reasoning.

## How It Works

You send in debugging traces with three types of events:
- **Reasoning**: Your hypotheses and thought process
- **Command**: Terminal commands you ran
- **Edit**: Code changes with diffs

When you finalize a trace, it:
1. Clones the repo and applies your edits
2. Runs tests in Docker
3. Uses GPT-4o to score your debugging quality (1-5 scale)
4. Returns detailed feedback on strengths, weaknesses, and recommendations

Built with FastAPI, SQLite, Docker, and OpenAI's API.

## Quick Start

```bash
# Set your OpenAI API key
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Start everything
docker compose up
```

API runs at `http://localhost:8000`. Docs at `/docs`.

## API

- `POST /api/traces` - Submit a trace (runs QA automatically)
- `GET /api/traces/{id}` - Get trace with QA results
- `POST /api/traces/{id}/events` - Add events incrementally
- `POST /api/traces/{id}/finalize` - Manually trigger QA

Example trace format:
```json
{
  "developer_id": "dev_001",
  "repo_url": "https://github.com/example/repo",
  "bug_description": "Login button doesn't work",
  "events": [
    {
      "type": "reasoning",
      "timestamp": "2024-01-15T10:00:00Z",
      "details": {
        "text": "I think it's an event handler issue",
        "reasoning_type": "hypothesis",
        "confidence": "high"
      }
    },
    {
      "type": "command",
      "timestamp": "2024-01-15T10:05:00Z",
      "details": {
        "command": "grep -r login-button src/",
        "output": "src/components/Login.jsx:15"
      }
    }
  ]
}
```

## Local Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -c "from app.database import init_db; init_db()"
uvicorn app.main:app --reload
```

## Testing

```bash
pytest
```

## What I Learned

The hardest part was getting database tests working—SQLite's in-memory DBs are connection-specific, so I switched to temporary file-based DBs. Docker test execution required handling different project types and applying diffs correctly. Getting consistent JSON from GPT-4o needed structured outputs and robust parsing.

## Next Steps

Planning to build a VSCode extension for automatic trace collection, add a frontend dashboard, and migrate to PostgreSQL + async processing for production scale.

**Status**: MVP complete ✅
