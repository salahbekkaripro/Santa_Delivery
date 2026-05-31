# Prompt Gemini CLI - Generation presentation soutenance

Utilise ce prompt dans Gemini CLI depuis la racine du projet.

```text
Tu es un assistant expert en presentations techniques universitaires.

Contexte :
Je dois presenter un projet de la matiere "Graphes et Open Data".
Le projet s'appelle Operation Noel.
Il s'agit d'une application web qui optimise les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes.

Problematique exacte :
"Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?"

Objectif :
Generer une presentation de soutenance en francais, style Noel moderne, technique mais claire.
La presentation doit etre structuree, visuelle, avec peu de texte par slide.
Elle doit expliquer le projet reel, les fichiers, le pipeline, les matrices, le solveur, les profils IA, le score, les limites et les difficultes.

Style visuel souhaite :
- theme Noel sobre et moderne
- couleurs : rouge profond, vert sapin, blanc neige, or discret
- pas de surcharge
- icons simples : cadeau, traineau, graphe, carte, CO2, horloge
- design professionnel, pas enfantin
- chaque slide doit avoir un titre clair
- utiliser des schemas pipeline quand c'est pertinent
- utiliser des tableaux seulement quand ils clarifient

Contraintes :
- Ne pas faire une presentation marketing.
- Faire une presentation technique de soutenance.
- Garder les textes courts sur les slides.
- Mettre les explications dans les notes orales.
- Toujours relier les parties a la problematique des tournees du Pere Noel.
- Mentionner explicitement que certaines donnees sont optionnelles : meteo reelle, relief SRTM, CO2 ADEME, incidents, multimodal.
- Mentionner que le large scale est heuristique et ne garantit pas l'optimalite globale.
- Mentionner que l'IA apprenante existe mais necessite encore de l'entrainement.

Contenu obligatoire des slides :

1. Titre
Titre : Optimisation des tournees du Pere Noel avec graphes et open data
Sous-titre : OpenStreetMap · Open-Meteo · SRTM NASA · ADEME · OR-Tools

2. Problematique
Afficher la problematique exacte.
Ajouter les enjeux : rapidite, couverture, capacite, budget, CO2.

3. Pipeline global
Adresse utilisateur -> Open data -> Graphe routier -> Matrices -> Solveur -> Score -> Visualisation.

4. Donnees ouvertes
OpenStreetMap : reseau routier reel
Overpass : noms de lieux / POI
Open-Meteo : meteo reelle
SRTM NASA : altitude / relief
ADEME Impact CO2 : facteur carbone

5. Cache d'une mission
Montrer la structure :
cache/api_missions/<mission_id>/
mission.json
human_state.json
core_data/
production_output/

6. Points de livraison
Fichier livraisons_5eme.csv.
Colonnes : id, lat, lon, poids_colis, nom_client, tw_start, tw_end, cargo_label.

7. Graphe OpenStreetMap
Ville reelle -> graphe.
Noeuds = intersections.
Aretes = routes.
Poids = temps, distance, CO2, risque.
G = (V, E).

8. Vitesse, temps et meteo
vitesse = maxspeed OSM ou vitesse par type de voie.
temps = distance / vitesse.
temps final = temps x facteur meteo / speed_multiplier.

9. Relief SRTM NASA
lat/lon -> OpenTopoData SRTM90m -> altitude -> pente -> ajustement temps.
Montee ralentit, descente accelere legerement.

10. CO2
ADEME si active, fallback local sinon.
drive = 120 g/km, bike = 8 g/km, walk = 0.
CO2 = distance_km x facteur_g/km.

11. Matrices
live_time_matrix.npy, matrix_5eme.npy, co2_matrix.npy, risk_matrix.npy, composite_cost_matrix.npy.
case [i,j] = cout entre deux points.

12. Matrice composite
cout = 0.55 temps + 0.20 distance + 0.15 CO2 + 0.10 risque.
Preciser normalisation.

13. Contraintes metier
Depot unique, plusieurs traineaux, capacite, 8h, fenetres horaires, budget, clients non livres possibles.

14. Limite 8h et fenetres horaires
tw_start / tw_end.
arrivee_client <= tw_end.
duree_tournee <= 28800s.

15. Clients non livres
drop_penalty.
Un client peut etre non livre si la solution complete est impossible ou trop couteuse.

16. Budget et cout de flotte
budget, sleigh_cost, vehicle_fixed_cost.
Plus de traineaux = meilleure couverture mais cout plus eleve.

17. Selection automatique des traineaux
k_min_capacity = ceil(poids_total / capacite)
k_base = ceil(nombre_clients / 3)
score = cout operationnel + cout colis non livres

18. OR-Tools
Moteur d'optimisation combinatoire.
Matrices -> RoutingModel -> contraintes -> tournees.

19. Parametres OR-Tools
first_solution_strategy, local_search_metaheuristic, solver_time_limit_s, drop_penalty, global_span_cost, vehicle_capacity, vehicle_fixed_cost, time_slack_s, max_route_time_s.

20. Profils IA
Express : temps, parallel_cheapest_insertion, guided_local_search.
Ecolo : distance / CO2, savings, simulated_annealing.
Prudent : marge / robustesse, parallel_cheapest_insertion, guided_local_search.

21. IA apprenante
Objectif : apprendre les meilleurs profils/parametres selon contexte.
Entrees : colis, densite, meteo, incidents, budget, score, dropped.
Limite : pas encore assez entrainee.

22. Solveur classique
Petites/moyennes missions.
OR-Tools -> solution initiale -> metaheuristique -> ALNS/ILS.

23. Solveur large scale
A partir de 150 colis.
Generation de tournees candidates.
Selection CP-SAT.
Penalites de non-livraison.

24. Score final
45% temps, 20% CO2, 10% budget, 25% couverture.
CO2_saved = CO2_naif - CO2_optimise.

25. Benchmark
Naif vs optimise.
Temps gagne, distance, CO2, clients livres.

26. Modules application
Mission, Solveur, Debriefing, Versus, Social/Messages, Donnees/Coulisses.

27. Mode Versus
Comparer deux joueurs ou deux strategies sur une meme mission.
Critères : temps, couverture, CO2, budget, score.

28. Resultats
Montrer exemples : 200 colis environ 1 min, 1000 colis matrice 1001x1001, selection des traineaux, CO2 economise.

29. Difficultes
OSM lourd, APIs instables, 1000 colis, choix des traineaux, clients non livres, coherence score/CO2/benchmark, frontend lourd.

30. Solutions apportees
Cache mission, fallbacks, mode drive sur grosses missions, large scale, candidates paralleles, selection economique des traineaux, scripts de debug.

31. Limites
Clients simules, optimalite non garantie, OSM lent grand rayon, CO2 fallback, IA apprenante pas assez entrainee, affichage 1000 colis lourd.

32. Perspectives
Cache OSM, OSRM/GraphHopper, vraies commandes, entrainement IA apprenante, priorites colis, visualisation clusterisee.

33. Conclusion
Open data -> graphe reel -> matrices -> solveur -> tournees du Pere Noel optimisees.

Sortie attendue :
Genere un fichier de presentation ou un plan tres detaille slide par slide.
Pour chaque slide, donne :
- titre
- texte exact a mettre sur la slide
- visuel conseille
- notes orales courtes

Important :
Ne surcharge pas les slides. Mets les details dans les notes orales.
```

Commande conseillee :

```bash
cd /home/bekkari/Documents/Graphes/Noel
gemini < presentation_soutenance_noel/PROMPT_GEMINI_CLI.md
```
