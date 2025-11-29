#!/bin/bash
# Test script for Debug Trace API endpoints

BASE_URL="http://localhost:8000"
echo "Testing Debug Trace API endpoints..."
echo ""

# 1. Health check
echo "1. Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo -e "\n"

# 2. Root endpoint
echo "2. Root Endpoint:"
curl -s "$BASE_URL/" | python3 -m json.tool
echo -e "\n"

# 3. Create a trace with full data (triggers QA pipeline)
echo "3. Create Trace (Full Submission):"
TRACE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_001",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "The login button does not respond when clicked",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "text": "I suspect the issue is in the event handler. The button might not be properly bound to the click event.",
          "reasoning_type": "hypothesis",
          "confidence": "high"
        }
      },
      {
        "type": "command",
        "timestamp": "2024-01-15T10:05:00Z",
        "details": {
          "command": "grep -r \"login-button\" src/",
          "output": "src/components/Login.jsx:15: <button id=\"login-button\">",
          "working_directory": "/project"
        }
      },
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:10:00Z",
        "details": {
          "file": "src/components/Login.jsx",
          "change": "Added event listener to login button",
          "diff": "@@ -15,6 +15,8 @@\n <button id=\"login-button\">Login</button>\n+document.getElementById(\"login-button\").addEventListener(\"click\", handleLogin);\n+"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:15:00Z",
        "details": {
          "text": "I added the event listener. This should fix the issue. Let me test it.",
          "reasoning_type": "note",
          "confidence": "medium"
        }
      },
      {
        "type": "command",
        "timestamp": "2024-01-15T10:20:00Z",
        "details": {
          "command": "npm test",
          "output": "Tests passed: 15/15",
          "working_directory": "/project"
        }
      }
    ]
  }')

echo "$TRACE_RESPONSE" | python3 -m json.tool
TRACE_ID=$(echo "$TRACE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])")
echo -e "\nTrace ID: $TRACE_ID\n"

# 4. Get trace by ID
echo "4. Get Trace by ID:"
curl -s "$BASE_URL/api/traces/$TRACE_ID" | python3 -m json.tool
echo -e "\n"

# 5. Create a trace for incremental ingestion test
echo "5. Create Trace for Incremental Ingestion:"
INCREMENTAL_TRACE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_002",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Test incremental ingestion",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T11:00:00Z",
        "details": {
          "text": "Starting to investigate the bug",
          "reasoning_type": "hypothesis",
          "confidence": "low"
        }
      }
    ]
  }')

INCREMENTAL_TRACE_ID=$(echo "$INCREMENTAL_TRACE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])" 2>/dev/null || echo "")
echo "Incremental Trace ID: $INCREMENTAL_TRACE_ID"
echo -e "\n"

# 6. Add event to trace (incremental ingestion - bonus feature)
if [ ! -z "$INCREMENTAL_TRACE_ID" ]; then
  echo "6. Add Event to Trace (Incremental):"
  curl -s -X POST "$BASE_URL/api/traces/$INCREMENTAL_TRACE_ID/events" \
    -H "Content-Type: application/json" \
    -d '{
      "type": "command",
      "timestamp": "2024-01-15T11:05:00Z",
      "details": {
        "command": "git log --oneline",
        "output": "abc123 Fix typo\n def456 Add feature",
        "working_directory": "/project"
      }
    }' | python3 -m json.tool
  echo -e "\n"
fi

# 7. Finalize trace (triggers QA pipeline)
if [ ! -z "$INCREMENTAL_TRACE_ID" ]; then
  echo "7. Finalize Trace (Trigger QA):"
  curl -s -X POST "$BASE_URL/api/traces/$INCREMENTAL_TRACE_ID/finalize" | python3 -m json.tool
  echo -e "\n"
fi

# 8. Get trace after finalization
if [ ! -z "$INCREMENTAL_TRACE_ID" ]; then
  echo "8. Get Finalized Trace:"
  curl -s "$BASE_URL/api/traces/$INCREMENTAL_TRACE_ID" | python3 -m json.tool
  echo -e "\n"
fi

echo "Testing complete!"

