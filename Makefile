.PHONY: help install dev test test-unit test-smoke test-cov lint format check build clean

# Default target
help:
	@echo "CVE Analysis Pipeline - Development Tasks"
	@echo ""
	@echo "Installation & Setup:"
	@echo "  make install      Install dependencies"
	@echo "  make dev          Install dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run all tests (unit + smoke)"
	@echo "  make test-unit    Run unit tests only"
	@echo "  make test-smoke   Run smoke tests only"
	@echo "  make test-cov     Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         Run linters (ruff, mypy)"
	@echo "  make format       Auto-format code (black, isort)"
	@echo "  make check        Run all checks (format + lint + test)"
	@echo ""
	@echo "Build & Cleanup:"
	@echo "  make build        Build project"
	@echo "  make clean        Clean build artifacts and caches"

# Installation targets
install:
	pip install -r requirements.txt

dev: install
	pip install -r requirements-dev.txt

# Testing targets
test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/test_core_*.py -v

test-smoke:
	python -m pytest tests/test_smoke_pipeline.py -v

test-cov:
	python -m pytest tests/ -v --cov=src --cov=agent_orchestrator --cov-report=html --cov-report=term-missing

# Code quality targets
lint:
	@echo "Running linters..."
	ruff check src/ agent_orchestrator.py tests/
	mypy src/ agent_orchestrator.py --ignore-missing-imports

format:
	@echo "Formatting code..."
	black src/ agent_orchestrator.py tests/ --line-length=100
	isort src/ agent_orchestrator.py tests/ --profile black

check: format lint test
	@echo "✓ All checks passed!"

# Build & cleanup targets
build: check
	@echo "Build completed successfully"

clean:
	@echo "Cleaning build artifacts and caches..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup completed"

# Development workflow shortcuts
watch-test:
	@echo "Watching for changes... (Press Ctrl+C to stop)"
	@while true; do clear; make test; sleep 2; done

quick-test:
	@python -m pytest tests/ -x --tb=short

# CI/local verification
verify: clean dev test-cov
	@echo "✓ Full verification completed"

# Project information
info:
	@echo "CVE Analysis Pipeline"
	@echo ""
	@echo "Key modules:"
	@echo "  - agent_orchestrator: Main pipeline orchestration"
	@echo "  - src/core: Core utilities and abstractions"
	@echo "  - src/core/agent: Agent patterns and base classes"
	@echo "  - src/core/serialization: Data serialization utilities"
	@echo "  - src/core/persistence: Database persistence"
	@echo ""
	@echo "Run 'make help' for available commands"
