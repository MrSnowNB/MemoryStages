.PHONY: dev test smoke test-stage4 test-full-stage4 format clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  dev               - Run development server with auto-reload"
	@echo "  test              - Run all tests"
	@echo "  smoke             - Run smoke tests only"
	@echo "  test-stage4       - Run Stage 4 specific tests"
	@echo "  test-full-stage4  - Run full Stage 4 integration test suite"
	@echo "  format            - Format code (if tools available)"
	@echo "  clean             - Clean up temporary files"

# Development server
dev:
	uvicorn src.api.main:app --reload --port 8000

# Run all tests
test:
	pytest -q

# Run smoke tests only
smoke:
	pytest -q tests/test_smoke.py

# Run Stage 4 specific tests (schema validation + approval workflow + audit logging)
test-stage4:
	pytest -q tests/test_schema_valid.py tests/test_approval.py tests/test_logging_stage4.py

# Run full Stage 4 integration test suite
test-full-stage4:
	pytest -q tests/test_full_app_stage4.py::TestStage4FullWorkflow::test_full_workflow_with_approval

# Format code (optional - requires black/ruff)
format:
	@if command -v black >/dev/null 2>&1; then \
		echo "Formatting with black..."; \
		black src/ tests/; \
	elif command -v ruff >/dev/null 2>&1; then \
		echo "Formatting with ruff..."; \
		ruff format src/ tests/; \
	else \
		echo "No formatter available (install black or ruff)"; \
	fi

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
