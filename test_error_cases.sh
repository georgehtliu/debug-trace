#!/bin/bash
# Test error cases and edge cases

BASE_URL="http://localhost:8000"
echo "Testing Error Cases and Edge Cases..."
echo ""

# 1. Test with missing required fields
echo "1. Test Missing Required Fields:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{"developer_id":"test"}' | python3 -m json.tool
echo -e "\n"

# 2. Test with invalid JSON
echo "2. Test Invalid JSON:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{"invalid": json}' | python3 -m json.tool
echo -e "\n"

# 3. Test with non-existent trace ID
echo "3. Test Non-Existent Trace ID:"
curl -s "$BASE_URL/api/traces/non-existent-id-12345" | python3 -m json.tool
echo -e "\n"

# 4. Test with empty events array
echo "4. Test Empty Events Array:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_empty",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Test with no events",
    "events": []
  }' | python3 -m json.tool
echo -e "\n"

# 5. Test with invalid event type
echo "5. Test Invalid Event Type:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_invalid",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Test invalid event",
    "events": [{
      "type": "invalid_type",
      "timestamp": "2024-01-15T10:00:00Z",
      "details": {}
    }]
  }' | python3 -m json.tool
echo -e "\n"

# 6. Test finalize on non-existent trace
echo "6. Test Finalize Non-Existent Trace:"
curl -s -X POST "$BASE_URL/api/traces/non-existent-id/finalize" | python3 -m json.tool
echo -e "\n"

# 7. Test add event to non-existent trace
echo "7. Test Add Event to Non-Existent Trace:"
curl -s -X POST "$BASE_URL/api/traces/non-existent-id/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "reasoning",
    "timestamp": "2024-01-15T10:00:00Z",
    "details": {"text": "test"}
  }' | python3 -m json.tool
echo -e "\n"

# 8. Test with very long bug description
echo "8. Test Very Long Bug Description:"
LONG_DESC=$(python3 -c "print('A' * 10000")
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d "{
    \"developer_id\": \"dev_long\",
    \"repo_url\": \"https://github.com/octocat/Hello-World\",
    \"bug_description\": \"$LONG_DESC\",
    \"events\": []
  }" | python3 -m json.tool | head -20
echo -e "\n"

# 9. Test with invalid timestamp format
echo "9. Test Invalid Timestamp Format:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_timestamp",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Test invalid timestamp",
    "events": [{
      "type": "reasoning",
      "timestamp": "invalid-date",
      "details": {"text": "test"}
    }]
  }' | python3 -m json.tool
echo -e "\n"

# 10. Test with missing event details
echo "10. Test Missing Event Details:"
curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev_no_details",
    "repo_url": "https://github.com/octocat/Hello-World",
    "bug_description": "Test missing details",
    "events": [{
      "type": "reasoning",
      "timestamp": "2024-01-15T10:00:00Z"
    }]
  }' | python3 -m json.tool
echo -e "\n"

echo "Error case testing complete!"

