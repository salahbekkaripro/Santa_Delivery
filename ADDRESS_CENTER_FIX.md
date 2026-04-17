# Correctif Adresse Centrale (Mode Salon)

## Problème
Quand une adresse était saisie, le centre de recherche était correct, mais le dépôt pouvait être placé aléatoirement ailleurs dans le cercle.

## Correction appliquée
1. Si un centre est fourni (`center_lat`, `center_lon`), le dépôt est désormais fixé sur le nœud routier le plus proche de ce centre.
2. Le tirage aléatoire ne concerne plus que les clients.
3. Le comportement sans centre explicite reste inchangé (tirage aléatoire dépôt + clients).

## Fichiers modifiés
- `scripts/generator_engine.py`
- `tests/test_generator_engine_selection.py`

## Détail technique
- Ajout d’une fonction de sélection:
  - `_select_depot_and_clients(nodes, num_clients, center_lat, center_lon)`
- Règle:
  - Avec centre: `depot = argmin(distance_haversine(node, center))`
  - Clients: échantillonnage aléatoire sur les nœuds restants.

## Validation
- Tests exécutés et passants:
  - `tests/test_generator_engine_selection.py`
  - `tests/test_search_constraints.py`
  - `tests/test_api.py`
  - `tests/test_auth_service.py`
  - `tests/test_repository.py`
- Résultat: `21 passed`
