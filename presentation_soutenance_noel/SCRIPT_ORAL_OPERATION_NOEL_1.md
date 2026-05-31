# Script oral lisible - Operation_Noel(1).pptx

Objectif : environ 13 a 16 minutes.

Rythme conseille :
- 35 a 45 secondes pour les slides simples.
- 50 secondes a 1 minute pour les slides techniques.
- Les slides 6 et 12 semblent etre des slides visuelles ou de transition : utilise-les pour respirer ou faire une mini-demonstration.

## Slide 1 - Introduction

Bonjour, je vais vous presenter notre projet Operation Noel, realise dans le cadre de la matiere Graphes et Open Data.

L'objectif est d'organiser les tournees de livraison du Pere Noel dans une vraie ville, pas sur une carte fictive.

Pour cela, on part de donnees ouvertes, notamment OpenStreetMap, puis on construit un graphe routier. Ensuite, on calcule les couts entre les points de livraison et on utilise un solveur pour organiser les tournees.

Le projet combine donc trois elements : les donnees ouvertes, les graphes, et l'optimisation de tournees.

## Slide 2 - Contraintes de livraison

Avant de parler d'algorithmes, il faut comprendre les contraintes du probleme.

On a un depot unique, plusieurs traineaux, une capacite limitee par traineau, un budget, et des fenetres horaires.

On a aussi une contrainte temporelle forte : une tournee ne doit pas depasser 8 heures, donc 28 800 secondes.

Enfin, certains clients peuvent ne pas etre livres si toutes les contraintes ne peuvent pas etre respectees. Dans ce cas, le solveur applique une penalite.

C'est pour cela que ce n'est pas un simple probleme de plus court chemin. C'est un VRP contraint, c'est-a-dire un probleme de tournees de vehicules avec plusieurs contraintes.

## Slide 3 - Problematique

La problematique est la suivante :

Comment organiser efficacement les tournees de livraison du Pere Noel, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?

La difficulte vient du fait qu'on n'a pas un seul objectif.

Une solution peut etre tres rapide mais trop couteuse. Une autre peut etre economique mais livrer trop peu de clients. Une autre peut reduire le CO2 mais augmenter les temps de parcours.

Le but du projet est donc de trouver un compromis entre ces criteres.

## Slide 4 - Open Data utilisees

Le projet repose sur plusieurs sources de donnees ouvertes.

OpenStreetMap fournit le reseau routier reel. C'est la base principale pour construire le graphe.

Overpass permet d'interroger certaines informations autour de la zone, comme des lieux ou des points d'interet.

Open-Meteo fournit la meteo reelle, qui peut modifier les temps de trajet.

SRTM NASA fournit les donnees d'altitude. Elles permettent d'estimer le relief et donc d'ajuster les temps sur les routes en pente.

Enfin, ADEME Impact CO2 peut fournir un facteur carbone. Si l'API n'est pas disponible, le projet utilise un fallback local.

L'idee importante est que le graphe n'est pas invente : il vient de donnees ouvertes.

## Slide 5 - Pipeline global du projet

Le pipeline commence par une adresse saisie par l'utilisateur.

Ensuite, le backend interroge les APIs et recupere les donnees necessaires. Ces donnees servent a construire un graphe routier.

A partir de ce graphe, on calcule plusieurs matrices de cout : temps, distance, CO2, risque et cout multicritere.

Ces matrices sont envoyees au solveur OR-Tools, qui calcule les tournees.

Enfin, l'application affiche un score, un debriefing et une visualisation sur carte.

Donc le principe est simple : une adresse devient une mission optimisee.

## Slide 6 - Transition ou demonstration

Cette slide peut servir de transition.

Ici, tu peux dire :

Avant de rentrer dans les calculs, il faut retenir que toute la suite repose sur une transformation importante : on passe d'une carte reelle a un graphe exploitable par des algorithmes.

Une fois que la ville est representee comme un graphe, on peut calculer des plus courts chemins, des matrices, puis des tournees.

## Slide 7 - Temps, vitesse, meteo et relief

Pour calculer les temps de trajet, on part des aretes du graphe OpenStreetMap.

Si OpenStreetMap donne une vitesse maximale, on peut l'utiliser. Sinon, le projet utilise une vitesse par type de voie.

Par exemple, une rue residentielle est estimee a 30 kilometres par heure, une route tertiaire a 50, une route secondaire a 60, le velo a 18 et la marche a 5.

La formule de base est : temps egal distance divisee par vitesse.

Ensuite, ce temps peut etre ajuste avec la meteo. Par temps clair, le facteur est 1. S'il pleut, le temps augmente. En cas de neige, brouillard ou orage, il augmente davantage.

Le relief peut aussi etre pris en compte avec SRTM : on recupere l'altitude, on calcule une pente, puis on ajuste le temps. Une montee augmente le temps, une descente peut le reduire legerement.

## Slide 8 - Des plus courts chemins aux tournees

Cette slide est le coeur de la partie graphes.

La ville est d'abord representee comme un graphe. Les noeuds sont les intersections ou les points routiers. Les aretes sont les routes. Chaque arete possede des poids : temps, distance, CO2 et risque.

Ensuite, on utilise Dijkstra pour calculer les plus courts chemins entre le depot et les clients, puis entre les clients eux-memes.

Le resultat de Dijkstra n'est pas encore une tournee. Il sert a remplir des matrices : pour chaque paire de points, on connait le cout du meilleur chemin.

Ensuite, OR-Tools utilise ces matrices pour resoudre le VRP. Il choisit quel traineau livre quels clients, dans quel ordre, en respectant les contraintes de capacite, de temps, de fenetres horaires et de penalites.

Donc Dijkstra construit les couts entre les points, et OR-Tools construit l'organisation globale des tournees.

## Slide 9 - Matrices de cout

Le projet genere plusieurs matrices.

La matrice de temps contient les temps de trajet entre les points. La matrice de distance contient les distances. La matrice CO2 estime les emissions. La matrice de risque ajoute un cout lie aux routes. Et la matrice composite combine plusieurs criteres.

Chaque case i, j correspond au cout du plus court chemin entre le point i et le point j.

Il faut bien comprendre que ces matrices sont les donnees d'entree du solveur. OR-Tools ne recalcule pas le graphe OpenStreetMap : il utilise ces couts pour prendre ses decisions.

## Slide 10 - Parametres OR-Tools et profils IA

OR-Tools est le moteur d'optimisation utilise pour resoudre le probleme de tournees.

Les parametres affiches controlent son comportement : la strategie de premiere solution, la metaheuristique locale, le temps de recherche, les penalites, la capacite des vehicules et les contraintes de temps.

Les profils IA ne sont pas une IA generative. Ce sont des politiques de parametrage du solveur.

Le profil Express privilegie le temps. Le profil Ecolo donne plus d'importance a la distance et au CO2. Le profil Prudent garde plus de marge temporelle et tolere mieux les incidents.

Donc les profils changent la facon d'arbitrer, mais le probleme de base reste le meme.

## Slide 11 - Resolution et amelioration

Le projet utilise deux strategies selon la taille de la mission.

Pour les petites et moyennes missions, on utilise le solveur classique. OR-Tools produit une premiere bonne solution avec une solution initiale et une metaheuristique.

Ensuite, on applique un post-traitement local. Il utilise ALNS puis ILS, avec des mouvements comme 3-opt, or-opt, 2-opt etoile et double-bridge.

L'objectif est d'ameliorer localement la solution d'OR-Tools, par exemple en changeant l'ordre des clients ou en reorganisant des morceaux de tournees.

Pour les grandes missions, a partir de 150 colis, on active le mode large scale. Au lieu de resoudre directement un VRP geant, on genere des tournees candidates faisables, puis on selectionne les meilleures avec CP-SAT.

Cette approche permet de garder le solveur classique quand il fonctionne bien, et d'avoir une strategie plus scalable pour les grands volumes.

## Slide 12 - Transition vers la flotte

Cette slide peut servir a introduire la question du nombre de traineaux.

Tu peux dire :

Une fois qu'on sait calculer les tournees, il reste une question importante : combien de traineaux faut-il utiliser ?

Trop peu de traineaux peut empecher de livrer tous les clients. Trop de traineaux augmente le cout de flotte. Le projet doit donc choisir automatiquement un compromis.

## Slide 13 - Selection automatique des traineaux

Ici, on choisit automatiquement le nombre de traineaux.

On commence par une heuristique, c'est-a-dire une regle simple pour eviter de tester toutes les possibilites.

D'abord, on calcule k_min : c'est le minimum de traineaux necessaire selon le poids total des colis et la capacite d'un traineau.

Ensuite, on calcule k_base, qui est une estimation liee au nombre de clients.

Puis le solveur teste plusieurs nombres de traineaux. Pour chaque essai, il calcule un score : le cout operationnel plus le cout des clients non livres.

Si on prend trop peu de traineaux, on risque de ne pas livrer assez de clients. Si on en prend trop, le cout de flotte augmente.

Le bon nombre de traineaux est donc celui qui combine couverture et rentabilite.

## Slide 14 - IA apprenante

L'IA apprenante vise a aller plus loin que les profils fixes.

L'idee est d'apprendre, a partir des missions passees, quels profils et quels parametres fonctionnent le mieux selon le contexte.

Les entrees peuvent etre le nombre de colis, la densite, la meteo, les incidents, le budget, le score obtenu et les clients non livres.

En sortie, le modele peut recommander un profil ou un parametrage OR-Tools.

Mais il faut etre precis : ce n'est pas du deep learning. C'est plutot un modele statistique de recommandation contextuelle, avec un lissage bayesien pour eviter de trop faire confiance a peu d'exemples.

Aujourd'hui, ce module existe, mais il n'est pas encore assez entraine pour remplacer les profils fixes.

## Slide 15 - Score final et benchmark

Le score final sert a evaluer une solution avec plusieurs criteres.

Le temps compte pour 45%, la couverture des colis pour 25%, le CO2 pour 20% et le budget pour 10%.

C'est important, parce qu'une solution tres rapide mais qui livre peu de clients n'est pas une bonne solution. De la meme facon, une solution qui livre tout le monde mais depasse le budget n'est pas ideale non plus.

Le benchmark compare la tournee optimisee avec une tournee naive. On mesure le temps gagne, la distance reduite, le CO2 economise et le nombre de clients livres.

Le resultat n'est donc pas seulement une route : c'est une solution evaluee avec plusieurs criteres.

## Slide 16 - Engineering du projet

Cette slide montre la partie engineering.

Le backend est construit avec FastAPI et gere la creation des missions, les donnees, les matrices, le solveur et les resultats.

Le frontend est construit avec Next.js. Il permet de configurer une mission, de lancer le calcul et de visualiser les resultats.

Pour la robustesse, le projet utilise un cache par mission. Cela evite de recalculer inutilement les memes donnees. Il y a aussi des fallbacks locaux si certaines APIs sont indisponibles.

Pour les grandes missions, le mode drive est force automatiquement, car le multimodal devient trop couteux.

Pour la performance, les matrices sont sauvegardees, certaines generations sont parallelisees, et des tests verifient le solveur, l'API et le post-traitement.

## Slide 17 - Difficultes, limites et conclusion

Les principales difficultes ont ete liees au passage a l'echelle.

Les graphes peuvent etre lourds, les APIs externes peuvent etre instables, et le passage a 1000 colis augmente fortement la taille des matrices et le temps de calcul.

Il a aussi fallu gerer le choix du nombre de traineaux et l'affichage frontend.

Les limites sont que les clients sont simules, que l'optimalite globale n'est pas garantie, qu'OpenStreetMap peut etre lent sur de grands rayons, et que l'IA apprenante n'est pas encore assez entrainee.

Pour conclure, ce projet montre comment transformer des donnees ouvertes en graphe exploitable, puis en decisions de tournees grace aux plus courts chemins et a l'optimisation combinatoire.

A partir d'une ville reelle, on passe donc d'un reseau routier brut a une organisation de livraison capable d'arbitrer entre temps, contraintes, cout, couverture et impact environnemental.

# Questions rapides possibles

## Pourquoi Dijkstra et OR-Tools ?

Dijkstra calcule les plus courts chemins dans le graphe. OR-Tools utilise ensuite les matrices de cout pour organiser les tournees globales.

## Le gain du benchmark est-il general ?

Non. Le gain depend de la mission, du rayon, du nombre de colis, des contraintes et de la baseline naive.

## Pourquoi certains clients ne sont pas livres ?

Parce que le solveur respecte les contraintes. Si tout livrer depasse les 8 heures, la capacite, les fenetres horaires ou le budget, certains clients peuvent etre abandonnes avec une penalite.

## L'IA apprenante est-elle du deep learning ?

Non. C'est un modele statistique de recommandation contextuelle. Il estime quel profil ou quels parametres devraient fonctionner selon les missions passees.
