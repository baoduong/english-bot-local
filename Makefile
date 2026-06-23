PYTHON := venv/bin/python3
PYTEST := $(PYTHON) -m pytest

.PHONY: help test test-be test-ios test-fast coverage coverage-gate fault-injection load-test lint format clean-test precommit

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: test-be test-ios  ## Run all tests

test-be:  ## Run backend Python tests
	$(PYTEST) tests/ -x --tb=short

test-ios:  ## Run iOS tests via xcodebuild
	cd ios/EnglishBotApp && xcodebuild test -scheme EnglishBotApp -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -20

test-fast:  ## Run fast-marked tests only (<30s)
	$(PYTEST) tests/ -m fast -x --tb=short

coverage:  ## Run tests with coverage report
	$(PYTEST) tests/ --cov=api --cov=engines --cov=analysis --cov=db --cov-report=xml --cov-report=html --cov-config=.coveragerc

coverage-gate: coverage  ## Enforce 70% diff-cover on changed files
	$(PYTHON) -m diff_cover.diff_cover_tool coverage.xml --compare-branch=pre-qa-baseline-v1 --fail-under=70 --html-report=.omo/evidence/coverage-diff.html

fault-injection:  ## Run fault injection tests
	$(PYTEST) tests/ -m fault_injection -x --tb=short -v

load-test:  ## Run locust load test (5min, 10 users)
	@echo "Starting backend with mocks..."
	EB_MOCK_WHISPER=1 EB_MOCK_OLLAMA=1 EB_MOCK_AZURE=1 $(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8765 & echo $$! > /tmp/loadtest-be.pid && sleep 5
	$(PYTHON) -m locust -f load/practice_audio.locustfile.py --headless -u 10 -r 2 -t 5m --host=http://localhost:8765 --csv=.omo/evidence/load --html=.omo/evidence/load.html || true
	@kill $$(cat /tmp/loadtest-be.pid) 2>/dev/null; rm -f /tmp/loadtest-be.pid

lint:  ## Run ruff linter
	$(PYTHON) -m ruff check . --fix

format:  ## Run black formatter
	$(PYTHON) -m black .

precommit:  ## Run pre-commit hooks
	pre-commit run --all-files

clean-test:  ## Clean test artifacts
	rm -rf htmlcov/ coverage.xml .coverage .pytest_cache/ .omo/evidence/
