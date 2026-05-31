# Script oral - Operation_Noel.pptx

Objectif : environ 12 a 16 minutes.

Rythme conseille :
- Slides courtes : 30 a 40 secondes.
- Slides techniques : 50 secondes a 1 minute.
- Ne lis pas les slides mot pour mot : explique le sens.

## Slide 1 - Optimisation des tournees du Pere Noel

Bonjour, je vais vous presenter notre projet Operation Noel, realise dans le cadre de la matiere Graphes et Open Data.

L'objectif est d'organiser les tournees de livraison du Pere Noel dans une vraie ville, a partir de donnees ouvertes.

On part d'une adresse, on construit un graphe routier reel avec OpenStreetMap, puis on calcule des tournees optimisees en tenant compte du temps, des colis, du budget, de la capacite des traineaux et de l'impact CO2.

Le projet combine donc trois idees : les donnees ouvertes, les graphes, et l'optimisation de tournees.

## Slide 2 - Contraintes de livraison

Avant meme de parler d'algorithme, il faut comprendre que le probleme est contraint.

On a un depot unique, plusieurs traineaux, une capacite limitee par traineau, des fenetres horaires, un budget, et une limite de 8 heures, donc 28 800 secondes.

Il y a aussi une contrainte importante : tous les clients ne sont pas forcement livrables. Si une livraison devient impossible a cause du temps, de la capacite ou du cout, le solveur peut laisser certains clients non livres, avec une penalite.

C'est pour cela qu'on ne resout pas un simple plus court chemin. On resout un VRP contraint, c'est-a-dire un probleme de tournees de vehicules avec contraintes.

## Slide 3 - Problematique

La problematique du projet est :

Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?

La difficulte, c'est qu'on ne cherche pas un seul optimum simple.

Une solution peut etre rapide mais trop chere. Une autre peut etre peu couteuse mais livrer trop peu de colis. Une autre peut reduire le CO2 mais augmenter les temps.

Le projet doit donc trouver un compromis entre plusieurs objectifs.

## Slide 4 - Modules de l'application

Le projet n'est pas seulement un script d'optimisation. C'est une application complete.

Le module Mission sert a creer une mission a partir d'une adresse, d'un rayon et d'un nombre de colis.

Le module Solveur calcule les tournees. Le debriefing explique les resultats. Le mode Versus permet de comparer deux strategies ou deux joueurs sur la meme mission.

Il y a aussi les parties Social, Messages, Donnees et Coulisses, qui permettent de naviguer dans l'application et de montrer ce qui est genere derriere.

Le pipeline applicatif est donc : creation de mission, resolution, resultats, puis comparaison.

## Slide 5 - Open Data utilisees

Le projet repose sur plusieurs sources de donnees ouvertes.

La plus importante est OpenStreetMap, qui donne le reseau routier reel. C'est ce qui permet de construire le graphe de la ville.

Overpass permet de recuperer des informations autour de la zone, comme des lieux ou des points d'interet.

Open-Meteo fournit la meteo reelle. Elle peut influencer les temps de trajet.

SRTM NASA fournit des donnees d'altitude. Cela permet d'estimer le relief et donc d'ajuster les temps sur les routes en pente.

Enfin, ADEME Impact CO2 peut donner un facteur carbone. Si ce service n'est pas disponible, le projet utilise un fallback local.

L'idee importante ici, c'est que la carte n'est pas fictive : elle vient de donnees ouvertes.

## Slide 6 - Pipeline global du projet

Voici le pipeline global.

On commence avec une adresse utilisateur. A partir de cette adresse, on recupere des donnees ouvertes. Ces donnees permettent de construire un graphe routier.

Ensuite, on transforme ce graphe en matrices de cout : temps, distance, CO2, risque et cout multicritere.

Ces matrices sont donnees au solveur OR-Tools, qui calcule les tournees. Puis l'application produit un score, un debriefing et une visualisation sur carte.

Donc la logique du projet est : une adresse devient une mission optimisee.

## Slide 7 - Temps, vitesse, meteo et relief

Pour calculer les temps de trajet, on part des aretes du graphe OpenStreetMap.

Si OSM donne une vitesse maximale, on l'utilise. Sinon, on applique une vitesse par type de voie. Par exemple, une rue residentielle est estimee a 30 km/h, une route tertiaire a 50 km/h, une route secondaire a 60 km/h, le velo a 18 km/h et la marche a 5 km/h.

Le temps de base est calcule avec la formule : temps egal distance divisee par vitesse.

Ensuite, ce temps peut etre ajuste avec la meteo. Par temps clair, on garde un facteur 1. S'il pleut, on augmente le temps. En cas de neige, brouillard ou orage, on augmente encore plus.

Le relief est aussi optionnel. Avec les latitudes et longitudes, on recupere une altitude via SRTM, puis on estime une pente. Une montee augmente le temps, une descente peut le reduire legerement.

## Slide 8 - Des plus courts chemins aux tournees

Cette slide est le coeur de la partie graphes.

OpenStreetMap est transforme en graphe. Les noeuds representent les intersections ou les points routiers. Les aretes representent les routes. Chaque arete a des poids : temps, distance, CO2 et risque.

Ensuite, on utilise des algorithmes de plus courts chemins, notamment Dijkstra via NetworkX, pour calculer les meilleurs trajets entre le depot et les clients, puis entre les clients eux-memes.

Le resultat, ce n'est pas encore une tournee. Le resultat, ce sont des matrices : pour chaque paire de points, on connait le cout du meilleur chemin.

OR-Tools utilise ensuite ces matrices pour resoudre le VRP : il choisit quel traineau livre quels clients, et dans quel ordre, en respectant les contraintes.

Donc Dijkstra sert a passer du graphe routier aux matrices, et OR-Tools sert a passer des matrices aux tournees.

## Slide 9 - Matrices de cout

Le projet genere plusieurs matrices.

La matrice de temps contient les temps de trajet entre chaque paire de points. La matrice de distance contient les distances. La matrice CO2 estime les emissions. La matrice de risque ajoute un cout lie au type de route. Et la matrice composite combine plusieurs criteres.

Chaque case i, j correspond au cout du plus court chemin entre le point i et le point j.

Pour le CO2, le projet peut utiliser ADEME Impact CO2. Sinon, il applique un fallback local : par exemple 120 grammes par kilometre pour la voiture, 8 grammes par kilometre pour le velo et 0 pour la marche.

La commande affichee permet de montrer directement un extrait des matrices dans le terminal.

## Slide 10 - Selection automatique des traineaux

Ici, on choisit automatiquement le nombre de traineaux.

On commence avec une heuristique, c'est-a-dire une regle simple pour eviter de tester toutes les possibilites.

D'abord, on calcule k_min, le minimum de traineaux necessaire avec le poids total des colis et la capacite d'un traineau.

Ensuite, on calcule k_base, une estimation liee au nombre de clients.

Apres cela, le solveur teste plusieurs nombres de traineaux. Pour chaque essai, il calcule un score : le cout operationnel plus une penalite pour les clients non livres.

Donc si on prend trop peu de traineaux, on risque de ne pas livrer assez de colis. Mais si on en prend trop, le cout de flotte augmente.

Le but est de trouver le meilleur compromis entre couverture des colis et rentabilite.

## Slide 11 - Parametres OR-Tools et profils IA

OR-Tools est le moteur qui resout le probleme de tournees.

Les parametres affiches permettent de controler son comportement : la strategie de solution initiale, la metaheuristique locale, le temps de recherche, les penalites, la capacite des vehicules et la limite de temps.

Les profils IA ne sont pas une IA generative. Ce sont des politiques de parametrage du solveur.

Le profil Express privilegie le temps et cherche rapidement une solution.

Le profil Ecolo privilegie davantage la distance et le CO2.

Le profil Prudent garde plus de marge temporelle et resiste mieux aux incidents.

Donc les profils changent la maniere d'arbitrer, mais le probleme de base reste le meme.

## Slide 12 - IA apprenante

L'idee de l'IA apprenante est d'aller plus loin que les profils fixes.

Elle pourrait apprendre quels parametres fonctionnent le mieux selon le contexte : nombre de colis, densite de la zone, meteo, incidents, budget, score obtenu ou clients non livres.

En sortie, elle pourrait recommander un profil ou directement un parametrage OR-Tools.

Mais aujourd'hui, ce module n'est pas encore assez entraine pour remplacer les profils fixes. Il est present comme perspective d'evolution, mais le solveur principal repose sur les profils definis et sur OR-Tools.

## Slide 13 - Resolution et amelioration

Le projet utilise deux strategies selon la taille de la mission.

Pour les petites et moyennes missions, on utilise le solveur classique. OR-Tools produit une premiere bonne solution avec une solution initiale et une metaheuristique.

Ensuite, on applique un post-traitement local : ALNS puis ILS. Ces methodes essaient d'ameliorer les tournees avec des mouvements comme 3-opt, or-opt, 2-opt etoile ou double-bridge.

L'idee est de repartir d'une bonne solution, puis de modifier localement l'ordre des clients ou des morceaux de tournees pour reduire le cout.

Pour les grandes missions, a partir de 150 colis, on active le mode large scale. Au lieu de resoudre directement un VRP geant, on genere des tournees candidates faisables, puis on selectionne les meilleures avec CP-SAT.

Cette strategie permet de garder l'ancien solveur pour les cas ou il fonctionne bien, et d'avoir une approche plus scalable pour les gros volumes.

## Slide 14 - Score final et benchmark

Le score final permet d'evaluer la qualite d'une solution.

Il est compose de plusieurs parties : le temps compte pour 45%, la couverture des colis pour 25%, le CO2 pour 20% et le budget pour 10%.

C'est important, parce qu'une solution tres rapide mais qui livre peu de clients ne serait pas une bonne solution. De la meme maniere, une solution qui livre tout le monde mais explose le budget n'est pas ideale non plus.

Le benchmark compare une tournee naive avec une tournee optimisee. On regarde le temps gagne, la distance reduite, le CO2 economise et le nombre de clients livres.

Donc le resultat n'est pas seulement une route : c'est une solution evaluee avec plusieurs criteres.

## Slide 15 - Engineering du projet

Cette slide montre la partie engineering du projet.

L'architecture repose sur un backend FastAPI et un frontend Next.js.

Le backend gere la creation des missions, le calcul des graphes, les matrices, le solveur et les resultats. Le frontend permet de configurer une mission, de lancer le calcul et de visualiser les tournees.

Pour rendre le projet plus robuste, on utilise un cache par mission. Cela evite de recalculer inutilement les memes donnees. Il y a aussi des fallbacks locaux si certaines APIs sont indisponibles.

Pour les grandes missions, le projet force automatiquement le mode drive, car le multimodal devient trop couteux. Il y a aussi une limite entre le solveur classique et le solveur large scale.

Cote performance, les matrices sont sauvegardees, la generation des candidates peut etre parallelisee, et des tests verifient le solveur, l'API et le post-traitement.

## Slide 16 - Difficultes, limites et conclusion

Les principales difficultes ont ete liees au passage a l'echelle.

Les graphes OpenStreetMap peuvent etre lourds, les APIs externes peuvent etre instables, et le passage a 1000 colis augmente fortement la taille des matrices et le temps de calcul.

Il a aussi fallu gerer le choix du nombre de traineaux, les clients non livres et l'affichage frontend.

Les limites sont aussi importantes : les clients sont simules, l'optimalite globale n'est pas garantie, OSM peut etre lent sur les grands rayons, et l'IA apprenante n'est pas encore assez entrainee.

Pour conclure, le projet montre que les graphes et l'open data permettent de construire une aide a la decision realiste pour organiser les tournees de livraison du Pere Noel.

On part de donnees ouvertes, on construit un graphe, on calcule des plus courts chemins, puis on resout un probleme de tournees contraint avec un solveur d'optimisation.

# Reponses courtes aux questions probables

## Pourquoi utiliser Dijkstra alors qu'il y a OR-Tools ?

Dijkstra calcule les plus courts chemins dans le graphe routier. OR-Tools utilise ensuite ces couts pour construire les tournees. Les deux n'ont donc pas le meme role.

## Le gain ALNS / ILS est-il le score final ?

Non. Le gain ALNS / ILS est un gain technique sur le cout interne des tournees, principalement le temps total calcule avec la matrice de temps. Le score final de l'application combine ensuite temps, CO2, budget et couverture.

## Pourquoi certains clients peuvent ne pas etre livres ?

Parce que le solveur respecte des contraintes. Si livrer tout le monde depasse les 8 heures, la capacite, les fenetres horaires ou le budget, certains clients peuvent etre abandonnes avec une penalite.

## Pourquoi garder seulement la grande composante fortement connexe ?

Parce que le reseau routier est oriente. On garde la plus grande partie du graphe ou tous les points sont accessibles entre eux dans les deux sens, pour eviter des trajets impossibles dans les matrices.

## Pourquoi un mode large scale ?

Parce qu'un VRP avec beaucoup de colis devient trop lourd a resoudre directement. Le mode large scale genere d'abord des tournees candidates faisables, puis selectionne les meilleures.

## Quelle est la vraie contribution du projet pour la matiere ?

La contribution principale est la transformation de donnees ouvertes en graphe exploitable, puis en matrices de plus courts chemins, avant de resoudre un probleme de tournees contraint.
