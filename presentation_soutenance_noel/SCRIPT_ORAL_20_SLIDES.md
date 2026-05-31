# Script oral - Soutenance Operation Noel

Objectif : environ 15 a 18 minutes.

Conseil de rythme :
- Slides 1 a 3 : introduction rapide.
- Slides 4 a 10 : coeur "Graphes et Open Data".
- Slides 11 a 18 : optimisation et solveur.
- Slides 19 a 20 : application, difficultes, conclusion.

## Slide 1 - Optimisation des tournees du Pere Noel

Bonjour, aujourd'hui je vais presenter notre projet Operation Noel, realise dans le cadre de la matiere Graphes et Open Data.

L'idee du projet est de partir d'une situation concrete : le Pere Noel doit livrer des colis dans une vraie ville. On ne travaille donc pas sur une carte abstraite, mais sur un reseau routier reel, construit a partir de donnees ouvertes.

Le but est de transformer une adresse en une mission de livraison, puis de calculer des tournees efficaces avec plusieurs contraintes : le temps, la capacite des traineaux, le budget, le nombre de colis livres et l'impact CO2.

## Slide 2 - Problematique

La problematique du projet est la suivante :

Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?

Cette problematique est interessante parce qu'il n'y a pas un seul objectif. Si on veut seulement aller vite, on peut utiliser beaucoup de traineaux, mais cela augmente le cout. Si on veut reduire le cout, on risque de livrer moins de colis. Et si on ajoute les contraintes de temps, de capacite ou de CO2, le probleme devient un vrai probleme d'optimisation sur graphe.

## Slide 3 - Pipeline global du projet

Le pipeline global commence par une adresse saisie par l'utilisateur.

A partir de cette adresse, le backend recupere ou construit une zone de livraison. Ensuite, il utilise des donnees ouvertes pour construire un graphe routier. Ce graphe sert a calculer plusieurs matrices de cout : temps, distance, CO2, risque et cout composite.

Ces matrices sont ensuite envoyees au solveur, qui calcule les tournees. Enfin, l'application affiche les resultats : carte, score, clients livres, clients non livres, benchmark et debriefing.

Donc l'idee principale est : une adresse devient une mission optimisee.

## Slide 4 - Open data utilisees

Le projet repose sur plusieurs sources open data.

La plus importante est OpenStreetMap, qui fournit le reseau routier reel. C'est grace a OSM qu'on peut transformer une ville en graphe, avec des routes, des intersections et des distances.

Overpass sert a interroger certaines informations autour de la zone, par exemple des noms de lieux ou des points d'interet.

Open-Meteo fournit la meteo reelle, qui peut modifier les temps de trajet.

SRTM NASA fournit des donnees d'altitude, ce qui permet d'estimer le relief et donc d'ajuster les temps si une route monte ou descend.

Enfin, ADEME Impact CO2 peut fournir un facteur carbone. Si cette option n'est pas disponible, le projet utilise un fallback local.

## Slide 5 - Cache d'une mission

Pour rendre le projet exploitable, chaque mission genere un cache.

Dans le dossier cache/api_missions, chaque mission possede son propre identifiant. A l'interieur, on retrouve les fichiers de configuration, les donnees de base, les matrices et les resultats du solveur.

Par exemple, dans core_data, on retrouve le fichier des livraisons, le graphe OpenStreetMap sauvegarde en GraphML, puis les matrices au format numpy.

Ce cache est important pour deux raisons. D'abord, il evite de rappeler les APIs ou de recalculer certaines donnees a chaque fois. Ensuite, il permet de montrer concretement toutes les etapes du projet pendant la soutenance.

## Slide 6 - Points de livraison et graphe

Les clients sont stockes dans le fichier livraisons_5eme.csv.

Chaque ligne correspond a un point de livraison, avec un identifiant, une latitude, une longitude, un poids de colis, un nom client et parfois des fenetres horaires.

Ensuite, la ville est modelisee comme un graphe G = V, E. Les noeuds representent les intersections ou les points routiers, et les aretes representent les segments de route.

Chaque arete peut avoir plusieurs poids : une distance, un temps, un CO2 estime et un risque. C'est cette modelisation qui permet ensuite d'appliquer des algorithmes de graphes.

## Slide 7 - Temps, vitesse, meteo et relief

Pour calculer le temps de trajet, on part de la distance des aretes du graphe.

Quand OpenStreetMap donne une vitesse maximale, on peut l'utiliser. Sinon, le projet applique des vitesses par defaut selon le type de voie. Par exemple, une rue residentielle est estimee autour de 30 km/h, une voie tertiaire autour de 50 km/h, et le velo autour de 18 km/h.

La formule de base est simple : temps egal distance divisee par vitesse.

Ensuite, ce temps peut etre ajuste par la meteo. S'il pleut, neige ou s'il y a du brouillard, le temps augmente.

Le relief peut aussi intervenir avec SRTM NASA : a partir des latitudes et longitudes, on recupere une altitude, on estime une pente, et on ajuste le temps. Une montee coute plus cher en temps, une descente peut reduire legerement le temps.

## Slide 8 - Des plus courts chemins aux tournees

Cette slide est centrale pour la matiere Graphes.

D'abord, on construit un graphe OpenStreetMap. Les noeuds sont les intersections, les aretes sont les routes, et les poids representent le temps, la distance, le CO2 ou le risque.

Ensuite, on utilise des algorithmes de plus courts chemins, notamment via NetworkX et Dijkstra, pour calculer les meilleurs trajets entre le depot et les clients, puis entre les clients eux-memes.

Le resultat de cette etape, ce ne sont pas encore des tournees. Ce sont des matrices : pour chaque paire de points i et j, on connait le cout du meilleur chemin.

Ensuite, ces matrices deviennent l'entree du VRP, c'est-a-dire le Vehicle Routing Problem. OR-Tools ne travaille donc pas directement sur toutes les routes OSM, mais sur les couts entre les points importants.

En resume : Dijkstra sert a transformer le graphe routier en matrices, puis OR-Tools utilise ces matrices pour construire les tournees.

## Slide 9 - Matrices de cout

Le projet produit plusieurs matrices.

La matrice de temps indique le temps de trajet entre chaque paire de points. La matrice de distance indique les distances. La matrice CO2 estime les emissions associees aux trajets. La matrice de risque ajoute une notion de route plus ou moins risquee. Enfin, la matrice composite combine plusieurs criteres.

Chaque case i, j correspond au cout du plus court chemin entre le point i et le point j.

Pour le CO2, si ADEME Impact CO2 est actif, on peut utiliser son facteur carbone. Sinon, on applique un fallback local : par exemple 120 grammes par kilometre pour la voiture, 8 grammes par kilometre pour le velo et 0 pour la marche.

Cette slide est aussi utile pour montrer le script de debug qui affiche les matrices directement dans le terminal.

## Slide 10 - Matrice composite

La matrice composite sert a combiner plusieurs objectifs dans un seul cout.

Dans le projet, on combine le temps, la distance, le CO2 et le risque avec des poids. Par exemple, le temps compte pour 55%, la distance pour 20%, le CO2 pour 15% et le risque pour 10%.

Avant de les combiner, les matrices sont normalisees. C'est important, parce que le temps est en secondes, la distance en metres, le CO2 en grammes, et le risque a sa propre echelle.

L'interet est que le solveur peut optimiser une decision plus riche qu'une simple distance minimale. Il peut arbitrer entre aller vite, faire moins de distance, produire moins de CO2 et prendre moins de risque.

## Slide 11 - Contraintes de livraison

Le probleme n'est pas simplement un plus court chemin.

On a un depot unique, plusieurs traineaux, une capacite limitee, une duree maximale de 8 heures, des fenetres horaires, un budget, et la possibilite que certains clients ne soient pas livres.

La limite de 8 heures est traduite en secondes : 28800 secondes. Les fenetres horaires sont representees dans les colonnes tw_start et tw_end.

Donc le solveur doit construire des tournees realisables : un traineau doit partir du depot, livrer certains clients, respecter les contraintes, puis revenir.

C'est pour cela qu'on parle de VRP contraint, et pas seulement de chemin le plus court.

## Slide 12 - Budget, flotte et clients non livres

Une partie importante du projet est l'arbitrage economique.

Ajouter plus de traineaux peut permettre de livrer plus de clients. Mais chaque traineau a un cout fixe, donc ajouter trop de traineaux peut rendre la solution moins rentable.

Le projet gere aussi les clients non livres. Un client peut etre abandonne si les contraintes rendent sa livraison impossible ou trop couteuse : capacite insuffisante, fenetre horaire trop difficile, limite de 8 heures ou cout trop eleve.

Pour representer cela, on utilise une penalite de non-livraison, appelee drop_penalty. Plus cette penalite est forte, plus le solveur est pousse a livrer les clients.

## Slide 13 - Selection automatique des traineaux

Le nombre de traineaux n'est pas choisi au hasard.

On calcule d'abord un minimum lie a la capacite : si le poids total des colis est trop grand, il faut assez de traineaux pour transporter cette charge.

Ensuite, on calcule aussi une base liee au nombre de clients. Le solveur teste plusieurs valeurs de k, c'est-a-dire plusieurs nombres de traineaux.

Chaque valeur est evaluee avec un score economique : cout operationnel plus cout des colis non livres.

Le but n'est donc pas forcement d'utiliser le minimum de traineaux, ni le maximum. Le but est de trouver un bon compromis entre couverture, temps, distance et cout de flotte.

## Slide 14 - OR-Tools

OR-Tools est le moteur d'optimisation combinatoire utilise dans le projet.

Il prend en entree les matrices calculees a partir du graphe. Ensuite, on lui donne les contraintes : le depot, le nombre de vehicules, la capacite, le temps, les fenetres horaires et les penalites.

OR-Tools cherche alors une solution de tournees : quels clients sont servis par quel traineau, et dans quel ordre.

L'avantage est qu'on ne code pas a la main toute la logique du VRP. On utilise un solveur specialise, mais on le nourrit avec nos donnees ouvertes et nos matrices issues du graphe.

## Slide 15 - Parametres OR-Tools et profils IA

Les profils IA ne sont pas une IA generative. Ce sont plutot des politiques de parametrage du solveur.

Par exemple, le profil Express donne plus d'importance au temps. Il utilise une strategie plus agressive et un temps de recherche plus court.

Le profil Ecolo donne plus d'importance a la distance et au CO2. Il cherche une solution plus conservatrice.

Le profil Prudent ajoute plus de marge temporelle et une meilleure tolerance aux incidents.

Derriere ces profils, on ajuste des parametres OR-Tools comme la strategie de solution initiale, la metaheuristique locale, le temps de recherche, les penalites, les couts fixes et les contraintes de temps.

## Slide 16 - IA apprenante

Le projet contient aussi l'idee d'une IA apprenante.

L'objectif est d'apprendre, a partir des missions passees, quels profils et quels parametres fonctionnent le mieux selon le contexte.

Les entrees peuvent etre le nombre de colis, la densite de la zone, la meteo, les incidents, le budget, le score obtenu ou le nombre de clients non livres.

En sortie, cette IA pourrait recommander un profil ou un parametrage OR-Tools.

Mais pour l'instant, cette partie reste limitee, parce qu'il faut suffisamment de donnees d'entrainement pour qu'elle remplace vraiment les profils fixes.

## Slide 17 - Resolution et amelioration

Le projet utilise deux modes de resolution.

Pour les petites et moyennes missions, on utilise le solveur classique. OR-Tools produit une premiere bonne solution, puis on applique un post-traitement local pour essayer de l'ameliorer.

Ce post-traitement combine ALNS puis ILS. L'idee est de modifier localement les tournees avec des mouvements comme 3-opt, or-opt, 2-opt etoile ou double-bridge.

Ces mouvements changent l'ordre des clients ou echangent des morceaux de tournees pour reduire le cout.

Pour les grandes missions, au-dessus de 150 colis, on active un mode large scale. Au lieu de demander directement a OR-Tools de resoudre un VRP enorme, on genere d'abord des tournees candidates faisables. Ensuite, on selectionne les meilleures avec CP-SAT, en tenant compte des penalites pour les colis non livres.

Donc le projet garde le solveur classique quand il est adapte, et ajoute une strategie speciale quand le nombre de colis devient tres grand.

## Slide 18 - Score final et benchmark

Le score final combine plusieurs dimensions.

Il y a une partie temps, une partie CO2, une partie budget et une partie couverture des colis. La couverture compte beaucoup, parce qu'une solution tres rapide mais qui livre peu de colis n'est pas satisfaisante.

Le CO2 saved correspond a la difference entre une reference naive et la solution optimisee.

Le benchmark compare donc une tournee naive avec une tournee optimisee. On peut mesurer le temps gagne, la distance reduite, le CO2 economise et le nombre de clients livres.

Cette partie permet de justifier que le solveur ne produit pas seulement une route, mais une solution que l'on peut evaluer.

## Slide 19 - Modules de l'application

L'application ne contient pas seulement le solveur.

Le module Mission sert a creer une mission a partir d'une adresse, d'un rayon et d'un nombre de colis.

Le module Solveur lance l'optimisation et affiche les tournees.

Le debriefing explique les resultats obtenus.

Le mode Versus permet de comparer deux joueurs ou deux strategies sur une meme mission, avec des criteres comme le temps, les clients livres, le CO2, le budget et le score final.

Les pages Donnees et Coulisses permettent de montrer ce qui se passe derriere : les matrices, les caches, les graphes et les resultats.

## Slide 20 - Difficultes, limites et conclusion

Les principales difficultes ont ete liees au passage du prototype a des cas plus grands.

Les graphes OpenStreetMap peuvent etre lourds, les APIs externes peuvent etre instables, et le passage a 1000 colis augmente fortement la taille des matrices et le temps de calcul.

Il a aussi fallu gerer le choix du nombre de traineaux, les clients non livres, la coherence du score et l'affichage frontend.

Pour repondre a ces problemes, on a ajoute du cache, des fallbacks locaux, un mode drive automatique pour les grandes missions, un solveur large scale, une generation parallele de candidates et des scripts de debug.

Les limites restent importantes : les clients sont simules, l'optimalite globale n'est pas garantie, OSM peut etre lent sur de grands rayons, et l'IA apprenante n'est pas encore assez entrainee.

Pour conclure, le projet montre que les graphes et l'open data permettent de construire une aide a la decision realiste pour organiser les tournees du Pere Noel, en combinant donnees geographiques, algorithmes de graphes et optimisation combinatoire.

# Questions / reponses possibles

## Pourquoi utiliser OpenStreetMap ?

Parce que la matiere porte sur les graphes et l'open data. OpenStreetMap permet de construire un graphe routier reel au lieu d'utiliser des distances a vol d'oiseau ou une carte fictive.

## Pourquoi Dijkstra si OR-Tools resout deja le VRP ?

Dijkstra et OR-Tools ne font pas la meme chose. Dijkstra calcule les plus courts chemins dans le graphe routier. OR-Tools utilise ensuite les couts calcules par Dijkstra pour resoudre le probleme de tournees.

## Pourquoi ne pas donner directement le graphe OSM a OR-Tools ?

Parce que le graphe OSM contient beaucoup trop de noeuds et d'aretes. OR-Tools travaille plus efficacement avec une matrice entre les points importants : depot et clients.

## Est-ce que la solution est optimale ?

Pour les petits cas, le solveur peut s'approcher fortement d'une tres bonne solution. Mais sur les grands cas, l'optimalite globale n'est pas garantie. Le projet cherche une bonne solution realisable dans un temps raisonnable.

## Pourquoi certains clients ne sont pas livres ?

Parce que le projet respecte des contraintes. Si livrer tout le monde depasse les 8 heures, la capacite, les fenetres horaires ou le budget, le solveur peut abandonner certains clients avec une penalite.

## Pourquoi avoir un mode large scale ?

Parce qu'un VRP avec 1000 colis devient tres lourd. Le mode large scale evite de resoudre directement un probleme geant. Il genere des tournees candidates faisables, puis selectionne les meilleures.

## Pourquoi le nombre de traineaux n'est pas toujours maximal ?

Parce que plus de traineaux augmente la couverture possible, mais augmente aussi le cout de flotte. Le solveur cherche un compromis economique entre livrer plus et payer plus.

## Pourquoi le CO2 est important ?

Il ajoute un critere environnemental a l'optimisation. Mais dans cette soutenance, il reste secondaire par rapport au coeur de la matiere : open data, graphe, plus courts chemins et VRP.

## Quelle est la partie la plus importante techniquement ?

La transformation d'une zone reelle en graphe, puis en matrices exploitables par le solveur. C'est le lien principal entre Open Data, graphes et optimisation.

## Quelle amelioration serait prioritaire ?

Pour aller plus loin, la priorite serait d'ameliorer le passage a grande echelle : cache OSM plus avance, moteur de routage specialise comme OSRM ou GraphHopper, et meilleure visualisation pour 1000 colis.
