# Rapport des Travaux IA / RO

Date: 24 avril 2026

## Objectif global
Mettre en place une IA apprenante autour du solveur OR-Tools pour:
- automatiser la collecte de données (sans faire les missions manuellement),
- entraîner et évaluer un modèle de recommandation,
- améliorer la partie Recherche Opérationnelle (heuristiques, métaheuristiques),
- fournir un protocole d'expérimentation reproductible.

## Ce qui a été réalisé

### 1) IA apprenante (profil de stratégie)
- Modèle de recommandation de profil IA (express, ecolo, prudent, opportuniste, agressive, championne).
- Version active: `AI_LEARNING_MODEL_VERSION = "2.0"`.
- Fichier modèle: `cache/api_missions/ai_learning_model.json`.
- Coût d'apprentissage basé sur un coût composite (temps, distance, drop, budget, météo).

### 2) Évaluation du modèle améliorée
- Remplacement du split simple par un split stratifié.
- Version finale du split: `stratified_by_context_profile`.
- Champ de sortie API: `split_strategy`.
- Impact: métriques d'évaluation plus stables et plus représentatives.

### 3) Auto-tuner OR-Tools (nouveau)
- Ajout d'un modèle qui apprend à recommander les paramètres OR-Tools selon le contexte.
- Version active: `ORTOOLS_TUNER_MODEL_VERSION = "1.0"`.
- Fichier modèle: `cache/api_missions/ortools_tuner_model.json`.
- Paramètres appris:
- `first_solution_strategy`
- `local_search_metaheuristic`
- `solver_time_limit_s`
- `time_slack_s`
- `max_route_time_s`
- `drop_penalty`
- `global_span_cost`
- Intégration dans `solve-learned`: si le tuner est disponible, ses paramètres sont appliqués avant résolution.

### 4) Endpoints backend ajoutés
- `POST /api/ortools-tuner/train`
- `GET /api/ortools-tuner/evaluate`
- `GET /api/missions/{mission_id}/ortools-tuner/recommendation`

### 5) Scripts d'automatisation ajoutés
- `scripts/auto_generate_and_train.py`
  - création batch de missions,
  - résolution (`preset`, `learned`, `mixed`),
  - entraînement IA,
  - évaluation IA,
  - sortie JSON de synthèse.
- `scripts/ro_heuristics_experiment.py`
  - protocole RO apparié (même mission, plusieurs politiques),
  - comparaison heuristique + métaheuristique,
  - logs bruts JSONL + rapport agrégé JSON.

### 6) Makefile
- Ajout de `make ro-experiment` pour lancer rapidement une expérimentation RO.

### 7) Frontend
- Ajout/affichage de `split_strategy` dans les métriques IA du workspace mission.

## Fichiers principaux modifiés
- `backend/app/services.py`
- `backend/app/main.py`
- `frontend/lib/types.ts`
- `frontend/components/mission-workspace.tsx`
- `scripts/auto_generate_and_train.py`
- `scripts/ro_heuristics_experiment.py`
- `Makefile`
- `tests/test_ai_learning_service.py`
- `tests/test_ai_learning_api.py`

## Résultats obtenus (mesures)

### IA apprenante (runs batch)
- `daily_reports/auto_learning_run_summary.proof.json`
  - train samples: 17
  - contexts: 4
  - top1: 0.0
  - regret: 208.9952
- `daily_reports/auto_learning_run_summary.tuned30.json`
  - train samples: 47
  - contexts: 5
  - top1: 0.0
  - regret: 2086.8189
- `daily_reports/auto_learning_run_summary.tuned54.json`
  - train samples: 71
  - contexts: 5
  - top1: 0.0
  - regret: 237.4038

### Expérimentation RO (smoke test)
- `daily_reports/ro_heuristics_experiment_smoke.json`
  - 1 instance, 1 politique
  - pipeline complet validé (solve + benchmark + coût composite + rapport)

## Qualité et validation
- Compilation Python validée (`py_compile`) sur les fichiers ajoutés/modifiés.
- Tests unitaires API + service passés:
- `15 passed` sur:
- `tests/test_ai_learning_service.py`
- `tests/test_ai_learning_api.py`

## Commandes utiles

### Entraîner et évaluer IA apprenante (batch)
```bash
.venv/bin/python scripts/auto_generate_and_train.py \
  --missions 30 \
  --solve-mode preset \
  --ai-profile-mode cycle \
  --context-mode stable \
  --min-clients 12 \
  --max-clients 12 \
  --train-limit 8000 \
  --eval-limit 8000 \
  --holdout-ratio 0.2 \
  --output-json daily_reports/auto_learning_run_summary.tuned30.json
```

### Entraîner / évaluer le tuner OR-Tools (API)
```bash
curl -X POST "http://127.0.0.1:8000/api/ortools-tuner/train?limit=2000"
curl "http://127.0.0.1:8000/api/ortools-tuner/evaluate?limit=2000&holdout_ratio=0.25"
```

### Lancer expérimentation RO heuristiques
```bash
make ro-experiment
```

ou

```bash
.venv/bin/python scripts/ro_heuristics_experiment.py \
  --mode existing \
  --instances 8 \
  --output-json daily_reports/ro_heuristics_experiment_summary.json \
  --output-jsonl daily_reports/ro_heuristics_experiment_runs.jsonl
```

## Limites actuelles
- Les contextes restent peu variés dans certains runs, ce qui peut biaiser `top1`.
- L'évaluation peut avoir peu de contextes effectivement comparables selon le split et les données disponibles.
- Le tuner OR-Tools est en place, mais sa qualité dépend fortement de la diversité des instances expérimentales.

## Prochaine étape recommandée (pour le prof RO)
- Lancer un plan d'expérience complet:
- 12 à 20 instances fixes (seedées),
- 6 politiques OR-Tools (heuristique + métaheuristique),
- comparaison appariée sur les mêmes instances,
- tableau final: coût moyen, écart-type, wins par politique, delta vs baseline.
