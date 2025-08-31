# Makefile for now-playing project
# Compatible with local development and container environments (Codespaces, DevContainers)
# Automatically detects environment type and virtualenv tool availability

.PHONY: format lint test coverage hooks install-dev recreate-venv commit-ai check help env

# ─── Environment Detection ───────────────────────────────────────────────
ENV_DESC := $(shell \
	if [ -n "$$CODESPACES" ]; then echo "Codespace"; \
	elif grep -qi 'vscode' /etc/passwd 2>/dev/null || [ "$$USER" = "vscode" ] || [ -d "/workspaces" ]; then echo "DevContainer"; \
	else echo "Local Machine"; fi)

# ─── Format Code ─────────────────────────────────────────────────────────
format:
	@echo "Running formatter (black)..."
	@echo "Environment: $(ENV_DESC)"
	@command -v black >/dev/null 2>&1 || { echo "black not found. Activate your virtualenv."; exit 1; }
	black .

# ─── Lint Code ───────────────────────────────────────────────────────────
lint:
	@echo "Running linter (flake8)..."
	@echo "Environment: $(ENV_DESC)"
	@command -v flake8 >/dev/null 2>&1 || { echo "flake8 not found. Activate your virtualenv."; exit 1; }
	flake8 .

# ─── Run Tests ───────────────────────────────────────────────────────────
test:
	@echo "Running tests..."
	@echo "Environment: $(ENV_DESC)"
	@command -v pytest >/dev/null 2>&1 || { echo "pytest not found. Activate your virtualenv."; exit 1; }
	pytest -vv tests/

# ─── Test Coverage ───────────────────────────────────────────────────────
coverage:
	@echo "Running test coverage..."
	@command -v pytest >/dev/null 2>&1 || { echo "pytest not found. Activate your virtualenv."; exit 1; }
	pytest --cov=nowplaying --cov-report=term-missing

# ─── Pre-commit Hooks ────────────────────────────────────────────────────
hooks:
	@echo "Running pre-commit hooks..."
	@command -v pre-commit >/dev/null 2>&1 || { echo "pre-commit not found. Activate your virtualenv."; exit 1; }
	pre-commit run --all-files

# ─── Install Dev Requirements ────────────────────────────────────────────
install-dev:
	@echo "Installing dev dependencies..."
	@python3 -m venv .venv
	@.venv/bin/pip install --upgrade pip
	@.venv/bin/pip install -r requirements-dev.txt

# ─── Recreate Venv ───────────────────────────────────────────────────────
recreate-venv:
	@echo "Recreating virtual environment..."
	rm -rf .venv
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt
	@echo "Virtual environment recreated."

# ─── AI Commit ───────────────────────────────────────────────────────────
commit-ai:
	@echo "Running AI-powered commit..."
	@command -v aicommits >/dev/null 2>&1 || { echo "aicommits not found. Is Node installed?"; exit 1; }
	aicommits
	@echo "AI commit completed."

# ─── Run All Checks ──────────────────────────────────────────────────────
check: format lint test

# ─── Environment Info ────────────────────────────────────────────────────
env:
	@echo "Detected environment: $(ENV_DESC)"

# ─── Help ────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Available make targets:"
	@grep -E '^[a-zA-Z_-]+:' Makefile | grep -v '.PHONY' | sort
	@echo ""
