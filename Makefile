SHELL := /bin/bash

ROOT_DIR := $(CURDIR)
VENV_PYTHON := $(ROOT_DIR)/.venv/bin/python
VENV_PIP := $(ROOT_DIR)/.venv/bin/pip
BACKEND_APP := backend.app.main:app
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: help install test lint backend frontend dev docker clean legacy-clean

help:
	@echo "🎅 Santa Router Optimizer - Commandes disponibles :"
	@echo "  make install   - Installe les dépendances Backend et Frontend"
	@echo "  make dev       - Lance Backend et Frontend en local (parallèle)"
	@echo "  make test      - Lance les tests d'intégration (pytest)"
	@echo "  make lint      - Vérifie la syntaxe (Python + TypeScript)"
	@echo "  make docker    - Lance l'application via Docker Compose"
	@echo "  make clean     - Nettoie les artefacts de build"

install:
	$(VENV_PIP) install -r requirements.txt
	cd frontend && npm install

test:
	$(VENV_PYTHON) -m pytest tests/test_api_v2.py

lint:
	$(VENV_PYTHON) -m py_compile backend/app/*.py scripts/*.py final_scripts/*.py
	cd frontend && npm run lint && ./node_modules/.bin/tsc --noEmit

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
