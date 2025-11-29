# Test Commands for Debug Trace API

## Quick Test (One-Line Commands)

### 1. Health Check
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

### 2. Root Endpoint
```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

### 3. Create Trace (Full Submission - Triggers QA Pipeline)
```bash
curl -s -X POST http://localhost:8000/api/traces -H "Content-Type: application/json" -d '{"developer_id":"dev_001","repo_url":"https://github.com/octocat/Hello-World","bug_description":"The login button does not respond when clicked","events":[{"type":"reasoning","timestamp":"2024-01-15T10:00:00Z","details":{"text":"I suspect the issue is in the event handler. The button might not be properly bound to the click event.","reasoning_type":"hypothesis","confidence":"high"}},{"type":"command","timestamp":"2024-01-15T10:05:00Z","details":{"command":"grep -r \"login-button\" src/","output":"src/components/Login.jsx:15: <button id=\"login-button\">","working_directory":"/project"}},{"type":"edit","timestamp":"2024-01-15T10:10:00Z","details":{"file":"src/components/Login.jsx","change":"Added event listener to login button","diff":"@@ -15,6 +15,8 @@\n <button id=\"login-button\">Login</button>\n+document.getElementById(\"login-button\").addEventListener(\"click\", handleLogin);\n+"}},{"type":"reasoning","timestamp":"2024-01-15T10:15:00Z","details":{"text":"I added the event listener. This should fix the issue. Let me test it.","reasoning_type":"note","confidence":"medium"}},{"type":"command","timestamp":"2024-01-15T10:20:00Z","details":{"command":"npm test","output":"Tests passed: 15/15","working_directory":"/project"}}]}' | python3 -m json.tool
```

### 4. Get Trace by ID (Replace TRACE_ID with actual ID from step 3)
```bash
TRACE_ID="your-trace-id-here"
curl -s http://localhost:8000/api/traces/$TRACE_ID | python3 -m json.tool
```

### 5. Create Trace for Incremental Ingestion
```bash
curl -s -X POST http://localhost:8000/api/traces -H "Content-Type: application/json" -d '{"developer_id":"dev_002","repo_url":"https://github.com/octocat/Hello-World","bug_description":"Test incremental ingestion","events":[{"type":"reasoning","timestamp":"2024-01-15T11:00:00Z","details":{"text":"Starting to investigate the bug","reasoning_type":"hypothesis","confidence":"low"}}]}' | python3 -m json.tool
```

### 6. Add Event to Trace (Incremental - Replace TRACE_ID)
```bash
TRACE_ID="your-trace-id-here"
curl -s -X POST http://localhost:8000/api/traces/$TRACE_ID/events -H "Content-Type: application/json" -d '{"type":"command","timestamp":"2024-01-15T11:05:00Z","details":{"command":"git log --oneline","output":"abc123 Fix typo\n def456 Add feature","working_directory":"/project"}}' | python3 -m json.tool
```

### 7. Finalize Trace (Triggers QA Pipeline - Replace TRACE_ID)
```bash
TRACE_ID="your-trace-id-here"
curl -s -X POST http://localhost:8000/api/traces/$TRACE_ID/finalize | python3 -m json.tool
```

### 8. Get Finalized Trace (Replace TRACE_ID)
```bash
TRACE_ID="your-trace-id-here"
curl -s http://localhost:8000/api/traces/$TRACE_ID | python3 -m json.tool
```

## Using the Test Script

Run all tests at once:
```bash
./test_endpoints.sh
```

## Manual Step-by-Step Testing

### Step 1: Create a trace and capture the trace_id
```bash
RESPONSE=$(curl -s -X POST http://localhost:8000/api/traces -H "Content-Type: application/json" -d '{"developer_id":"dev_001","repo_url":"https://github.com/octocat/Hello-World","bug_description":"Test bug","events":[{"type":"reasoning","timestamp":"2024-01-15T10:00:00Z","details":{"text":"Testing","reasoning_type":"hypothesis","confidence":"medium"}}]}')
TRACE_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])")
echo "Trace ID: $TRACE_ID"
```

### Step 2: Get the trace
```bash
curl -s http://localhost:8000/api/traces/$TRACE_ID | python3 -m json.tool
```

### Step 3: Add an event (if using incremental ingestion)
```bash
curl -s -X POST http://localhost:8000/api/traces/$TRACE_ID/events -H "Content-Type: application/json" -d '{"type":"command","timestamp":"2024-01-15T10:05:00Z","details":{"command":"ls -la","output":"file1 file2","working_directory":"/project"}}' | python3 -m json.tool
```

### Step 4: Finalize and trigger QA
```bash
curl -s -X POST http://localhost:8000/api/traces/$TRACE_ID/finalize | python3 -m json.tool
```

## Expected Responses

- **Health Check**: `{"status":"healthy"}`
- **Create Trace**: Returns trace with `trace_id`, `status: "completed"` (after QA), and `qa_results`
- **Get Trace**: Returns full trace with events and QA results
- **Add Event**: Returns `{"message": "Event added successfully"}`
- **Finalize**: Returns trace with updated status and QA results

## Notes

- The QA pipeline may take 30-60 seconds to complete (Docker build + test execution + LLM evaluation)
- If the repository URL is not accessible, the Docker test step will fail gracefully
- The LLM evaluation requires a valid OpenAI API key in `.env`

