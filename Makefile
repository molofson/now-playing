# Makefile for now-playing project
# Compatible with local development and container environments (Codespaces, DevContainers)
# Automatically detects environment type and virtualenv tool availability

.PHONY: format lint test coverage hooks install-dev recreate-venv commit-ai check help env pre-commit-install ensure-venv

# ─── Environment Detection ───────────────────────────────────────────────
ENV_DESC := $(shell \
	if [ -n "$$CODESPACES" ]; then echo "Codespace"; \
	elif grep -qi 'vscode' /etc/passwd 2>/dev/null || [ "$$USER" = "vscode" ] || [ -d "/workspaces" ]; then echo "DevContainer"; \
	else echo "Local Machine"; fi)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Use fallback to system commands if not in virtualenv
PYTEST := $(shell test -x "$(VENV)/bin/pytest" && echo "$(VENV)/bin/pytest" || command -v pytest)
COVERAGE := $(shell test -x "$(VENV)/bin/coverage" && echo "$(VENV)/bin/coverage" || command -v coverage)
BLACK := $(shell test -x "$(VENV)/bin/black" && echo "$(VENV)/bin/black" || command -v black)
FLAKE8 := $(shell test -x "$(VENV)/bin/flake8" && echo "$(VENV)/bin/flake8" || command -v flake8)
PRECOMMIT := $(shell test -x "$(VENV)/bin/pre-commit" && echo "$(VENV)/bin/pre-commit" || command -v pre-commit)

# ─── Format Code ─────────────────────────────────────────────────────────
format:
	@echo "Running formatter (black)..."
	@echo "Environment: $(ENV_DESC)"
	@$(BLACK) . || { echo "black not found. Install dependencies or activate your virtualenv."; exit 1; }

# ─── Lint Code ───────────────────────────────────────────────────────────
lint:
	@echo "Running linter (flake8)..."
	@echo "Environment: $(ENV_DESC)"
	@$(FLAKE8) . || { echo "flake8 not found. Install dependencies or activate your virtualenv."; exit 1; }

# ─── Run Tests ───────────────────────────────────────────────────────────
test:
	@echo "Running tests..."
	@echo "Environment: $(ENV_DESC)"
	@$(PYTEST) --cov=nowplaying \
	           --cov-report=term-missing \
	           tests/

# ─── Test Coverage ───────────────────────────────────────────────────────
coverage: test
	@echo "Running test coverage..."
	@$(COVERAGE) xml
	@$(COVERAGE) html

# ─── Pre-commit Hooks ────────────────────────────────────────────────────
hooks:
	@echo "Running pre-commit hooks..."
	@$(PRECOMMIT) run --all-files

pre-commit-install:
	@echo "Installing pre-commit hook..."
	@$(PRECOMMIT) install

# ─── Preview Changelog ────────────────────────────────────────────────────
preview-changelog:
	@echo "Previewing unreleased changelog..."
	@command -v git-cliff >/dev/null 2>&1 || { echo "git-cliff not found. Skipping."; exit 0; }
	git-cliff --config ./cliff.toml --unreleased --stdout

# ─── Install Dev Requirements ────────────────────────────────────────────
install-dev:
	@echo "Installing dev dependencies..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

# ─── Recreate Venv ───────────────────────────────────────────────────────
recreate-venv:
	@echo "Recreating virtual environment..."
	rm -rf $(VENV)
	make install-dev
	make pre-commit-install
	@echo "Virtual environment recreated."

# ─── Run All Checks ──────────────────────────────────────────────────────
check: format lint test

# ─── CI Check (All Steps Used in GitHub Actions) ─────────────────────────
ci-check: format lint test coverage hooks

# ─── Clean Generated Files ───────────────────────────────────────────────
clean:
	@echo "Cleaning up generated files..."
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov coverage.xml
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@find . -type f -name '*.orig' -delete

clean-venv: clean
	# rm -rf .venv

# ─── Environment Info ────────────────────────────────────────────────────
env:
	@echo "Detected environment: $(ENV_DESC)"
	@echo "  Python version: $$(python3 --version 2>/dev/null || echo 'not found')"
	@echo "  black version: $$($(BLACK) --version 2>/dev/null || echo 'not found')"
	@echo "  flake8 version: $$($(FLAKE8) --version 2>/dev/null || echo 'not found')"
	@echo "  isort version: $$(isort --version-number 2>/dev/null || echo 'not found')"
	@echo "  pytest version: $$($(PYTEST) --version 2>/dev/null || echo 'not found')"
	@echo "  coverage version: $$($(COVERAGE) --version 2>/dev/null | head -n1 || echo 'not found')"
	@echo "  pre-commit version: $$($(PRECOMMIT) --version 2>/dev/null || echo 'not found')"

# ─── Ensure Virtual Environment ──────────────────────────────────────────
ensure-venv:
	@if [ ! -x "$(VENV)/bin/pytest" ]; then \
		echo "❌ .venv not found or incomplete. Run: make install-dev"; \
		exit 1; \
	fi

# ─── Help ────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Available make targets:"
	@echo ""
	@echo "  # Setup and Environment"
	@echo "  install-dev         Create virtualenv and install dev dependencies"
	@echo "  recreate-venv       Recreate virtualenv from scratch"
	@echo "  ensure-venv         Verify .venv exists and is populated"
	@echo "  env                 Print environment and tool versions"
	@echo "  clean               Remove test coverage artifacts"
	@echo "  clean-venv          Remove .venv"
	@echo ""
	@echo "  # Code Quality and Testing"
	@echo "  format              Run code formatter (black)"
	@echo "  lint                Run linter (flake8)"
	@echo "  test                Run unit tests with pytest and HTML/terminal coverage"
	@echo "  coverage            Run coverage reporting only (xml + html)"
	@echo ""
	@echo "  # Git and Pre-commit"
	@echo "  hooks               Run all configured pre-commit hooks"
	@echo "  pre-commit-install  Install pre-commit hook into .git/hooks"
	@echo ""
	@echo "  # Composite Targets"
	@echo "  check               Run basic dev checks (format + lint + test)"
	@echo "  ci-check            Run full CI validation (format, lint, test, coverage, hooks)"
	@echo ""
