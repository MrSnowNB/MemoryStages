.PHONY: dev web web-no-browser demo test smoke test-stage4 test-full-stage4 test-stage6 test-dashboard test-dashboard-integration test-full-stage5 test-regression-with-dashboard test-privacy test-privacy-disabled test-full-stage6 format clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  dev               - Run API development server with auto-reload"
	@echo "  web               - Serve web UI chat interface"
	@echo "  web-no-browser    - Serve web UI without auto-opening browser"
	@echo "  demo              - Launch both API and web UI together"
	@echo "  test              - Run all tests"
	@echo "  smoke             - Run smoke tests only"
	@echo "  test-stage4       - Run Stage 4 specific tests"
	@echo "  test-full-stage4  - Run full Stage 4 integration test suite"
	@echo "  test-stage6       - Run Stage 6 privacy enforcement tests"
	@echo "  test-full-stage6  - Run full Stage 6 integration test suite"
	@echo "  test-dashboard    - Run Stage 5 dashboard tests"
	@echo "  test-dashboard-integration - Run Stage 5 dashboard integration tests"
	@echo "  test-full-stage5  - Run complete Stage 5 test suite"
	@echo "  test-regression-with-dashboard - Regression test with dashboard enabled"
	@echo "  format            - Format code (if tools available)"
	@echo "  clean             - Clean up temporary files"

# Development server
dev:
	uvicorn src.api.main:app --reload --port 8000

# Web UI server
web:
	python scripts/web_server.py

web-no-browser:
	python scripts/web_server.py --no-browser

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

# Stage 5 specific targets
test-dashboard:
	DASHBOARD_ENABLED=true DASHBOARD_AUTH_TOKEN=test_token \
		pytest tests/test_tui_*.py -q

test-dashboard-integration:
	pytest tests/test_tui_ops_integration.py -q

test-full-stage5: test-dashboard test-dashboard-integration
	@echo "✅ All Stage 5 tests passed"

# Regression testing with dashboard enabled
test-regression-with-dashboard:
	DASHBOARD_ENABLED=true pytest tests/test_smoke.py tests/test_full_app_stage4.py -q

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

# Stage 6 specific targets
test-stage6:
	pytest -q tests/test_privacy_enforcement.py tests/test_key_normalization.py tests/test_system_identity.py tests/test_semantic_chat_provenance.py -v

test-privacy:
	PRIVACY_ENFORCEMENT_ENABLED=true PRIVACY_AUDIT_LEVEL=standard \
		pytest tests/test_privacy_enforcement.py -q -v

test-privacy-disabled:
	PRIVACY_ENFORCEMENT_ENABLED=false \
		pytest tests/test_privacy_enforcement.py -q -v

test-full-stage6: test-privacy test-privacy-disabled
	@echo "✅ All Stage 6 tests passed"

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
