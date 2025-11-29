#!/bin/bash
# Test different event types comprehensively

BASE_URL="http://localhost:8000"
echo "Testing Different Event Types..."
echo ""

# Create trace with all event types
echo "Creating Trace with All Event Types:"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_all_events",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Comprehensive event type testing",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "text": "I hypothesize that the issue is related to async handling",
          "reasoning_type": "hypothesis",
          "confidence": "high"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:01:00Z",
        "details": {
          "text": "Alternative approach: use promises instead of callbacks",
          "reasoning_type": "alternative",
          "confidence": "medium"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:02:00Z",
        "details": {
          "text": "Note: Previous similar bug was fixed by adding error handling",
          "reasoning_type": "note",
          "confidence": "high"
        }
      },
      {
        "type": "command",
        "timestamp": "2024-01-15T10:05:00Z",
        "details": {
          "command": "grep -r \"async\" src/",
          "output": "src/api.js:15: async function fetchData()",
          "working_directory": "/project"
        }
      },
      {
        "type": "command",
        "timestamp": "2024-01-15T10:06:00Z",
        "details": {
          "command": "git diff HEAD~1",
          "output": "diff --git a/src/api.js...",
          "working_directory": "/project"
        }
      },
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:10:00Z",
        "details": {
          "file": "src/api.js",
          "change": "Added error handling to async function",
          "diff": "@@ -15,8 +15,12 @@\n async function fetchData() {\n+  try {\n     const response = await fetch(url);\n+    return response.json();\n+  } catch (error) {\n+    console.error(\"Error:\", error);\n+    return null;\n+  }\n }"
        }
      },
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:11:00Z",
        "details": {
          "file": "src/utils.js",
          "change": "Added null check",
          "diff": "@@ -5,6 +5,8 @@\n function process(data) {\n+  if (!data) return;\n   return data.map(...);\n }"
        }
      },
      {
        "type": "command",
        "timestamp": "2024-01-15T10:15:00Z",
        "details": {
          "command": "npm test",
          "output": "Tests: 20 passed, 0 failed",
          "working_directory": "/project"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:16:00Z",
        "details": {
          "text": "The fix works! All tests passing. The issue was missing error handling.",
          "reasoning_type": "note",
          "confidence": "high"
        }
      }
    ]
  }')

echo "$RESPONSE" | python3 -m json.tool
TRACE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])" 2>/dev/null)
echo -e "\nTrace ID: $TRACE_ID\n"

if [ ! -z "$TRACE_ID" ]; then
    echo "Retrieving full trace:"
    curl -s "$BASE_URL/api/traces/$TRACE_ID" | python3 -m json.tool | head -80
fi

echo -e "\nEvent types test complete!"

