#!/bin/bash
# Test QA Pipeline specifically

BASE_URL="http://localhost:8000"
echo "Testing QA Pipeline..."
echo ""

# Test 1: Trace with good reasoning
echo "1. Test with High-Quality Reasoning:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_good_reasoning",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Null pointer exception in data processing",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "text": "The error occurs when data is null. I need to check where data comes from and add null checks.",
          "reasoning_type": "hypothesis",
          "confidence": "high"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:01:00Z",
        "details": {
          "text": "Alternative approaches: 1) Add null check at entry point, 2) Use optional chaining, 3) Provide default value",
          "reasoning_type": "alternative",
          "confidence": "medium"
        }
      },
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:05:00Z",
        "details": {
          "file": "src/processor.js",
          "change": "Added null check with early return",
          "diff": "@@ -10,5 +10,7 @@\n function process(data) {\n+  if (!data) return null;\n   return data.map(...);\n }"
        }
      }
    ]
  }' | python3 -m json.tool | grep -A 5 "qa_results"
echo -e "\n"

# Test 2: Trace with poor reasoning
echo "2. Test with Low-Quality Reasoning:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_poor_reasoning",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Something is broken",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "text": "Maybe it works now?",
          "reasoning_type": "hypothesis",
          "confidence": "low"
        }
      }
    ]
  }' | python3 -m json.tool | grep -A 5 "qa_results"
echo -e "\n"

# Test 3: Trace with multiple reasoning events
echo "3. Test with Multiple Reasoning Events:"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_multi_reasoning",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Performance issue in data processing",
    "events": [
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "text": "The function is too slow. Need to optimize.",
          "reasoning_type": "hypothesis",
          "confidence": "high"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:01:00Z",
        "details": {
          "text": "Options: 1) Use memoization, 2) Reduce iterations, 3) Use more efficient algorithm",
          "reasoning_type": "alternative",
          "confidence": "medium"
        }
      },
      {
        "type": "reasoning",
        "timestamp": "2024-01-15T10:02:00Z",
        "details": {
          "text": "Chose memoization as it requires minimal code changes",
          "reasoning_type": "note",
          "confidence": "high"
        }
      },
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:05:00Z",
        "details": {
          "file": "src/optimizer.js",
          "change": "Added memoization cache",
          "diff": "@@ -5,6 +5,8 @@\n+const cache = new Map();\n function expensive(data) {\n+  if (cache.has(data)) return cache.get(data);\n   const result = compute(data);\n+  cache.set(data, result);\n   return result;\n }"
        }
      }
    ]
  }')

echo "$RESPONSE" | python3 -m json.tool | grep -A 10 "qa_results"
echo -e "\n"

# Test 4: Trace with no reasoning events
echo "4. Test with No Reasoning Events (should still work):"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_no_reasoning",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Bug fix without reasoning",
    "events": [
      {
        "type": "edit",
        "timestamp": "2024-01-15T10:00:00Z",
        "details": {
          "file": "src/file.js",
          "change": "Fixed typo",
          "diff": "@@ -1,1 +1,1 @@\n-consol.log(\"test\");\n+console.log(\"test\");"
        }
      }
    ]
  }' | python3 -m json.tool | grep -A 5 "qa_results"
echo -e "\n"

echo "QA Pipeline testing complete!"

