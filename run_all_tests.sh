#!/bin/bash
# Run all test scripts

echo "=========================================="
echo "Running All Test Suites"
echo "=========================================="
echo ""

SCRIPTS=(
    "test_endpoints.sh"
    "test_error_cases.sh"
    "test_incremental.sh"
    "test_event_types.sh"
    "test_qa_pipeline.sh"
    "test_performance.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "=========================================="
        echo "Running: $script"
        echo "=========================================="
        ./"$script"
        echo ""
        echo "Press Enter to continue to next test..."
        read
    else
        echo "Warning: $script not found, skipping..."
    fi
done

echo "=========================================="
echo "All tests complete!"
echo "=========================================="

