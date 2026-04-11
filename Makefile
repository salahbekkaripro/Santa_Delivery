SHELL := /bin/bash

ROOT_DIR := $(CURDIR)
VENV_PYTHON := $(ROOT_DIR)/.venv/bin/python
BACKEND_APP := backend.app.main:app
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: help test pycheck backend frontend dev docker clean

help:
	@echo "Cibles disponibles :"
	@echo "  make test      - Lance les tests backend"
	@echo "  make pycheck   - Verifie la syntaxe Python"
	@echo "  make backend   - Lance FastAPI en local"
	@echo "  make frontend  - Lance Next.js en local"
	@echo "  make dev       - Lance le script run_all.sh"
	@echo "  make docker    - Lance docker compose up --build"
	@echo "  make clean     - Nettoie les artefacts locaux"

test:
	$(VENV_PYTHON) -m unittest tests.test_api tests.test_routing_payloads tests.test_repository

pycheck:
	$(VENV_PYTHON) -m py_compile backend/app/main.py backend/app/services.py backend/app/schemas.py scripts/routing_payloads.py

backend:
	$(VENV_PYTHON) -m uvicorn $(BACKEND_APP) --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

frontend:
	cd frontend && npm run dev -- --port $(FRONTEND_PORT)

dev:
	./run_all.sh

docker:
	docker compose up --build

clean:
	rm -rf frontend/.next
	rm -rf frontend/node_modules/.cache
	rm -rf cache/run_all
