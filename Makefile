# Makefile for now-playing project
# Compatible with local devel# ─── Install Dev Requirements ────────────────────────────────────────
install-dev:
	@echo "Installing dev dependencies..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

# ─── Install Production ──────────────────────────────────────────────
install:
	@echo "Installing production dependencies..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e . and container environments (Codespaces, DevContainers)
# Automatically detects environment type and virtualenv tool availability

.PHONY: format lint test coverage hooks install-dev install recreate-venv commit-ai check help env pre-commit-install ensure-venv

# ─── Environment Detection ───────────────────────────────────────────────
ENV_DESC := $(shell \
	if [ -n "$$CODESPACES" ]; then echo "Codespace"; \
	elif grep -qi 'vscode' /etc/passwd 2>/dev/null || [ "$$USER" = "vscode" ] || [ -d "/workspaces" ]; then echo "DevContainer"; \
	elif [ -n "$$VIRTUAL_ENV" ]; then echo "Virtual Environment"; \
	else echo "Local Machine"; fi)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Use fallback to system commands if not in virtualenv
PYTEST := $(shell test -x "$(VENV)/bin/pytest" && echo "$(VENV)/bin/pytest" || command -v pytest)
COVERAGE := $(shell test -x "$(VENV)/bin/coverage" && echo "$(VENV)/bin/coverage" || command -v coverage)
BLACK := $(shell test -x "$(VENV)/bin/black" && echo "$(VENV)/bin/black" || command -v black)
ISORT := $(shell test -x "$(VENV)/bin/isort" && echo "$(VENV)/bin/isort" || command -v isort)
FLAKE8 := $(shell test -x "$(VENV)/bin/flake8" && echo "$(VENV)/bin/flake8" || command -v flake8)
VULTURE := $(shell test -x "$(VENV)/bin/vulture" && echo "$(VENV)/bin/vulture" || command -v vulture)
MYPY := $(shell test -x "$(VENV)/bin/mypy" && echo "$(VENV)/bin/mypy" || command -v mypy)
PRECOMMIT := $(shell test -x "$(VENV)/bin/pre-commit" && echo "$(VENV)/bin/pre-commit" || command -v pre-commit)

# ─── Format Code ─────────────────────────────────────────────────────────
format:
	@echo "Running formatters (black + isort)..."
	@echo "Environment: $(ENV_DESC)"
	@$(BLACK) . || { echo "black not found. Install dependencies or activate your virtualenv."; exit 1; }
	@$(ISORT) . || { echo "isort not found. Install dependencies or activate your virtualenv."; exit 1; }

# ─── Lint Code ───────────────────────────────────────────────────────────
lint:
	@echo "Running linters (flake8)..."
	@echo "Environment: $(ENV_DESC)"
	@$(FLAKE8) . || { echo "flake8 not found. Install dependencies or activate your virtualenv."; exit 1; }

# ─── Dead Code Detection ─────────────────────────────────────────────────
dead-code:
	@echo "Checking for dead code (vulture)..."
	@echo "Environment: $(ENV_DESC)"
	@$(VULTURE) nowplaying/ devtools/ || { echo "vulture not found. Install dependencies or activate your virtualenv."; exit 1; }

# ─── Type Checking ───────────────────────────────────────────────────────
type-check:
	@echo "Running type checker (mypy)..."
	@echo "Environment: $(ENV_DESC)"
	@$(MYPY) nowplaying/ devtools/ || { echo "mypy not found. Install dependencies or activate your virtualenv."; exit 1; }

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

# ─── AI-Powered Commits ──────────────────────────────────────────────────
commit-ai:
	@echo "Generating AI-powered commit message..."
	@command -v npm >/dev/null 2>&1 || { echo "❌ npm not found. Please install Node.js."; exit 1; }
	@if [ ! -d "node_modules" ]; then \
		echo "📦 Installing npm dependencies..."; \
		npm install; \
	fi
	@echo "🤖 Running aicommits..."
	@npm run commit-ai

# ─── Preview Changelog ────────────────────────────────────────────────────
preview-changelog:
	@echo "Previewing unreleased changelog..."
	@command -v git-cliff >/dev/null 2>&1 || { echo "git-cliff not found. Skipping."; exit 0; }
	git-cliff --config ./cliff.toml --unreleased --stdout

# ─── Recreate Venv ───────────────────────────────────────────────────────
recreate-venv:
	@echo "Recreating virtual environment..."
	rm -rf $(VENV)
	make install-dev
	make pre-commit-install
	@echo "Virtual environment recreated."

# ─── Run All Checks ──────────────────────────────────────────────────────
check: format lint dead-code test

# ─── CI Check (All Steps Used in GitHub Actions) ─────────────────────────
ci-check: format lint dead-code type-check test coverage hooks

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
	@echo "  isort version: $$($(ISORT) --version-number 2>/dev/null || echo 'not found')"
	@echo "  vulture version: $$($(VULTURE) --version 2>/dev/null || echo 'not found')"
	@echo "  mypy version: $$($(MYPY) --version 2>/dev/null || echo 'not found')"
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
	@echo "  format              Run code formatters (black + isort)"
	@echo "  lint                Run linter (flake8 with all plugins)"
	@echo "  dead-code           Run dead code detection (vulture)"
	@echo "  type-check          Run type checker (mypy)"
	@echo "  test                Run unit tests with pytest and HTML/terminal coverage"
	@echo "  coverage            Run coverage reporting only (xml + html)"
	@echo ""
	@echo "  # Git and Pre-commit"
	@echo "  hooks               Run all configured pre-commit hooks"
	@echo "  pre-commit-install  Install pre-commit hook into .git/hooks"
	@echo "  commit-ai           Generate AI-powered commit message and commit changes"
	@echo ""
	@echo "  # Composite Targets"
	@echo "  check               Run basic dev checks (format + lint + dead-code + test)"
	@echo "  ci-check            Run full CI validation (format, lint, dead-code, type-check, test, coverage, hooks)"
	@echo ""
