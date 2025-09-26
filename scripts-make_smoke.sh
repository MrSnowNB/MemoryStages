#!/bin/bash
# Smoke test script for Stage 1 validation

set -e

echo "🧪 Running Stage 1 Smoke Tests"
echo "==============================="
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Please install: pip install pytest"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "src/api/main.py" ]; then
    echo "❌ Not in project root directory. Please run from project root."
    exit 1
fi

# Run smoke tests with verbose output
echo "📋 Running automated smoke tests..."
echo ""

if pytest -q tests/test_smoke.py -v; then
    echo ""
    echo "✅ All smoke tests passed!"
    echo ""
    echo "Next steps:"
    echo "1. Run manual API tests: see docs/API_QUICKSTART.md" 
    echo "2. Complete Stage 1 checklist: docs/STAGE_CHECKS.md"
    echo "3. Get human approval before Stage 2 development"
    echo ""
    echo "🎉 Stage 1 foundation is ready!"
else
    echo ""
    echo "❌ Some smoke tests failed!"
    echo ""
    echo "Debug steps:"
    echo "1. Check database setup and permissions"
    echo "2. Verify .env configuration"
    echo "3. Run individual tests for more details"
    echo "4. Check logs for specific error messages"
    exit 1
fi