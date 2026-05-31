# Prompt Gemini - Soutenance 20 min Graphes et Open Data

Copie-colle tout le bloc ci-dessous dans Gemini pour lui faire generer un diaporama complet. Gemini n'a pas acces au projet : toutes les informations, les visuels attendus, les preuves, le script oral et la FAQ sont donc fournis ici.

---

## PROMPT A DONNER A GEMINI

Tu es expert en creation de slides universitaires, recherche operationnelle, theorie des graphes, open data et ingenierie web. Cree une presentation de soutenance de 20 minutes en francais pour un projet appele **Operation Noel / Santa Router Optimizer**.

Contexte du projet :
- Application web de logistique urbaine gamifiee autour du Pere Noel.
- Matiere : graphes et open data.
- Objectif fonctionnel : creer une mission de livraison sur un vrai reseau routier, generer des clients, construire des matrices de cout, puis optimiser les tournees avec un solveur VRPTW.
- Stack : backend FastAPI/Python, frontend Next.js/TypeScript, cartographie Leaflet/Mapbox, solveur Google OR-Tools, graphes OSM avec OSMnx/NetworkX, stockage local en fichiers et SQLite.
- Duree de presentation : 20 minutes.
- Niveau attendu : technique mais clair pour un jury. Il faut expliquer les donnees, les transformations, les choix algorithmiques, les IA, le solveur, le site et les preuves.

Contraintes importantes :
- Ne pas inventer de fonctionnalites non citees.
- Quand tu parles de meteo, utilise **Open-Meteo**, pas OpenWeatherMap : certains anciens textes du projet mentionnent OpenWeatherMap, mais le code actuel utilise Open-Meteo.
- Precise que les profils IA ne sont pas du deep learning : ce sont d'abord des presets de strategie OR-Tools ; l'IA apprenante est une couche statistique de recommandation/tuning basee sur l'historique des missions.
- Le ton doit etre professionnel, clair, soutenance universitaire, pas marketing.
- Style visuel : sobre, technique, cartographique. Palette recommandee : fond clair ou gris tres sombre, accents bleu cartographique, vert open data/ecologie, rouge discret pour Noel. Eviter une ambiance trop enfantine.

Livrables a produire :
1. Un plan de **16 slides** pour 20 minutes.
2. Pour chaque slide : titre, duree, message principal, contenu exact a afficher, visuel a creer, notes orales du presentateur.
3. Une section "preuves dans le projet" avec les fichiers et lignes a citer.
4. Une FAQ finale avec questions probables du jury et reponses courtes.
5. Une slide annexe optionnelle avec limites et perspectives.

---

## Structure des slides attendue

### Slide 1 - Titre et probleme general (1 min)
Titre : **Operation Noel : optimiser des tournees sur graphe routier reel**

Texte a afficher :
- Livrer des colis en une nuit.
- Contraintes : temps, capacite, meteo, incidents, CO2.
- Donnees ouvertes : OpenStreetMap, Overpass, Open-Meteo, SRTM, ADEME.
- Probleme central : VRPTW, Vehicle Routing Problem with Time Windows.

Visuel :
- Fond : carte urbaine stylisee avec un depot et plusieurs points clients.
- Ajouter trois routes colorees partant du depot.
- Badge discret : "Graphes + Open Data + Recherche Operationnelle".

Notes orales :
"Je presente Operation Noel, une application de logistique urbaine. Derriere le theme ludique, le probleme est reel : organiser des tournees de livraison sous contraintes. La ville est modelisee comme un graphe oriente pondere issu d'OpenStreetMap, puis un solveur de recherche operationnelle calcule les tournees."

Preuves :
- README.md : description generale, FastAPI, Next.js, OR-Tools, OSMnx.
- backend/app/main.py lignes 120 et 435 : creation et resolution de mission.

---

### Slide 2 - Pourquoi c'est un probleme de graphes (1 min)
Titre : **La ville devient un graphe oriente pondere**

Texte a afficher :
- Noeud = intersection ou point routier OSM.
- Arc = troncon de route, souvent oriente a cause des sens uniques.
- Poids = temps, distance, CO2, risque.
- Plus court chemin local : Dijkstra / A*.
- Tournee globale : VRPTW.

Visuel :
- Schema simple : carte -> graphe avec noeuds et arcs -> matrice de cout.
- Ajouter les formules :
  - `G = (V, E)`
  - `w(u,v) = travel_time, distance, co2, risk`

Notes orales :
"Le premier passage important est la transformation de la carte en graphe. Une rue n'est pas juste une ligne : elle a une longueur, une vitesse, parfois un sens unique, donc un cout. Cette structure permet d'utiliser les algorithmes classiques de graphes."

Preuves :
- scripts/generator_engine.py lignes 680-695 : telechargement OSMnx et sauvegarde du graphe.
- scripts/generator_engine.py lignes 147-189 : annotation des arcs avec temps, CO2, risque.
- frontend/app/explore/page.tsx lignes 51-58 et 88-93 : explication pedagogique dans le site.

---

### Slide 3 - Sources open data (1 min 15)
Titre : **Le pipeline s'appuie sur des donnees ouvertes**

Texte a afficher sous forme de tableau :
- OpenStreetMap via OSMnx : reseau routier, noeuds, arcs, longueurs, sens.
- Overpass API : noms reels de commerces, amenites et POI pour les clients.
- Open-Meteo : meteo reelle, convertie en facteur de vitesse.
- OpenTopoData / SRTM 90 m : altitudes et pente.
- ADEME Impact CO2 : facteur officiel d'emission par mode quand active.

Visuel :
- Diagramme de flux :
  `Open Data -> Graphe OSM -> Points clients -> Matrices -> OR-Tools -> Tournees`

Notes orales :
"Le projet ne part pas d'une grille abstraite. Il utilise des sources ouvertes. OSM donne le reseau, Overpass enrichit les noms de points de livraison, Open-Meteo influence la vitesse, SRTM ajoute le relief et ADEME permet de recalculer le CO2 quand l'option est active."

Preuves :
- scripts/generator_engine.py lignes 201-253 : Overpass API.
- scripts/weather_engine.py lignes 33-75 : Open-Meteo et fallback simulation.
- scripts/elevation_engine.py lignes 1-15 et 58-103 : SRTM via OpenTopoData.
- scripts/generator_engine.py lignes 296-362 et 875-886 : ADEME Impact CO2.

---

### Slide 4 - Alimentation et transformation des donnees (1 min 15)
Titre : **De l'adresse utilisateur aux matrices exploitables**

Texte a afficher :
Etapes :
1. L'utilisateur choisit zone, nombre de clients, mode, options CO2/relief/meteo.
2. Le backend telecharge le graphe OSM.
3. Le depot et les clients sont projetes sur des noeuds routiers.
4. Les clients recoivent un poids, une categorie et une fenetre horaire.
5. Les matrices temps/distance/CO2/risque/composite sont calculees et stockees en `.npy`.

Visuel :
- Timeline horizontale avec 5 etapes.
- Afficher un mini-exemple de CSV :
  `id, lat, lon, poids_colis, tw_start, tw_end, cargo_code`

Notes orales :
"L'alimentation de la donnee est automatisee a la creation de mission. Les points clients sont generes sur des noeuds reels du graphe pour eviter des positions impossibles. Ensuite, on pre-calcule les matrices car OR-Tools doit acceder tres vite aux couts pendant la resolution."

Preuves :
- backend/app/services.py lignes 2121-2195 : creation mission.
- scripts/generator_engine.py lignes 742-837 : selection depot/clients et CSV.
- scripts/generator_engine.py lignes 840-965 : matrices et profil multimodal.
- core_data/livraisons_5eme.csv : exemple de donnees generees.

---

### Slide 5 - Modele de cout : temps, distance, CO2, risque (1 min 15)
Titre : **Une matrice composite pour optimiser plusieurs objectifs**

Texte a afficher :
Formules :
- `travel_time_s = length_m / speed_m_s`
- `co2_g = (length_m / 1000) * factor_g_per_km`
- `risk_score = (length_m / 1000) * risk_factor * oneway_penalty`
- `composite = 0.55*time + 0.20*distance + 0.15*co2 + 0.10*risk`

Ajouter :
- Normalisation robuste par mediane.
- Objectif configurable : temps, distance ou composite.

Visuel :
- Heatmap 4 matrices -> somme ponderee -> matrice composite.
- Mettre les poids en gros : 55%, 20%, 15%, 10%.

Notes orales :
"Le solveur peut minimiser le temps ou la distance, mais le projet va plus loin avec une matrice composite. Chaque cout est normalise pour etre comparable, puis pondere. Cela permet d'integrer l'ecologie et le risque sans casser le modele."

Preuves :
- scripts/generator_engine.py lignes 45-50 : poids par defaut.
- scripts/generator_engine.py lignes 147-189 : calcul temps, CO2, risque par arc.
- scripts/generator_engine.py lignes 542-576 : normalisation et matrice composite.
- final_scripts/solve_santa_final.py lignes 247-280 : fallback composite si besoin.

---

### Slide 6 - Dijkstra et A* : deux niveaux de cheminement (1 min 15)
Titre : **Plus courts chemins : Dijkstra pour les matrices, A* pour les routes**

Texte a afficher :
- Dijkstra source-unique : robuste pour calculer les matrices entre tous les points.
- A* : utilise une heuristique Haversine pour reconstruire les routes affichees.
- Formule A* :
  - `f(n) = g(n) + h(n)`
  - `h(n) = distance_haversine(n, destination) / 13.89`
- 13.89 m/s = 50 km/h, heuristique admissible.

Visuel :
- Comparaison en deux colonnes :
  - Dijkstra : exploration circulaire.
  - A* : exploration dirigee vers la cible.

Notes orales :
"Dijkstra reste le bon choix pour construire des matrices de cout sur des poids positifs. A* est plus adapte pour reconstruire une route ponctuelle a afficher, car il guide l'exploration vers la destination avec une heuristique qui ne surestime pas le cout."

Preuves :
- scripts/generator_engine.py lignes 420-445 : Dijkstra source-unique pour matrices.
- scripts/routing_payloads.py lignes 307-321 : heuristique Haversine.
- scripts/routing_payloads.py lignes 341-387 : candidats A*, shortest path et k-shortest paths.
- scripts/routing_payloads.py lignes 645-717 : reconstruction geometrique des routes IA.

---

### Slide 7 - Analyse du graphe et robustesse (1 min 15)
Titre : **Les carrefours centraux rendent le reseau fragile**

Texte a afficher :
- Exemple analyse Paris :
  - 124 noeuds, 210 arcs.
  - Diametre : 35.
  - Noeud critique #1 : Pont Marie, centralite betweenness environ 0.484.
  - Supprimer 1 noeud critique : perte de connectivite de 60.5%.
  - Supprimer 5 noeuds aleatoires : perte de 13.7%.
- Conclusion : les incidents doivent etre integres au solveur.

Visuel :
- Carte avec 5 points rouges pour les carrefours critiques.
- Petit bar chart : attaque ciblee vs suppression aleatoire.

Notes orales :
"L'analyse de centralite montre qu'un reseau urbain n'est pas homogene. Quelques noeuds supportent une grande part des plus courts chemins. C'est pour cela que le projet integre les incidents et la replanification."

Preuves :
- core_data/graph_analysis_soutenance.json : metadonnees et top 5.
- core_data/robustness_report.json : experience de suppression de noeuds.
- RAPPORT_GRAPHES.md : interpretation de centralite et robustesse.

---

### Slide 8 - Modele mathematique du VRPTW (1 min 15)
Titre : **Le coeur mathematique : CVRPTW / VRPTW**

Texte a afficher :
Definitions :
- Depot unique.
- Clients `i = 1..n`.
- Vehicules `k = 1..K`.
- Demande `q_i`, capacite `Q`.
- Fenetre horaire `[a_i, b_i]`.
- Cout de transition `c_ij`.

Contraintes :
- Chaque client servi au plus une fois.
- Charge par vehicule <= capacite.
- Arrivee dans les fenetres horaires.
- Retour au depot.
- Penalite si un point est impossible a servir.

Visuel :
- Schema depot + 3 tournees.
- Encadre "Probleme NP-difficile".

Notes orales :
"La difficulte vient du fait que ce n'est pas un simple plus court chemin. Il faut choisir l'ordre des clients, affecter les clients aux vehicules, respecter les capacites et les horaires. C'est un probleme combinatoire NP-difficile."

Preuves :
- final_scripts/solve_santa_final.py lignes 303-305 : RoutingIndexManager et RoutingModel.
- final_scripts/solve_santa_final.py lignes 351-380 : dimension temps et time windows.
- final_scripts/solve_santa_final.py lignes 382-388 : dimension capacite.
- final_scripts/solve_santa_final.py lignes 402-403 : penalites de non-livraison.

---

### Slide 9 - Comment OR-Tools resout la mission (1 min 30)
Titre : **OR-Tools : solution initiale puis metaheuristique**

Texte a afficher :
Pipeline solveur :
1. Charger CSV, meteo, matrices.
2. Choisir la matrice objectif : temps, distance ou composite.
3. Enregistrer les callbacks de cout.
4. Ajouter contraintes temps, capacite, penalites.
5. First solution : PATH_CHEAPEST_ARC, SAVINGS ou PARALLEL_CHEAPEST_INSERTION.
6. Amelioration : GUIDED_LOCAL_SEARCH, TABU_SEARCH ou SIMULATED_ANNEALING.
7. Sauvegarde des tournees et KPI.

Visuel :
- Diagramme "Model -> Constraints -> Initial solution -> Local search -> Tours".
- Afficher les noms OR-Tools en monospace.

Notes orales :
"OR-Tools combine une construction rapide de solution avec une recherche locale. Le projet expose plusieurs strategies via les profils IA. On ne demande pas au solveur de tout recalculer sur la carte : il travaille sur les matrices precalculees."

Preuves :
- final_scripts/solve_santa_final.py lignes 149-180 : signature du solveur.
- final_scripts/solve_santa_final.py lignes 209-246 : chargement et ajustement meteo/matrices.
- final_scripts/solve_santa_final.py lignes 405-436 : parametres de recherche et solve.
- backend/app/services.py lignes 51-164 : presets de profils IA.

---

### Slide 10 - Choix automatique de flotte et multimodalite (1 min 15)
Titre : **Le backend peut choisir le nombre de traineaux et les modes**

Texte a afficher :
- L'utilisateur donne une borne ou une proposition.
- Le backend peut ajuster `k` par recherche progressive (halving).
- Score de selection :
  `score = total_time + 0.015*distance + drop_weight*drops + fleet_weight*k*sleigh_cost`
- Modes possibles : drive, bike, walk.
- En multimodal, le backend teste des combinaisons et garde le meilleur `vehicle_modes`.

Visuel :
- Tableau de candidats `k=1,2,3,4` avec scores.
- Mini schema : vehicule 1 = drive, vehicule 2 = bike, vehicule 3 = walk.

Notes orales :
"Un choix important est de ne pas figer la flotte. Le backend peut sonder plusieurs nombres de vehicules et plusieurs mixes de modes. C'est plus realiste : parfois un vehicule supplementaire aide, parfois il coute trop cher."

Preuves :
- backend/app/services.py lignes 3388-3414 : selection k puis selection modes.
- final_scripts/solve_santa_final.py lignes 288-345 : matrices et couts par vehicule.
- final_scripts/solve_santa_final.py lignes 390-392 : cout fixe par vehicule.
- core_data/mode_matrices/*.npy et core_data/multimodal_profile.json : matrices par mode si disponibles.

---

### Slide 11 - Incidents, meteo et relief (1 min 15)
Titre : **Le cout routier varie avec le contexte**

Texte a afficher :
- Meteo : facteur multiplicatif sur les temps.
  - pluie x1.3, neige x2.0, orage x2.0 ou plus selon mapping.
- Incidents : certains segments sont penalises ou retires.
- Relief SRTM :
  - montee : `temps *= 1 + min(slope*6, 0.80)`
  - descente : `temps *= 1 + max(slope*1.5, -0.20)`
  - energie : `distance *= 1 + abs(slope)*4`

Visuel :
- Trois cartes miniatures : meteo, incident, pente.
- Courbe simple pente -> facteur temps.

Notes orales :
"Le projet ne se limite pas au graphe statique. Il modifie les couts selon le contexte : meteo, incidents, relief. Le solveur ne change pas de nature, mais les matrices qu'il optimise deviennent plus realistes."

Preuves :
- scripts/weather_engine.py lignes 12-20 et 33-75 : scenarios et Open-Meteo.
- scripts/routing_payloads.py lignes 211-253 : incidents sur les routes utilisateur.
- backend/app/services.py lignes 3518-3576 : generation d'incidents.
- scripts/elevation_engine.py lignes 30-53 et 108-146 : modele de pente.
- scripts/generator_engine.py lignes 596-636 et 887-930 : integration SRTM.

---

### Slide 12 - IA : presets, apprentissage et auto-tuning (1 min 30)
Titre : **Les IA sont des strategies de resolution, pas une boite noire**

Texte a afficher :
Trois niveaux :
1. Profils IA presets :
   - Express : rapide, objectif temps.
   - Ecolo : distance/CO2, plus conservateur.
   - Prudent, Opportuniste, Agressive, Championne.
2. Recommandation apprenante :
   - historique de missions resolues.
   - contexte : meteo, incidents, taille, budget, cout flotte, densite.
   - lissage bayesien.
3. Auto-tuner OR-Tools :
   - recommande first solution, metaheuristique, limite de temps, slack, penalites.

Formules a afficher :
- `composite_cost = time/client + 95*dist/client + 2400*drop_ratio + 1200*budget_over_ratio + 180*weather_penalty`
- `expected = (n_context*mean_context + alpha*mean_global)/(n_context + alpha)`

Visuel :
- Schema : mission context -> recommender -> profil -> tuner OR-Tools -> solveur.

Notes orales :
"J'appelle ces modes IA parce qu'ils prennent des decisions de strategie. Mais il faut etre precis : les profils sont des configurations de solveur. La partie apprenante selectionne le profil et les parametres attendus les plus pertinents selon les missions passees."

Preuves :
- backend/app/services.py lignes 51-164 : profils IA.
- backend/app/services.py lignes 1106-1136 : entrainement/chargement du modele.
- backend/app/services.py lignes 1139-1201 : cout attendu et recommandation.
- backend/app/services.py lignes 1346-1455 : auto-tuner OR-Tools.
- cache/api_missions/ai_learning_model.json : modele version 2.0, 71 echantillons.
- cache/api_missions/ortools_tuner_model.json : tuner version 1.0, 66 echantillons.

---

### Slide 13 - Post-traitement et comparaison des politiques (1 min 15)
Titre : **Pourquoi comparer plusieurs heuristiques**

Texte a afficher :
- OR-Tools donne une bonne solution, mais pas forcement optimale.
- Post-traitement possible :
  - ALNS : destroy / repair adaptatif.
  - ILS : perturbation puis recherche locale.
- Experience RO :
  - 36 runs, 6 politiques, 0 echec.
  - Meilleur cout composite moyen observe : SAVINGS + TABU, environ 851.82.
  - PATH_CHEAPEST_ARC + GLS rapide : cout moyen environ 863.01, temps de calcul stable 12 s.

Visuel :
- Diagramme ALNS : "Destroy -> Repair -> Accept/Reject -> Repeat".
- Tableau 3 lignes comparant politiques.

Notes orales :
"Le choix d'une heuristique n'est pas dogmatique. Le projet inclut un protocole d'experimentation qui compare plusieurs politiques sur les memes instances. Cela permet de justifier les choix avec des mesures."

Preuves :
- final_scripts/solve_santa_final.py lignes 487-542 : ALNS puis ILS.
- daily_reports/ro_heuristics_experiment_summary.json : 36 runs, 6 politiques.
- scripts/ro_heuristics_experiment.py : protocole experimental.

---

### Slide 14 - Le site web et l'architecture logicielle (1 min 15)
Titre : **Une application complete : creation, mission, comparaison, debrief**

Texte a afficher :
Architecture :
- Frontend : Next.js 14, TypeScript, React Query, Leaflet/Mapbox, Recharts.
- Backend : FastAPI, services Python, OR-Tools, NetworkX, OSMnx.
- API REST :
  - `POST /api/missions`
  - `POST /api/missions/{id}/solve`
  - `POST /api/missions/{id}/solve-learned`
  - `POST /api/missions/{id}/simulation/incident-replan`
  - endpoints IA learning et OR-Tools tuner.
- Donnees :
  - `cache/api_missions/{id}/`
  - matrices `.npy`
  - snapshots SQLite.

Visuel :
- Schema architecture : Frontend -> API FastAPI -> Services -> OR-Tools/OSMnx/SQLite -> fichiers.
- Ajouter captures recommandees : page solveur, carte mission, debrief.

Notes orales :
"Le projet n'est pas seulement un script d'optimisation. Le frontend permet de configurer une mission, visualiser les routes, comparer l'humain et l'IA, puis analyser les KPI. Le backend centralise la generation, la resolution et les experiences."

Preuves :
- backend/app/main.py lignes 49-57 : API FastAPI et CORS.
- backend/app/main.py lignes 120-125 : endpoint creation mission.
- backend/app/main.py lignes 435-452 : endpoints solve et solve-learned.
- backend/app/main.py lignes 465-508 : endpoints apprentissage et tuner.
- frontend/package.json : Next.js, React, Leaflet, Recharts.
- frontend/app/solver/page.tsx lignes 658-664 : page solveur.
- frontend/app/explore/page.tsx lignes 547-660 : explication VRP dans l'interface.

---

### Slide 15 - Resultats, KPI et reproductibilite (1 min 15)
Titre : **Mesurer les gains et prouver la reproductibilite**

Texte a afficher :
KPI exemples :
- Benchmark courant : gain temps 53.2%, distance 15.293 km -> 7.413 km, CO2 economise 0.95 kg.
- Benchmark IA vs glouton sur 5 missions de 20 clients : 36.7% de gain en temps, 36.1% en distance.
- Robustesse graphe : 1 noeud critique retire -> -60.5% connectivite.
- Reproductibilite : 4/4 signatures identiques, taux 1.0.

Score affiche :
- `timeScorePct = clamp(time_saved_pct * 2.5, 0, 100)`
- `co2Score = clamp((co2_saved_kg / max(1, clients*0.1)) * 100, 0, 100)`
- `baseScore = 0.45*time + 0.20*co2 + 0.10*budget + 0.25*coverage`

Visuel :
- 4 cartes KPI.
- Un petit tableau "preuve -> fichier".

Notes orales :
"J'ai voulu que la soutenance puisse s'appuyer sur des preuves. Les gains sont compares a une baseline naive ou gloutonne, les graphes sont analyses, et le pipeline de reproductibilite hash les artefacts pour verifier que deux runs donnent la meme signature."

Preuves :
- core_data/benchmark_results.json : gain temps 53.2%, CO2 0.95 kg.
- RAPPORT_PERFORMANCES_IA.md : 36.7% temps et 36.1% distance.
- daily_reports/repro_solver_pipeline_summary.json : reproductibilite 1.0.
- scripts/benchmark_engine.py lignes 16-145 : calcul benchmark.
- RAPPORT_DETAILS_SOLVER.md section score : formules detaillees.

---

### Slide 16 - Conclusion, limites et perspectives (1 min 15)
Titre : **Bilan : graphes, open data et optimisation**

Texte a afficher :
Bilan :
- Transformation d'open data en graphe exploitable.
- Optimisation VRPTW sur contraintes reelles.
- Integration meteo, relief, CO2, incidents.
- IA pragmatique : profils, recommandation, tuning.
- Interface web pour rendre le solveur comprehensible.

Limites :
- APIs externes parfois indisponibles : fallbacks necessaires.
- VRPTW NP-difficile : pas de garantie d'optimalite globale sur grosses instances.
- Les donnees OSM dependent de la qualite de contribution locale.
- L'IA apprenante depend de la diversite des missions historiques.

Perspectives :
- Donnees GTFS transports publics.
- Incidents temps reel.
- Meilleur protocole experimental multi-villes.
- Optimisation multi-objectif lexicographique stricte.

Visuel :
- "Avant / Apres" : donnees brutes -> decision optimisee.
- Mettre une phrase finale : "Un projet qui relie theorie des graphes, open data et decision operationnelle."

Notes orales :
"Ce projet montre comment passer d'une carte ouverte a une decision de tournee optimisee. Les limites sont celles d'un vrai systeme : donnees imparfaites, complexite combinatoire, APIs externes. Mais l'architecture est extensible et les preuves montrent que les choix sont mesurables."

Preuves :
- README.md : architecture et commandes.
- RAPPORT_TRAVAUX_IA_RO.md : limites IA/tuner et prochaine etape experimentale.
- tests/ : tests API, solveur, routage, IA et scoring.

---

## Visuels exacts a generer ou demander dans les slides

1. Carte stylisee avec depot + clients + routes colorees.
2. Schema carte -> graphe -> matrice.
3. Diagramme de pipeline open data.
4. Heatmap de matrices temps/distance/CO2/risque/composite.
5. Comparaison Dijkstra vs A* avec zones explorees.
6. Carte des noeuds critiques et bar chart robustesse.
7. Schema VRPTW depot + plusieurs vehicules.
8. Diagramme OR-Tools : modele, contraintes, heuristique, metaheuristique.
9. Tableau selection automatique du nombre de traineaux.
10. Schema meteo/incidents/relief qui modifient les couts.
11. Schema IA : contexte mission -> recommandation -> tuner -> solveur.
12. Diagramme ALNS destroy/repair.
13. Architecture frontend/backend.
14. Cartes KPI resultats.

Images/captures disponibles ou a faire dans le projet :
- `production_output/output_final.html` : sortie cartographique.
- `production_output/clustering_map.html` : carte de clustering si generee.
- `rapport/Presentation_Operation_Noel.pptx` : ancienne presentation.
- `frontend/app/solver/page.tsx` : page solveur a capturer en local.
- `frontend/app/explore/page.tsx` : page pedagogique graphes/Dijkstra/A*/VRP.
- `frontend/app/data/page.tsx` : page pipeline data, mais verifier la mention meteo car le code actuel utilise Open-Meteo.

---

## Preuves techniques a citer dans la soutenance

### Architecture API
- `backend/app/main.py:49` : creation FastAPI.
- `backend/app/main.py:120` : endpoint creation mission.
- `backend/app/main.py:435` : endpoint solve.
- `backend/app/main.py:445` : endpoint solve-learned.
- `backend/app/main.py:465` : endpoints entrainement/evaluation IA.

### Creation mission et pipeline data
- `backend/app/services.py:2121` : `create_mission`.
- `scripts/generator_engine.py:639` : `generate_new_zone`.
- `scripts/generator_engine.py:680` : OSMnx `graph_from_point`.
- `scripts/generator_engine.py:687` : OSMnx `graph_from_place`.
- `scripts/generator_engine.py:787` : enrichissement Overpass.
- `scripts/generator_engine.py:796` : fenetres horaires clients.
- `scripts/generator_engine.py:850` : calcul matrices multimodales.
- `scripts/generator_engine.py:939` : sauvegarde matrices `.npy`.

### Open data externes
- `scripts/generator_engine.py:201` : Overpass API.
- `scripts/weather_engine.py:33` : Open-Meteo.
- `scripts/elevation_engine.py:23` : endpoint OpenTopoData SRTM.
- `scripts/generator_engine.py:296` : ADEME Impact CO2.

### Graphes et couts
- `scripts/generator_engine.py:147` : annotation multimodale des arcs.
- `scripts/generator_engine.py:420` : Dijkstra source-unique pour matrices.
- `scripts/generator_engine.py:542` : robust scaling.
- `scripts/generator_engine.py:556` : matrice composite.
- `scripts/routing_payloads.py:307` : heuristique Haversine A*.
- `scripts/routing_payloads.py:390` : calcul des options de route.

### Solveur OR-Tools
- `final_scripts/solve_santa_final.py:149` : fonction `solve_vrp`.
- `final_scripts/solve_santa_final.py:303` : manager/model OR-Tools.
- `final_scripts/solve_santa_final.py:343` : cout par vehicule.
- `final_scripts/solve_santa_final.py:351` : dimension temps.
- `final_scripts/solve_santa_final.py:382` : dimension capacite.
- `final_scripts/solve_santa_final.py:390` : cout fixe vehicule.
- `final_scripts/solve_santa_final.py:402` : disjunction/drop penalty.
- `final_scripts/solve_santa_final.py:405` : parametres de recherche.
- `final_scripts/solve_santa_final.py:487` : post-traitement ALNS/ILS.

### IA et tuning
- `backend/app/services.py:51` : `AI_PROFILE_PRESETS`.
- `backend/app/services.py:1106` : entrainement modele IA.
- `backend/app/services.py:1178` : recommandation profil.
- `backend/app/services.py:1346` : entrainement tuner OR-Tools.
- `backend/app/services.py:1415` : recommandation tuner.
- `backend/app/services.py:3764` : `solve_mission_learned`.
- `cache/api_missions/ai_learning_model.json` : modele IA v2.0, 71 echantillons.
- `cache/api_missions/ortools_tuner_model.json` : tuner v1.0, 66 echantillons.

### Resultats et validation
- `core_data/graph_analysis_soutenance.json` : 124 noeuds, 210 arcs, robustesse.
- `core_data/benchmark_results.json` : benchmark courant.
- `RAPPORT_PERFORMANCES_IA.md` : benchmark IA vs glouton.
- `daily_reports/repro_solver_pipeline_summary.json` : reproductibilite.
- `daily_reports/ro_heuristics_experiment_summary.json` : comparaison politiques RO.
- `tests/` : tests unitaires et API.

---

## FAQ a ajouter en fin de presentation

Q1. Pourquoi OR-Tools au lieu d'un algorithme maison ?
Reponse : Le VRPTW combine affectation, ordre des clients, capacite, fenetres horaires et penalites. OR-Tools gere ces contraintes industriellement. Le travail du projet est surtout l'integration open data, les matrices, le tuning et l'explicabilite.

Q2. Est-ce que l'IA est du machine learning profond ?
Reponse : Non. Les profils sont des strategies OR-Tools parametrees. La partie apprenante est un modele statistique contextuel avec lissage bayesien qui recommande un profil et une politique OR-Tools selon l'historique.

Q3. Pourquoi utiliser Dijkstra alors qu'A* est plus rapide ?
Reponse : Dijkstra source-unique est robuste pour construire des matrices tous-vers-tous sur des poids positifs. A* est utilise pour les requetes ponctuelles et la geometrie des routes affichees, car son heuristique Haversine reduit l'exploration.

Q4. Comment les donnees sont-elles alimentees ?
Reponse : A la creation d'une mission, le backend telecharge le graphe OSM, choisit depot et clients sur des noeuds reels, enrichit les noms via Overpass, calcule les matrices, applique meteo/relief/CO2 si active, puis stocke tout dans le dossier de mission.

Q5. Que se passe-t-il si une API externe echoue ?
Reponse : Le code contient des fallbacks : noms fictifs si Overpass echoue, meteo simulee si Open-Meteo echoue, sol plat si SRTM echoue, facteur CO2 local si ADEME echoue.

Q6. Le solveur garantit-il l'optimalite ?
Reponse : Non, pas sur les grandes instances. Le VRPTW est NP-difficile. OR-Tools fournit une tres bonne solution dans un budget temps donne, amelioree par metaheuristiques, portfolio et post-traitement.

Q7. Comment le nombre de vehicules est-il choisi ?
Reponse : Le backend peut tester plusieurs valeurs de `k` avec une recherche progressive. Le score combine temps, distance, points non servis et cout fixe de flotte.

Q8. Pourquoi une matrice composite ?
Reponse : Minimiser seulement le temps peut ignorer la distance, le CO2 ou le risque. La matrice composite normalise les couts et les pondere, ce qui donne une decision plus equilibree.

Q9. Comment le CO2 est-il calcule ?
Reponse : Par une matrice CO2. Si ADEME est active, le facteur g/km vient d'Impact CO2. Sinon, le projet utilise un facteur local par mode, avec fallback explicite.

Q10. Quelles sont les limites principales ?
Reponse : Dependances aux donnees OSM et APIs, absence de garantie d'optimalite globale, qualite du modele apprenant dependante du volume et de la diversite des missions.

---

## Derniere consigne pour Gemini

Genere les slides avec un design lisible, peu charge, une idee principale par slide. Pour chaque formule, ajoute une phrase d'interpretation. Pour chaque chiffre, affiche le fichier de preuve en petit en bas de slide. Ajoute des notes orales suffisamment completes pour tenir 20 minutes sans lire les slides mot a mot.
