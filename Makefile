SHELL := /bin/bash

ROOT_DIR := $(CURDIR)
VENV_PYTHON := $(ROOT_DIR)/.venv/bin/python
VENV_PIP := $(ROOT_DIR)/.venv/bin/pip
BACKEND_APP := backend.app.main:app
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: help install test lint e2e ci protect-main backend frontend dev docker clean legacy-clean ro-experiment

help:
	@echo "🎅 Santa Router Optimizer - Commandes disponibles :"
	@echo "  make install   - Installe les dépendances Backend et Frontend"
	@echo "  make dev       - Lance Backend et Frontend en local (parallèle)"
	@echo "  make test      - Lance les tests d'intégration (pytest)"
	@echo "  make lint      - Vérifie la syntaxe (Python + TypeScript)"
	@echo "  make e2e       - Lance les tests end-to-end Playwright (frontend)"
	@echo "  make ci        - Lance lint + test + e2e"
	@echo "  make protect-main - Protège la branche main (check requis: CI / ci)"
	@echo "  make docker    - Lance l'application via Docker Compose"
	@echo "  make clean     - Nettoie les artefacts de build"
	@echo "  make ro-experiment - Lance une experience RO heuristiques appairee"

install:
	$(VENV_PIP) install -r requirements.txt
	cd frontend && npm install

test:
	$(VENV_PYTHON) -m pytest tests/test_api_v2.py tests/test_api.py tests/test_route_options_feasibility.py

lint:
	$(VENV_PYTHON) -m py_compile backend/app/*.py scripts/*.py final_scripts/*.py
	cd frontend && npm run lint && ./node_modules/.bin/tsc --noEmit

e2e:
	cd frontend && npm run e2e -- --project=chromium

ci: lint test e2e

protect-main:
	bash scripts/protect_main_branch.sh main "CI / ci"

backend:
	$(VENV_PYTHON) -m uvicorn $(BACKEND_APP) --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

frontend:
	cd frontend && npm run dev -- --port $(FRONTEND_PORT)

dev:
	@echo "🚀 Lancement simultané du Backend et Frontend..."
	make -j 2 backend frontend

docker:
	docker compose up --build

clean:
	rm -rf frontend/.next
	rm -rf cache/api_missions/*
	find . -type d -name "__pycache__" -exec rm -rf {} +

legacy-clean:
	rm -rf legacy/

ro-experiment:
	$(VENV_PYTHON) scripts/ro_heuristics_experiment.py --mode existing --instances 6
