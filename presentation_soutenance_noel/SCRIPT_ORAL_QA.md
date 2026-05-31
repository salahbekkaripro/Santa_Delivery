# Script oral + Questions/Reponses - Operation Noel

## Introduction

Bonjour, je vais vous presenter Operation Noel, un projet de graphes et open data dont l'objectif est d'optimiser des tournees de livraison du Pere Noel.

La problematique est la suivante :

**Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?**

L'idee centrale du projet est de partir d'une ville reelle, de la transformer en graphe routier, puis d'utiliser ce graphe pour calculer des tournees optimisees sous contraintes.

## Pipeline global

Le pipeline commence par une adresse choisie par l'utilisateur. A partir de cette adresse, le projet recupere des donnees ouvertes, notamment OpenStreetMap pour le reseau routier, Open-Meteo pour la meteo, SRTM NASA pour le relief, et ADEME pour le CO2 quand l'option est activee.

Ces donnees permettent de generer une mission. Chaque mission est stockee dans un dossier de cache avec ses fichiers propres : le CSV des livraisons, le graphe OSM, les matrices de cout, les resultats du solveur et le benchmark.

Ensuite, le solveur utilise ces matrices pour produire les tournees du Pere Noel.

## Donnees ouvertes

Le projet utilise plusieurs sources open data.

OpenStreetMap fournit le reseau routier reel. Les routes deviennent les aretes du graphe et les intersections deviennent les noeuds.

Overpass est utilise pour enrichir les points avec des noms de lieux ou des points d'interet. Ce n'est pas critique : si Overpass est indisponible, le projet utilise des noms generes.

Open-Meteo donne la meteo reelle. La meteo influence les temps de trajet : pluie, neige, brouillard ou orage augmentent les durees.

SRTM NASA, via OpenTopoData, donne les altitudes a partir des latitudes et longitudes. Cela permet d'estimer l'effet du relief.

ADEME Impact CO2 donne un facteur carbone officiel quand l'option est activee. Sinon, le projet utilise un fallback local.

## Cache mission

Chaque mission est stockee dans `cache/api_missions/<mission_id>/`.

On y retrouve `mission.json`, qui decrit la mission, `human_state.json`, qui garde l'etat de l'utilisateur, un dossier `core_data`, qui contient les donnees et matrices, et un dossier `production_output`, qui contient les resultats finaux.

Ce cache est important parce qu'il permet de rejouer, verifier et expliquer les resultats. Pour une soutenance, c'est aussi une preuve que le projet ne fonctionne pas uniquement en memoire.

## Points de livraison

Les points de livraison sont stockes dans `livraisons_5eme.csv`.

Chaque ligne represente soit le depot, soit un client. On y trouve l'identifiant, la latitude, la longitude, le poids du colis, le nom du client et les fenetres horaires.

Les colonnes `tw_start` et `tw_end` sont importantes car elles permettent de representer des contraintes temporelles. Par exemple, certains clients doivent etre livres dans une partie precise de la nuit.

## Graphe OpenStreetMap

La ville est modelisee comme un graphe.

Les noeuds correspondent aux intersections ou points du reseau routier. Les aretes correspondent aux segments de route. Chaque arete possede une longueur, un type de voie, parfois une vitesse maximale, et des couts calcules par le projet.

On ne travaille donc pas sur une carte abstraite. On travaille sur un vrai reseau routier, extrait d'OpenStreetMap.

## Vitesse, temps et meteo

Pour calculer le temps d'un segment, le projet recupere d'abord sa distance.

Ensuite, il cherche une vitesse. Si OpenStreetMap fournit un `maxspeed`, le projet l'utilise. Sinon, il applique une vitesse par defaut selon le type de route : par exemple 30 km/h pour une rue residentielle, 50 km/h pour une route tertiaire, 60 km/h pour une route secondaire.

La formule est :

**temps = distance / vitesse**

Ensuite, ce temps peut etre ajuste par la meteo :

**temps final = temps x facteur meteo / speed_multiplier**

Par exemple, une meteo claire vaut x1.0, la pluie vaut x1.3, la neige ou le brouillard peuvent aller jusqu'a x2.0.

## Relief SRTM NASA

Le relief est optionnel.

Quand il est active, le projet envoie les coordonnees latitude/longitude des points a OpenTopoData, qui fournit des altitudes issues de SRTM NASA.

Ensuite, pour chaque paire de points, le projet estime un denivele :

**denivele = altitude_arrivee - altitude_depart**

Puis une pente :

**pente = denivele / distance**

Si la pente est positive, le temps augmente. Si la pente est negative, le temps diminue legerement, mais avec une limite pour rester realiste.

## CO2

Le CO2 est calcule a partir de la distance.

Si ADEME Impact CO2 est active, le projet recupere un facteur officiel en grammes par kilometre. Sinon, il utilise un fallback local : 120 g/km pour la voiture, 8 g/km pour le velo, 0 g/km pour la marche.

La formule est :

**CO2 = distance_km x facteur_g/km**

Par exemple, si la distance est 0,701 km en voiture :

**0,701 x 120 = 84,12 g de CO2**

C'est exactement ce que l'on retrouve dans la matrice CO2.

## Matrices

Le graphe routier est ensuite transforme en matrices.

Chaque matrice est de taille `n x n`, ou `n` correspond au depot plus le nombre de clients. Pour 1000 colis, on obtient donc une matrice `1001 x 1001`.

La case `[i, j]` represente le cout pour aller du point `i` au point `j`.

Les principales matrices sont la matrice temps, la matrice distance, la matrice CO2, la matrice risque et la matrice composite.

La matrice composite combine les criteres avec les poids :

**55% temps, 20% distance, 15% CO2, 10% risque**

Avant d'additionner, les matrices sont normalisees pour etre comparables.

## Contraintes metier

Le probleme n'est pas seulement de trouver un plus court chemin.

On a un depot unique, plusieurs traineaux, une capacite limitee par traineau, une limite de 8h, des fenetres horaires, un budget et la possibilite que certains clients ne soient pas livres si la mission complete est impossible.

C'est donc un probleme de type VRP : Vehicle Routing Problem.

## Limite de 8h et fenetres horaires

La limite de 8h correspond a une nuit de livraison.

Dans le code, cela correspond a 28800 secondes.

Chaque tournee doit respecter cette limite. De plus, certains clients ont des fenetres horaires : le solveur doit arriver avant `tw_end`, et parfois attendre si le client n'est pas encore disponible.

Cela rend le probleme plus realiste qu'une simple tournee sans contrainte.

## Clients non livres

Dans certains cas, livrer tout le monde est impossible.

Par exemple, il peut manquer de capacite, les distances peuvent etre trop longues, ou les fenetres horaires peuvent etre incompatibles avec les 8h.

Le projet gere cela avec une penalite de non-livraison appelee `drop_penalty`.

Le solveur cherche donc un compromis : livrer le plus possible, mais sans produire une solution irrealisable.

## Budget et cout de flotte

Ajouter un traineau peut ameliorer la couverture et reduire la duree des tournees, mais cela coute plus cher.

Le projet prend en compte le cout par traineau, le budget et un cout fixe de vehicule.

C'est important car le meilleur choix n'est pas toujours d'utiliser un maximum de traineaux. Le but est de trouver une tournee efficace economiquement.

## Selection automatique des traineaux

Le nombre de traineaux est choisi automatiquement.

D'abord, le projet calcule un minimum theorique par capacite :

**k_min_capacity = ceil(poids_total / capacite)**

Ensuite, il utilise aussi une base :

**k_base = ceil(nombre_clients / 3)**

Puis il teste plusieurs valeurs de `k` et choisit celle qui minimise un score economique :

**score = cout operationnel + cout des colis non livres**

Le cout operationnel inclut le temps, la distance et le cout de flotte. Le cout des colis non livres depend de `drop_penalty`.

## OR-Tools

OR-Tools est le moteur d'optimisation utilise dans le projet.

Il recoit les matrices de cout et construit un modele de routage avec un depot, plusieurs vehicules, des contraintes de capacite, de temps, de penalites et de fenetres horaires.

OR-Tools ne travaille pas directement sur la carte. Il travaille sur les matrices qui viennent du graphe.

## Parametres OR-Tools

Le comportement d'OR-Tools depend de plusieurs parametres.

`first_solution_strategy` determine comment construire une premiere solution.

`local_search_metaheuristic` determine comment ameliorer cette solution.

`solver_time_limit_s` limite le temps de recherche.

`drop_penalty` represente le cout d'un client non livre.

`vehicle_capacity`, `vehicle_fixed_cost`, `time_slack_s` et `max_route_time_s` representent les contraintes metier.

## Profils IA

Le projet contient trois profils IA principaux.

Express privilegie la vitesse. Il utilise une strategie d'insertion rapide et Guided Local Search.

Ecolo privilegie la distance et donc indirectement le CO2. Il utilise une strategie Savings et Simulated Annealing.

Prudent garde plus de marge temporelle. Il est plus robuste face aux incidents et aux contraintes.

Ces profils ne sont pas des IA generatives. Ce sont des politiques de parametrage du solveur.

## IA apprenante

Le projet contient aussi une IA apprenante.

Son objectif est d'apprendre, a partir des missions resolues, quel profil et quels parametres fonctionnent le mieux selon le contexte.

Elle peut utiliser des informations comme le nombre de colis, la densite, la meteo, les incidents, le budget, le score obtenu ou les clients non livres.

Cependant, elle necessite encore plus d'entrainement. Elle existe dans l'architecture, mais elle n'est pas encore assez testee pour remplacer les profils fixes.

## Solveur classique

Pour les petites et moyennes missions, le projet utilise OR-Tools directement.

Le solveur construit une solution initiale, puis l'ameliore avec une metaheuristique.

Ensuite, le projet peut appliquer un post-traitement local : ALNS puis ILS, avec des mouvements comme 3-opt, or-opt, 2-opt* ou double-bridge.

L'objectif est de partir d'une bonne solution OR-Tools et de l'ameliorer localement.

## Solveur large scale

Pour les grandes missions, a partir de 150 colis, le projet utilise un mode large scale.

Le principe est de generer de nombreuses tournees candidates. Chaque tournee candidate part du depot, revient au depot et respecte la capacite et la limite de 8h.

Ensuite, CP-SAT selectionne la meilleure combinaison de tournees.

Cette approche permet de gerer de tres grandes instances sans resoudre directement un VRP geant.

## Score final

Le score final est compose de plusieurs dimensions :

45% pour le temps, 20% pour le CO2, 10% pour le budget et 25% pour la couverture des colis.

Cela permet de ne pas valoriser uniquement la vitesse. Une solution rapide mais qui livre peu de clients doit etre penalisee.

Le CO2 economise est calcule par comparaison entre la tournee naive et la tournee optimisee.

## Benchmark

Le benchmark compare une tournee naive et la solution optimisee.

La tournee naive livre les clients dans un ordre simple, sans optimisation avancee.

La solution optimisee est celle produite par le solveur.

On compare ensuite le temps, la distance, le CO2 et les clients livres.

## Modules de l'application

L'application est organisee en plusieurs modules.

Le module Mission cree les donnees. Le module Solveur optimise les tournees. Le module Debriefing explique les resultats. Le mode Versus permet de comparer deux joueurs ou deux strategies. Les modules Social et Messages gerent les interactions. Enfin, les pages Donnees et Coulisses permettent de montrer les graphes, matrices et choix algorithmiques.

## Mode Versus

Le mode Versus permet de comparer deux joueurs ou deux strategies sur une meme mission.

Cela transforme l'optimisation en experience comparative.

Les criteres compares sont le temps, les clients livres, le CO2, le budget et le score final.

## Resultats

Sur une mission de 200 colis, le projet peut produire une solution en environ une minute avec un rayon raisonnable.

Sur 1000 colis, on obtient une matrice 1001 x 1001 et le mode large scale est active.

Le projet montre donc qu'il peut passer d'une mission moyenne a une mission beaucoup plus grande, avec une strategie adaptee.

## Difficultes

Les difficultes principales ont ete les graphes OSM lourds, les APIs externes parfois instables, le passage a 1000 colis, le choix du nombre de traineaux, la gestion des clients non livres, la coherence entre CO2, score et benchmark, et l'affichage frontend.

Ces difficultes ont oblige a mettre en place des fallbacks, du cache, un mode large scale et des outils de debug.

## Limites

Le projet reste un prototype avance.

Les clients sont simules. L'optimalite globale n'est pas garantie sur les grandes instances. OSM peut etre lent sur de grands rayons. Le CO2 peut utiliser un fallback si ADEME n'est pas active. L'IA apprenante n'est pas encore assez entrainee.

## Conclusion

Pour conclure, le projet montre que les graphes et l'open data permettent de construire un systeme realiste d'aide a la decision pour organiser les tournees du Pere Noel.

On part d'une ville reelle, on construit un graphe, on calcule des matrices, puis on optimise les tournees sous contraintes.

Le projet repond donc a la problematique en montrant comment transformer des donnees ouvertes en decisions logistiques exploitables.

# Questions / Reponses

## Q1. Pourquoi utiliser un graphe ?

Parce qu'un reseau routier est naturellement un graphe : les intersections sont des noeuds et les routes sont des aretes. Cela permet d'utiliser des algorithmes de plus court chemin et de calculer des matrices de cout.

## Q2. Pourquoi OpenStreetMap ?

OpenStreetMap fournit un reseau routier reel, ouvert et exploitable. Cela permet de travailler sur une ville reelle, pas sur une grille artificielle.

## Q3. Comment est calcule le temps ?

Le temps est calcule par distance divisee par vitesse. La vitesse vient de `maxspeed` dans OSM si disponible, sinon d'une vitesse par defaut selon le type de voie. Ensuite, le temps est ajuste par la meteo et eventuellement par le relief.

## Q4. Comment est calcule le CO2 ?

Le CO2 est calcule par distance en kilometres multipliee par un facteur d'emission en g/km. Si ADEME est active, le facteur vient de l'API Impact CO2. Sinon, le projet utilise un fallback local.

## Q5. Pourquoi certains clients peuvent ne pas etre livres ?

Parce que toutes les contraintes peuvent rendre la livraison complete impossible : capacite, limite de 8h, fenetres horaires ou cout trop eleve. Le projet utilise une penalite de non-livraison pour trouver le meilleur compromis.

## Q6. Est-ce que le solveur garantit l'optimum ?

Pas sur les grandes instances. Le VRP est un probleme NP-difficile. OR-Tools et le mode large scale cherchent de tres bonnes solutions dans un temps raisonnable, mais ne garantissent pas toujours l'optimum global.

## Q7. Pourquoi avoir cree un mode large scale ?

Parce qu'un VRP direct avec 1000 colis devient tres lourd. Le mode large scale genere des tournees candidates faisables, puis selectionne la meilleure combinaison avec CP-SAT.

## Q8. Comment est choisi le nombre de traineaux ?

Le projet calcule un minimum par capacite, puis teste plusieurs nombres de traineaux. Il choisit selon un score economique combinant temps, distance, cout de flotte et cout des colis non livres.

## Q9. Pourquoi ne pas toujours prendre beaucoup de traineaux ?

Parce que plus de traineaux augmente le cout de flotte. Le but est de livrer suffisamment de colis tout en gardant un cout raisonnable.

## Q10. A quoi servent les profils IA ?

Ils representent differentes politiques d'optimisation. Express favorise la vitesse, Ecolo favorise distance et CO2, Prudent garde plus de marge face aux contraintes.

## Q11. Est-ce une vraie IA ?

Les profils fixes sont surtout des politiques de parametrage du solveur. Il existe aussi une IA apprenante, mais elle necessite encore plus de donnees d'entrainement pour etre fiable.

## Q12. Pourquoi utiliser OR-Tools ?

OR-Tools est une bibliotheque mature pour les problemes de routage. Elle gere les capacites, les fenetres horaires, les penalites et les heuristiques.

## Q13. Quel est le role de Dijkstra ?

Dijkstra calcule les plus courts chemins sur le graphe entre le depot et les clients. Ces resultats remplissent les matrices temps, distance, CO2 et risque.

## Q14. Pourquoi la matrice composite est normalisee ?

Parce que les criteres n'ont pas la meme unite : secondes, metres, grammes de CO2, score de risque. La normalisation permet de les combiner proprement.

## Q15. Que fait SRTM NASA ?

SRTM fournit les altitudes a partir de la latitude et longitude. Le projet utilise ces altitudes pour estimer une pente et ajuster les temps de trajet.

## Q16. Que se passe-t-il si une API externe echoue ?

Le projet a des fallbacks : noms generes si Overpass echoue, meteo simulee si Open-Meteo echoue, sol plat si SRTM echoue, facteur CO2 local si ADEME echoue.

## Q17. Pourquoi OSM peut etre lent ?

Parce que les grands rayons generent des graphes routiers tres volumineux. Plus le rayon est grand, plus le nombre de routes et d'intersections augmente.

## Q18. Pourquoi passer en mode drive pour les grandes missions ?

Parce que le multimodal telecharge et traite plusieurs graphes : voiture, velo, marche. Sur de grosses missions, cela multiplie le cout. Le mode drive est plus stable pour les tests large scale.

## Q19. Comment est calcule le score final ?

Il combine 45% temps, 20% CO2, 10% budget et 25% couverture. Cela evite de recompenser une solution rapide mais qui livre peu de clients.

## Q20. Quelle est la principale limite du projet ?

La principale limite est que c'est un prototype avance : les clients sont simules et l'optimalite globale n'est pas garantie sur les grandes instances.

## Q21. Quelle serait la meilleure amelioration ?

Utiliser OSRM ou GraphHopper pour accelerer les matrices, ajouter un cache OSM plus avance, entrainer l'IA apprenante et ameliorer la visualisation des grandes missions.

## Q22. En quoi le projet repond a la problematique ?

Il transforme des donnees ouvertes en graphe, transforme le graphe en matrices de cout, puis utilise ces matrices pour optimiser les tournees du Pere Noel sous contraintes de temps, capacite, budget, couverture et CO2.
