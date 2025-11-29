#!/bin/bash
# Test incremental ingestion workflow

BASE_URL="http://localhost:8000"
echo "Testing Incremental Ingestion Workflow..."
echo ""

# 1. Create initial trace with one event
echo "1. Create Initial Trace:"
INITIAL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_incremental",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Testing incremental ingestion",
    "events": [{
      "type": "reasoning",
      "timestamp": "2024-01-15T10:00:00Z",
      "details": {
        "text": "Starting investigation",
        "reasoning_type": "hypothesis",
        "confidence": "low"
      }
    }]
  }')

TRACE_ID=$(echo "$INITIAL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])" 2>/dev/null)
echo "Trace ID: $TRACE_ID"
echo "$INITIAL_RESPONSE" | python3 -m json.tool | head -15
echo -e "\n"

if [ -z "$TRACE_ID" ]; then
    echo "Failed to create trace. Exiting."
    exit 1
fi

# 2. Add command event
echo "2. Add Command Event:"
curl -s -X POST "$BASE_URL/api/traces/$TRACE_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "command",
    "timestamp": "2024-01-15T10:05:00Z",
    "details": {
      "command": "git log --oneline -5",
      "output": "abc123 Fix bug\ndef456 Add feature",
      "working_directory": "/project"
    }
  }' | python3 -m json.tool
echo -e "\n"

# 3. Add reasoning event
echo "3. Add Reasoning Event:"
curl -s -X POST "$BASE_URL/api/traces/$TRACE_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "reasoning",
    "timestamp": "2024-01-15T10:10:00Z",
    "details": {
      "text": "Looking at the git history, I see recent changes. Let me check the diff.",
      "reasoning_type": "hypothesis",
      "confidence": "medium"
    }
  }' | python3 -m json.tool
echo -e "\n"

# 4. Add edit event
echo "4. Add Edit Event:"
curl -s -X POST "$BASE_URL/api/traces/$TRACE_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "edit",
    "timestamp": "2024-01-15T10:15:00Z",
    "details": {
      "file": "src/utils.js",
      "change": "Fixed null pointer exception",
      "diff": "@@ -10,5 +10,7 @@\n function processData(data) {\n+  if (!data) return null;\n   return data.map(...);\n }"
    }
  }' | python3 -m json.tool
echo -e "\n"

# 5. Add another command event
echo "5. Add Test Command Event:"
curl -s -X POST "$BASE_URL/api/traces/$TRACE_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "command",
    "timestamp": "2024-01-15T10:20:00Z",
    "details": {
      "command": "npm test",
      "output": "All tests passing",
      "working_directory": "/project"
    }
  }' | python3 -m json.tool
echo -e "\n"

# 6. Get trace to see all events
echo "6. Get Trace with All Events:"
curl -s "$BASE_URL/api/traces/$TRACE_ID" | python3 -m json.tool | head -50
echo -e "\n"

# 7. Finalize trace (triggers QA)
echo "7. Finalize Trace (Trigger QA Pipeline):"
echo "This may take 30-60 seconds..."
curl -s -X POST "$BASE_URL/api/traces/$TRACE_ID/finalize" | python3 -m json.tool
echo -e "\n"

# 8. Get finalized trace with QA results
echo "8. Get Finalized Trace with QA Results:"
sleep 2
curl -s "$BASE_URL/api/traces/$TRACE_ID" | python3 -m json.tool
echo -e "\n"

echo "Incremental ingestion test complete!"

