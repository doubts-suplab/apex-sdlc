# APEX SDLC — offline demos, tests, and checks.
#
# Everything here runs offline with the deterministic stub provider — no Postgres,
# Redis, S3, or API keys. Start with `make install`, then `make help`.
#
# PYTHON auto-detects the backend virtualenv (platform/backend/.venv) if present,
# so `make journey` works after `make install` without activating the venv.
# Override with `make PYTHON=python3.12 ...` if needed.

BACKEND  := platform/backend
FRONTEND := platform/frontend
VENV_PY  := $(BACKEND)/.venv/bin/python
PYTHON   ?= $(shell [ -x $(VENV_PY) ] && echo $(VENV_PY) || echo python3)
# Run demos from the backend dir so `-m app.demo.*` resolves; stub provider = offline.
RUN      := cd $(BACKEND) && LLM_PROVIDER=stub $(PYTHON)

.DEFAULT_GOAL := help

.PHONY: help
help: ## List available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Using PYTHON=$(PYTHON)"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: install
install: ## Create the backend venv and install the package (with dev extras)
	cd $(BACKEND) && python3 -m venv .venv && \
		.venv/bin/pip install --upgrade pip && \
		.venv/bin/pip install -e '.[dev]'
	@echo "\nInstalled. Demos/tests will now use $(VENV_PY) automatically."

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies (npm ci)
	cd $(FRONTEND) && npm ci

# ---------------------------------------------------------------------------
# Offline demos — each regenerates a committed fixture under examples/
# ---------------------------------------------------------------------------

.PHONY: journey
journey: ## Regenerate the reference journey → examples/reference-project/
	$(RUN) -m app.demo.reference_journey

.PHONY: gate-report
gate-report: ## Regenerate the gate report → examples/reference-project/gate-report.md
	$(RUN) -m app.demo.gate_report

.PHONY: generate-repo
generate-repo: ## Emit a scaffolded repo tree → examples/generated-repo/
	$(RUN) -m app.demo.generate_repo

.PHONY: devops-flow
devops-flow: ## Run the governed DevOps NL-intent flow → examples/devops-flow/
	$(RUN) -m app.demo.devops_flow

.PHONY: onboard
onboard: ## Run the onboarding bridge → examples/onboarded-project/
	$(RUN) -m app.demo.onboard_project

.PHONY: demos
demos: journey gate-report generate-repo devops-flow onboard ## Run every offline demo

# ---------------------------------------------------------------------------
# Tests & checks (offline)
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run the full backend test suite
	cd $(BACKEND) && $(PYTHON) -m pytest

.PHONY: test-governance
test-governance: ## Run the governance tests only (harness gate, authority ladder)
	cd $(BACKEND) && $(PYTHON) -m pytest --noconftest tests/agents/

.PHONY: lint
lint: ## ruff check + format check
	cd $(BACKEND) && $(PYTHON) -m ruff check app tests && \
		$(PYTHON) -m ruff format --check app tests

.PHONY: typecheck
typecheck: ## mypy (strict) over the backend
	cd $(BACKEND) && $(PYTHON) -m mypy app

.PHONY: frontend-check
frontend-check: ## Frontend type-check
	cd $(FRONTEND) && npm run type-check

.PHONY: frontend-build
frontend-build: ## Frontend production build
	cd $(FRONTEND) && npm run build

# ---------------------------------------------------------------------------
# Smoke test — the one-command offline confidence check
# ---------------------------------------------------------------------------

.PHONY: smoke
smoke: ## Regenerate fixtures, assert examples/ byte-identical, run governance tests
	cd $(BACKEND) && $(PYTHON) scripts/smoke_test.py

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove Python caches and coverage artifacts
	find $(BACKEND) -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -f $(BACKEND)/.coverage $(BACKEND)/coverage.xml
