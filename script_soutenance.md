# SCRIPT DE SOUTENANCE — OPÉRATION NOËL
# Ce que tu dis mot pour mot sur chaque slide

---

## SLIDE 1 — PAGE DE TITRE
⏱️ 30 secondes

"Bonjour à tous.
Je vais vous présenter Opération Noël.
C'est un projet qui part d'une question très simple :
comment optimiser une tournée de livraison en une seule nuit,
dans une vraie ville, avec de vraies contraintes ?

Pour répondre à cette question, on a construit une plateforme web complète
qui combine des données ouvertes, la théorie des graphes,
et de l'intelligence artificielle."

---

## SLIDE 2 — PLAN
⏱️ 20 secondes

"Voici notre plan pour ces 20 minutes.
On va commencer par le contexte et le problème qu'on résout.
Ensuite je vous montrerai le site et son architecture.
Puis on plongera dans la donnée, les graphes, et l'IA.
On finira par les résultats et les questions."

---

## SLIDE 3 — CONTEXTE & PROBLÉMATIQUE
⏱️ 1 minute

"Le problème du Père Noël, c'est en réalité le problème du voyageur de commerce.
C'est ce qu'on appelle le VRP — Vehicle Routing Problem.
Et il est NP-difficile.

Concrètement, pour 10 clients, il y a 3,6 millions de tournées possibles.
Pour 20 clients, on dépasse les 2 milliards de milliards.
Aucun humain, aucun ordinateur ne peut tester toutes les options.

En plus de ça, on a des contraintes réelles :
des fenêtres horaires — certains clients ne peuvent être livrés qu'à des heures précises,
une capacité de chargement par véhicule,
un budget limité,
et une météo qui change les temps de trajet.

Notre réponse : construire le graphe de la ville à partir de vraies données OpenStreetMap,
calculer les meilleures routes avec Dijkstra et A*,
et optimiser les tournées avec un solveur VRPTW et de l'IA."

---

## SLIDE 4 — OBJECTIFS
⏱️ 40 secondes

"On s'est fixé 4 objectifs.

Éducatif d'abord : on veut que l'utilisateur comprenne intuitivement ce que font les algorithmes.
Pas seulement voir un résultat, mais visualiser Dijkstra et A* en train de s'exécuter.

Technique ensuite : résoudre un vrai VRP avec de vraies données géographiques.

Comparatif : le mode versus permet de mesurer la performance humaine face à l'IA en temps réel.

Et écologique : on intègre les données CO₂ officielles de l'ADEME pour calculer l'empreinte carbone de chaque tournée."

---

## SLIDE 5 — FONCTIONNALITÉS DU SITE
⏱️ 50 secondes

"Le site propose 6 espaces distincts.

L'accueil, qui présente les différents modes de jeu.

La Campagne, qui est le cœur du site : des missions guidées avec un système de scoring progressif.

Le Solver libre, où on peut tester librement tous les paramètres et tous les profils IA.

Le mode Versus, un duel 1v1 en temps réel contre l'IA, ou contre un autre joueur.

Explore, qui permet de visualiser pas à pas les algorithmes de graphes directement sur la carte.

Et le Leaderboard, avec un classement global, hebdomadaire, et entre amis."

---

## SLIDE 6 — PARCOURS UTILISATEUR
⏱️ 1 minute

"Voici le parcours complet d'une mission.

L'utilisateur crée son compte — mot de passe haché avec PBKDF2 et 120 000 itérations, conforme au standard NIST 2023.

Il sélectionne ensuite sa mission : une zone géographique, un nombre de clients entre 8 et 200, une météo, un budget, des incidents éventuels.

Le backend télécharge alors automatiquement le graphe OpenStreetMap, génère les matrices de coût, et récupère de vrais noms de commerces via l'API Overpass.

L'utilisateur joue : il choisit son itinéraire parmi 3 options proposées à chaque étape. Ces options sont calculées en temps réel par l'algorithme A* sur le graphe.

À la fin, il obtient son score sur 100 et un debrief complet avec la comparaison IA, l'analyse CO₂, et l'amélioration possible via 2-opt.

Son score est soumis au leaderboard avec un hash d'intégrité."

---

## SLIDE 7 — VERSUS & SOLVER
⏱️ 40 secondes

"Deux modes spéciaux.

Le mode Versus propose des duels 1v1 en temps réel via WebSocket.
On peut rejoindre une file publique, créer un salon privé, ou envoyer une invitation.
3 maps préconfigurées : Paris par temps clair, Berlin sous la pluie, Montréal sous la neige avec incidents.

Le Solver libre donne accès à tous les paramètres du solveur.
On peut choisir le profil IA, le nombre de véhicules, le mode de transport — voiture, vélo ou marche —
et observer directement les routes optimisées s'afficher sur la carte."

---

## SLIDE 8 — ARCHITECTURE TECHNIQUE
⏱️ 1 minute

"L'architecture suit le pattern frontend-backend découplé.

En haut, le frontend Next.js 14 en TypeScript.
Il communique avec le backend via REST pour les missions,
et via WebSocket pour le versus en temps réel.

Le backend FastAPI orchestre trois moteurs :
le solveur OR-Tools pour le VRPTW,
le générateur de graphes basé sur OSMnx,
et le module d'apprentissage IA.

En bas : une base SQLite pour les joueurs et le leaderboard,
des fichiers NumPy pour les matrices de coût,
et 5 APIs externes — toutes gratuites, toutes sans clé propriétaire :
OpenStreetMap, Open-Meteo, ADEME, Overpass, et OpenTopoData de la NASA."

---

## SLIDE 9 — STACK TECHNIQUE
⏱️ 30 secondes

"Toute la stack est open-source et sans licence payante.

Je veux souligner deux choix en particulier.

NumPy en format .npy pour les matrices : c'est 30 fois plus rapide que JSON.
Quand on manipule des matrices 180 par 180, c'est un choix décisif.

FastAPI plutôt que Django : parce qu'il est asynchrone nativement et génère automatiquement la documentation de l'API.

Tout le reste — Next.js, OR-Tools, Leaflet, SQLite — est justifié par le même critère : performant, gratuit, sans dépendance externe."

---

## SLIDE 10 — 5 SOURCES OPEN DATA
⏱️ 1 minute 30 secondes

"Toutes nos données viennent de sources ouvertes.

Première source : OpenStreetMap via la bibliothèque OSMnx.
On télécharge le graphe routier de n'importe quelle ville dans le monde.
Pour Paris 5ème : 2 500 nœuds, 6 000 arêtes.
Gratuit, mondial, communautaire.

Deuxième : l'API Overpass, aussi basée sur OSM.
Elle nous donne les vrais noms des commerces et restaurants dans une zone.
C'est ce qui permet d'avoir des missions avec de vrais points de livraison réalistes.

Troisième : Open-Meteo pour la météo en temps réel.
Elle retourne un code WMO qu'on convertit en facteur multiplicatif sur les temps de trajet.
Pluie : facteur 1.35. Neige : 1.80. Tempête : 2.0.
Aucune clé API nécessaire.

Quatrième : OpenTopoData, les données d'élévation satellite de la NASA — résolution 90 mètres.
On corrige les temps de trajet selon la pente des rues.

Cinquième : l'API ADEME Impact CO₂, la source officielle du gouvernement français pour les bilans carbone.
120 grammes par km pour une voiture thermique, 8g pour un vélo, 0 pour la marche.
Ce sont des données légalement référençables."

---

## SLIDE 11 — PIPELINE ETL
⏱️ 1 minute

"Voici le pipeline complet de traitement de la donnée, en 7 étapes.

Extraction : on télécharge le graphe OSM, les noms POI, la météo, et les facteurs CO₂ ADEME.

Nettoyage : on extrait la composante fortement connexe du graphe — j'y reviens dans la slide suivante — et on supprime les boucles et doublons.

Annotation des arêtes : pour chaque rue, on calcule le temps de trajet, les émissions CO₂, et un score de risque selon le type de voie.

Génération des matrices : on lance Dijkstra depuis chaque point de livraison vers tous les autres.
On obtient 4 matrices n×n : temps, distance, CO₂, risque.

Normalisation robuste : on divise chaque matrice par sa médiane pour éliminer les effets d'échelle.
Les valeurs infinies — routes impossibles — sont remplacées par 10 exposant 9.

Matrice composite : on combine les 4 matrices avec des poids.
55% pour le temps, 20% pour la distance, 15% pour le CO₂, 10% pour le risque.

Stockage en cache NumPy .npy pour ne pas recalculer à chaque fois."

---

## SLIDE 12 — CONSTRUCTION DU GRAPHE
⏱️ 1 minute

"Parlons de la structure du graphe.

C'est un MultiDiGraph orienté.
Orienté parce que les rues ont des sens de circulation.
Multi parce que deux intersections peuvent être reliées par plusieurs arêtes — une rue et une piste cyclable par exemple.

Les nœuds représentent les intersections, avec leur latitude et longitude.
Les arêtes représentent les segments de rue, annotés avec le temps de trajet, la vitesse légale, les émissions CO₂, et le score de risque.

On a 3 graphes distincts selon le mode de transport : voiture jusqu'à 110 km/h sur autoroute, vélo entre 10 et 25 km/h, marche entre 3 et 6.5 km/h.

Pourquoi extraire la composante fortement connexe ?
Parce qu'un graphe OSM brut contient des impasses directionnelles — des rues en sens unique mal reliées.
Sans la SCC, le solveur peut trouver un chemin pour aller chez un client mais pas en revenir.
La SCC garantit qu'on peut aller de n'importe quel point à n'importe quel autre."

---

## SLIDE 13 — DIJKSTRA VS A*
⏱️ 1 minute 30 secondes

"On utilise deux algorithmes de plus court chemin selon le contexte.

Dijkstra pour générer les matrices de coût.
Son principe : explorer les nœuds du plus proche au plus éloigné, en maintenant un tas min.
Il explore dans toutes les directions.
Complexité en O de V plus E fois log V avec un tas binaire.
On en a besoin pour tous les chemins entre tous les points — donc on explore tout.

A* pour les options de route en temps réel.
Sa formule : f de n égal g de n plus h de n.
g de n est le coût réel depuis la source.
h de n est l'heuristique — une estimation du coût restant.

Notre heuristique, c'est la distance haversine divisée par la vitesse maximale.
La haversine, c'est la distance à vol d'oiseau entre deux points.
Cette heuristique est admissible : elle sous-estime toujours le temps réel,
parce que la distance à vol d'oiseau est toujours inférieure ou égale au chemin routier réel.

L'admissibilité garantit que A* trouve l'optimum, comme Dijkstra.
Mais en guidant la recherche vers le but, A* explore 20 à 40% de nœuds en moins.
C'est ce qu'on utilise pour calculer les 3 options de route proposées au joueur en temps réel."

---

## SLIDE 14 — VRPTW
⏱️ 1 minute 30 secondes

"Le cœur du solveur, c'est le VRPTW — Vehicle Routing Problem with Time Windows.

Le problème en entrée : n clients à livrer, k véhicules, une capacité Q par véhicule, et un horizon T de 8 heures — soit 28 800 secondes.
Pour chaque client, une fenêtre horaire et un poids de colis.
Pour chaque paire de points, 4 matrices de coût.

L'objectif est de minimiser la somme des coûts sur toutes les routes.

Les contraintes sont de quatre types.
Visite unique : chaque client est visité exactement une fois.
Capacité : la somme des poids sur chaque route ne dépasse pas Q.
Fenêtres temporelles : on arrive dans la fenêtre horaire de chaque client.
Contrainte une nuit : toutes les livraisons se terminent en 8 heures.

Pour les clients qu'il est impossible de livrer dans les contraintes,
on ne déclare pas l'infaisabilité.
On leur applique une pénalité d'abandon d'un million de points.
Ça permet au solveur de toujours trouver une solution valide,
quitte à laisser quelques clients non livrés."

---

## SLIDE 15 — OR-TOOLS & MÉTAHEURISTIQUES
⏱️ 1 minute

"Le solveur OR-Tools de Google fonctionne en deux phases.

Phase 1 : construire rapidement une solution valide.
On a trois stratégies.
PATH_CHEAPEST_ARC : greedy, on va toujours au client le plus proche.
PARALLEL_CHEAPEST_INSERTION : on insère chaque client au meilleur endroit possible dans la tournée.
SAVINGS, ou algorithme de Clarke-Wright de 1964 : on fusionne des routes partielles en cherchant les économies maximales.

Phase 2 : améliorer itérativement jusqu'à la limite de temps.
Trois métaheuristiques.
Guided Local Search : pénalise les arêtes qui reviennent trop souvent dans les minima locaux. C'est le meilleur pour minimiser le temps.
Simulated Annealing : accepte des solutions légèrement pires avec une probabilité décroissante — ça permet d'explorer globalement.
Tabu Search : maintient une liste des mouvements récents et les interdit — ça évite de tourner en rond.

Après le solveur, on applique systématiquement un post-traitement 2-opt."

---

## SLIDE 16 — 2-OPT & K-MEANS
⏱️ 1 minute

"Deux algorithmes complémentaires que nous avons implémentés nous-mêmes.

Le 2-opt.
Son principe : tester toutes les paires d'arêtes dans une tournée.
Si inverser le segment entre i et j réduit le coût total, on l'inverse.
On répète jusqu'à ce qu'aucune inversion n'améliore plus.
C'est O de n² par itération.
On l'applique après le solveur OR-Tools, et aussi sur la route du joueur humain pour lui montrer le potentiel d'amélioration.

Le K-Means spatial.
Implémenté from scratch — pas de scikit-learn.
Le principe : diviser les clients en k zones géographiques, puis optimiser chaque zone indépendamment.
Ça réduit la complexité de n clients à k sous-problèmes de n sur k clients.
L'algorithme : initialiser k centroïdes aléatoires, assigner chaque client au centroïde le plus proche, recalculer les centroïdes, répéter jusqu'à convergence.
La convergence est garantie parce que l'inertie décroît strictement à chaque étape.

Ce K-Means alimente le profil IA le plus difficile — Championne (Secteurs) — avec un bonus de difficulté de 10."

---

## SLIDE 17 — CENTRALITÉ & ROBUSTESSE
⏱️ 45 secondes

"On a aussi analysé le graphe urbain lui-même.

La centralité de betweenness mesure pour chaque nœud combien de plus courts chemins le traversent.
Les nœuds avec la centralité la plus haute sont les hubs critiques du réseau — les grands carrefours, les artères principales.

On a fait un test de robustesse sur Paris 5ème.
Résultat : supprimer 1% seulement des nœuds les plus centraux provoque une perte de 60% de connectivité.
En revanche, supprimer 10% des nœuds de façon aléatoire ne dégrade que 15% la connectivité.

Le graphe urbain est donc fragile aux attaques ciblées — c'est un réseau scale-free.
Quelques nœuds concentrent l'essentiel du trafic.
Un incident sur un hub, c'est une paralysie partielle.
C'est visualisé dans le débrief de mission."

---

## SLIDE 18 — IA VUE GLOBALE
⏱️ 30 secondes

"Notre système IA se décompose en 3 niveaux.

Niveau 1 : les 7 profils IA paramétrés.
Ce sont des configurations expertes du solveur.

Niveau 2 : un modèle d'apprentissage bayésien léger.
Il apprend quel profil convient le mieux selon le contexte — météo, taille de mission, incidents.

Niveau 3 : le Sleigh Search et l'Auto-Tuner.
Le Sleigh Search optimise dynamiquement le nombre de véhicules.
L'Auto-Tuner apprend les paramètres OR-Tools les plus efficaces selon le contexte."

---

## SLIDE 19 — LES 7 PROFILS IA
⏱️ 1 minute

"Les 7 profils sont des configurations expertes du solveur OR-Tools.
Chaque profil choisit une stratégie initiale, une métaheuristique, et une limite de temps différentes.

Express : rapide, 12 secondes, Guided Local Search. Bonus de difficulté ×2.

Écolo : optimise la distance plutôt que le temps, avec l'algorithme de Clarke-Wright et le Simulated Annealing. Bonus ×3.

Prudent : conservateur, beaucoup de marges de sécurité, 28 secondes. Bonus ×4.

Opportuniste : Tabu Search, flexible sur les arbitrages. Bonus ×4.

Agressive : seulement 10 secondes, accepte d'abandonner des clients coûteux pour aller plus vite. Bonus ×6.

Championne : configuration complète, 35 secondes. Bonus ×8.

Championne (Secteurs) : utilise d'abord K-Means pour découper la ville en secteurs, puis optimise chaque secteur. 40 secondes. Bonus ×10 — c'est le plus difficile à battre.

Le bonus de difficulté multiplie la contribution du profil au score final."

---

## SLIDE 20 — MODÈLE BAYÉSIEN
⏱️ 1 minute

"Comment choisir automatiquement le meilleur profil selon la situation ?

C'est le rôle du modèle d'apprentissage bayésien.

Pour chaque résolution passée, on enregistre le contexte — météo, taille de mission, incidents —
le profil utilisé, et le coût composite obtenu.

Ce coût composite est notre signal de qualité :
il combine le temps par client, la distance, le taux d'abandon, le dépassement de budget, et la pénalité météo.

Pour recommander, on calcule le coût attendu de chaque profil dans un contexte donné.
Formule : n_contexte fois la moyenne du contexte, plus alpha fois la moyenne globale, divisé par n_contexte plus alpha.
Alpha vaut 3 — c'est le paramètre de lissage bayésien.

Ce lissage vers la moyenne globale évite le surapprentissage.
Le modèle fonctionne dès 8 exemples.

Pourquoi pas du deep learning ?
Parce qu'on a 10 à 100 résolutions, pas des milliers.
Le bayésien est interprétable, léger — moins de 10 ko en JSON — et ne nécessite pas de GPU."

---

## SLIDE 21 — SLEIGH SEARCH & AUTO-TUNER
⏱️ 1 minute

"Le Sleigh Search résout le problème du nombre optimal de véhicules.

Trop peu de véhicules, des clients ne sont pas livrés.
Trop, le coût de flotte explose.

L'algorithme fonctionne comme un bracket de tournoi.
On commence avec plusieurs candidats — différentes tailles de flotte.
Pour chaque candidat, on lance une résolution rapide de 2 secondes.
On calcule un score : temps total plus 0.015 fois la distance, plus une pénalité pour les abandons, plus 2 fois k fois le coût du véhicule.
On élimine la moitié la moins bonne.
On recommence jusqu'à un seul candidat.

L'Auto-Tuner applique le même principe bayésien au niveau des paramètres OR-Tools eux-mêmes.
Il apprend quelle combinaison stratégie-métaheuristique-temps fonctionne le mieux selon le contexte.

L'endpoint solve-learned combine tout ça : il sonde 4 stratégies en parallèle sur 2 secondes chacune, sélectionne la meilleure, puis lance la résolution complète."

---

## SLIDE 22 — CHOIX TECHNIQUES
⏱️ 1 minute

"Je veux expliquer les principaux arbitrages techniques.

OR-Tools plutôt que CPLEX ou Gurobi :
OR-Tools est open-source et au niveau des solveurs commerciaux sur les benchmarks académiques.
Zéro coût de licence.

Dijkstra plutôt que Bellman-Ford pour les matrices :
pas de poids négatifs dans notre graphe, donc Dijkstra est optimal.
Bellman-Ford serait plus lent pour rien.

NumPy .npy plutôt que JSON :
30 fois plus rapide en lecture-écriture.
Décisif quand on charge des matrices 180 par 180 à chaque requête.

K-Means maison plutôt que scikit-learn :
50 lignes de code, maîtrise algorithmique complète prouvée.

SQLite plutôt que PostgreSQL :
pas de serveur à gérer, ACID, suffisant pour quelques dizaines d'utilisateurs simultanés.
La migration vers PostgreSQL ne changerait qu'une seule couche — repository.py.

Bayésien plutôt que deep learning :
efficace dès 8 exemples, interprétable, sans GPU, sans milliers de données."

---

## SLIDE 23 — SÉCURITÉ
⏱️ 40 secondes

"Trois points sur la sécurité.

Les mots de passe sont hachés avec PBKDF2-HMAC-SHA256 et 120 000 itérations.
C'est le standard recommandé par le NIST en 2023.
Chaque mot de passe a un sel aléatoire de 32 octets.
Les réinitialisations expirent après 30 minutes.

Les scores du leaderboard sont calculés entièrement côté serveur.
L'utilisateur ne soumet jamais un score — il soumet l'état de sa mission.
Le serveur recalcule et signe chaque soumission avec HMAC.
Un score falsifié côté client sera rejeté.

Chaque mission est isolée dans son propre répertoire.
L'accès est vérifié par identifiant joueur.
Pas de lecture croisée possible entre joueurs."

---

## SLIDE 24 — RÉSULTATS & BENCHMARKS
⏱️ 1 minute

"Les résultats.

On compare toujours contre une baseline naïve :
livrer les clients dans l'ordre 1 à N, répartis équitablement entre les véhicules, sans aucune optimisation.

Le solveur IA réduit le temps de tournée de 36.7%.
La distance totale baisse de 36.1%.
Les émissions CO₂ diminuent de 15 à 25% selon les scénarios.
Et tout ça en moins de 30 secondes de calcul pour 50 clients.

La formule de score combine 4 composantes :
45% pour le gain de temps, 20% pour le CO₂, 10% pour le budget restant, 25% pour le taux de couverture — le ratio de clients livrés.
Des bonus s'ajoutent selon la difficulté du profil IA choisi, la météo, et les incidents.

Sur les algorithmes de graphes :
A* explore 20 à 40% de nœuds en moins que Dijkstra sur les mêmes requêtes.
Et la robustesse du graphe Paris 5ème confirme sa fragilité : 1% de nœuds supprimés = 60% de connectivité perdue."

---

## SLIDE 25 — LIMITES & AMÉLIORATIONS
⏱️ 40 secondes

"Soyons honnêtes sur les limites.

La scalabilité est la limite principale.
Au-delà de 200 clients, le calcul des matrices dépasse 2 minutes.
La génération du graphe peut prendre 15 à 60 secondes selon la disponibilité de l'API OSM.

Le modèle IA souffre du problème du cold start :
sur un contexte jamais vu, il revient à la moyenne globale.
Et il n'y a pas encore d'apprentissage par renforcement pour adapter les routes en cours de mission.

Les données sont statiques : le graphe ne se met pas à jour avec les incidents routiers réels.

Les pistes d'amélioration les plus prometteuses :
K-Means automatique pour décomposer les grands problèmes,
cuOpt de NVIDIA pour le calcul GPU des matrices,
et l'apprentissage par renforcement pour adapter les décisions en temps réel."

---

## SLIDE 26 — CONCLUSION
⏱️ 30 secondes

"En résumé.

5 sources de données ouvertes.
7 profils IA paramétrés.
3 algorithmes de graphes — Dijkstra, A*, et 2-opt.
5 matrices de coût.
3 modes de transport.
Plus de 40 tests automatisés.
36.7% de réduction du temps versus la baseline naïve.
Et moins de 30 secondes de calcul pour 50 clients.

Tout est open-source, tout est gratuit, tout est reproductible.
Un pipeline complet qui va de la donnée brute OpenStreetMap jusqu'à une interface web jouable.

Je suis prêt pour vos questions."

---

---

# QUESTIONS FRÉQUENTES — RÉPONSES COURTES

---

**"Pourquoi OR-Tools et pas votre propre solveur ?"**

"OR-Tools est la bibliothèque de référence open-source pour le VRP, utilisée en production par des entreprises de logistique mondiale.
Implémenter un solveur compétitif from scratch prendrait des années.
Notre valeur ajoutée, c'est l'orchestration intelligente — les 7 profils, le Sleigh Search, le modèle bayésien — pas la réimplémentation de l'état de l'art."

---

**"L'heuristique haversine est-elle vraiment admissible pour A* ?"**

"Oui, par construction.
La distance à vol d'oiseau est toujours inférieure ou égale au chemin routier réel.
Donc h de n est toujours inférieure ou égale au coût réel h étoile de n.
L'admissibilité est garantie, et avec elle l'optimalité de A*."

---

**"Pourquoi K-Means et pas DBSCAN ?"**

"DBSCAN est pertinent quand on ne connaît pas le nombre de clusters à l'avance.
Ici on connaît k — c'est le nombre de véhicules.
K-Means est donc le bon choix.
De plus, les centroïdes correspondent directement aux barycentres géographiques des zones de livraison, ce qui est très interprétable."

---

**"Votre modèle bayésien, c'est vraiment de l'apprentissage ?"**

"C'est de l'apprentissage statistique au sens strict — l'inférence bayésienne avec prior.
Au cold start on recommande aléatoirement.
Après 8 exemples dans un contexte donné, le modèle recommande avec confiance.
C'est la même logique que les systèmes de recommandation classiques.
Ce n'est pas du deep learning, mais c'est délibéré : on n'a pas des milliers d'exemples."

---

**"SQLite en production, c'est sérieux ?"**

"Pour quelques dizaines d'utilisateurs simultanés, SQLite est parfaitement adapté.
Il est ACID, supporte les lectures concurrentes.
La seule limite c'est l'écriture concurrente.
Et la migration vers PostgreSQL ne changerait qu'une seule couche — repository.py.
L'architecture est prévue pour ça."

---

**"Comment vous protégez les scores contre la triche ?"**

"L'utilisateur ne soumet jamais un score directement.
Il soumet l'état de sa mission — quels clients livrés, dans quel ordre, à quelle heure.
Le serveur recalcule le score intégralement.
Chaque soumission est signée côté serveur par HMAC.
Un score falsifié côté client sera rejeté."

---

**"Que se passe-t-il si l'API OSM est indisponible ?"**

"Chaque appel externe a un fallback.
Pour Overpass : si indisponible, on génère des noms de clients de façon procédurale.
Pour ADEME CO₂ : on bascule sur des constantes locales — 120 g/km pour la voiture.
Pour Open-Meteo : on simule une météo avec des probabilités pondérées.
Aucune API externe n'est critique — le système reste fonctionnel dans tous les cas."

---

**"Scalable à 500 clients ?"**

"Pas dans l'état actuel.
La matrice 500×500 prendrait plusieurs minutes à calculer.
Les solutions : K-Means automatique pour décomposer en sous-problèmes, calcul parallèle des matrices, et cuOpt de NVIDIA pour le GPU.
C'est la première amélioration à implémenter."

---

**"Pourquoi services.py fait 5 923 lignes ?"**

"C'est une dette technique assumée.
En production, on découperait en modules thématiques : solver_service, ai_service, graph_service, player_service.
C'est la croissance organique du projet — chaque feature a été ajoutée dans le même fichier.
La refactorisation est la première amélioration architecturale à prévoir."

---

**"Vos données OSM sont-elles fiables ?"**

"En zone urbaine dense comme Paris, la qualité d'OSM est comparable à Google Maps pour le réseau routier.
Vitesses légales, types de voies, sens de circulation — tout est là.
Pour un usage en production réelle, on enrichirait avec des données de trafic temps réel comme TomTom ou HERE.
Pour un projet académique, c'est la référence standard."
