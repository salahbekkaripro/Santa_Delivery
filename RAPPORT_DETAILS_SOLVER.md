# Détails du solveur Noel (état actuel du code)

Ce document résume le fonctionnement réel du solveur: pipeline, matrices, choix du nombre de traîneaux, profils IA, incidents, relief SRTM, CO2 et score.

## 1) Pipeline global (`/solver`)

1. Création mission (`create_mission`):
- Génère le graphe et les points de livraison.
- Calcule les matrices: temps, distance, CO2, risque, composite.
- Optionnel: applique le relief SRTM (pente) sur temps et distance.
- Optionnel: active ADEME Impact CO2 pour recalculer la matrice CO2.

2. Résolution (`solve_mission`):
- Appelle `_solve_mission_internal(..., use_portfolio=True, optimize_sleigh_count=True)`.
- Peut adapter la stratégie IA (portfolio + incidents).
- Peut ajuster le nombre de traîneaux via `sleigh_search`.
- Applique la contrainte "une nuit" (horizon max configurable) si activée.
- Priorise la couverture (nombre de colis servis) via pénalité de drop renforcée.
- Lance OR-Tools pour la solution finale.
- Calcule benchmark (naïf vs optimisé) puis score/KPI.

## 2) Matrices et objectif d’optimisation

### 2.1 Matrices
- `time_matrix`: coût temps.
- `dist_matrix`: coût distance.
- `co2_matrix`: coût CO2 par arc.
- `risk_matrix`: coût risque.
- `composite_matrix`: somme pondérée normalisée des 4.

Formules arc-level (base):
- `travel_time_s = length_m / speed_m_s`
- `co2_g = (length_m / 1000) * mode_co2`
- `risk_score = (length_m / 1000) * risk_factor * oneway_penalty`

### 2.2 Composite

Normalisation robuste (médiane), puis:

`composite = w_time*time + w_dist*dist + w_co2*co2 + w_risk*risk`

Poids envoyés par `/solver`:
- time `0.55`
- distance `0.20`
- co2 `0.15`
- risk `0.10`

Quand le mode "une nuit" est activé:
- l’horizon `night_horizon_s` borne explicitement les arrivées,
- la fonction objectif est orientée "servir un maximum de colis" via une pénalité de non-livraison calibrée dynamiquement.

## 3) Comment le solveur choisit le nombre de traîneaux (`k`)

### 3.1 Principe
Le frontend envoie un `num_vehicles` initial, mais le backend peut le remplacer avec `_select_sleigh_count_with_halving` quand `optimize_sleigh_count=True`.

### 3.2 Bornes de recherche
- `k_base`: valeur initiale de la stratégie.
- `k_min`: contrainte de capacité: `ceil(total_weight / vehicle_capacity)`.
- `k_upper`: `min(SLEIGH_SEARCH_MAX_K, num_clients, max(k_min, k_base + 2), max_vehicles_cap optionnel)`.

Note:
- si `max_vehicles_cap < k_min`, le solveur teste quand même `k=max_vehicles_cap` (solution possiblement partielle avec drops).

### 3.3 Candidats testés
- Le moteur ne balaie pas tous les `k`.
- Il échantillonne au plus `SLEIGH_SEARCH_MAX_CANDIDATES` (défaut 4) via `_sleigh_candidates`.

### 3.4 Halving progressif (rapide)
- Rounds de probe courts:
  - mode compact: `[1s, 2s]`
  - sinon `[2s, 4s]`
- À chaque round:
  - solve OR-Tools pour chaque `k` actif,
  - score chaque `k`,
  - garde la meilleure moitié,
  - répète jusqu’à convergence.

### 3.5 Fonction de score `k`

`score = total_time_s`
`      + DIST_WEIGHT * total_dist_m`
`      + DROP_WEIGHT * drop_penalty * dropped_count`
`      + FLEET_WEIGHT * k * sleigh_cost`

Poids (env):
- `NOEL_SLEIGH_SEARCH_DIST_WEIGHT` (défaut `0.015`)
- `NOEL_SLEIGH_SEARCH_DROP_WEIGHT` (défaut `0.0015`)
- `NOEL_SLEIGH_SEARCH_FLEET_WEIGHT` (défaut `2.0`)

Note:
- en mode "une nuit", `drop_penalty` peut être augmenté automatiquement avant chaque solve pour privilégier la couverture client.

Conclusion: le solveur choisit `k` par recherche progressive (halving), pas par brute-force complet.

## 4) Choix du mode par traîneau (multimodal)

### 4.1 Principe
Le solveur peut attribuer un mode différent à chaque traîneau:
- ex: `["drive", "bike", "drive"]`.
- la décision est faite automatiquement côté backend.

Le frontend n’impose pas un mode unique final: il fournit le contexte, puis le backend peut chercher un meilleur mix.

### 4.2 Données utilisées
À la création mission multimodale:
- calcul des matrices par mode (`drive`, `bike`, `walk`) pour: temps, distance, CO2, risque, composite;
- sauvegarde dans `core_data/mode_matrices/*.npy`;
- index des fichiers dans `core_data/multimodal_profile.json` (`mode_matrix_files`).

### 4.3 Recherche du meilleur mix de modes
Le backend utilise une recherche type halving (comme pour `k`):
- construit des candidats de mix de modes;
- lance des probes rapides OR-Tools sur chaque candidat;
- score chaque candidat;
- garde la meilleure moitié;
- répète jusqu’au meilleur mix.

Configuration:
- `NOEL_MODE_MIX_SEARCH_ENABLED=1`
- `NOEL_MODE_MIX_SEARCH_MAX_CANDIDATES=8` (exemple)

### 4.4 Pourquoi on “voit les 3 modes lancés”
Quand tu vois `drive`, `bike`, `walk` passer:
- c’est la phase de test des candidats (exploration);
- ce n’est pas 3 solutions finales simultanées.

À la fin:
- un seul mix est retenu (`vehicle_modes`) et utilisé pour la résolution finale.

### 4.5 Comment OR-Tools l’applique
Le solveur utilise des coûts par véhicule:
- `SetArcCostEvaluatorOfVehicle(...)`
- `AddDimensionWithVehicleTransits(...)`

Donc chaque traîneau est réellement optimisé avec sa propre matrice de mode, pas une matrice globale unique.

## 5) Profils IA

### 5.1 Presets (pas ML)
Profils (`express`, `ecolo`, `prudent`, `agressive`, etc.) = paramètres OR-Tools:
- cible (`time`/`distance`/`composite`),
- limite de temps,
- first-solution,
- métaheuristique,
- slack,
- pénalités, etc.

### 5.2 Recommandation apprenante (ML léger)
Le projet a un modèle statistique contextuel (historique de missions), avec lissage bayésien simple.

Coût d’entraînement:

`composite_cost = time_per_client_s`
`               + 95 * dist_per_client_km`
`               + 2400 * drop_ratio`
`               + 1200 * budget_over_ratio`
`               + 180 * weather_penalty`

Estimation profil:

`expected = (n_context * mean_context + alpha * mean_global) / (n_context + alpha)`

### 5.3 `solve-learned`: fonctionnement exact

`solve-learned` n’est pas un autre solveur VRP: c’est une couche de sélection/tuning avant le même OR-Tools final.

Flux:
1. Charge le modèle apprenant profil IA (`load_ai_learning_model`), ou tente un entraînement auto si absent.
2. Construit un contexte mission:
- météo (bucket),
- incidents,
- taille mission (clients),
- budget/client,
- coût traîneau,
- densité géographique.
3. Classe les profils IA par coût attendu (`expected_cost`) avec lissage bayésien:

`expected = (n_context * mean_context + alpha * mean_global) / (n_context + alpha)`

4. (Optionnel) applique un auto-tuner OR-Tools appris:
- choisit une policy (first solution, metaheuristic, time limit, slack, penalties) selon contexte + profil.
5. Construit un petit portfolio de stratégies candidates:
- base,
- meilleures policies tuner,
- presets RO.
6. Lance des probes rapides sur les candidates, puis garde la meilleure.
7. Passe la stratégie retenue à `_solve_mission_internal(...)`.
8. Résolution finale:
- même pipeline que `solve`:
  - ajustement incidents,
  - recherche du nombre de traîneaux (`k`) si activée,
  - recherche du mix de modes par traîneau (`vehicle_modes`),
  - solve OR-Tools final.

Donc:
- `solve-learned` = meilleure sélection de paramètres en amont,
- solveur de tournée final = identique (`solve_vrp` OR-Tools).

## 6) Reliefs / SRTM

### 6.1 Source
- SRTM (Shuttle Radar Topography Mission), via OpenTopoData.

### 6.2 Effet
- Temps ajusté selon pente (montée pénalisée, descente allégée avec cap).
- Distance “énergétique” ajustée.
- Donc impact direct sur la matrice composite et la tournée finale.

## 7) Incidents

### 7.1 Génération
- Si `random_incidents=true`, des segments peuvent être pénalisés.
- Matrice incident construite avec pénalités de temps fortes (`*6`, cap).

### 7.2 Impact
- Le solveur replanifie avec ces coûts modifiés.
- En contexte tendu (incidents/météo/taille), budget de recherche peut être boosté.

## 8) CO2 (harmonisé partout)

## 8.1 Source CO2 utilisée
La source opérationnelle est la `co2_matrix` mission:
- si option ADEME activée: facteur g/km récupéré via API ADEME Impact CO2,
- sinon: facteur local par mode,
- fallback sécurisé distance×facteur si nécessaire.

Cette source est tracée dans:
- `core_data/multimodal_profile.json` > `co2_source`.

## 8.2 KPI benchmark
Le benchmark calcule désormais:
- `naive.total_co2_kg`
- `optimized.total_co2_kg`
- `savings.co2_saved_kg = naive - optimized`

Donc plus de dépendance principale à `120 g/km` fixe.

Le bloc `benchmark.co2_model` indique la provenance:
- `source = "matrix"` si matrice CO2 utilisée,
- `source = "distance_fallback"` sinon.

## 8.3 Analyse éco (`/api/missions/{id}/eco/co2-analysis`)
L’analyse éco recalcule IA/naïf/humain à partir de la même logique CO2 (matrice mission + fallback), et expose aussi:
- `co2_model.source`
- `co2_model.fallback_factor_g_per_km`

## 9) Score affiché

Composantes:
- Temps économisé.
- CO2 économisé.
- Budget restant.
- Couverture colis (`served_ratio`).

Formules:

`timeScorePct = clamp(time_saved_pct * 2.5, 0, 100)`

`co2RefKg = max(1.0, num_clients * 0.1)`

`co2Score = clamp((co2_saved_kg / co2RefKg) * 100, 0, 100)`

`coverageScorePct = clamp(served_ratio * 100, 0, 100)`

`baseScore = 0.45*timeScorePct + 0.20*co2Score + 0.10*budgetRemainingPct + 0.25*coverageScorePct`

Puis bonus:
- bonus profil IA (`difficulty_bonus`),
- bonus incidents,
- bonus météo,
- bonus humain vs IA (debrief backend).

Score final borné à `[0, 100]`.

## 10) Réponse courte

- Oui, le backend peut choisir le nombre de traîneaux automatiquement via `sleigh_search`.
- Oui, en multimodal le backend peut aussi choisir automatiquement le mode de chaque traîneau (`vehicle_modes`) via recherche progressive.
- Oui, le CO2 est maintenant aligné entre optimisation, benchmark, analyse éco et score (avec fallback explicite si données incomplètes).

## 11) `/solver` vs missions: même solveur ?

Oui.

Les deux parcours appellent le même endpoint de résolution backend:
- `/api/missions/{mission_id}/solve` (ou `/solve-learned`).
- puis `_solve_mission_internal(...)`.
- puis `solve_vrp(...)` (OR-Tools).

Donc:
- `/solver` et l’écran mission partagent le même moteur de résolution final.
- seule la préparation amont peut différer (ex: `solve-learned`).

## 12) Pourquoi ces algorithmes et pas d’autres

### 12.1 Plus court chemin / matrices
- Matrices mission: Dijkstra source-unique répété (`single_source_dijkstra_path_length`) pour temps/distance/CO2/risque.
- Tracé de route segmentaire: A* (heuristique Haversine admissible) + fallbacks.

Raison:
- Dijkstra est robuste et naturel pour poids positifs et calcul massif des matrices.
- A* réduit l’exploration pour les requêtes ponctuelles A→B.

### 12.2 Optimisation globale
- Le problème principal est un VRP (capacités, fenêtres, pénalités, flotte, modes), pas un simple plus court chemin.
- Le solveur final est OR-Tools (constructif + métaheuristiques).

### 12.3 Alternatives considérées
- Floyd-Warshall / Dijkstra bidirectionnel / A* bidirectionnel: présents pour analyse et endpoints pédagogiques.
- OR-Tools presets/tuning/portfolio: comparés par probes internes avant sélection finale.

## 13) Tests et validation

### 13.1 Tests présents dans le projet
Le dossier `tests/` couvre:
- API et services,
- profils IA / modèle apprenant,
- routage humain et options de route,
- multimodal,
- score,
- intégrité post-process solveur.

Exemples:
- `tests/test_ai_profiles.py`
- `tests/test_multimodal_generator.py`
- `tests/test_solver_postprocess_integrity.py`
- `tests/test_routing_payloads.py`

### 13.2 Exécution vérifiée pendant l’analyse
Run ciblé exécuté:

`PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_multimodal_generator.py tests/test_solver_postprocess_integrity.py`

Résultat:
- `11 passed`

## 14) Valeurs chiffrées pour comparer les choix

### 14.1 KPI benchmark (naïf vs optimisé)
- `benchmark.naive.total_time_s`
- `benchmark.optimized.total_time_s`
- `benchmark.naive.total_dist_m`
- `benchmark.optimized.total_dist_m`
- `benchmark.naive.total_co2_kg`
- `benchmark.optimized.total_co2_kg`
- `benchmark.savings.time_saved_pct`
- `benchmark.savings.co2_saved_kg`
- `results.dropped_points`
- `results.served_points_count`
- `results.total_clients_count`
- `results.served_ratio`

### 14.2 Choix auto de stratégie (traces comparatives)
- `sleigh_search`:
  - scores par `k`,
  - `total_time_s`, `total_dist_m`, `dropped_count` par candidat,
  - `k` retenu.
- `mode_mix_search`:
  - scores par `vehicle_modes`,
  - résultat des rounds de halving,
  - mix final retenu.
- `ro_portfolio.probe_results`:
  - `probe_cost` par candidate OR-Tools,
  - candidate sélectionnée.

### 14.3 Comparaison Dijkstra / A* (graph)
- `reduction_pct` sur nœuds explorés:
  - A* bidirectionnel vs Dijkstra unidirectionnel.

## 15) Conclusion consolidée

- Oui, plusieurs méthodes ont été étudiées/testées (plus courts chemins, heuristiques OR-Tools, portfolio, tuning).
- Oui, il existe des métriques quantitatives pour comparer les choix.
- Oui, la résolution finale en prod reste unifiée autour de `solve_vrp` (OR-Tools), avec sélection amont de paramètres (`solve` ou `solve-learned`).

## 16) Routes affichées en mission (les 3 options utilisateur)

### 16.1 Pourquoi il y en a souvent 3
Dans le mode mission guidé, la requête d’options de trajet utilise `k=3` par défaut.
Le frontend n’envoie généralement pas de `k` explicite, donc le backend renvoie 3 alternatives.

Important:
- ce ne sont pas forcément les “3 plus courtes distances” strictes;
- ce sont 3 candidates construites pour offrir un compromis vitesse / distance / diversité.

### 16.2 Comment ces 3 routes sont construites
Pour un segment `from_id -> to_id`, le backend:
1. projette départ/arrivée sur le graphe OSM (nœuds les plus proches),
2. génère un pool de candidats:
- A* pondéré temps (`travel_time`) pour la route rapide,
- shortest path pondéré distance (`length`) pour la route courte,
- `k_shortest_paths` en distance et en temps pour enrichir,
3. déduplique et calcule `dist_m`, `time_s`, géométrie,
4. filtre par diversité (overlap d’arêtes) pour éviter 3 routes quasi identiques,
5. étiquette:
- `Plus rapide` (temps min parmi les options retenues),
- `Plus court` (distance min parmi les options retenues),
- sinon `Alternative diverse N`.

Donc:
- oui, parmi les 3 il y en a une “distance min” (`Plus court`),
- mais l’ensemble n’est pas “top-3 distance” pur.

### 16.3 Sens de circulation et perception “bizarre”
Le calcul suit la topologie routière OSM orientée:
- sens uniques,
- accessibilité du mode,
- incidents (évités ou pénalisés),
- facteur météo/vitesse.

Une rue “intuitive” visuellement peut donc ne pas sortir si elle est moins optimale ou moins faisable dans le graphe.

### 16.4 Différence avec le solveur IA
Mode mission guidé:
- l’utilisateur choisit parmi 3 options locales pour un segment A→B.

Solveur IA (`solve` / `solve-learned`):
- n’utilise pas ce sélecteur “3 options” segment par segment;
- optimise globalement toute la tournée avec OR-Tools sur matrices et contraintes;
- les rues exactes sont reconstruites ensuite pour affichage cartographique.

### 16.5 Mode “free routing”
Si activé (`isFreeRouting`), l’utilisateur peut avancer nœud par nœud via les adjacences:
- contrôle beaucoup plus fin des rues,
- au prix d’un pilotage plus manuel.

## 17) Source de données et traitement (API + engineering)

### 17.1 Sources externes utilisées

1. Carte et réseau routier:
- OpenStreetMap via OSMnx:
  - `graph_from_place(...)` ou `graph_from_point(...)` selon le cas.
- Utilisé pour construire le graphe de circulation (drive/bike/walk).

2. Noms de points de livraison (POI):
- Overpass API (données OSM) pour récupérer des noms réels (`shop`, `amenity`, etc.).
- Si indisponible, fallback sur noms fictifs.

3. Météo:
- Open-Meteo (API gratuite, sans CB) quand `weather_key="real"`.
- Sinon:
  - `weather_key="random"` -> météo simulée pondérée,
  - valeur fixe (`Clear`, `Rain`, etc.) si profil explicite.

4. Relief:
- OpenTopoData (dataset SRTM90m NASA) pour altitudes.
- Utilisé si `with_elevation=true`.

5. CO2:
- ADEME Impact CO2 (endpoint transport) si `use_ademe_co2=true`.
- Sinon facteur local par mode (`drive/bike/walk`).
- Fallback de sécurité si l’API échoue.

### 17.2 Données internes générées

- Missions, clients, météo, incidents, résultats sont persistés par mission.
- Matrices stockées en `.npy`:
  - `time`, `distance`, `co2`, `risk`, `composite`.
- En multimodal:
  - matrices par mode dans `core_data/mode_matrices/*.npy`,
  - métadonnées dans `multimodal_profile.json` (dont `co2_source`).

### 17.3 Nettoyage / validation des données

1. Graphe:
- réduction au plus grand composant connecté (fort puis faible) pour limiter les nœuds inatteignables.
- fallback géographique robuste si `graph_from_place` échoue.

2. Attributs d’arêtes:
- normalisation `highway`,
- parsing `maxspeed` (dont conversion mph -> km/h),
- reconstruction `length` si manquante via Haversine.

3. Paramètres d’objectif:
- normalisation des poids (`time`, `distance`, `co2`, `risk`) pour sommer à 1.
- fallback sur poids par défaut si payload invalide.

4. Robustesse API:
- Overpass: multi-endpoints + fallback local.
- Open-Meteo / ADEME / OpenTopoData: try/catch + replis explicites.

### 17.4 Feature engineering principal

1. Features réseau par arête:
- `travel_time` (distance / vitesse mode),
- `co2_g` (distance × facteur mode/API),
- `risk_score` (distance × facteur voie + effet sens unique),
- `speed_kph_legal`, `oneway_effective`.

2. Features mission:
- fenêtres temporelles (`tw_start`, `tw_end`),
- catégories de colis (normal/fragile/réfrigéré/encombrant),
- poids ajusté par catégorie.

3. Features contexte IA (apprentissage):
- bucket météo, incidents, taille, budget/client, coût traîneau, densité.
- utilisées par le modèle de recommandation profil + auto-tuner OR-Tools.

4. Matrice composite:
- scaling robuste (médiane) par matrice,
- somme pondérée `time/dist/co2/risk`.

### 17.5 Ce qui est “réel” vs “simulé”

- Réel (open data/API): graphe OSM, POI Overpass, météo Open-Meteo (si `real`), relief SRTM, facteur CO2 ADEME (si activé).
- Simulé/généré: position finale des clients (échantillonnage nœuds), catégories colis, incidents aléatoires, météo simulée (`random`), fallback CO2 local.

### 17.6 Conséquence produit

Le pipeline mélange open data réelle + génération contrôlée:
- assez réaliste pour l’optimisation sur réseau urbain réel,
- reproductible et robuste même quand une API externe répond mal.

## 18) Amélioration 2026-05-21: Contrainte "une nuit" + objectif couverture colis

### 18.1 Ce qui a changé
- Le générateur mission crée désormais des fenêtres par défaut sur une nuit complète:
  - clients non contraints: `tw_start=0`, `tw_end=28800`.
  - clients contraints: fenêtres serrées `0-7200` ou `7200-14400`.
- Le solveur OR-Tools accepte un horizon `night_horizon_s`:
  - borne la dimension temps (`max_route_time_s` effectif),
  - borne les `tw_end` à l’horizon nuit,
  - fixe le départ des traîneaux à `t=0` en mode nuit.
- La logique de drop est orientée couverture:
  - calcul d’une pénalité minimale dynamique pour les non-livrés,
  - objectif pratique: livrer le plus de colis possible dans l’horizon.
- Les sorties solveur exposent de nouveaux champs:
  - `served_points_count`, `total_clients_count`, `served_ratio`,
  - `objective.night_horizon_s`,
  - `objective.prioritize_served_points`,
  - `objective.effective_drop_penalty`,
  - bloc `one_night` dans les résultats backend.

### 18.2 Pourquoi
- Besoin produit: simuler une opération Noël réaliste "en une seule nuit".
- Besoin optimisation: accepter qu’une mission puisse être partiellement servie et maximiser le volume livré plutôt que forcer une couverture impossible.

### 18.3 Impact produit / technique
- Produit:
  - le solveur reste faisable sous contrainte temporelle stricte,
  - en cas de tension, il privilégie la couverture colis au lieu d’optimiser uniquement le coût de trajet.
- Technique:
  - tuning backend de stratégie via env (`one_night`),
  - enrichissement du contrat de sortie pour suivre la couverture réelle,
  - génération de données alignée avec une fenêtre de nuit complète.

### 18.4 Fichiers modifiés
- `.env.example`
- `scripts/generator_engine.py`
- `final_scripts/solve_santa_final.py`
- `backend/app/services.py`
- `tests/test_ai_profiles.py`
- `tests/test_solver_postprocess_integrity.py`
- `RAPPORT_DETAILS_SOLVER.md`

### 18.5 Variables d’environnement concernées
- `NOEL_ONE_NIGHT_ENABLED` (défaut `1`)
- `NOEL_ONE_NIGHT_DURATION_S` (défaut `28800`)
- `NOEL_ONE_NIGHT_PRIORITIZE_SERVED` (défaut `1`)

### 18.6 Tests exécutés + résultat
- Commande:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
- Résultat:
  - `39 passed in 2.09s`
- Vérification syntaxe:
  - `python3 -m py_compile backend/app/services.py final_scripts/solve_santa_final.py scripts/generator_engine.py tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py`
  - résultat: succès (aucune erreur).

### 18.7 Limites restantes
- La maximisation "nombre de colis livrés" reste implémentée via pondération/pénalité (approche pragmatique), pas via objectif lexicographique strict multi-objectif OR-Tools.
- L’horizon nuit est global (env) et non paramétré mission par mission côté payload API/front.
- Les fenêtres clients restent en partie aléatoires; elles peuvent rendre certaines missions très sélectives selon tirage.

## 19) Amélioration 2026-05-21: Score avec couverture colis

### 19.1 Ce qui a changé
- Le calcul du score backend (`get_debrief`) inclut maintenant la couverture:
  - `coverageScorePct = served_ratio * 100`.
  - nouvelle base:
    - `0.45 * timeScorePct`
    - `0.20 * co2Score`
    - `0.10 * budgetRemainingPct`
    - `0.25 * coverageScorePct`
- Le breakdown score expose les composantes coverage (`coverage_score_pct`, `coverage_contribution`).
- Le frontend `/solver` applique la même formule pour garder un affichage cohérent.
- Le frontend debrief affiche explicitement la contribution coverage quand disponible.

### 19.2 Pourquoi
- Avec la contrainte "une nuit", la qualité d’une solution dépend aussi du volume de colis réellement servis.
- Sans cette composante, un plan partiel pouvait rester trop bien noté.

### 19.3 Impact produit / technique
- Produit:
  - le score valorise maintenant à la fois performance et couverture réelle.
- Technique:
  - backend: source de vérité score ajustée.
  - frontend: alignement formule score immédiat.
  - types TS enrichis pour les champs de couverture.

### 19.4 Fichiers modifiés
- `backend/app/services.py`
- `frontend/app/solver/page.tsx`
- `frontend/lib/types.ts`
- `frontend/components/debrief-view.tsx`
- `tests/test_ai_profiles.py`
- `RAPPORT_DETAILS_SOLVER.md`

### 19.5 Variables d’environnement concernées
- Aucune nouvelle variable d’environnement pour cette amélioration.

### 19.6 Tests exécutés + résultat
- Commandes:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
  - `cd frontend && npx tsc -p tsconfig.json --noEmit`
- Résultats:
  - `40 passed in 2.86s`
  - `tsc` sans erreur.

### 19.7 Limites restantes
- La pondération score est fixe dans le code (pas encore configurable).
- Le score frontend `/solver` reste une estimation locale tant que l’utilisateur n’ouvre pas le debrief backend.

## 20) Amélioration 2026-05-21: Cap optionnel du nombre de traîneaux

### 20.1 Ce qui a changé
- Ajout d’un paramètre API `max_vehicles` optionnel sur `SolveMissionRequest`.
- Le backend applique ce cap à la stratégie avant solve final.
- La recherche auto `sleigh_search` respecte ce cap:
  - borne `k_upper` par `max_vehicles_cap`,
  - conserve un candidat même si le cap est inférieur au `k_min` capacité (cas partiel assumé).
- Le debug solveur expose `max_vehicles_cap` et `k_min_capacity`.
- Le frontend `/solver` ajoute une option:
  - checkbox "Limiter le nombre max de traîneaux",
  - champ numérique "Max traîneaux autorisés",
  - envoi du cap via `solveMission(..., max_vehicles=...)`.

### 20.2 Pourquoi
- Sans plafond de flotte, on pouvait livrer presque tout en augmentant les traîneaux.
- Le cap rend le scénario "une nuit" plus réaliste et force de vrais arbitrages.

### 20.3 Impact produit / technique
- Produit:
  - l’utilisateur peut choisir un niveau de contrainte flotte.
  - la couverture baisse naturellement quand le cap est serré.
- Technique:
  - API enrichie sans rupture (champ optionnel),
  - pipeline de sélection `k` adapté au cap,
  - télémétrie debug plus explicite.

### 20.4 Fichiers modifiés
- `backend/app/schemas.py`
- `backend/app/services.py`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/app/solver/page.tsx`
- `tests/test_ai_profiles.py`
- `RAPPORT_DETAILS_SOLVER.md`

### 20.5 Variables d’environnement concernées
- Aucune nouvelle variable d’environnement.

### 20.6 Tests exécutés + résultat
- Commandes:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
  - `cd frontend && npx tsc -p tsconfig.json --noEmit`
- Résultats:
  - `41 passed in 2.97s`
  - `tsc` sans erreur.

### 20.7 Limites restantes
- Le cap est maintenant propagé au flow `simulation/incident-replan` du mode `/solver` (voir section 22).
- Le cap est maintenant prévu dans la configuration de création `versus` custom (voir section 23).

## 21) Amélioration 2026-05-21: Cap traîneaux intégré au mode mission

### 21.1 Ce qui a changé
- Le mode mission (`MissionWorkspace`) envoie désormais `max_vehicles` au solveur quand l’option est activée.
- La sidebar mission ajoute les contrôles:
  - toggle "Limiter",
  - champ numérique "Cap max solveur".
- Les types frontend associés au debug/stratégie conservent l’info cap (`max_vehicles_cap`, `k_min_capacity`) pour lecture côté mission.

### 21.2 Pourquoi
- Tu voulais le même comportement qu’en `/solver` dans le mode mission.
- Sans ce câblage, la contrainte de flotte restait partielle selon l’écran utilisé.

### 21.3 Impact produit / technique
- Produit:
  - cohérence UX: même règle de cap flotte en mission et en solveur libre.
  - meilleur contrôle du réalisme "une nuit" pendant une mission guidée.
- Technique:
  - aucun changement API supplémentaire (réutilisation du champ `max_vehicles` déjà ajouté),
  - simple propagation front mission -> backend solve.

### 21.4 Fichiers modifiés
- `frontend/components/mission-workspace.tsx`
- `frontend/components/mission-sidebar.tsx`
- `frontend/lib/types.ts`
- `RAPPORT_DETAILS_SOLVER.md`

### 21.5 Variables d’environnement concernées
- Aucune nouvelle variable d’environnement.

### 21.6 Tests exécutés + résultat
- Commandes:
  - `cd frontend && npx tsc -p tsconfig.json --noEmit`
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
- Résultats:
  - `tsc` sans erreur.
  - `41 passed in 2.31s`

### 21.7 Limites restantes
- Le cap mission est appliqué sur le solve principal.
- L’écran mission n’expose pas encore de module dédié `incident/replan`; la simulation incident reste portée par le bac `/solver` (couvert section 22).

## 22) Amélioration 2026-05-21: Cap traîneaux propagé à la simulation incident/replan

### 22.1 Ce qui a changé
- Le payload `simulateIncidentReplan` accepte maintenant `max_vehicles` côté frontend.
- L’endpoint backend `IncidentReplanRequest` accepte aussi `max_vehicles`.
- Le service `simulate_incident_replan` relaie `max_vehicles` au solve interne, avec fallback sur `ai_strategy.max_vehicles_cap` du run précédent.
- Le frontend `/solver` envoie le cap actif pendant la simulation incident/replan (si l’option "Limiter" est activée).
- Un test API vérifie l’acceptation et la transmission de `max_vehicles` sur l’endpoint incident/replan.

### 22.2 Pourquoi
- Sans cette propagation, le cap était appliqué au solve initial mais pas au replan incident.
- Cela créait une incohérence produit: la simulation pouvait remonter le nombre de traîneaux malgré la contrainte choisie.

### 22.3 Impact produit / technique
- Produit:
  - le comportement de cap flotte reste cohérent entre solve initial et replan incident.
  - les comparaisons avant/après incident reflètent la même contrainte opérationnelle.
- Technique:
  - contrat API incident/replan enrichi sans rupture (`max_vehicles` optionnel).
  - fallback backend sur le cap déjà calculé pour limiter les divergences entre runs.

### 22.4 Fichiers modifiés
- `frontend/app/solver/page.tsx`
- `frontend/lib/api.ts`
- `backend/app/schemas.py`
- `backend/app/services.py`
- `tests/test_api.py`
- `RAPPORT_DETAILS_SOLVER.md`

### 22.5 Variables d’environnement concernées
- Aucune nouvelle variable d’environnement.

### 22.6 Tests exécutés + résultat
- Commandes:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
  - `cd frontend && npx tsc -p tsconfig.json --noEmit`
- Résultats:
  - `42 passed in 2.39s`
  - `tsc` sans erreur.

### 22.7 Limites restantes
- Le cap incident/replan est désormais cohérent avec `mission_config.max_vehicles` en `versus custom` (voir section 23).

## 23) Amélioration 2026-05-21: Cap traîneaux ajouté au mode versus custom

### 23.1 Ce qui a changé
- Ajout du champ optionnel `max_vehicles` dans la configuration `versus` custom:
  - schémas backend (`VersusMissionConfigRequest`),
  - types frontend (`VersusMissionConfig`, `VersusMissionSummary`).
- Validation/sanitation backend:
  - `max_vehicles` autorisé dans `mission_config`,
  - normalisé entre 1 et 20,
  - borné au `num_clients` de la mission custom.
- UI builder `versus custom`:
  - nouveau contrôle "Cap max traîneaux (optionnel)" avec toggle `Limiter` + input numérique.
- Propagation vers mission live:
  - le `mission_payload` cloné pour les joueurs conserve `max_vehicles`,
  - la mission lit ce cap et verrouille la configuration locale de cap dans la sidebar,
  - le solve mission force ce cap si présent dans `mission.mission.max_vehicles`.
- Résumé invitation:
  - affichage du cap traîneaux dans le preview d’invitation.
- Tests:
  - API: acceptation du champ en création de match custom + rejet valeur hors borne schema,
  - service: clamp de `max_vehicles` au nombre de clients.

### 23.2 Pourquoi
- Tu as demandé le même comportement de cap dans les autres modes, pas seulement solveur/mission.
- En versus custom, il fallait que la contrainte soit partagée et non contournable par un joueur.

### 23.3 Impact produit / technique
- Produit:
  - l’hôte peut définir un cap flotte dès la création d’un duel custom.
  - les deux joueurs héritent de la même contrainte de cap dans leur mission.
  - meilleure cohérence des règles entre création de match, mission live, solve et replan.
- Technique:
  - extension non-breaking des contrats (champ optionnel),
  - sanitation centralisée backend pour éviter les caps incohérents,
  - verrouillage front mission quand le cap vient de la config de match.

### 23.4 Fichiers modifiés
- `backend/app/schemas.py`
- `backend/app/services.py`
- `frontend/lib/types.ts`
- `frontend/components/versus-map-builder.tsx`
- `frontend/components/mission-workspace.tsx`
- `frontend/components/mission-sidebar.tsx`
- `frontend/app/versus/invite/page.tsx`
- `tests/test_api.py`
- `tests/test_ai_profiles.py`
- `RAPPORT_DETAILS_SOLVER.md`

### 23.5 Variables d’environnement concernées
- Aucune nouvelle variable d’environnement.

### 23.6 Tests exécutés + résultat
- Commandes:
  - `PYTHONPATH=. pytest -q tests/test_ai_profiles.py tests/test_solver_postprocess_integrity.py tests/test_api.py`
  - `cd frontend && npx tsc -p tsconfig.json --noEmit`
- Résultats:
  - `44 passed in 2.47s`
  - `tsc` sans erreur.

### 23.7 Limites restantes
- Les templates versus prédéfinis n’exposent pas encore un paramètre cap traîneaux dédié (seulement le mode custom).
