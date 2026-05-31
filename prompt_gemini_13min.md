# PROMPT GEMINI — SOUTENANCE "OPÉRATION NOËL"
# Présentation 13 minutes — 16 slides

---

## INSTRUCTIONS POUR GEMINI

Crée une présentation professionnelle de **16 slides** pour une soutenance de **13 minutes**.

**Sujet :** Opération Noël — Plateforme web d'optimisation de tournées de livraison nocturnes, basée sur les graphes, l'Open Data et l'IA.

**Audience :** Jury universitaire (niveau Master / Licence pro).

**Ton :** Clair, pédagogique, accessible. Pas trop technique. Les slides doivent être compréhensibles par quelqu'un qui ne code pas.

**Style visuel :**
- Fond : bleu nuit profond `#0D1B2A` (slides techniques) ou blanc cassé `#FAFAFA` (slides légères)
- Accent principal : rouge festif `#E63946`
- Accent secondaire : or `#FFD700` pour les chiffres clés et formules
- Texte : blanc sur fond sombre, gris foncé `#1C1C1C` sur fond clair
- Police : Inter Bold pour les titres, Inter Regular pour le corps
- Code : fond `#1E1E2E`, police monospace, si utilisé garder court
- Icônes : Lucide ou Material Design Icons
- Chaque slide : bandeau coloré en haut indiquant la section, numéro de slide en bas
- Élément récurrent discret : traîneau + réseau de nœuds en filigrane

**Couleurs par section :**
- Intro : bleu `#1565C0`
- Site & données : vert `#2E7D32`
- Graphes & solveur : orange `#E65100`
- IA : rouge `#C62828`
- Résultats : or `#F57F17`

---

## SLIDE 1 — TITRE
⏱️ 20 secondes

**Titre (grand, centré) :**
```
Opération Noël ✦
```

**Sous-titre :**
```
Optimiser des tournées de livraison nocturnes
grâce aux graphes, à l'Open Data et à l'IA
```

**Bas de slide :**
```
Graphes & Open Data — Soutenance de projet — Mai 2026
```

**Visuel :**
- Image de fond : vue aérienne nocturne de Paris, lumières orangées, routes lumineuses
- Superposé : réseau de nœuds et arêtes, style graphe, semi-transparent, bleu électrique
- Coin bas droit : traîneau de Noël flat design

---

## SLIDE 2 — PLAN
⏱️ 15 secondes

**Titre :** Plan

**Contenu (liste simple, grande police) :**
```
1. Contexte & problème à résoudre
2. Le site — fonctionnalités et données
3. Les graphes & le solveur
4. L'intelligence artificielle
5. Résultats & limites
```

**Visuel :** Liste avec puces rondes colorées (une couleur par section)

---

## SLIDE 3 — CONTEXTE : LE PROBLÈME
⏱️ 50 secondes — Section : INTRO

**Titre :** Un problème impossible à résoudre à la main

**Contenu (3 blocs côte à côte) :**

Bloc 1 :
```
🎄 La situation
Une nuit pour tout livrer.
Plusieurs véhicules.
Des clients avec des créneaux précis.
Un budget limité.
Une météo incertaine.
```

Bloc 2 :
```
⚠️ Pourquoi c'est difficile
Problème NP-difficile :

10 clients  →  3 600 000 tournées possibles
20 clients  →  2 400 000 000 000 000 000

Impossible de tester toutes les options.
```

Bloc 3 :
```
✦ Notre approche
→ Modéliser la ville comme un graphe
→ Calculer les meilleurs chemins
→ Optimiser avec un solveur + IA
→ Comparer humain vs machine
```

**Visuel :** Illustration centrale d'un graphe de ville avec des points de livraison colorés, flèches montrant différentes routes possibles

---

## SLIDE 4 — LE SITE : CE QU'ON PEUT FAIRE
⏱️ 55 secondes — Section : SITE & DONNÉES

**Titre :** Un site web jouable et éducatif

**Contenu (4 cartes en grille 2×2) :**

```
🎯 Campagne guidée
Missions progressives sur une vraie carte.
On livre des colis, on choisit ses routes,
on reçoit un score sur 100.
```

```
⚔️ Versus — Humain vs IA
Duel en temps réel contre l'IA
sur la même carte et les mêmes données.
Qui livre le plus vite ?
```

```
🗺️ Explorer les algorithmes
Visualiser Dijkstra et A* s'exécuter
pas à pas sur la carte.
Comprendre comment fonctionne
un algorithme de chemin.
```

```
🏆 Leaderboard
Classement global et entre amis.
Scores vérifiés côté serveur
pour éviter la triche.
```

**Visuel :** Aperçu stylisé d'une carte Leaflet avec des pins de livraison et des routes tracées

---

## SLIDE 5 — PARCOURS UTILISATEUR
⏱️ 45 secondes — Section : SITE & DONNÉES

**Titre :** Comment se déroule une mission ?

**Contenu : frise chronologique horizontale, 5 étapes :**

```
[1. Choisir sa mission]
Zone, nombre de clients (8 à 200),
météo, budget, incidents éventuels

       ↓

[2. La carte se génère]
Le graphe de la ville est téléchargé
en temps réel depuis OpenStreetMap.
De vrais noms de commerces apparaissent.

       ↓

[3. On livre]
À chaque étape, 3 options de route
sont proposées (calculées par A*).
Stats en direct : temps, distance, CO₂.

       ↓

[4. Résultats & débrief]
Score sur 100.
Comparaison avec la solution IA.
Analyse CO₂. Amélioration possible.

       ↓

[5. Leaderboard]
Score soumis et classé
parmi tous les joueurs.
```

**Visuel :** Frise avec bulles numérotées et flèches, fond légèrement sombre

---

## SLIDE 6 — LES DONNÉES OPEN DATA
⏱️ 1 minute 15 secondes — Section : SITE & DONNÉES

**Titre :** 5 sources de données ouvertes — zéro données propriétaires

**Contenu (5 cartes horizontales) :**

```
🗺️ OpenStreetMap
Le graphe routier de la ville.
Nœuds = intersections. Arêtes = rues.
Paris 5ᵉ : 2 500 nœuds, 6 000 arêtes.
Gratuit · Mondial · Mis à jour en continu
```

```
📍 Overpass API (OSM)
Les vrais noms des commerces et restaurants.
→ Des points de livraison réalistes.
Fallback automatique si indisponible.
```

```
🌤️ Open-Meteo
Météo en temps réel.
Impact direct sur les temps de trajet :
Pluie × 1.35 — Neige × 1.80 — Orage × 2.0
Sans clé API, sans inscription.
```

```
🛰️ OpenTopoData (NASA SRTM)
Altitude par coordonnées GPS.
Résolution 90m — données satellite NASA.
Corrige les temps selon la pente des rues.
```

```
🌿 ADEME Impact CO₂
API officielle du gouvernement français.
Facteurs CO₂ par mode de transport :
Voiture 120g/km · Vélo 8g/km · Marche 0g/km
Données légalement référençables.
```

**Visuel :** 5 cartes avec icône, titre en gras, contenu en dessous. Fond légèrement coloré par carte.

---

## SLIDE 7 — COMMENT LA DONNÉE EST TRANSFORMÉE
⏱️ 50 secondes — Section : SITE & DONNÉES

**Titre :** De la donnée brute à la matrice de coût

**Contenu : pipeline simplifié en 4 étapes (vertical) :**

```
        ┌──────────────────────────────────┐
        │  Téléchargement du graphe OSM    │
        │  + météo + CO₂ ADEME             │
        └─────────────┬────────────────────┘
                      │
        ┌─────────────▼────────────────────┐
        │  Nettoyage du graphe             │
        │  Garder uniquement les rues      │
        │  où on peut aller ET revenir     │
        └─────────────┬────────────────────┘
                      │
        ┌─────────────▼────────────────────┐
        │  Calcul des coûts par rue        │
        │  → Temps de trajet               │
        │  → Émissions CO₂                 │
        │  → Score de risque               │
        └─────────────┬────────────────────┘
                      │
        ┌─────────────▼────────────────────┐
        │  Matrice de coût finale          │
        │  55% temps · 20% distance        │
        │  15% CO₂ · 10% risque            │
        │  Stockée en cache (×30 plus vite)│
        └──────────────────────────────────┘
```

**Pourquoi une matrice ?**
```
Pour que le solveur puisse comparer
le coût de n'importe quel trajet
entre n'importe quels deux points
en une seule lecture.
```

---

## SLIDE 8 — LE GRAPHE : C'EST QUOI ?
⏱️ 55 secondes — Section : GRAPHES & SOLVEUR

**Titre :** Le graphe — représenter la ville

**Contenu (2 blocs côte à côte) :**

Bloc gauche — Définition simple :
```
Un graphe, c'est un ensemble de
nœuds reliés par des arêtes.

Ici :
  Nœud  = intersection de rues
  Arête = segment de rue
  Poids = temps de trajet (secondes)

Le graphe est orienté :
  les rues ont un sens de circulation.

Le graphe est annoté :
  chaque rue connaît sa vitesse légale,
  ses émissions CO₂, son niveau de risque.
```

Bloc droit — Paris 5ᵉ en chiffres :
```
Graphe brut OSM :
→ ~3 200 nœuds
→ ~7 500 arêtes

Après nettoyage :
→ 2 500 nœuds
→ 6 000 arêtes

3 graphes selon le mode :
🚗 Voiture  (jusqu'à 110 km/h)
🚲 Vélo     (10 à 25 km/h)
🚶 Marche   (3 à 6.5 km/h)
```

**Pourquoi nettoyer ?**
```
Certaines rues en sens unique créent des
"impasses directionnelles" : on peut y aller
mais pas en revenir. On les élimine pour
garantir que toutes les livraisons sont faisables.
```

**Visuel :** Illustration côte à côte : carte réelle Paris 5ᵉ à gauche, graphe stylisé à droite (nœuds bleus, arêtes blanches)

---

## SLIDE 9 — DIJKSTRA ET A* — TROUVER LE MEILLEUR CHEMIN
⏱️ 1 minute — Section : GRAPHES & SOLVEUR

**Titre :** Trouver le plus court chemin — Dijkstra et A*

**Contenu (2 colonnes) :**

Colonne gauche — Dijkstra :
```
📐 Dijkstra
"Explorer du plus proche au plus loin"

→ Part du point de départ
→ Explore progressivement
  tous les nœuds du graphe
→ Garantit le chemin optimal
→ Explore dans toutes les directions

On l'utilise pour :
Calculer la distance entre
TOUS les paires de points
(génération des matrices)
```

Colonne droite — A* :
```
⭐ A* (A étoile)
"Explorer en direction du but"

→ Comme Dijkstra, mais guidé
  par une estimation de la distance
  restante (distance vol d'oiseau)
→ Garantit aussi le chemin optimal
→ Explore 20 à 40% de nœuds en moins

On l'utilise pour :
Calculer les 3 options de route
proposées au joueur en temps réel
```

**Formule A* (grande, au centre) :**
```
Coût total estimé = Coût déjà parcouru + Estimation distance restante
                     (réel, précis)         (vol d'oiseau ÷ vitesse max)
```

**Visuel :** Deux illustrations côte à côte montrant l'exploration — Dijkstra = cercle complet, A* = demi-cercle orienté vers le but

---

## SLIDE 10 — LE SOLVEUR VRP
⏱️ 55 secondes — Section : GRAPHES & SOLVEUR

**Titre :** Le solveur — optimiser toutes les tournées d'un coup

**Contenu :**

Bloc 1 — Le problème à résoudre :
```
VRP = Vehicle Routing Problem

Données :
  N clients à livrer
  K véhicules disponibles
  Chaque client a une fenêtre horaire
  Chaque véhicule a une capacité max
  Horizon total : 8 heures (une nuit)

Objectif :
  Trouver les routes qui minimisent
  le temps total, la distance et le CO₂
  tout en respectant toutes les contraintes.
```

Bloc 2 — Comment ça marche :
```
On utilise Google OR-Tools,
la bibliothèque de référence open-source
pour ce type de problème.

Fonctionnement en 2 phases :
  1. Construire une solution de départ
     en quelques secondes (greedy)
  2. L'améliorer en boucle
     jusqu'à la limite de temps

Si un client est impossible à livrer :
  → Il est "abandonné" avec une pénalité
  → Le solveur reste valide
  → Le score est impacté
```

Bloc 3 — Performance :
```
50 clients optimisés en < 30 secondes.
Gain vs tournée naïve : −36% de temps.
```

**Visuel :** Illustration d'une carte avec plusieurs routes colorées (une par véhicule) convergeant vers un dépôt central

---

## SLIDE 11 — LES 3 PROFILS IA
⏱️ 1 minute — Section : IA

**Titre :** 3 profils IA — 3 façons d'optimiser

**Contenu (3 grandes cartes côte à côte) :**

```
🚀 EXPRESS
"Rush urbain"

Objectif : Livrer le plus vite possible.
Stratégie : Aggressive, peu de marge.
Temps de calcul : 12 secondes.

Profil idéal par temps clair,
peu d'incidents, mission urgente.

Difficulté à battre : ×2
```

```
🌿 ÉCOLO
"Trajectoires sobres"

Objectif : Minimiser les kilomètres
           et les émissions CO₂.
Stratégie : Optimisation de distance,
            exploration plus large.
Temps de calcul : 18 secondes.

Profil idéal pour les missions
où l'empreinte carbone compte.

Difficulté à battre : ×3
```

```
🗺️ CHAMPIONNE (ZONES)
"Architecture hybride"

Objectif : La meilleure solution possible.
Stratégie : Découpe d'abord la ville
            en secteurs (K-Means),
            puis optimise chaque secteur.
Temps de calcul : 40 secondes.

Profil le plus difficile à battre.

Difficulté à battre : ×10
```

**Légende :**
```
La difficulté à battre multiplie le bonus de score.
Battre Championne (Zones) rapporte 10× plus que battre Express.
```

**Visuel :** 3 cartes distinctes, chacune avec une couleur dominante (rouge, vert, or), icône et stats visibles

---

## SLIDE 12 — L'IA APPRENANTE
⏱️ 1 minute 10 secondes — Section : IA

**Titre :** L'IA qui apprend — choisir le bon profil automatiquement

**Contenu :**

Bloc 1 — Le problème :
```
❓ Quel profil choisir ?

Le profil optimal dépend du contexte :
→ Météo (pluie, neige, orage)
→ Nombre de clients
→ Y a-t-il des incidents ?
→ Quel est le budget disponible ?

Un humain ne peut pas tout mémoriser.
```

Bloc 2 — La solution (schéma) :
```
Chaque résolution lancée sur la plateforme
         │
         ▼
Contexte + profil utilisé + qualité du résultat
         │
         ▼
Stockés dans un modèle léger (fichier JSON < 10 Ko)
         │
         ▼
Prochaine fois, même contexte
         │
         ▼
"D'après mes données, le meilleur profil ici c'est Écolo"
```

Bloc 3 — Pourquoi pas du deep learning :
```
✅ Notre choix : inférence bayésienne

→ Fonctionne dès 8 exemples
   (pas besoin de milliers de données)
→ Interprétable : on sait pourquoi
   il recommande tel ou tel profil
→ Léger : pas de GPU, pas de serveur IA
→ Robuste : si contexte inconnu,
   revient à la moyenne globale

Un réseau de neurones aurait besoin
de 10 000× plus de données pour fonctionner.
```

**Visuel :** Schéma en entonnoir — plusieurs missions en entrée, modèle au centre, recommandation en sortie

---

## SLIDE 13 — RÉSULTATS
⏱️ 50 secondes — Section : RÉSULTATS

**Titre :** Ce qu'on obtient concrètement

**Contenu (3 grands chiffres + tableau) :**

**Chiffres clés (grand format, centré) :**
```
−36.7%          −36.1%          < 30 sec
de temps        de distance     pour optimiser
vs tournée      vs tournée      50 clients
naïve           naïve
```

**Tableau comparatif :**

| | Tournée naïve | Solution IA | Gain |
|---|---|---|---|
| Temps total | Référence | −36.7% | ✅ |
| Distance | Référence | −36.1% | ✅ |
| Émissions CO₂ | Référence | −15% à −25% | ✅ |
| Temps de calcul | — | < 30 secondes | ✅ |

**Formule de score :**
```
Score (sur 100) =
  45% × gain de temps
+ 20% × réduction CO₂
+ 25% × clients livrés
+ 10% × budget restant
+ bonus météo & incidents
```

**Robustesse du graphe (fait marquant) :**
```
Supprimer 1% des carrefours les plus importants
= 60% de connectivité perdue.
Le réseau urbain est fragile aux points névralgiques.
```

---

## SLIDE 14 — LIMITES & AMÉLIORATIONS
⏱️ 35 secondes — Section : RÉSULTATS

**Titre :** Limites et pistes d'amélioration

**Contenu (2 colonnes) :**

Colonne gauche :
```
⚠️ Ce qu'on ne fait pas encore

→ Au-delà de 200 clients :
  les calculs prennent trop de temps

→ Pas de données trafic temps réel
  (Waze, TomTom...)

→ L'IA apprenante part de zéro
  sur un nouveau contexte

→ Pas d'app mobile native
```

Colonne droite :
```
🚀 Ce qu'on pourrait faire

→ Calcul sur GPU (cuOpt, NVIDIA)
  pour des milliers de clients

→ Apprentissage par renforcement :
  l'IA adapte les routes en cours
  de livraison en temps réel

→ Étendre à d'autres villes
  (le graphe se génère partout
  dans le monde via OSM)

→ Véhicules électriques :
  autonomie + bornes de recharge
```

---

## SLIDE 15 — CONCLUSION
⏱️ 25 secondes

**Titre :** Ce qu'on a construit

**Contenu (grands chiffres, centré) :**
```
5   sources Open Data — zéro donnée propriétaire
3   profils IA + 1 IA apprenante
3   algorithmes de graphes (Dijkstra, A*, K-Means)
40+ tests automatisés
−36.7% de temps vs la méthode naïve
< 30 secondes de calcul

Un pipeline complet :
Open Data  →  Graphe  →  Solveur  →  IA  →  Site web jouable
```

**Bas de slide :**
```
Questions ?
```

**Visuel :** Même carte nocturne de Paris que slide 1 — cohérence visuelle. Chiffres en or sur fond sombre.

---

## SLIDE 16 — FAQ / QUESTIONS
⏱️ Slide de secours pendant les questions

**Titre :** Questions fréquentes

**Contenu (4 mini-blocs) :**
```
Pourquoi OR-Tools ?
Open-source, au niveau des solveurs commerciaux,
zéro coût de licence.
```
```
Pourquoi bayésien et pas deep learning ?
10 à 100 données disponibles, pas des milliers.
Le bayésien fonctionne dès 8 exemples.
```
```
Données OSM fiables ?
Qualité comparable à Google Maps en zone urbaine.
Standard académique reconnu.
```
```
Scalable à 1000 clients ?
Pas encore. La limite actuelle est 200.
Solution : découpage K-Means + calcul GPU.
```

---

## NOTES DE STYLE GLOBALES POUR GEMINI

- Garder le texte court sur chaque slide : maximum 6 lignes par bloc
- Privilégier les icônes et schémas sur le texte dense
- Les formules mathématiques : les écrire en langage naturel d'abord, formule ensuite
- Pas de code source dans les slides (sauf si demandé explicitement)
- Chaque slide doit pouvoir se lire en 10 secondes
- Animations recommandées : apparition progressive des blocs (pas de transitions flashy)
- Images libres de droits : Unsplash pour Paris nocturne, Flaticon pour les icônes
