# Slides - Soutenance Operation Noel

## Slide 1 - Titre

**Optimisation des tournees du Pere Noel avec graphes et open data**

Sous-titre :
**OpenStreetMap · Open-Meteo · SRTM NASA · ADEME · OR-Tools**

Elements visuels :
- carte de l'application
- icones graphe, cadeau, traineau, CO2

---

## Slide 2 - Problematique

**Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?**

Elements cles :
- livrer vite
- livrer un maximum de colis
- respecter les 8h et la capacite
- limiter distance, cout et CO2

---

## Slide 3 - Pipeline global du projet

**Adresse utilisateur**
-> **Open data**
-> **Graphe routier**
-> **Matrices de cout**
-> **Solveur**
-> **Score / debriefing**
-> **Visualisation**

Elements a afficher :
- schema pipeline
- dossier `cache/api_missions/<mission_id>/`

---

## Slide 4 - Donnees ouvertes utilisees

| Source | Role dans le projet |
|---|---|
| OpenStreetMap | reseau routier reel |
| Overpass | noms de lieux / POI |
| Open-Meteo | meteo reelle |
| SRTM NASA | altitude / relief |
| ADEME Impact CO2 | facteur carbone |

Message cle :
**Le graphe n'est pas fictif : il vient de donnees ouvertes.**

---

## Slide 5 - Cache d'une mission

Fichiers a montrer :
- `mission.json`
- `human_state.json`
- `core_data/livraisons_5eme.csv`
- `core_data/paris5.graphml`
- `core_data/*.npy`
- `production_output/resultats_finaux.json`

Message cle :
**Chaque mission possede ses donnees, matrices et resultats pour etre rejouee et analysee.**

---

## Slide 6 - Points de livraison

Fichier :
`core_data/livraisons_5eme.csv`

Colonnes importantes :
- `id`
- `lat`, `lon`
- `poids_colis`
- `nom_client`
- `tw_start`, `tw_end`
- `cargo_label`

Message cle :
**On transforme une zone reelle en depot + clients geolocalises.**

---

## Slide 7 - Graphe OpenStreetMap

**Ville reelle -> graphe**

Definitions :
- noeuds = intersections / points routiers
- aretes = routes
- poids = distance, temps, CO2, risque

Attributs OSM :
- `length`
- `highway`
- `maxspeed`

Formule :
**G = (V, E)**

---

## Slide 8 - Vitesse, temps et meteo

Formules :
**vitesse = maxspeed OSM ou vitesse par defaut**

**temps = distance / vitesse**

**temps final = temps x facteur meteo / speed_multiplier**

Exemples :
- Clear -> x1.0
- Rain -> x1.3
- Snow -> x2.0

---

## Slide 9 - Relief SRTM NASA

Pipeline :
**latitude / longitude**
-> **OpenTopoData SRTM90m**
-> **altitude**
-> **pente**
-> **ajustement du temps**

Formules :
**denivele = altitude_j - altitude_i**

**pente = denivele / distance**

Impact :
- montee -> temps augmente
- descente -> temps diminue legerement

---

## Slide 10 - CO2

Deux sources :
- ADEME Impact CO2 si active
- fallback local sinon

Fallback :
- voiture = 120 g/km
- velo = 8 g/km
- marche = 0 g/km

Formule :
**CO2 = distance_km x facteur_g/km**

Exemple :
**0,701 km x 120 = 84,12 g CO2**

---

## Slide 11 - Matrices de cout

Matrices :
- `live_time_matrix.npy` -> temps
- `matrix_5eme.npy` -> distance
- `co2_matrix.npy` -> CO2
- `risk_matrix.npy` -> risque
- `composite_cost_matrix.npy` -> cout multicritere

Interpretation :
**case [i, j] = cout du plus court chemin entre i et j**

Commande :
`python scripts/show_matrices.py --size 5`

---

## Slide 12 - Matrice composite

Objectif :
**combiner plusieurs criteres dans un seul cout**

Formule :
**cout = 0.55 temps + 0.20 distance + 0.15 CO2 + 0.10 risque**

Precision :
**les matrices sont normalisees avant combinaison**

---

## Slide 13 - Contraintes de la tournee du Pere Noel

Contraintes :
- depot unique
- plusieurs traineaux
- capacite limitee
- limite de 8h
- fenetres horaires
- budget
- clients non livres possibles

Message cle :
**Ce n'est pas un simple plus court chemin : c'est un VRP contraint.**

---

## Slide 14 - Limite de 8h et fenetres horaires

Dans le CSV :
- `tw_start`
- `tw_end`

Contraintes :
**arrivee_client <= tw_end**

**duree_tournee <= 28800 s**

Message cle :
**Le solveur doit produire une tournee realisable dans la nuit de livraison.**

---

## Slide 15 - Clients non livres

Pourquoi un client peut ne pas etre livre :
- capacite insuffisante
- fenetre horaire impossible
- limite de 8h
- cout trop eleve

Mecanisme :
**drop_penalty = cout de non-livraison**

Message cle :
**Le projet maximise la couverture sous contraintes, au lieu de forcer une solution impossible.**

---

## Slide 16 - Budget et cout de flotte

Parametres :
- budget
- cout par traineau
- `vehicle_fixed_cost`
- `sleigh_cost`

Arbitrage :
**plus de traineaux = meilleure couverture possible**

mais :
**plus de traineaux = cout de flotte plus eleve**

---

## Slide 17 - Selection automatique des traineaux

Calculs :
**k_min_capacity = ceil(poids_total / capacite)**

**k_base = ceil(nombre_clients / 3)**

Selection :
**tester plusieurs k**

**score = cout operationnel + cout colis non livres**

Avec :
- cout operationnel = temps + distance + cout flotte
- cout colis non livres = drop_penalty x clients non livres

---

## Slide 18 - OR-Tools

**OR-Tools = moteur d'optimisation combinatoire de Google**

Dans le projet :
- RoutingModel
- depot
- flotte
- capacite
- temps
- penalites
- fenetres horaires

Schema :
**matrices -> OR-Tools -> contraintes -> tournees**

---

## Slide 19 - Parametres OR-Tools

Parametres principaux :
- `first_solution_strategy`
- `local_search_metaheuristic`
- `solver_time_limit_s`
- `drop_penalty`
- `global_span_cost`
- `vehicle_capacity`
- `vehicle_fixed_cost`
- `time_slack_s`
- `max_route_time_s`

Message cle :
**Les profils IA sont des politiques de parametrage du solveur.**

---

## Slide 20 - Profils IA

**Express**
- priorite temps
- plus agressif
- `parallel_cheapest_insertion`
- `guided_local_search`

**Ecolo**
- priorite distance / CO2
- `savings`
- `simulated_annealing`

**Prudent**
- plus de marge
- meilleure robustesse
- `parallel_cheapest_insertion`
- `guided_local_search`

---

## Slide 21 - IA apprenante

Objectif :
**apprendre quels profils et parametres fonctionnent le mieux selon le contexte**

Entrees :
- nombre de colis
- densite
- meteo
- incidents
- budget
- score obtenu
- clients non livres

Sortie :
- profil recommande
- parametrage OR-Tools recommande

Limite :
**module present mais pas encore assez entraine pour remplacer les profils fixes**

---

## Slide 22 - Solveur classique

Utilise pour :
**petites et moyennes missions**

Pipeline :
**OR-Tools**
-> **solution initiale**
-> **metaheuristique**
-> **post-traitement**

Post-traitement :
- ALNS
- ILS
- 3-opt
- or-opt
- 2-opt*
- double-bridge

---

## Slide 23 - Solveur large scale

Active a partir de :
**150 colis**

Pipeline :
1. generer des tournees candidates
2. respecter depot, capacite, 8h
3. selectionner les meilleures avec CP-SAT
4. penaliser les colis non livres

Message cle :
**On evite de resoudre directement un VRP geant.**

---

## Slide 24 - Score final

Composition :
- 45% temps
- 20% CO2
- 10% budget
- 25% couverture colis

CO2 saved :
**CO2_saved = CO2_naif - CO2_optimise**

Message cle :
**Le score valorise rapidite, ecologie, budget et couverture.**

---

## Slide 25 - Benchmark

Comparaison :
- tournee naive
- tournee optimisee

Mesures :
- temps gagne
- distance reduite
- CO2 economise
- clients livres

Fichier :
`benchmark_results.json`

---

## Slide 26 - Modules de l'application

Modules :
- Mission
- Solveur
- Debriefing
- Versus
- Social / Messages
- Donnees / Coulisses

Pipeline applicatif :
**creation mission -> resolution -> resultats -> comparaison**

---

## Slide 27 - Mode Versus

Objectif :
**comparer deux joueurs ou deux strategies sur une meme mission**

Critères :
- temps
- clients livres
- CO2
- budget
- score final

Message cle :
**Le mode versus rend l'optimisation comparable.**

---

## Slide 28 - Resultats

Exemples a montrer :
- 200 colis -> environ 1 min
- 1000 colis -> matrice 1001 x 1001
- selection automatique des traineaux
- clients livres / non livres
- CO2 economise

Visuels :
- carte
- score
- matrices
- benchmark

---

## Slide 29 - Difficultes

Difficultes :
- graphes OSM lourds
- APIs externes instables
- passage a 1000 colis
- choix du nombre de traineaux
- clients non livres
- coherence CO2 / score / benchmark
- affichage frontend lourd

---

## Slide 30 - Solutions apportees

Solutions :
- cache par mission
- fallbacks locaux
- mode drive automatique pour grandes missions
- solveur large scale
- generation parallele de candidates
- selection economique des traineaux
- scripts de debug des matrices

---

## Slide 31 - Limites

Limites :
- clients simules
- optimalite globale non garantie
- OSM lent sur grands rayons
- CO2 parfois fallback
- IA apprenante pas encore assez entrainee
- visualisation 1000 colis encore lourde

---

## Slide 32 - Perspectives

Perspectives :
- cache OSM avance
- OSRM / GraphHopper
- vraies commandes
- meilleure priorite colis
- entrainement de l'IA apprenante
- visualisation clusterisee
- meilleure estimation economique des tournees

---

## Slide 33 - Conclusion

Resume :
**open data -> graphe reel**

**graphe -> matrices**

**matrices -> solveur**

**solveur -> tournees du Pere Noel optimisees**

Conclusion :
**Les graphes et l'open data permettent de construire une aide a la decision realiste pour organiser les tournees de livraison du Pere Noel.**
