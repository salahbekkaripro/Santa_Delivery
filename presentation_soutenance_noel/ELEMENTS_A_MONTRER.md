# Elements a montrer pendant la soutenance

Objectif : ouvrir rapidement les preuves techniques sans chercher dans le projet.

## 1. Application web

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Dans un autre terminal :

```bash
cd /home/bekkari/Documents/Graphes/Noel/frontend
npm run dev -- --port 3000
```

URL :

```text
http://localhost:3000/solver
```

Capture a faire :
- page solveur
- carte avec zone
- resultat de tournee
- score final

## 2. Dossier de mission

Dossier type :

```text
cache/api_missions/<mission_id>/
```

Derniere grosse mission testee :

```text
cache/api_missions/cd0c178cd408/
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
ls -R cache/api_missions/cd0c178cd408 | head -80
```

Ce que ca prouve :
- une mission est stockee avec ses donnees
- les matrices sont sauvegardees
- les resultats sont auditables

## 3. Fichier clients

Fichier :

```text
cache/api_missions/cd0c178cd408/core_data/livraisons_5eme.csv
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
head -n 10 cache/api_missions/cd0c178cd408/core_data/livraisons_5eme.csv
```

A montrer :
- `id`
- `lat`
- `lon`
- `poids_colis`
- `nom_client`
- `tw_start`
- `tw_end`

Ce que ca prouve :
- depot + clients
- coordonnees reelles
- poids et contraintes horaires

## 4. Graphe OpenStreetMap

Fichier :

```text
cache/api_missions/cd0c178cd408/core_data/paris5.graphml
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
ls -lh cache/api_missions/cd0c178cd408/core_data/paris5.graphml
```

Ce que ca prouve :
- le reseau routier vient d'OSM
- le graphe est sauvegarde et reutilisable

## 5. Matrices

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
source .venv/bin/activate
python scripts/show_matrices.py cd0c178cd408 --size 5
```

Matrices affichees :
- temps
- distance
- CO2
- risque
- composite

Ce que ca prouve :
- le graphe est converti en couts entre clients
- le solveur travaille sur des matrices exploitables

## 6. Resultats du solveur

Fichier :

```text
cache/api_missions/cd0c178cd408/production_output/resultats_finaux.json
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
python -m json.tool cache/api_missions/cd0c178cd408/production_output/resultats_finaux.json | head -120
```

A montrer :
- `tours`
- `dropped_points`
- `large_scale`
- `ai_strategy`
- `sleigh_search`

Ce que ca prouve :
- tournees produites
- clients non livres possibles
- mode large scale actif
- nombre de traineaux choisi

## 7. Benchmark

Fichier :

```text
cache/api_missions/cd0c178cd408/core_data/benchmark_results.json
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
python -m json.tool cache/api_missions/cd0c178cd408/core_data/benchmark_results.json | head -100
```

A montrer :
- gain de temps
- CO2 economise
- comparaison naive / optimisee

## 8. Code generation graphe et matrices

Fichier :

```text
scripts/generator_engine.py
```

Lignes a montrer :
- vitesses par type de voie
- annotation des aretes
- calcul temps / CO2 / risque
- calcul matrices
- composite

Commandes :

```bash
cd /home/bekkari/Documents/Graphes/Noel
nl -ba scripts/generator_engine.py | sed -n '52,188p'
nl -ba scripts/generator_engine.py | sed -n '840,936p'
```

## 9. Code relief SRTM NASA

Fichier :

```text
scripts/elevation_engine.py
```

Commande :

```bash
cd /home/bekkari/Documents/Graphes/Noel
nl -ba scripts/elevation_engine.py | sed -n '1,150p'
```

A montrer :
- API OpenTopoData SRTM
- latitude / longitude
- altitude
- pente
- facteur temps

## 10. Code solveur OR-Tools et large scale

Fichier :

```text
final_scripts/solve_santa_final.py
```

Commandes :

```bash
cd /home/bekkari/Documents/Graphes/Noel
nl -ba final_scripts/solve_santa_final.py | sed -n '30,45p'
nl -ba final_scripts/solve_santa_final.py | sed -n '760,1030p'
nl -ba final_scripts/solve_santa_final.py | sed -n '1329,1415p'
```

A montrer :
- strategies OR-Tools
- CP-SAT
- generation de candidates
- dispatch classique / large scale

## 11. Code profils IA et selection des traineaux

Fichier :

```text
backend/app/services.py
```

Commandes :

```bash
cd /home/bekkari/Documents/Graphes/Noel
nl -ba backend/app/services.py | sed -n '50,150p'
nl -ba backend/app/services.py | sed -n '2935,3135p'
```

A montrer :
- profils Express / Ecolo / Prudent
- parametres OR-Tools
- score de selection des traineaux
- `k_min_capacity`
- `k_base`

## 12. Fichiers crees pour la soutenance

Dossier :

```text
presentation_soutenance_noel/
```

Fichiers :

```text
SLIDES_CONTENU.md
ELEMENTS_A_MONTRER.md
PROMPT_GEMINI_CLI.md
SCRIPT_ORAL_QA.md
```
