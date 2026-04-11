# Operation Noel

Migration progressive du projet de livraison de Noel depuis `Streamlit` vers une architecture `FastAPI + Next.js`, en conservant le moteur Python existant :
- `OSMnx`
- `NetworkX`
- `OR-Tools`
- météo, incidents, benchmark

Le repo contient donc aujourd'hui :
- le moteur Python historique
- l'ancienne interface Streamlit
- la nouvelle API FastAPI
- le nouveau frontend Next.js

## Stack

- Backend : `FastAPI`
- Frontend : `Next.js` App Router
- Carte : `Leaflet`
- Solveur : `OR-Tools`
- Graphe routier : `OSMnx` / `NetworkX`

## Arborescence

- [backend](/home/bekkari/Documents/Graphes/Noel/backend) : API FastAPI
- [frontend](/home/bekkari/Documents/Graphes/Noel/frontend) : interface Next.js
- [scripts](/home/bekkari/Documents/Graphes/Noel/scripts) : services Python partages
- [final_scripts](/home/bekkari/Documents/Graphes/Noel/final_scripts) : solveur et visualisation finale
- [pages](/home/bekkari/Documents/Graphes/Noel/pages) : ancienne interface Streamlit
- [tests](/home/bekkari/Documents/Graphes/Noel/tests) : tests backend et payloads
- [run_all.sh](/home/bekkari/Documents/Graphes/Noel/run_all.sh) : lancement local en une commande
- [Makefile](/home/bekkari/Documents/Graphes/Noel/Makefile) : raccourcis de dev

## Prerequis

- Python `3.10+`
- Node.js `18+`
- un environnement virtuel Python dans `.venv`
- `npm`

Optionnel :
- Docker avec `docker compose`

## Installation locale

### 1. Backend Python

```bash
cd ~/Documents/Graphes/Noel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend Next.js

```bash
cd ~/Documents/Graphes/Noel/frontend
npm install
```

## Lancement rapide

Depuis la racine du projet :

```bash
./run_all.sh
```

Ce script :
- lance les tests backend
- demarre FastAPI en arriere-plan
- demarre Next.js au premier plan

URLs :
- frontend : `http://localhost:3000`
- API : `http://127.0.0.1:8000`
- docs API : `http://127.0.0.1:8000/docs`
- historique missions : `http://127.0.0.1:8000/api/missions`

## Lancement manuel

### Terminal 1 : tests

```bash
cd ~/Documents/Graphes/Noel
source .venv/bin/activate
python -m unittest tests.test_api tests.test_routing_payloads tests.test_repository
```

### Terminal 2 : backend

```bash
cd ~/Documents/Graphes/Noel
source .venv/bin/activate
python -m uvicorn backend.app.main:app --reload
```

### Terminal 3 : frontend

```bash
cd ~/Documents/Graphes/Noel/frontend
npm run dev
```

## Commandes utiles

Le [Makefile](/home/bekkari/Documents/Graphes/Noel/Makefile) expose :

```bash
make help
make test
make pycheck
make backend
make frontend
make dev
make docker
make clean
```

## Tests et verification

### Tests backend

```bash
python -m unittest tests.test_api tests.test_routing_payloads tests.test_repository
```

### Verification Python

```bash
python -m py_compile backend/app/main.py backend/app/services.py backend/app/schemas.py scripts/routing_payloads.py
```

### Build frontend

```bash
cd frontend
npm run build
```

## Docker

Les fichiers suivants sont fournis :
- [docker-compose.yml](/home/bekkari/Documents/Graphes/Noel/docker-compose.yml)
- [backend/Dockerfile](/home/bekkari/Documents/Graphes/Noel/backend/Dockerfile)
- [frontend/Dockerfile](/home/bekkari/Documents/Graphes/Noel/frontend/Dockerfile)

Lancement :

```bash
docker compose up --build
```

Si ton installation utilise encore l'ancien binaire :

```bash
docker-compose up --build
```

Variables utiles :
- [frontend/.env.local.example](/home/bekkari/Documents/Graphes/Noel/frontend/.env.local.example)
- [.env.example](/home/bekkari/Documents/Graphes/Noel/.env.example)

## Etat actuel de la migration

Deja migre :
- creation de mission via API
- snapshots de mission dans SQLite
- page mission Next.js
- choix de chemin humain
- ETA et heures d'arrivee
- incidents et retours depot
- solve IA
- page resultats
- page debrief
- tests backend de base

Encore legacy :
- interface Streamlit complete dans [pages](/home/bekkari/Documents/Graphes/Noel/pages)
- une partie du moteur historique encore appelee par les scripts Python existants

## Notes

- Le backend garde les artefacts lourds en fichiers, mais synchronise maintenant les snapshots de mission dans SQLite.
- Base SQLite par defaut : `cache/api_missions/operation_noel.db`
- `Streamlit` coexiste encore, mais le flux principal de migration est maintenant `FastAPI + Next.js`.
