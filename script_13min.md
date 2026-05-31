# SCRIPT 13 MINUTES — OPÉRATION NOËL
# Ce que tu dis mot pour mot sur chaque slide

---

## SLIDE 1 — TITRE
⏱️ 20 secondes

"Bonjour à tous.
Je vais vous présenter Opération Noël.
C'est une plateforme web qui permet d'optimiser des tournées de livraison
dans une vraie ville, en une seule nuit,
en utilisant des données ouvertes et de l'intelligence artificielle."

---

## SLIDE 2 — PLAN
⏱️ 15 secondes

"Voici le plan.
On va voir le problème qu'on résout, comment le site fonctionne,
comment on traite les données, les graphes et le solveur,
puis l'IA — et notamment l'IA qui apprend d'elle-même.
On finit sur les résultats."

---

## SLIDE 3 — CONTEXTE
⏱️ 50 secondes

"Le problème du Père Noël, en vrai, c'est un problème mathématique très connu :
le Vehicle Routing Problem. Et il est NP-difficile.

Ce que ça veut dire concrètement :
pour 10 clients, il y a 3,6 millions de tournées possibles à évaluer.
Pour 20 clients, on dépasse les 2 milliards de milliards.
Aucun humain, aucune machine ne peut tout tester.

En plus de ça, on a des vraies contraintes :
des créneaux horaires par client, un poids maximum par véhicule,
un budget, et une météo qui change les temps de trajet.

Notre réponse : modéliser la ville comme un graphe,
calculer les meilleures routes avec des algorithmes dédiés,
et laisser un solveur optimisé par l'IA faire le reste."

---

## SLIDE 4 — LE SITE
⏱️ 55 secondes

"Le site propose 4 modes principaux.

La Campagne, c'est le mode guidé.
On joue des missions, on livre des colis sur une vraie carte,
on choisit ses routes, et à la fin on reçoit un score sur 100.

Le mode Versus, c'est un duel en temps réel.
Toi contre l'IA, sur la même carte, les mêmes données.
Qui livre le plus vite et le plus efficacement ?

Explore, c'est la partie éducative.
On peut visualiser les algorithmes de graphes s'exécuter pas à pas —
voir en direct comment Dijkstra et A* trouvent leurs chemins.

Et le Leaderboard : un classement global avec des scores
vérifiés côté serveur pour garantir l'intégrité."

---

## SLIDE 5 — PARCOURS UTILISATEUR
⏱️ 45 secondes

"Voici comment se déroule une mission en 5 étapes.

D'abord on choisit sa mission : une zone géographique, un nombre de clients,
une météo, un budget, des incidents éventuels.

Ensuite la carte se génère automatiquement.
Le graphe de la ville est téléchargé en temps réel depuis OpenStreetMap.
De vrais noms de commerces apparaissent comme points de livraison.

Pendant la mission, à chaque étape on a 3 options de route proposées.
Ces options sont calculées en temps réel par l'algorithme A*.
Les stats s'affichent en direct — temps, distance, CO₂, budget restant.

Une fois terminé, on reçoit notre score, une comparaison avec la solution IA,
et une analyse CO₂ de la tournée.

Et enfin, le score est classé sur le leaderboard."

---

## SLIDE 6 — LES DONNÉES OPEN DATA
⏱️ 1 minute 15 secondes

"Toutes les données qu'on utilise sont des données ouvertes.
Zéro donnée propriétaire, zéro licence payante.

OpenStreetMap via OSMnx nous donne le graphe routier de n'importe quelle ville du monde.
Pour Paris 5ème : 2 500 intersections, 6 000 segments de rue.

L'API Overpass, aussi basée sur OpenStreetMap, nous donne les vrais noms
des commerces et restaurants dans une zone.
C'est ce qui rend les missions réalistes.

Open-Meteo nous fournit la météo actuelle sans inscription, sans clé API.
La pluie multiplie les temps de trajet par 1.35, la neige par 1.80, un orage par 2.

OpenTopoData de la NASA nous donne l'altitude par coordonnées GPS —
résolution 90 mètres — pour corriger les temps selon la pente des rues.

Et l'API ADEME, c'est la source officielle du gouvernement français pour les bilans carbone.
120 grammes de CO₂ par kilomètre pour une voiture, 8 grammes pour un vélo, 0 pour la marche.
Des données légalement référençables."

---

## SLIDE 7 — PIPELINE DE DONNÉES
⏱️ 50 secondes

"Comment on passe de ces données brutes à quelque chose d'utilisable par le solveur ?

En 4 étapes.

D'abord on télécharge le graphe, la météo, et les facteurs CO₂.

Ensuite on nettoie le graphe.
On garde uniquement les rues où on peut aller ET revenir —
parce que certaines rues en sens unique créent des impasses directionnelles.

Puis on calcule le coût de chaque rue :
temps de trajet, émissions CO₂, niveau de risque selon le type de voie.

Enfin on construit une matrice de coût finale :
55% de poids pour le temps, 20% pour la distance, 15% pour le CO₂, 10% pour le risque.

Cette matrice est mise en cache.
La lecture d'un fichier NumPy est 30 fois plus rapide que du JSON —
c'est un choix technique important quand on manipule des matrices de 180 lignes par 180 colonnes."

---

## SLIDE 8 — LE GRAPHE
⏱️ 55 secondes

"Parlons du graphe plus concrètement.

Un graphe c'est simplement un ensemble de points — les nœuds — reliés par des liens — les arêtes.
Ici les nœuds sont les intersections de rues, et les arêtes sont les segments de rue.

Le graphe est orienté parce que les rues ont des sens de circulation.
Chaque arête connaît la vitesse légale, les émissions CO₂ associées, et son niveau de risque.

On construit en fait 3 graphes différents selon le mode de transport :
voiture avec les vitesses légales jusqu'à 110 km/h sur autoroute,
vélo entre 10 et 25 km/h,
et marche entre 3 et 6.5 km/h.

Le solveur peut donc optimiser une tournée multimodale :
certains véhicules en voiture, d'autres à vélo."

---

## SLIDE 9 — DIJKSTRA ET A*
⏱️ 1 minute

"On utilise deux algorithmes de plus court chemin selon le contexte.

Dijkstra explore le graphe du nœud le plus proche au plus éloigné.
Il examine toutes les directions à la fois, et garantit de trouver le chemin optimal.
On l'utilise pour calculer les distances entre tous les paires de points —
c'est la génération de la matrice de coût.

A étoile, c'est Dijkstra amélioré.
Au lieu d'explorer dans toutes les directions, il est guidé par une estimation :
la distance à vol d'oiseau vers le but.
Il explore 20 à 40% de nœuds en moins tout en garantissant le même résultat optimal.

Cette estimation est toujours inférieure ou égale au chemin routier réel —
on ne peut jamais aller moins loin que le vol d'oiseau — ce qui garantit qu'on trouve bien l'optimum.

On l'utilise pour les 3 options de route proposées au joueur en temps réel
parce qu'on n'a pas besoin de tous les chemins, juste du meilleur vers un point précis."

---

## SLIDE 10 — LE SOLVEUR VRP
⏱️ 55 secondes

"Le solveur doit résoudre un problème complexe :
comment répartir N clients entre K véhicules,
en respectant les créneaux horaires de chaque client,
la capacité de chargement de chaque véhicule,
et en terminant en moins de 8 heures ?

On utilise Google OR-Tools, la bibliothèque de référence open-source pour ce type de problème.
Elle est utilisée en production par de grandes entreprises de logistique.

Le solveur fonctionne en deux phases.
D'abord il construit rapidement une solution de départ — pas parfaite mais valide.
Ensuite il l'améliore en boucle jusqu'à la limite de temps fixée.

Si un client est impossible à livrer dans les contraintes,
le solveur ne plante pas.
Il l'abandonne avec une pénalité et continue.
Ça permet d'avoir toujours une solution, même imparfaite.

Résultat : 50 clients optimisés en moins de 30 secondes."

---

## SLIDE 11 — LES 3 PROFILS IA
⏱️ 1 minute

"Le solveur peut être configuré de différentes façons selon l'objectif.
On a 3 profils principaux.

Express : optimisé pour la vitesse, 12 secondes de calcul.
C'est le profil agressif — il prend des risques, accepte de laisser des clients coûteux en temps.
Idéal par temps clair, mission urgente. Difficile à battre d'un facteur 2.

Écolo : optimisé pour minimiser les kilomètres et les émissions CO₂.
Il prend 18 secondes et utilise une stratégie différente, basée sur l'algorithme de Clarke-Wright de 1964.
Facteur 3.

Championne (Zones) : le plus difficile.
Il commence par découper la ville en secteurs géographiques avec K-Means,
puis optimise chaque secteur indépendamment.
40 secondes de calcul. Facteur 10 — battre ce profil donne 10 fois plus de points.

Le facteur de difficulté multiplie directement le bonus de score.
Plus le profil est fort, plus le battre est gratifiant."

---

## SLIDE 12 — L'IA APPRENANTE
⏱️ 1 minute 10 secondes

"Et maintenant la partie que je trouve la plus intéressante : l'IA qui apprend.

Le problème : quel profil choisir selon la situation ?
Express par temps clair, Écolo si on veut minimiser le CO₂, Championne (Zones) pour faire le meilleur score ?
Ça dépend du contexte — météo, nombre de clients, incidents, budget.

On a construit un modèle qui apprend de chaque résolution passée.
À chaque fois qu'une mission est optimisée, on stocke le contexte, le profil utilisé, et la qualité du résultat.

La prochaine fois qu'on a un contexte similaire —
pluie, 30 clients, 2 incidents —
le modèle regarde ce qui a fonctionné dans des situations proches
et recommande le profil le plus adapté.

Pourquoi pas un réseau de neurones ?
Parce qu'on a 10 à 100 résolutions, pas des milliers.
Un réseau de neurones aurait besoin de beaucoup plus de données pour être fiable.

Notre modèle bayésien fonctionne dès 8 exemples.
Il est interprétable — on sait exactement pourquoi il recommande tel profil.
Et il pèse moins de 10 kilooctets.
Si un contexte est complètement nouveau, il revient prudemment à la moyenne globale plutôt que d'extrapoler."

---

## SLIDE 13 — RÉSULTATS
⏱️ 50 secondes

"Les résultats.

On compare toujours contre une baseline naïve :
livrer les clients dans l'ordre, sans aucune optimisation.

Le solveur IA réduit le temps de tournée de 36.7%.
La distance baisse de 36.1%.
Les émissions CO₂ diminuent de 15 à 25% selon les scénarios.
Et tout ça en moins de 30 secondes pour 50 clients.

Le score sur 100 combine 4 critères :
45% pour le gain de temps, 20% pour le CO₂, 25% pour le ratio de clients livrés, et 10% pour le budget restant.

Un fait marquant sur la robustesse du graphe :
supprimer seulement 1% des carrefours les plus importants de Paris 5ème
provoque une perte de 60% de connectivité.
Le réseau urbain est fragile sur ses points névralgiques.
C'est un résultat de l'analyse de centralité — les quelques grandes artères portent l'essentiel du trafic."

---

## SLIDE 14 — LIMITES
⏱️ 35 secondes

"Les limites.

Au-delà de 200 clients, les temps de calcul deviennent trop longs.
La solution : découpage automatique en sous-problèmes et calcul sur GPU.

L'IA apprenante souffre du cold start — sur un contexte jamais vu,
elle revient à la moyenne. L'apprentissage par renforcement serait la prochaine étape.

Le graphe est statique : il ne se met pas à jour avec les incidents routiers du moment.

Et pas encore d'app mobile native."

---

## SLIDE 15 — CONCLUSION
⏱️ 25 secondes

"En résumé.

5 sources de données ouvertes, zéro donnée propriétaire.
3 profils IA et un modèle qui apprend.
Une réduction de 36.7% du temps de livraison versus la méthode naïve.
Moins de 30 secondes de calcul.

Un pipeline complet qui va de la donnée brute OpenStreetMap
jusqu'à une interface web jouable, avec de vraies contraintes, sur de vraies villes.

Je suis prêt pour vos questions."

---

---

# QUESTIONS — RÉPONSES COURTES

---

**"Pourquoi OR-Tools plutôt que votre propre solveur ?"**
"OR-Tools est la référence open-source pour le VRP, utilisée en production par de grandes entreprises.
Notre valeur ajoutée c'est l'orchestration — les profils, l'IA apprenante —
pas la réimplémentation d'un solveur qu'une équipe de Google a mis des années à construire."

---

**"A* garantit vraiment l'optimum ?"**
"Oui, parce que l'estimation qu'il utilise — la distance à vol d'oiseau — sous-estime toujours le temps réel.
On ne peut jamais aller plus vite qu'en ligne droite.
Cette propriété garantit qu'on ne rate jamais le chemin optimal."

---

**"Votre IA apprenante c'est vraiment de l'IA ?"**
"C'est de l'apprentissage statistique bayésien — pas un réseau de neurones, mais c'est de l'apprentissage au sens strict.
Le modèle s'améliore avec chaque résolution.
Le choix du bayésien est délibéré : on n'a pas assez de données pour le deep learning,
et le bayésien est interprétable et robuste dès 8 exemples."

---

**"Pourquoi K-Means maison et pas une bibliothèque ?"**
"Pour démontrer la maîtrise algorithmique.
C'est 50 lignes de code, et ça prouve qu'on comprend l'algorithme de l'intérieur.
Le commentaire dans le code dit explicitement : 'prouve la maîtrise algorithmique pour la soutenance'."

---

**"Les données OSM sont-elles fiables ?"**
"En zone urbaine dense comme Paris, la qualité est comparable à Google Maps pour le réseau routier.
C'est la source standard dans la communauté académique.
Pour une production réelle, on enrichirait avec des données trafic temps réel."

---

**"Scalable à plus de 200 clients ?"**
"Pas encore.
Le goulot d'étranglement c'est le calcul de la matrice de coût, qui est en O(n²).
La solution : K-Means automatique pour décomposer le problème,
et cuOpt de NVIDIA pour le calcul GPU.
C'est la première évolution à implémenter."

---

**"Que se passe-t-il si OpenStreetMap est indisponible ?"**
"On a un système de cache.
Si le graphe de la zone a déjà été téléchargé, on utilise la version en cache.
Pour les noms des commerces, on génère des noms procéduralement.
Pour les données CO₂, on bascule sur des constantes locales.
Aucune API externe n'est critique."
