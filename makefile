PY := $(CURDIR)/.venv/bin/python
CHART := infra/helm/todo
KIND_CLUSTER := todo

.PHONY: install test test-backend test-frontend test-arch test-e2e openapi load load-vegeta load-locust load-ui api web cli \
        up down k8s-up k8s-down

install:
	python3 -m venv .venv
	$(PY) -m pip install -r backend/requirements-dev.txt -r load/requirements.txt
	cd frontend && npm install && npx playwright install chromium

## Testes ---------------------------------------------------------------
test: test-backend test-frontend test-e2e

test-backend:            # unit + integração + arquitetura + docs (sem E2E)
	cd backend && $(PY) -m pytest -m "not e2e"

test-frontend:           # type-check + unit + arquitetura
	cd frontend && npx vue-tsc --noEmit && npx vitest run

test-arch:
	cd backend && $(PY) -m pytest tests/architecture
	cd frontend && npx vitest run tests/architecture.test.ts

test-e2e:                # backend: uvicorn real + contrato OpenAPI; frontend: Playwright
	cd backend && $(PY) -m pytest -m e2e
	cd frontend && npx playwright test

## Documentação -----------------------------------------------------------
openapi:                 # regenera docs/openapi.yaml a partir do código
	cd backend && $(PY) export_openapi.py

## Carga -----------------------------------------------------------------
# Sobe um servidor próprio com banco temporário (ou use TARGET=http://...).
# Ajustes: RATE=200 DURATION=30s USERS=100 SPAWN=20 make load
load:
	load/run.sh all

load-vegeta:
	load/run.sh vegeta

load-locust:
	load/run.sh locust

load-ui:                 # interface web do Locust em http://localhost:8089
	$(PY) -m locust -f load/locustfile.py --host $${TARGET:-http://localhost:8000}

## Desenvolvimento --------------------------------------------------------
api:
	cd backend && $(PY) -m uvicorn server:app --reload --port 8000

web:
	cd frontend && npm run dev

cli:
	cd backend && $(PY) main.py $(ARGS)

## Docker Compose ---------------------------------------------------------
up:
	docker compose up -d --build --wait
	@echo "http://localhost:8080"

down:
	docker compose down

## Kubernetes (kind + Helm) -----------------------------------------------
k8s-up:
	docker compose build
	kind get clusters | grep -qx $(KIND_CLUSTER) || kind create cluster --name $(KIND_CLUSTER) --wait 120s
	kind load docker-image todo-backend:local todo-frontend:local --name $(KIND_CLUSTER)
	helm --kube-context kind-$(KIND_CLUSTER) upgrade --install todo $(CHART) \
		--namespace todo --create-namespace --wait
	@echo "kubectl --context kind-$(KIND_CLUSTER) -n todo port-forward svc/todo-frontend 8080:80"

k8s-down:
	kind delete cluster --name $(KIND_CLUSTER)
