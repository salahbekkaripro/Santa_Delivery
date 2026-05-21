# Rapport Avancements Solveur

Date: 2026-05-21

## 1) Objectif initial

Passer les missions sur le solveur existant (`/solver`), garder l'affichage du score IA en resultats, puis renforcer:
- qualite algorithmique,
- performance,
- observabilite,
- reproductibilite.

## 2) Integrations produit (missions + score IA)

- Utilisation du solveur pour les missions (flux mission -> solve -> benchmark).
- Affichage du score solveur dans la page resultats:
  - priorite a `benchmark.savings.score`,
  - fallback sur `debrief.score.value`.
- Correction du cas "score IA absent" sur la vue resultats.

## 3) Clarification algo (ce que fait le solveur)

- Plus court chemin local: Dijkstra / A* selon contexte.
- Optimisation mission globale: OR-Tools (VRPTW) sur matrice de cout.
- Post-traitement local: ALNS + ILS (si faisable), avec garde d'integrite.

## 4) Optimisations backend implementees

### 4.1 Cache itineraire candidat

- Ajout d'un cache LRU pour les routes candidates dans `scripts/routing_payloads.py`.
- Impact mesure: acceleration nette des appels route-options.

### 4.2 Tuning incidents intelligent

- Boost solveur sous incidents (temps de recherche + marges) dans `backend/app/services.py`.
- Activation conditionnelle:
  - incidents >= seuil,
  - ou mission grande,
  - ou meteo severe + incident.
- Seuils config via env:
  - `NOEL_INCIDENT_TUNING_MIN_INCIDENTS`
  - `NOEL_INCIDENT_TUNING_MIN_CLIENTS`
- Ajout des variables dans `.env.example`.

### 4.3 Endpoint debug solveur

- Nouvel endpoint:
  - `GET /api/missions/{mission_id}/solver-debug`
- Expose:
  - contexte mission,
  - incidents + seuils + decision boost,
  - strategie appliquee,
  - snapshot score solveur.

## 5) Reproductibilite (etape clef)

### 5.1 Pipeline reproductible

- Nouveau script:
  - `scripts/repro_solver_pipeline.py`
- Nouvelle commande:
  - `make repro-check`
- Le rapport JSON inclut:
  - hash SHA256 des artefacts open data (graphe, matrices, meteo, incidents),
  - hash SHA256 canonique des solutions,
  - taux de reproductibilite (2 passes meme seed).

### 5.2 Resultats

- Run principal: `4/4` signatures identiques.
- Exemple valide: `reproducibility_rate = 1.0`.

## 6) Tests multi-politiques

Politiques testees:
- `pca_gls_fast`
- `pca_sa_balanced`
- `pci_gls_deep`
- `savings_tabu`
- `pca_gls_distance`
- `pci_gls_distance`

Constat:
- presque toutes a `1.0` directement,
- `pci_gls_deep` avait un cas non deterministe.

## 7) Fix determinisme `pci_gls_deep`

Actions:
- seed explicite propage au solveur,
- seed explicite pour ALNS et ILS,
- seed stable derive du contexte mission/politique,
- seed stable aussi pour les scripts d'experiences.

Fichiers cles touches:
- `final_scripts/solve_santa_final.py`
- `scripts/ro_improvements.py`
- `backend/app/services.py`
- `scripts/ro_heuristics_experiment.py`

Validation:
- rerun cible `pci_gls_deep` -> `reproducibility_rate = 1.0`.

## 8) Benchmark multi-villes

Nouveau script:
- `scripts/multi_city_benchmark.py`

Nouvelle commande:
- `make multi-city-benchmark`

Fonction:
- genere missions par ville,
- evalue plusieurs politiques,
- repete les passes pour verifier la reproductibilite,
- sort meilleur policy par ville + metriques.

Fix important:
- parsing des villes avec virgules (`--zone` repetable, `--zones` separateur `|`).

Smoke test:
- 2 villes, 2 politiques, 2 passes,
- reproductibilite globale `1.0`,
- meilleur policy peut varier selon ville (normal).

## 9) Artefacts produits

- `daily_reports/repro_solver_pipeline_summary.json`
- `daily_reports/repro_pca_gls_fast.json`
- `daily_reports/repro_pca_sa_balanced.json`
- `daily_reports/repro_pci_gls_deep.json`
- `daily_reports/repro_pci_gls_deep_after_fix.json`
- `daily_reports/repro_savings_tabu.json`
- `daily_reports/repro_pca_gls_distance.json`
- `daily_reports/repro_pci_gls_distance.json`
- `daily_reports/multi_city_benchmark_smoke.json`
- `daily_reports/multi_city_benchmark_smoke.jsonl`

## 10) Commandes utiles

```bash
# reproductibilite solveur
make repro-check

# benchmark heuristiques
make ro-experiment

# benchmark multi-villes (preset rapide)
make multi-city-benchmark

# benchmark multi-villes custom
PYTHONPATH=. .venv/bin/python scripts/multi_city_benchmark.py \
  --zone "Le Marais, Paris" \
  --zone "Mitte, Berlin" \
  --zone "Vieux Lyon, Lyon" \
  --zone "Quartier des Marolles, Bruxelles" \
  --missions-per-zone 3 \
  --repeat-runs 2 \
  --context-mode stable
```

## 11) Etat actuel

- Solveur bien branche pour les missions.
- Score IA affiche dans resultats.
- Debug solveur disponible.
- Reproductibilite validee.
- Pipeline benchmark multi-villes operationnel.

## 12) Points clarifies aujourd'hui (a inclure en soutenance)

### 12.1 Meme moteur entre `/solver` et les missions

- Oui: `/solver` et l'ecran mission utilisent le meme coeur de resolution:
  - endpoint `/api/missions/{mission_id}/solve` (ou `/solve-learned`),
  - puis `_solve_mission_internal(...)`,
  - puis `solve_vrp(...)` (OR-Tools).
- Difference: `solve-learned` ajoute une couche de recommandation/tuning en amont, mais la resolution finale reste le meme solveur.

### 12.2 Choix auto du nombre de traineaux et des modes

- Nombre de traineaux (`k`):
  - recherche progressive (halving), pas brute-force complet.
  - score multi-termes (temps + distance + drops + cout flotte).
- Mix de modes par traineau (`vehicle_modes`):
  - en multimodal, le backend peut tester plusieurs affectations (drive/bike/walk),
  - puis retenir un seul mix final optimise.

### 12.3 Clarification UX: les "3 routes" utilisateur

- En mode mission guidee, l'utilisateur voit en general 3 options locales (`k=3`):
  - `Plus rapide`,
  - `Plus court`,
  - `Alternative diverse`.
- Ce ne sont pas forcement les "3 plus courtes distances" pures:
  - les candidates viennent de A* / shortest path / k-shortest,
  - puis sont filtrees par diversite.
- Le solveur IA global, lui, n'optimise pas en choisissant ces 3 cartes segment par segment:
  - il optimise la tournee complete via OR-Tools sur matrices de cout.

### 12.4 Open Data & graphes: ingestion, traitement, robustesse

- Sources utilisees:
  - OSM/OSMnx (graphe routier),
  - Overpass (POI),
  - Open-Meteo (meteo reelle),
  - OpenTopoData SRTM (relief),
  - ADEME Impact CO2 (facteur CO2).
- Data engineering:
  - nettoyage graphe (plus grand composant),
  - enrichissement aretes (temps, distance, CO2, risque),
  - normalisation robuste + matrice composite.
- Difficultes rencontrees (visibles dans le code/rapports):
  - indisponibilites API (Overpass, meteo, relief, CO2),
  - zones OSM insuffisantes/complexes,
  - non-determinisme d'une politique RO (`pci_gls_deep`).
- Reponses techniques:
  - fallbacks explicites,
  - retries/cache,
  - seeds stables + pipeline de reproductibilite.

### 12.5 Tests et preuves

- Tests unitaires/integration presents (API, profils IA, multimodal, routing, integrite solveur).
- Verification executee sur le scope critique:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_multimodal_generator.py tests/test_solver_postprocess_integrity.py`
  - resultat observe: `11 passed`.
- KPI compares disponibles pour la soutenance:
  - `time_saved_pct`, `co2_saved_kg`,
  - temps/distance naive vs optimisee,
  - `dropped_points`,
  - traces `sleigh_search`, `mode_mix_search`, `ro_portfolio`.
