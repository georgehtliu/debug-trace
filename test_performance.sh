#!/bin/bash
# Performance and load testing

BASE_URL="http://localhost:8000"
echo "Performance Testing..."
echo ""

# Test 1: Multiple rapid requests
echo "1. Testing 5 Rapid Requests:"
for i in {1..5}; do
    echo "Request $i..."
    time curl -s -X POST "$BASE_URL/api/traces" \
      -H "Content-Type: application/json" \
      -d "{
        \"developer_id\": \"dev_perf_$i\",
        \"repo_url\": \"https://github.com/octocat/Hello-World\",
        \"bug_description\": \"Performance test $i\",
        \"events\": [{
          \"type\": \"reasoning\",
          \"timestamp\": \"2024-01-15T10:00:00Z\",
          \"details\": {\"text\": \"Test $i\", \"reasoning_type\": \"hypothesis\", \"confidence\": \"medium\"}
        }]
      }" > /dev/null
done
echo -e "\n"

# Test 2: Large trace with many events
echo "2. Testing Large Trace (20 events):"
EVENTS=""
for i in {1..20}; do
    if [ $i -eq 1 ]; then
        EVENTS="["
    else
        EVENTS="$EVENTS,"
    fi
    EVENTS="$EVENTS{\"type\":\"reasoning\",\"timestamp\":\"2024-01-15T10:$(printf %02d $i):00Z\",\"details\":{\"text\":\"Event $i\",\"reasoning_type\":\"hypothesis\",\"confidence\":\"medium\"}}"
done
EVENTS="$EVENTS]"

time curl -s -X POST "$BASE_URL/api/traces" \
  -H "Content-Type: application/json" \
  -d "{
    \"developer_id\": \"dev_large\",
    \"repo_url\": \"https://github.com/octocat/Hello-World\",
    \"bug_description\": \"Large trace test\",
    \"events\": $EVENTS
  }" > /dev/null

echo "Large trace submitted"
echo -e "\n"

# Test 3: Health check performance
echo "3. Health Check Performance (10 requests):"
time for i in {1..10}; do
    curl -s "$BASE_URL/health" > /dev/null
done
echo -e "\n"

# Test 4: Concurrent requests (if you have parallel tool)
echo "4. Testing Concurrent Requests:"
echo "Note: This requires 'parallel' or 'xargs -P'"
seq 1 3 | xargs -P 3 -I {} bash -c "curl -s -X POST '$BASE_URL/api/traces' -H 'Content-Type: application/json' -d '{\"developer_id\":\"dev_conc_{}\",\"repo_url\":\"https://github.com/octocat/Hello-World\",\"bug_description\":\"Concurrent test {}\",\"events\":[]}' > /dev/null && echo 'Request {} completed'"
echo -e "\n"

echo "Performance testing complete!"

