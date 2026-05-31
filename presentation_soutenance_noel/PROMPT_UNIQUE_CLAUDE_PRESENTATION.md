# Prompt unique pour Claude - Presentation Operation Noel

Copie-colle tout ce prompt dans Claude.

```text
Tu dois generer une presentation de soutenance en francais.

IMPORTANT :
- N'invente aucune information.
- N'ajoute aucune fonctionnalite qui n'est pas explicitement ecrite dans ce prompt.
- Ne change pas les termes techniques.
- Ne change pas les chiffres.
- Ne change pas la problematique.
- Ne rajoute pas de sources externes.
- Ne fais pas une presentation marketing.
- Tu dois uniquement transformer le contenu fourni ci-dessous en slides propres et bien agencees.
- Tu peux ameliorer la mise en page, les schemas, les icones et la hierarchie visuelle, mais pas le fond.
- Le style doit etre Noel moderne, technique, sobre : rouge profond, vert sapin, blanc neige, or discret.
- Les slides doivent etre lisibles, avec peu de texte, mais tous les elements listes doivent apparaitre.
- Quand une slide contient beaucoup d'elements, agence-les sous forme de blocs, tableau ou schema.
- Utilise un style professionnel de soutenance universitaire.
- La presentation doit faire exactement 16 slides.
- Ne cree pas de slide supplementaire.
- Ne supprime pas les messages cles.

Contexte du projet :
Le projet s'appelle Operation Noel.
Il appartient a la matiere "Graphes et Open Data".
Le but est d'optimiser les tournees de livraison du Pere Noel dans une ville reelle a partir de graphes et de donnees ouvertes.
L'application utilise OpenStreetMap, Overpass, Open-Meteo, SRTM NASA, ADEME Impact CO2, OR-Tools et un backend/frontend web.

Problematique exacte :
"Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?"

Format attendu :
Genere une presentation slide par slide.
Pour chaque slide, affiche uniquement :
1. Le titre de la slide
2. Le contenu exact a mettre dans la slide
3. Une indication visuelle courte entre parentheses si utile

Ne mets pas de long paragraphe dans les slides.
Ne mets pas de notes orales dans la presentation finale.

Voici le contenu exact a utiliser.

SLIDE 1
Titre :
Optimisation des tournees du Pere Noel

Contenu :
Graphes et Open Data
OpenStreetMap · Open-Meteo · SRTM NASA · ADEME · OR-Tools

Sous-titre :
Organiser des tournees de livraison realistes dans une ville reelle.

Visuel :
Carte + graphe + traineau + cadeaux

SLIDE 2
Titre :
Problematique

Contenu :
Comment organiser efficacement les tournees de livraison du Pere Noel a partir de graphes et de donnees ouvertes, en arbitrant entre rapidite, couverture des colis, capacite des traineaux, budget et impact CO2 ?

Blocs :
Livrer vite
Livrer un maximum de colis
Respecter les 8h et la capacite
Limiter distance, cout et CO2

SLIDE 3
Titre :
Pipeline global du projet

Contenu sous forme de schema :
Adresse utilisateur
-> donnees ouvertes
-> graphe routier
-> matrices de cout
-> solveur
-> score / debriefing
-> visualisation

Message cle :
Une adresse devient une mission optimisee.

SLIDE 4
Titre :
Open data utilisees

Contenu sous forme de tableau :
OpenStreetMap : reseau routier reel
Overpass : noms de lieux / POI
Open-Meteo : meteo reelle
SRTM NASA : altitude / relief
ADEME Impact CO2 : facteur carbone

Message cle :
Le graphe n'est pas fictif : il vient de donnees ouvertes.

SLIDE 5
Titre :
Temps, vitesse, meteo et relief

Contenu :
vitesse = maxspeed OSM ou vitesse par type de voie

Exemples :
residential -> 30 km/h
tertiary -> 50 km/h
secondary -> 60 km/h
bike -> 18 km/h
walk -> 5 km/h

Formules :
temps = distance / vitesse
temps final = temps x facteur meteo / speed_multiplier

Meteo :
Clear -> x1.0
Rain -> x1.3
Snow / Mist / Thunderstorm -> x2.0

Relief SRTM :
latitude / longitude -> altitude -> pente -> ajustement du temps

Options :
La meteo reelle et le relief sont optionnels.

SLIDE 6
Titre :
Des plus courts chemins aux tournees

Contenu :
1. Graphe OpenStreetMap
- noeuds = intersections / points routiers
- aretes = routes
- poids = temps, distance, CO2, risque

2. Plus courts chemins
- Dijkstra / NetworkX
- calcul entre depot et clients
- construction des matrices

3. Probleme de tournees
- les matrices deviennent l'entree du VRP
- OR-Tools choisit l'ordre des clients et les traineaux
- contraintes : capacite, 8h, fenetres horaires, penalites

Message cle :
On ne resout pas seulement un plus court chemin : on utilise les plus courts chemins pour construire un probleme de tournees.

SLIDE 7
Titre :
Matrices de cout

Contenu :
live_time_matrix.npy -> temps
matrix_5eme.npy -> distance
co2_matrix.npy -> CO2
risk_matrix.npy -> risque
composite_cost_matrix.npy -> cout multicritere

Interpretation :
case [i, j] = cout du plus court chemin entre i et j

CO2 :
ADEME Impact CO2 si active
fallback local sinon
CO2 = distance_km x facteur_g/km
voiture = 120 g/km
velo = 8 g/km
marche = 0 g/km

Commande a afficher :
python scripts/show_matrices.py --size 5

SLIDE 8
Titre :
Contraintes de livraison

Contenu :
Depot unique
Plusieurs traineaux
Capacite limitee
Limite de 8h
Fenetres horaires
Budget
Clients non livres possibles

Fenetres horaires :
tw_start
tw_end

Contrainte :
duree_tournee <= 28800 s

Message cle :
Ce n'est pas un simple plus court chemin : c'est un VRP contraint.

SLIDE 9
Titre :
Selection automatique des traineaux

Contenu :
Heuristique de depart :
k_min = ceil(poids_total / capacite)
k_base = ceil(nombre_clients / 3)

Optimisation du score :
score = cout operationnel + cout non-livres

Details :
cout operationnel = temps + distance + cout flotte
cout non-livres = drop_penalty x nombre de clients non livres

Message cle :
Le bon nombre de traineaux combine couverture et rentabilite.

SLIDE 10
Titre :
Parametres OR-Tools et profils IA

Contenu :
Parametres :
first_solution_strategy
local_search_metaheuristic
solver_time_limit_s
drop_penalty
global_span_cost
vehicle_capacity
vehicle_fixed_cost
time_slack_s
max_route_time_s

Profils :
Express : priorite temps, vitesse plus agressive, temps de recherche court
Ecolo : priorite distance / CO2, recherche plus conservatrice
Prudent : plus de marge temporelle, meilleure tolerance aux incidents

Message cle :
Les profils IA sont des politiques de parametrage du solveur.

SLIDE 11
Titre :
IA apprenante

Contenu :
Objectif :
apprendre quels profils et parametres fonctionnent le mieux selon le contexte

Entrees :
nombre de colis
densite
meteo
incidents
budget
score obtenu
clients non livres

Sorties :
profil recommande
parametrage OR-Tools recommande

Limite :
module present mais pas encore assez entraine pour remplacer les profils fixes

SLIDE 12
Titre :
Resolution et amelioration

Contenu sous forme de comparaison :

Solveur classique :
petites et moyennes missions
OR-Tools
solution initiale
metaheuristique
post-traitement local
ALNS, ILS, 3-opt, or-opt, 2-opt*, double-bridge

Logique :
OR-Tools trouve une bonne solution
le post-traitement cherche a l'ameliorer localement

Solveur large scale :
active a partir de 150 colis
generation de tournees candidates
chaque tournee respecte depot, capacite, 8h
selection avec CP-SAT
penalites pour colis non livres

Message cle :
On garde le solveur classique, on l'ameliore localement, puis on ajoute une strategie adaptee aux tres grandes missions.

SLIDE 13
Titre :
Score final et benchmark

Contenu :
Score final :
45% temps
20% CO2
10% budget
25% couverture colis

Benchmark :
tournee naive vs tournee optimisee
temps gagne
distance reduite
CO2 economise
clients livres

Fichier :
benchmark_results.json

Message cle :
Le resultat n'est pas seulement une route : c'est une solution evaluee avec plusieurs criteres.

SLIDE 14
Titre :
Modules de l'application

Contenu :
Mission
Solveur
Debriefing
Versus
Social / Messages
Donnees / Coulisses

Pipeline applicatif :
creation mission -> resolution -> resultats -> comparaison

Mode Versus :
comparer deux joueurs ou deux strategies sur une meme mission

Criteres Versus :
temps
clients livres
CO2
budget
score final

SLIDE 15
Titre :
Engineering du projet

Contenu :
Architecture :
backend FastAPI
frontend Next.js
cache par mission
scripts de debug

Robustesse :
fallbacks locaux si API indisponible
mode drive automatique pour grandes missions
limite classique / large scale selon le nombre de colis

Performance :
matrices sauvegardees
generation parallele de candidates
tests sur solveur, API et post-traitement

Message cle :
Le projet ne se limite pas a l'algorithme : il a fallu rendre le solveur utilisable dans une application complete.

SLIDE 16
Titre :
Difficultes, limites et conclusion

Contenu :
Difficultes :
graphes OSM lourds
APIs externes instables
passage a 1000 colis
choix du nombre de traineaux
clients non livres
affichage frontend lourd

Limites :
clients simules
optimalite globale non garantie
OSM lent sur grands rayons
CO2 parfois fallback
IA apprenante pas encore assez entrainee

Conclusion :
Les graphes et l'open data permettent de construire une aide a la decision realiste pour organiser les tournees de livraison du Pere Noel.
```
