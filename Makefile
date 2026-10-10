# SPOT dashboard: compose stack + every service's tests. See docs/RUNNING.md.
# Tests run in each service's own venv (create them with `make venvs`).

DB_PORT ?= $(or $(shell sed -n 's/^DB_PORT=\([0-9][0-9]*\).*/\1/p' .env 2>/dev/null),5433)
PY_BACKEND ?= backend/.venv/bin/python
PY_SYSTEM1 ?= amd/system1/.venv/bin/python
PYTHON_VISION ?= python3.12
PY_VISION  ?= amd/vision/.venv/bin/python
PY_MCP     ?= amd/mcp/.venv/bin/python
LOCAL_DB   ?= postgresql://postgres:postgres@localhost:$(DB_PORT)/spot

.PHONY: help up down wipe ps logs test test-policy test-backend test-backend-integration test-system1 \
        test-system1-fast test-vision vision-venv test-mcp test-db smoke e2e e2e-serial e2e-parallel venvs

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

up: ## build + start the stack for COMPOSE_PROFILES in .env (default local), wait until healthy
	docker compose up -d --build --wait

down: ## stop the stack (keeps the pgdata and hf-cache volumes)
	docker compose down

wipe: ## stop and delete the database volume (the hf-cache model volume is kept)
	docker compose down -v --remove-orphans

ps:
	docker compose ps -a

logs:
	docker compose logs -f --tail 50

test: test-policy test-backend test-system1 test-mcp test-vision ## all unit suites + the cross-service policy drift guard

test-policy: ## policy.py vs db/policy_rules.py vs backend validator vs MCP vendored copy, on all 297 kit events
	$(PY_BACKEND) -m pytest tests/test_policy_consistency.py -q -p no:cacheprovider

test-backend: ## backend unit tests (integration test skipped; see test-backend-integration)
	cd backend && SKIP_INTEGRATION=1 .venv/bin/python -m pytest -q

test-backend-integration: ## backend integration test against the compose db (re-seeds it)
	cd backend && INTEGRATION_DATABASE_URL=$(LOCAL_DB) .venv/bin/python -m pytest -q tests/test_integration.py

test-system1: ## system1 service tests (loads real base Laya on CPU, ~20 s)
	cd amd/system1 && .venv/bin/python -m pytest service/tests -q

test-system1-fast:
	cd amd/system1 && SYSTEM1_SKIP_MODEL=1 .venv/bin/python -m pytest service/tests -q

test-vision: ## CPU vision readers, API, OCR, kit checks and deterministic renderer
	cd amd/vision && $(abspath $(PY_VISION)) -m pytest tests -q

test-mcp: ## MCP unit tests (integration tests skip without DATABASE_URL + EMBED_URL)
	cd amd/mcp && .venv/bin/python -m pytest -q -p no:cacheprovider

test-db: ## seed is non-destructive (audit M5), on a throwaway DB in the running compose Postgres
	DB_PORT=$(DB_PORT) $(PY_BACKEND) -m pytest tests/test_seed_nondestructive.py -q -p no:cacheprovider

smoke: ## db smoke test inside the stack: 3 RAG queries + role permissions
	docker compose run --rm --no-deps --entrypoint db/job.sh db-init smoke --roles

e2e: ## end-to-end proof against the running stack, both TRIAGE_MODEs
	DB_PORT=$(DB_PORT) $(PY_BACKEND) scripts/e2e.py

e2e-serial:
	DB_PORT=$(DB_PORT) E2E_MODES=serial $(PY_BACKEND) scripts/e2e.py

e2e-parallel:
	DB_PORT=$(DB_PORT) E2E_MODES=parallel $(PY_BACKEND) scripts/e2e.py

venvs: vision-venv ## create the per-service test venvs (CPU torch for system1)
	test -x $(PY_BACKEND) || (python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements-dev.txt)
	test -x $(PY_MCP) || (python3 -m venv amd/mcp/.venv && amd/mcp/.venv/bin/pip install -r amd/mcp/requirements.txt pytest anyio)
	test -x $(PY_SYSTEM1) || (python3 -m venv amd/system1/.venv && amd/system1/.venv/bin/pip install torch \
	  && amd/system1/.venv/bin/pip install -r amd/system1/service/requirements-dev.txt)


# Vision has no torch dependency.
vision-venv: ## create the CPU vision development environment
	test -x $(PY_VISION) || $(PYTHON_VISION) -m venv amd/vision/.venv
	$(PY_VISION) -m pip install -r amd/vision/requirements-dev.txt
