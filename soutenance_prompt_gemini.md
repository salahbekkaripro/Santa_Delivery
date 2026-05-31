# PROMPT GEMINI — SOUTENANCE "OPÉRATION NOËL"
# Graphes, Open Data, IA & Optimisation — 20 minutes

---

## ──────────────────────────────────────────────
## INSTRUCTIONS GÉNÉRALES POUR GEMINI
## ──────────────────────────────────────────────

Tu dois créer une présentation professionnelle de **26 slides** pour une soutenance universitaire de **20 minutes**.

**Sujet :** Opération Noël — Plateforme web d'optimisation de tournées de livraison nocturnes basée sur les graphes, l'Open Data et l'Intelligence Artificielle.

**Audience :** Jury universitaire (niveau Master / Licence pro) et professionnels techniques.

**Ton :** Professionnel, rigoureux, pédagogique mais vivant. Pas trop formel.

**Palette de couleurs recommandée :**
- Fond : bleu nuit profond (#0D1B2A) ou blanc cassé (#FAFAFA)
- Accent principal : rouge/orange festif (#E63946) pour titres et éléments clés
- Accent secondaire : or/doré (#FFD700) pour les formules et highlights
- Texte : blanc (#FFFFFF) sur fonds sombres, gris foncé (#1C1C1C) sur fonds clairs
- Code : fond `#1E1E2E`, texte vert/cyan

**Police recommandée :**
- Titres : Inter Bold ou Montserrat Bold
- Corps : Inter Regular ou Source Sans Pro
- Code : JetBrains Mono ou Fira Code

**Icônes :** Utiliser des icônes Lucide, Heroicons ou Material Design Icons.

**Éléments visuels récurrents :**
- Logo/icon : traîneau de Noël + étoile + graphe de réseau (fond de slide discret)
- Barre de progression en bas de chaque slide (1/26 à 26/26)
- Section indicator en haut à droite (ex : "LA DONNÉE", "GRAPHES", "IA"...)

---

## ──────────────────────────────────────────────
## SLIDE 1 — PAGE DE TITRE
## Durée : 30 secondes
## ──────────────────────────────────────────────

**Titre principal (grande taille, centré) :**
```
Opération Noël ✦
```

**Sous-titre :**
```
Plateforme d'optimisation de tournées de livraison
par Graphes, Open Data et Intelligence Artificielle
```

**Bandeau bas gauche :**
```
Graphes & Open Data — Soutenance de projet
Mai 2026
```

**Visuel :**
- Image de fond : carte stylisée de Paris la nuit, vue aérienne, avec des lumières orange et des routes lumineuses (style "city lights from space" ou rendu Mapbox dark).
- Par-dessus : superposer un réseau de nœuds et arêtes (graphe stylisé, semi-transparent, couleur bleu électrique).
- En bas à droite : un traîneau de Noël pixel art ou flat design.

**Notes orales (ce que dit le présentateur) :**
> "Bonjour à tous. Je vais vous présenter Opération Noël — un projet qui part d'une question simple : comment optimiser une tournée de livraison en une nuit, à travers une ville réelle, avec de vraies contraintes ? Nous avons construit pour ça une plateforme web complète qui combine des données ouvertes, de la théorie des graphes et de l'intelligence artificielle."

---

## ──────────────────────────────────────────────
## SLIDE 2 — PLAN DE LA PRÉSENTATION
## Durée : 20 secondes
## ──────────────────────────────────────────────

**Titre :** Plan

**Contenu (liste numérotée, 2 colonnes) :**

Colonne gauche :
```
1. Contexte & problématique
2. Présentation fonctionnelle du site
3. Architecture technique
4. La Donnée & Open Data
5. Graphes & Algorithmes
```

Colonne droite :
```
6. Intelligence Artificielle
7. Choix techniques & arbitrages
8. Résultats & benchmarks
9. Limites & améliorations futures
10. FAQ
```

**Visuel :**
- Chaque numéro dans un cercle coloré (couleurs différentes par section).
- Ligne de connexion discrète entre les deux colonnes.

**Notes orales :**
> "Voici notre plan pour ces 20 minutes. On va aller du fonctionnel au technique, de la donnée brute aux algorithmes, en passant par l'IA."

---

## ──────────────────────────────────────────────
## SLIDE 3 — CONTEXTE & PROBLÉMATIQUE
## Section : INTRODUCTION
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Le problème du Père Noël est NP-difficile

**Contenu principal (3 blocs côte à côte) :**

Bloc 1 — "Le contexte" :
```
🎄 Une nuit de Noël
→ Des dizaines de livraisons à effectuer
→ Des contraintes de temps (fenêtres horaires)
→ Plusieurs véhicules disponibles
→ Un budget limité
→ Une météo variable
```

Bloc 2 — "La complexité" :
```
⚠️ Problème NP-difficile
→ Pour n clients :
   → Nombre de tournées possibles = n!
   → n=10 → 3,6 millions d'options
   → n=20 → 2,4 × 10¹⁸ options
→ Un humain ne peut pas trouver
  l'optimum à la main
```

Bloc 3 — "Notre réponse" :
```
✦ Opération Noël
→ Construire le graphe de la ville
  (données réelles OpenStreetMap)
→ Calculer les meilleures routes
  (algorithmes Dijkstra / A*)
→ Optimiser les tournées
  (solveur VRP + IA)
→ Comparer humain vs machine
```

**Visuel recommandé :**
- Diagramme central : nœuds et arêtes d'un graphe de ville stylisé (Paris).
- Flèches animées montrant plusieurs routes possibles, puis une seule route "optimale" mise en surbrillance.
- Icône chronomètre + neige en bas à gauche.

**Notes orales :**
> "Le problème du Père Noël est en réalité une variante du Problème du Voyageur de Commerce — VRP ou Vehicle Routing Problem — qui est NP-difficile. Aucun algorithme ne peut garantir l'optimum en temps polynomial. Notre approche : construire le graphe de la ville à partir de données réelles, et utiliser des heuristiques puissantes pour approcher cet optimum en moins de 30 secondes."

---

## ──────────────────────────────────────────────
## SLIDE 4 — OBJECTIFS DU PROJET
## Section : INTRODUCTION
## Durée : 40 secondes
## ──────────────────────────────────────────────

**Titre :** Objectifs du projet

**Contenu (4 cartes en grille 2×2) :**

Carte 1 — Éducatif :
```
📚 Apprendre en jouant
Visualiser Dijkstra, A* et
le solveur en action sur
une vraie carte de ville
```

Carte 2 — Technique :
```
⚙️ Résoudre un VRP réel
Construire un pipeline complet :
Open Data → Graphe → Matrices
→ IA → Optimisation → Résultat
```

Carte 3 — Comparatif :
```
🤖 Humain vs IA
Duel en temps réel :
le joueur contre le profil IA
sur le même graphe, les mêmes données
```

Carte 4 — Écologique :
```
🌿 Données officielles ADEME
Calculer et minimiser les
émissions CO₂ par tournée
avec des données gouvernementales
```

**Notes orales :**
> "Notre projet poursuit 4 objectifs : éducatif d'abord — on veut que l'utilisateur comprenne intuitivement ce que font les algorithmes. Technique ensuite — on résout un vrai problème de VRP sur des données réelles. Comparatif — le mode versus permet de mesurer la performance humaine face à l'IA. Et écologique — on intègre les données CO₂ officielles de l'ADEME."

---

## ──────────────────────────────────────────────
## SLIDE 5 — FONCTIONNALITÉS — VUE GLOBALE
## Section : SITE WEB
## Durée : 50 secondes
## ──────────────────────────────────────────────

**Titre :** Le site web — 6 espaces fonctionnels

**Contenu (sitemap visuel) :**

Générer un diagramme sitemap avec les nœuds suivants (disposés en arbre) :

```
[Accueil / Landing]
       │
  ┌────┴─────┬──────────┬───────────┬──────────────┐
[Campagne] [Solver] [Versus] [Explore] [Leaderboard]
  │                   │
[Mission]         [Duel Live]
  │
[Debrief]
```

**Description de chaque espace (liste à droite du diagramme) :**

```
🏠 Accueil       — Introduction gamifiée, sélection du mode
🎯 Campagne      — Missions guidées avec progression et scoring
⚙️ Solver        — Mode libre : tester tous les paramètres IA
⚔️ Versus        — Duel humain vs IA en temps réel
🗺️ Explore       — Visualiser Dijkstra et A* pas à pas sur la carte
🏆 Leaderboard   — Classements global, hebdo, amis
📊 Debrief       — Analyse post-mission : score, CO₂, 2-opt
```

**Visuel :**
- Diagramme en arbre, chaque nœud dans un rectangle arrondi coloré.
- Icônes distinctes par section.

**Notes orales :**
> "Le site propose 6 espaces fonctionnels. Le plus riche est la campagne avec ses missions guidées. Le mode Explore permet de visualiser en direct les algorithmes de graphes. Et le versus propose un duel en temps réel entre le joueur et l'IA."

---

## ──────────────────────────────────────────────
## SLIDE 6 — PARCOURS UTILISATEUR (MODE CAMPAGNE)
## Section : SITE WEB
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Parcours utilisateur — Mode Campagne guidé

**Contenu (timeline horizontale en 6 étapes) :**

```
[1. Inscription]
→ Création de compte
   Email + mot de passe hashé
   (SHA-256 + PBKDF2, 120 000 itérations)

[2. Sélection de mission]
→ Choix zone géographique
   Nombre de clients (8 à 200)
   Budget, météo, incidents

[3. Génération de la carte]
→ Téléchargement OSM automatique
   Graphe + matrice de coûts générés
   Points POI réels (Overpass API)

[4. Livraison guidée]
→ L'utilisateur choisit l'itinéraire
   3 options de route proposées par le solveur
   Stats live (temps, distance, CO₂, budget)

[5. Résultats & Debrief]
→ Score calculé sur 100
   Comparaison avec la solution IA
   Amélioration 2-opt suggérée

[6. Leaderboard]
→ Score soumis avec hash d'intégrité
   Classement mis à jour en temps réel
```

**Visuel recommandé :**
- Frise chronologique horizontale avec des flèches entre chaque étape.
- Chaque étape dans une bulle numérotée.
- Capture d'écran simulée (wireframe) du mission workspace à droite.

**Notes orales :**
> "Le parcours utilisateur est conçu pour être progressif. L'utilisateur crée une mission, le backend télécharge le graphe OpenStreetMap en direct, génère les matrices de coût, puis guide l'utilisateur pas à pas. À chaque point de livraison, trois options de route lui sont proposées, calculées en temps réel par A* sur le graphe."

---

## ──────────────────────────────────────────────
## SLIDE 7 — MODES VERSUS & SOLVER LIBRE
## Section : SITE WEB
## Durée : 40 secondes
## ──────────────────────────────────────────────

**Titre :** Modes spéciaux : Versus & Solver libre

**Contenu (2 blocs côte à côte) :**

Bloc gauche — Versus :
```
⚔️ Mode Versus (1v1 en temps réel)

• 3 modes d'accès :
  → File d'attente publique (queue)
  → Match privé (code de salon)
  → Invitation directe (lien)

• 3 maps préconfigurées :
  → Paris Rush (22 clients, ciel dégagé)
  → Berlin Rain Clash (28 clients, pluie)
  → Montreal Snow Battle (34 clients, neige + incidents)

• Synchronisation via WebSocket
• Le gagnant est celui qui livre
  le plus de clients en moins de temps

• Preuve technique : websocket endpoint
  /ws/versus/{match_id}
```

Bloc droit — Solver :
```
⚙️ Mode Solver libre

• Choisir n'importe quel profil IA :
  Express, Écolo, Prudent, Opportuniste,
  Agressive, Championne, Championne (Zones)

• Ajuster les paramètres avancés :
  → Nombre de véhicules
  → Budget
  → Météo
  → Incidents actifs
  → Mode de transport (voiture, vélo, marche)

• Observer la solution optimisée
  sur la carte en temps réel

• Preuve technique : endpoint
  POST /api/missions/{id}/solve
```

**Notes orales :**
> "Le mode Versus utilise des WebSockets pour synchroniser les deux joueurs en temps réel sur la même mission. Le mode Solver libre permet de tester librement tous les profils IA et d'observer directement les effets sur la solution."

---

## ──────────────────────────────────────────────
## SLIDE 8 — ARCHITECTURE TECHNIQUE GLOBALE
## Section : ARCHITECTURE
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Architecture technique — Vue d'ensemble

**Contenu : Schéma d'architecture à générer (diagramme en couches) :**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                     │
│  React 18 · TypeScript · Leaflet.js · Mapbox GL · Recharts   │
│  Pages : / · /campaign · /mission · /solver · /versus        │
│               · /explore · /leaderboard                      │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTP REST + WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI / Python)                │
│  services.py (5 923 lignes)  ·  routing_payloads.py          │
│  main.py (routes API)  ·  repository.py (SQLite)             │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Solver     │  │  Générateur  │  │  IA & Apprentissage │  │
│  │  OR-Tools   │  │  OSMnx/Graph │  │  7 profils + tuner  │  │
│  │  VRPTW      │  │  Matrices    │  │  Bayésien léger     │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐
│   SQLite    │ │  Fichiers    │ │   APIs Externes       │
│ (players,   │ │  .npy / .json│ │  OpenStreetMap (OSM)  │
│ leaderboard,│ │  .graphml    │ │  Open-Meteo (météo)   │
│ versus,     │ │  cache/      │ │  ADEME Impact CO₂     │
│ social)     │ │  core_data/  │ │  OpenTopoData (SRTM)  │
└─────────────┘ └──────────────┘ └──────────────────────┘
```

**Notes orales :**
> "L'architecture suit le pattern classique frontend/backend découplés. Le frontend Next.js communique avec l'API FastAPI via REST pour les missions et WebSocket pour le versus. Le backend orchestre trois moteurs : le solver OR-Tools, le générateur de graphes basé sur OSMnx, et le module d'apprentissage IA. Tout repose sur des données ouvertes — OpenStreetMap, Open-Meteo, ADEME — sans aucune dépendance à des API propriétaires payantes."

---

## ──────────────────────────────────────────────
## SLIDE 9 — STACK TECHNIQUE DÉTAILLÉ
## Section : ARCHITECTURE
## Durée : 30 secondes
## ──────────────────────────────────────────────

**Titre :** Stack technique

**Contenu (tableau 2 colonnes) :**

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| Frontend | Next.js 14 + TypeScript | SSR, routing, typage fort |
| Cartographie | Leaflet.js + Mapbox GL 3.21 | Open-source + perf GPU |
| Graphiques | Recharts 3.8 | Léger, composants React |
| Authentification | NextAuth + PBKDF2 | Standard industriel |
| Backend | FastAPI (Python 3.10+) | Async, typé, performant |
| Graphes | OSMnx 2.0 + NetworkX | Accès OSM direct |
| Solveur | Google OR-Tools | Meilleur VRP open-source |
| Matrices | NumPy (.npy) | 30x plus rapide que JSON |
| Base de données | SQLite | Léger, ACID, sans serveur |
| Tests | Pytest + Playwright (E2E) | 40+ tests, couverture ≥95% |
| Météo | Open-Meteo API | Gratuit, sans clé API |
| CO₂ | ADEME Impact CO₂ | Données officielles françaises |
| Élévation | OpenTopoData SRTM90m | NASA, satellite, 90m résolution |

**Notes orales :**
> "Toute la stack est open-source et gratuite. Le choix de FastAPI pour le backend s'explique par sa performance asynchrone et son typage Python natif. NumPy en format .npy est 30 fois plus rapide que JSON pour les matrices de coût — un choix crucial quand on manipule des matrices 180×180."

---

## ──────────────────────────────────────────────
## SLIDE 10 — 5 SOURCES OPEN DATA
## Section : LA DONNÉE
## Durée : 1 minute 30 secondes
## ──────────────────────────────────────────────

**Titre :** 5 sources de données ouvertes

**Contenu (5 cartes horizontales, chacune avec icône + nom + rôle + exemple) :**

Carte 1 :
```
🗺️ OpenStreetMap (via OSMnx 2.0)
Rôle : Graphe routier de la ville
Format : GraphML (.graphml)
Fichier : core_data/paris5.graphml
Exemple : Paris 5ᵉ → 2 500 nœuds, 6 000 arêtes
Accès : ox.graph_from_place("Paris 5e Arrondissement")
Gratuit · Mondial · Communautaire
```

Carte 2 :
```
📍 Overpass API (OSM POI)
Rôle : Points d'intérêt réels (shops, amenities)
= Noms de clients réalistes pour les missions
Format : JSON (Overpass QL)
Query : shops + amenities dans un rayon donné
Fallback : génération procédurale si API indisponible
Gratuit · Temps réel · Sans clé API
```

Carte 3 :
```
🌤️ Open-Meteo API
Rôle : Météo actuelle → facteur multiplicatif sur temps
Codes WMO : 0 (ciel clair) → 99 (orage violent)
Impact : facteur 1.0 (clair) à 2.0 (tempête de neige)
Exemples :
  Clear → ×1.0  |  Rain → ×1.35
  Snow → ×1.80  |  Thunderstorm → ×2.0
Sans clé API · Sans inscription
```

Carte 4 :
```
🛰️ OpenTopoData (NASA SRTM 90m)
Rôle : Données d'élévation (altitude par lat/lon)
Résolution : 90 mètres (satellite NASA)
Usage : Correction du temps de trajet selon la pente
Impact : montée = ralentissement, descente = accélération
Source : Shuttle Radar Topography Mission (NASA, 2000)
```

Carte 5 :
```
🌿 ADEME Impact CO₂ (API officielle française)
Rôle : Facteurs d'émission CO₂ par mode de transport
URL : https://impactco2.fr/api/v1/transport
Modes :
  → Voiture thermique (ID=4) : 120 g CO₂/km
  → Vélo mécanique (ID=7)   : 8 g CO₂/km
  → Marche (ID=30)           : 0 g CO₂/km
Fallback local si API indisponible
Données gouvernementales officielles
```

**Preuve code (bloc) :**
```python
# scripts/generator_engine.py — lignes 62-68
ADEME_CO2_API_URL = os.getenv(
    "NOEL_ADEME_CO2_API_URL",
    "https://impactco2.fr/api/v1/transport"
)
ADEME_TRANSPORT_ID_BY_MODE = {
    "drive": 4,   # Voiture thermique
    "bike": 7,    # Vélo mécanique
    "walk": 30,   # Marche à pied
}
```

**Notes orales :**
> "Toutes nos données sont des données ouvertes — aucune API propriétaire payante. OpenStreetMap nous fournit le graphe routier. Overpass nous donne de vrais noms de commerces pour les points de livraison. Open-Meteo nous fournit la météo en temps réel, qui influence directement les temps de trajet. ADEME nous fournit des facteurs CO₂ officiels du gouvernement français."

---

## ──────────────────────────────────────────────
## SLIDE 11 — PIPELINE ETL COMPLET
## Section : LA DONNÉE
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Pipeline de traitement de la donnée (ETL)

**Contenu : Diagramme de flux vertical (pipeline) :**

```
         ┌─────────────────────────────────────┐
         │  1. EXTRACTION (Sources Open Data)   │
         │  OSM → Graphe brut (MultiDiGraph)    │
         │  Overpass → Noms POI réels           │
         │  Open-Meteo → Conditions météo       │
         │  ADEME → Facteurs CO₂ par mode       │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  2. NETTOYAGE DU GRAPHE             │
         │  → Extraction SCC (composante        │
         │    fortement connexe la plus grande) │
         │  → Suppression boucles & doublons    │
         │  → Normalisation types de voies      │
         │    (motorway → residential → path)   │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  3. ANNOTATION DES ARÊTES           │
         │  Pour chaque arête (u, v) :          │
         │  → travel_time = longueur / vitesse  │
         │  → co2_g = (km) × facteur_mode       │
         │  → risk_score = km × facteur_voie    │
         │  → speed_kph (converti mph→kmh si /) │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  4. GÉNÉRATION DES MATRICES          │
         │  Dijkstra sur tous les paires (i,j)  │
         │  → matrix_time [n×n]                 │
         │  → matrix_dist [n×n]                 │
         │  → matrix_co2  [n×n]                 │
         │  → matrix_risk [n×n]                 │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  5. NORMALISATION ROBUSTE            │
         │  Pour chaque matrice :               │
         │  scaled[i,j] = valeur / médiane      │
         │  Infinis → 1×10⁹ (route impossible)  │
         │  Diagonale → 0 (dépôt vers lui-même) │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  6. MATRICE COMPOSITE                │
         │  composite = 0.55×time + 0.20×dist   │
         │             + 0.15×co2 + 0.10×risk   │
         └─────────────────┬───────────────────┘
                           │
         ┌─────────────────▼───────────────────┐
         │  7. STOCKAGE (Cache NumPy)           │
         │  core_data/*.npy (30× plus rapide)   │
         │  cache/api_missions/{id}/*.npy       │
         └─────────────────────────────────────┘
```

**Preuve code (bloc) :**
```python
# scripts/generator_engine.py — lignes 45-50
DEFAULT_OBJECTIVE_WEIGHTS = {
    "time":     0.55,  # Priorité maximale : temps
    "distance": 0.20,  # Distance parcourue
    "co2":      0.15,  # Empreinte carbone (ADEME)
    "risk":     0.10,  # Risque routier
}
```

**Notes orales :**
> "Le pipeline ETL comporte 7 étapes. L'étape critique est l'annotation des arêtes : pour chaque rue du graphe, on calcule le temps de trajet selon la vitesse légale, les émissions CO₂ selon le mode de transport, et un score de risque selon le type de voie. Ces données alimentent ensuite 4 matrices, normalisées par leur médiane pour éviter les effets d'échelle, puis combinées en une matrice composite pondérée."

---

## ──────────────────────────────────────────────
## SLIDE 12 — CONSTRUCTION DU GRAPHE
## Section : GRAPHES
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Construction du graphe — De OSM au graphe propre

**Contenu (2 parties : gauche = théorie, droite = exemples concrets) :**

Partie gauche — Structure du graphe :
```
Type : MultiDiGraph orienté
(chaque arête a une direction ET
 plusieurs arêtes possibles entre
 deux mêmes nœuds — voies à double sens)

Nœuds = intersections de rues
  → Attributs : latitude, longitude, osmid

Arêtes = segments de rue
  → Attributs (après annotation) :
     • length (m)
     • travel_time (s)
     • speed_kph_legal (km/h)
     • co2_g (g CO₂)
     • risk_score (sans unité)
     • highway (type de voie)
     • oneway_effective (booléen)
     • transport_mode (drive/bike/walk)

Représentation mémoire :
  → Liste d'adjacence (dict Python)
  → nx.MultiDiGraph (NetworkX)
  → Sérialisé en GraphML (XML compressé)
```

Partie droite — Exemple Paris 5ᵉ :
```
Graphe brut OSM :
→ ~3 200 nœuds
→ ~7 500 arêtes

Après nettoyage (SCC) :
→ 2 500 nœuds (−22%)
→ 6 000 arêtes (−20%)

Vitesses par type de voie :
motorway  → 110 km/h  (risque ×1.8)
primary   → 70 km/h   (risque ×1.45)
residential→ 30 km/h  (risque ×0.9)
cycleway  → 18 km/h   (risque ×0.55)
footway   → 5 km/h    (risque ×0.45)

Modes de transport :
🚗 drive  → graphe drive (vitesses voiture)
🚲 bike   → graphe bike (10-25 km/h max)
🚶 walk   → graphe walk (3-6.5 km/h max)
```

**Pourquoi la SCC ?**
```
Un graphe OSM brut contient des "culs-de-sac"
directionnels (rues à sens unique mal reliées).
Sans SCC, le solveur peut calculer un chemin
vers un nœud mais pas en revenir.
→ On extrait la plus grande composante fortement
  connexe (garantie de connectivité totale).
```

**Preuve code (bloc) :**
```python
# scripts/generator_engine.py — annotation arêtes
travel_time_s = length_m / speed_m_s
co2_g = (length_m / 1000.0) * mode_co2
risk_score = (length_m / 1000.0) * risk_base * oneway_penalty
```

**Notes orales :**
> "Le graphe est un MultiDiGraph orienté — orienté parce que les rues ont des sens de circulation, multi parce que deux nœuds peuvent être connectés par plusieurs arêtes — par exemple une rue qui a aussi une piste cyclable. On extrait la composante fortement connexe pour garantir qu'on peut aller de n'importe quel point à n'importe quel autre. Puis on annote chaque arête avec quatre métriques : temps, distance, CO₂ et risque."

---

## ──────────────────────────────────────────────
## SLIDE 13 — DIJKSTRA VS A* — ALGORITHMES DE PLUS COURT CHEMIN
## Section : GRAPHES
## Durée : 1 minute 30 secondes
## ──────────────────────────────────────────────

**Titre :** Dijkstra vs A* — Trouver le meilleur chemin

**Contenu (2 colonnes + formules + comparaison) :**

Colonne gauche — Dijkstra :
```
📐 Algorithme de Dijkstra
Complexité : O(|V|² ) naïf
             O((|V|+|E|) log |V|) avec tas

Principe :
  → Explorer les nœuds du plus proche
    au plus éloigné (BFS pondéré)
  → Maintenir un tas min (priority queue)
    avec les distances g(n)
  → Garantit l'optimum GLOBAL
  → Explore dans TOUTES les directions

Usage dans le projet :
  → Génération des matrices de coût
    (all-pairs shortest path)
  → Plus court chemin entre
    tous les paires de points
  
Fichier : scripts/ro_improvements.py:435
         (fonction dijkstra_steps)
```

Colonne droite — A* :
```
⭐ Algorithme A*
Complexité : O(|E|) dans le meilleur cas
             O(|V| log |V|) en moyenne

Principe :
  → f(n) = g(n) + h(n)
  → g(n) = coût réel depuis la source
  → h(n) = heuristique (estimation)
  → Explore en priorité les nœuds
    les plus "prometteurs" vers le but

Heuristique utilisée (admissible) :
  h(u, v) = haversine(u, v) / v_max
  
  → haversine = distance vol d'oiseau
  → v_max = 50 km/h (vitesse max)
  → Toujours ≤ temps réel (admissible)
  → Garantit donc l'optimum aussi !

Usage dans le projet :
  → Calcul des 3 options de route
    proposées en temps réel au joueur

Fichier : scripts/ro_improvements.py
         (fonction a_star ou path_options)
```

**Formule centrale (grande, bien lisible) :**
```
f(n) = g(n) + h(n)

où :
  g(n) = coût accumulé depuis le départ
  h(n) = haversine(n, but) / vitesse_max

Admissibilité : h(n) ≤ h*(n)  (toujours vrai car vol d'oiseau ≤ chemin routier)
→ Garantit l'optimalité de A*
```

**Comparaison résumée (tableau) :**

| Critère | Dijkstra | A* |
|---------|----------|-----|
| Cas d'usage | Matrices complètes | Routes en temps réel |
| Direction d'exploration | Toutes directions | Guidée vers le but |
| Nœuds explorés | 100% | 20-40% de moins |
| Optimalité | Garantie | Garantie si h admissible |
| Mémoire | O(\|V\|) | O(\|V\|) |
| Vitesse (pratique) | Référence | 20-40% plus rapide |

**Notes orales :**
> "On utilise deux algorithmes de plus court chemin selon le contexte. Dijkstra pour générer les matrices all-pairs — on a besoin de tous les chemins entre tous les points, donc on explore tout. A* pour les options de route en temps réel — là on cherche UN chemin précis, et l'heuristique haversine nous permet d'explorer 20 à 40% de nœuds en moins tout en garantissant l'optimum. L'admissibilité de l'heuristique est cruciale : la distance à vol d'oiseau est toujours inférieure ou égale au chemin routier réel."

---

## ──────────────────────────────────────────────
## SLIDE 14 — VRPTW — MODÈLE MATHÉMATIQUE
## Section : GRAPHES & SOLVEUR
## Durée : 1 minute 30 secondes
## ──────────────────────────────────────────────

**Titre :** Le solveur — VRPTW (Vehicle Routing Problem with Time Windows)

**Contenu :**

Bloc 1 — Définition du problème :
```
VRPTW = VRP + fenêtres temporelles

Données d'entrée :
  n  clients à livrer
  k  véhicules disponibles
  Q  capacité par véhicule (kg)
  T  horizon temporel = 8 heures (28 800 s)
  
  Pour chaque client i :
    → tw_start[i], tw_end[i]  : fenêtre horaire
    → weight[i]               : poids du colis (kg)
  
  Pour chaque paire (i,j) :
    → time_matrix[i][j]  : temps de trajet (s)
    → dist_matrix[i][j]  : distance (m)
    → co2_matrix[i][j]   : émissions CO₂ (g)
    → risk_matrix[i][j]  : score de risque
```

Bloc 2 — Modèle mathématique :

```
Minimiser :
  Σ Σ Σ  cost(i,j) × x[i,j,k]
  k i j

Sous contraintes :

[Visite unique]
  Σ Σ x[i,j,k] = 1    ∀ client i
  k j

[Capacité véhicule]
  Σ weight[i] × x[i,j,k] ≤ Q    ∀ véhicule k
  i

[Fenêtres temporelles]
  tw_start[i] ≤ arrival[i,k] ≤ tw_end[i]

[Contrainte "une nuit"]
  arrival[i,k] ≤ T = 28 800 s    ∀ (i,k)

[Continuité de la route]
  si x[i,j,k] = 1 → x[j,·,k] = 1  (le véhicule k continue)

Variables :
  x[i,j,k] ∈ {0,1}   (le véhicule k passe de i à j ?)
  arrival[i,k] ∈ ℝ⁺  (heure d'arrivée)
```

Bloc 3 — Penalité pour abandon :
```
Clients non livrables (infaisables) :
→ Pas d'échec mais une pénalité : 1 000 000 pts
→ Permet au solveur de trouver
  des solutions sub-optimales mais valides
→ drop_penalty configurable par profil IA

Preuve : services.py → "drop_penalty": 1_000_000
```

**Notes orales :**
> "Le VRPTW est la version avancée du problème du voyageur de commerce. En plus de trouver les meilleures tournées pour k véhicules avec des contraintes de capacité, on ajoute des fenêtres temporelles — certains clients ne peuvent être livrés qu'entre telle et telle heure. La contrainte 'une nuit' fixe un horizon de 8 heures maximum. Pour les clients qu'il est impossible de livrer, le solveur peut les 'abandonner' avec une forte pénalité plutôt que de déclarer l'infaisabilité."

---

## ──────────────────────────────────────────────
## SLIDE 15 — OR-TOOLS & MÉTAHEURISTIQUES
## Section : GRAPHES & SOLVEUR
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Google OR-Tools — Résolution en deux phases

**Contenu (2 phases) :**

Phase 1 — Solution initiale (3 stratégies) :
```
Objectif : trouver rapidement une solution VALIDE
(pas forcément optimale, point de départ pour la phase 2)

Stratégies disponibles :
  PATH_CHEAPEST_ARC
    → Greedy : toujours aller au client le plus proche
    → Très rapide, solution acceptable
    
  PARALLEL_CHEAPEST_INSERTION
    → Insérer chaque client au meilleur endroit
      dans la tournée existante
    → Meilleure qualité initiale
    
  SAVINGS (Clarke-Wright)
    → Fusion de routes partielles par économie
    → Bon pour minimiser la distance
    → Algorithme historique du VRP (1964)
```

Phase 2 — Amélioration locale (3 métaheuristiques) :
```
Objectif : améliorer itérativement la solution initiale

GUIDED LOCAL SEARCH (GLS)
  → Pénalise les arêtes fréquemment dans les minima locaux
  → S'échappe des optima locaux par guidance
  → Meilleur pour minimiser le temps
  → Profils : Express, Prudent, Agressive, Championne

SIMULATED ANNEALING (SA)
  → Accepte des solutions légèrement pires
    avec une probabilité décroissante (température)
  → Exploration globale du voisinage
  → Profil : Écolo

TABU SEARCH (TS)
  → Liste tabou des mouvements récents
  → Interdit de revenir en arrière
  → Bonne diversification
  → Profil : Opportuniste
```

**Diagramme de flux OR-Tools :**
```
Données d'entrée (matrices + contraintes)
         │
         ▼
[Stratégie initiale] → Solution 0 (valide)
         │
         ▼
[Métaheuristique] ←──── boucle d'amélioration
         │              (jusqu'à time_limit)
         ▼
Meilleure solution trouvée
         │
         ▼
[Post-traitement 2-opt] → Solution finale
```

**Preuve code (bloc) :**
```python
# final_scripts/solve_santa_final.py — lignes 30-42
FIRST_SOLUTION_STRATEGIES = {
    "path_cheapest_arc":           FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "parallel_cheapest_insertion": FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    "savings":                     FirstSolutionStrategy.SAVINGS,
    "christofides":                FirstSolutionStrategy.CHRISTOFIDES,
}
LOCAL_SEARCH_METAHEURISTICS = {
    "guided_local_search":  LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    "simulated_annealing":  LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    "tabu_search":          LocalSearchMetaheuristic.TABU_SEARCH,
}
```

**Notes orales :**
> "OR-Tools de Google fonctionne en deux phases. D'abord une stratégie initiale pour construire une solution valide rapidement — on utilise l'insertion parallèle ou l'algorithme de Clarke-Wright. Ensuite une métaheuristique affine cette solution pendant le temps imparti — guided local search pour la vitesse, simulated annealing pour la distance, tabu search pour la flexibilité. Après le solveur, on applique systématiquement un 2-opt pour éliminer les croisements résiduels."

---

## ──────────────────────────────────────────────
## SLIDE 16 — 2-OPT & K-MEANS — ALGORITHMES COMPLÉMENTAIRES
## Section : GRAPHES & SOLVEUR
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** 2-opt & K-Means — Deux algorithmes maison

**Contenu (2 blocs côte à côte) :**

Bloc gauche — 2-opt :
```
✂️ Amélioration 2-opt (post-traitement)

Principe :
  → Tester toutes les paires d'arêtes (i, j)
  → Si inverser le segment [i+1...j]
    réduit le coût → appliquer l'inversion
  → Répéter jusqu'à plus d'amélioration

Complexité : O(n²) par itération
             O(n³) dans le pire cas total

Formule de décision :
  cost_avant = dist(route[i], route[i+1])
             + dist(route[j], route[j+1])
             
  cost_après = dist(route[i], route[j])
             + dist(route[i+1], route[j+1])
             
  Si cost_après < cost_avant → inverser [i+1..j]

Usage :
  → Appliqué après OR-Tools sur chaque route
  → Appliqué en debrief sur la route humaine
  → Montre le "potentiel d'amélioration"

Fichier : scripts/ro_improvements.py:68
```

Bloc droit — K-Means spatial :
```
🗂️ K-Means (implémentation maison)

Principe :
  → Diviser les clients en k zones géographiques
  → Résoudre un VRP indépendant par zone
  → Réduction de la complexité :
    n clients → k × (n/k) clients
    
Algorithme :
  1. Initialiser k centroïdes aléatoires
  2. Répéter :
     a. Assigner chaque client au centroïde
        le plus proche (distance euclidienne)
     b. Recalculer centroïdes = barycentre
        des clients assignés
     c. Stopper si centroïdes stables
  
Convergence : garantie en nombre fini d'itérations
(l'inertie décroît à chaque étape)

Usage dans le projet :
  → Profil "Championne (Secteurs)"
  → Découpe la ville en k secteurs
  → Chaque traîneau couvre 1 secteur
  → difficulty_bonus ×10.0 (le plus difficile)

Fichier : scripts/zone_clustering.py:9
```

**Extrait code K-Means (bloc) :**
```python
# scripts/zone_clustering.py — lignes 9-31
def kmeans_spatial(points, k, max_iters=100):
    """Implémentation maison — prouve la maîtrise algorithmique."""
    idx = np.random.choice(len(points), k, replace=False)
    centroids = points[idx]
    
    for i in range(max_iters):
        distances = np.sqrt(((points - centroids[:, np.newaxis])**2).sum(axis=2))
        labels = np.argmin(distances, axis=0)
        new_centroids = np.array([
            points[labels == j].mean(axis=0) for j in range(k)
        ])
        if np.all(centroids == new_centroids):
            break
        centroids = new_centroids
    
    return labels, centroids
```

**Notes orales :**
> "Deux algorithmes complémentaires viennent enrichir le solveur. Le 2-opt est un post-traitement classique : on inverse des segments de route pour éliminer les croisements — c'est simple, efficace et rapide. Le K-Means est implémenté from scratch — c'est un choix pédagogique volontaire pour démontrer la maîtrise algorithmique. Il divise la ville en zones géographiques avant d'optimiser chaque zone indépendamment."

---

## ──────────────────────────────────────────────
## SLIDE 17 — CENTRALITÉ & ROBUSTESSE DU GRAPHE
## Section : GRAPHES
## Durée : 45 secondes
## ──────────────────────────────────────────────

**Titre :** Analyse du graphe — Centralité et robustesse

**Contenu (2 blocs) :**

Bloc gauche — Centralité de betweenness :
```
📊 Betweenness Centrality

Définition :
  BC(v) = Σ_{s≠v≠t} σ_st(v) / σ_st
  
  où σ_st = nb de plus courts chemins de s à t
      σ_st(v) = ceux passant par v

Interprétation :
  → Les nœuds avec BC élevé sont des "hubs"
  → Supprimer un hub fragmente le réseau
  → Visualisé en débrief de mission

Usage :
  → Identifier les nœuds critiques
  → Simuler des fermetures de rue
  → Visualiser la vulnérabilité du réseau

API : GET /api/missions/{id}/graph/betweenness-top
```

Bloc droit — Test de robustesse :
```
🔬 Résultat : Le graphe urbain est fragile

Test réalisé sur Paris 5ᵉ :
  → Supprimer 1% des nœuds les plus centraux
    = perte de 60% de connectivité
  → Supprimer 5% des nœuds
    = graphe quasi-déconnecté
  → Supprimer 10% aléatoirement
    = perte de seulement 15% (robuste)

Conclusion :
  Le graphe urbain est "scale-free" :
  quelques nœuds concentrent
  l'essentiel du trafic.

  → C'est le principe des axes structurants
    (boulevards, artères principales)
  → Un incident sur un hub = paralysie partielle
  
Fichier : scripts/graph_robustness.py
```

**Notes orales :**
> "La centralité de betweenness identifie les carrefours critiques du réseau. Notre test de robustesse sur Paris 5ᵉ est révélateur : supprimer 1% des nœuds les plus centraux provoque une perte de 60% de connectivité. Le graphe urbain est fragile aux attaques ciblées, comme les réseaux scale-free — c'est la réalité des villes, avec quelques grands axes qui portent l'essentiel du trafic."

---

## ──────────────────────────────────────────────
## SLIDE 18 — INTELLIGENCE ARTIFICIELLE — VUE GLOBALE
## Section : IA
## Durée : 30 secondes
## ──────────────────────────────────────────────

**Titre :** Intelligence Artificielle — 3 niveaux d'IA

**Contenu (diagramme hiérarchique) :**

```
                 ┌─────────────────────────────┐
                 │     3 niveaux d'IA           │
                 └──────────────┬──────────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ NIVEAU 1         │  │ NIVEAU 2         │  │ NIVEAU 3             │
│ 7 Profils IA     │  │ Modèle           │  │ Sleigh Search        │
│ paramétrés       │  │ d'apprentissage  │  │ (optimisation de     │
│                  │  │ Bayésien léger   │  │  flotte) +           │
│ → Règles fixes   │  │                  │  │ OR-Tools Auto-Tuner  │
│ → Métaheurist.   │  │ → Apprend quel   │  │                      │
│ → Limites temps  │  │   profil marche  │  │ → Apprend les params │
│                  │  │   le mieux selon │  │   OR-Tools optimaux  │
│ Fichier :        │  │   le contexte    │  │   selon le contexte  │
│ services.py:51   │  │                  │  │                      │
│                  │  │ Fichier :        │  │ Fichier :            │
│                  │  │ services.py:166  │  │ services.py:2938     │
└──────────────────┘  └──────────────────┘  └──────────────────────┘
```

**Notes orales :**
> "Notre système IA se décompose en 3 niveaux. Les 7 profils paramétrés forment la base — des règles expertes. Par-dessus, un modèle d'apprentissage bayésien léger apprend quel profil convient le mieux selon le contexte météo et la taille de la mission. Et enfin, le Sleigh Search et l'Auto-Tuner optimisent dynamiquement les paramètres du solveur."

---

## ──────────────────────────────────────────────
## SLIDE 19 — LES 7 PROFILS IA
## Section : IA
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Les 7 profils IA — Expertise paramétrée

**Contenu (tableau complet) :**

| Profil | Signature | Objectif | 1ère stratégie | Métaheuristique | Temps solveur | Bonus difficulté |
|--------|-----------|----------|----------------|-----------------|---------------|------------------|
| 🚀 **Express** | Rush urbain | Temps | Parallel Cheapest Insertion | Guided Local Search | 12s | ×2.0 |
| 🌿 **Écolo** | Trajectoires sobres | Distance | Savings (Clarke-Wright) | Simulated Annealing | 18s | ×3.0 |
| 🛡️ **Prudent** | Marge de sécurité | Temps + marges | Parallel Cheapest Insertion | Guided Local Search | 28s | ×4.0 |
| 🎯 **Opportuniste** | Rebond tactique | Temps flexible | Savings | Tabu Search | 22s | ×4.0 |
| ⚡ **Agressive** | Pression max | Temps rapide | Parallel Cheapest Insertion | Guided Local Search | 10s | ×6.0 |
| 🏆 **Championne** | Meta complète | Temps combiné | Savings | Guided Local Search | 35s | ×8.0 |
| 🗺️ **Championne (Zones)** | Architecture hybride | Temps + K-Means | Parallel Cheapest Insertion | Guided Local Search | 40s | ×10.0 |

**Légende explication bonus difficulté :**
```
Le bonus de difficulté multiplie la contribution du profil IA
au score final. Un joueur qui bat le profil "Championne (Zones)"
(×10) gagne 10 fois plus de points que s'il battait "Express" (×2).
```

**Preuve code :**
```python
# backend/app/services.py — lignes 51-163
AI_PROFILE_PRESETS = {
    "express": {
        "label": "Express",
        "signature": "Rush urbain",
        "difficulty_bonus": 2.0,
        "optimization_target": "time",
        "solver_time_limit_s": 12,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        ...
    },
    "championne_zone": {
        "difficulty_bonus": 10.0,
        "spatial_sectorization": True,  # ← active le K-Means !
        "solver_time_limit_s": 40,
        ...
    }
}
```

**Notes orales :**
> "Les 7 profils IA sont des configurations expertes du solveur OR-Tools. Chaque profil choisit une stratégie initiale et une métaheuristique d'amélioration différentes, selon l'objectif — vitesse ou distance. 'Agressive' prend 10 secondes seulement, accepte d'abandonner des clients chers en temps pour aller plus vite. 'Championne (Zones)' prend 40 secondes, utilise K-Means pour découper la ville, et vaut ×10 en bonus de difficulté."

---

## ──────────────────────────────────────────────
## SLIDE 20 — MODÈLE D'APPRENTISSAGE BAYÉSIEN
## Section : IA
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Apprentissage léger — Quel profil pour quel contexte ?

**Contenu :**

Bloc 1 — Problème :
```
❓ Comment choisir automatiquement le meilleur profil ?

Le profil optimal dépend du CONTEXTE :
  → Météo (pluie, neige, orage)
  → Nombre de clients (8 à 200)
  → Présence d'incidents actifs
  → Budget disponible par client
  → Densité géographique
```

Bloc 2 — Solution (modèle bayésien léger) :
```
📊 Modèle d'apprentissage bayésien
Fichier : cache/api_missions/ai_learning_model.json
Version : 2.0

Apprentissage :
  → Pour chaque résolution passée :
    stocker (contexte, profil, coût_composite)
  
  → Coût composite = signal de qualité :
    composite_cost = temps_par_client
                   + 95 × dist_par_client_km
                   + 2400 × taux_abandon
                   + 1200 × dépassement_budget
                   + 180 × pénalité_météo

Inférence (lissage bayésien) :
  coût_attendu = (n_contexte × moy_contexte
                  + α × moy_globale)
                 / (n_contexte + α)
  
  où α = 3.0 (paramètre de lissage)
  
  → Recommande le profil avec le plus faible
    coût_attendu pour ce contexte

  → Robuste au sur-apprentissage (lissage vers la moyenne)
```

Bloc 3 — Stratégie d'évaluation :
```
📐 Validation
  → Ratio holdout : 25% (ORTOOLS_TUNER_HOLDOUT_RATIO)
  → Découpage stratifié par (contexte, profil)
  → Échantillons min. pour fiabilité : 8
  → Mis à jour après chaque résolution
```

**Pourquoi pas du deep learning ?**
```
✅ Justification du choix bayésien :
  → Peu de données (10s à 100s de résolutions)
  → Deep learning nécessite des milliers d'exemples
  → Bayésien : efficace dès 8 exemples
  → Interpretable : on sait pourquoi il recommande X
  → Léger : <10 Ko en JSON, pas de GPU
  → Robuste : lissage vers la moyenne si contexte inconnu
```

**Notes orales :**
> "Le modèle d'apprentissage n'est pas un réseau de neurones — et c'est volontaire. Avec 10 à 100 résolutions, un deep learning serait inutilisable. On utilise à la place une inférence bayésienne avec lissage : on calcule le coût moyen de chaque profil dans un contexte donné, lissé vers la moyenne globale. C'est interprétable, rapide, et fonctionne dès 8 exemples."

---

## ──────────────────────────────────────────────
## SLIDE 21 — SLEIGH SEARCH & AUTO-TUNER
## Section : IA
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Sleigh Search & OR-Tools Auto-Tuner

**Contenu (2 blocs côte à côte) :**

Bloc gauche — Sleigh Search :
```
🛷 Sleigh Search : optimiser la taille de la flotte

Problème :
  Combien de véhicules utiliser ?
  → Trop peu → clients non livrés
  → Trop → coût de flotte élevé

Algorithme (élimination progressive) :
  1. Calculer k_min (contrainte capacité)
     k_min = ⌈poids_total / capacité⌉
  
  2. Sélectionner k candidats
     [k_min, k_base, k_max]
  
  3. Pour chaque k :
     → Résoudre le VRP rapidement (2s)
     → Calculer le score :
  
  score(k) = temps_total
           + 0.015 × distance_totale
           + 0.0015 × pénalité × abandons
           + 2.0 × k × coût_traîneau
  
  4. Garder la moitié la moins coûteuse
  5. Recommencer jusqu'à 1 candidat

Configurable : NOEL_SLEIGH_SEARCH_MAX_K=8
Fichier : services.py:2938
```

Bloc droit — OR-Tools Auto-Tuner :
```
⚙️ Auto-Tuner : apprendre les params OR-Tools

Paramètres appris :
  → first_solution_strategy
  → local_search_metaheuristic
  → solver_time_limit_s
  → time_slack_s
  → max_route_time_s
  → drop_penalty
  → global_span_cost

Mécanisme :
  → Même principe bayésien que le modèle profil
  → Enregistre les meilleures configurations
    par contexte (météo × taille × incidents)
  → Lissage α = 3.0, holdout 25%
  → Fichier : ortools_tuner_model.json

Endpoint "solve-learned" :
  POST /api/missions/{id}/solve-learned
  → Combine profils + tuner + RO portfolios
  → Sonde 4 stratégies en parallèle (2s chacune)
  → Sélectionne la meilleure
  → Lance la résolution complète
```

**Notes orales :**
> "Le Sleigh Search résout le problème du nombre de véhicules optimal par exploration progressive — on sonde rapidement plusieurs tailles de flotte et on élimine les moins prometteuses, comme un bracket de tournoi. L'Auto-Tuner va plus loin : il apprend les meilleurs paramètres OR-Tools pour chaque type de contexte, indépendamment du profil IA."

---

## ──────────────────────────────────────────────
## SLIDE 22 — CHOIX TECHNIQUES & ARBITRAGES
## Section : ARCHITECTURE
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Choix techniques — Pourquoi X plutôt que Y ?

**Contenu (tableau de comparaison) :**

| Décision | Choix retenu | Alternative écartée | Justification |
|----------|-------------|---------------------|---------------|
| Solveur VRP | **OR-Tools (Google)** | CPLEX, Gurobi | OR-Tools = gratuit, open-source, compétitif en perf |
| Plus court chemin (masse) | **Dijkstra** | Bellman-Ford | Pas de poids négatifs → Dijkstra optimal |
| Plus court chemin (temps réel) | **A*** | Dijkstra seul | 20-40% moins de nœuds explorés |
| Stockage matrices | **NumPy .npy** | JSON, CSV | 30× plus rapide en I/O, format binaire optimisé |
| Clustering | **K-Means maison** | scikit-learn | Maîtrise algorithmique prouvée + code ~50 lignes |
| Backend | **FastAPI** | Django, Flask | Async natif, typage Python, génération docs auto |
| Base de données | **SQLite** | PostgreSQL | Pas de serveur, ACID, suffisant pour la charge |
| Modèle IA | **Bayésien léger** | Deep Learning | Efficace dès 8 exemples, interprétable, sans GPU |
| Données météo | **Open-Meteo** | OpenWeatherMap | Gratuit, sans clé API, codes WMO standards |
| CO₂ | **ADEME Impact CO₂** | Facteurs manuels | Source officielle française, API gratuite |
| Graphe cartographique | **OSMnx + OSM** | HERE, Google Maps | Gratuit, mondial, données réelles et à jour |

**Notes orales :**
> "Tous nos choix techniques sont guidés par trois critères : coût zéro (tout open-source), performance suffisante pour notre échelle, et lisibilité du code. OR-Tools de Google est au niveau des solveurs commerciaux CPLEX et Gurobi sur les benchmarks académiques — et il est entièrement gratuit. SQLite suffit largement pour notre charge actuelle et évite la complexité d'un serveur PostgreSQL."

---

## ──────────────────────────────────────────────
## SLIDE 23 — SÉCURITÉ & INTÉGRITÉ
## Section : ARCHITECTURE
## Durée : 40 secondes
## ──────────────────────────────────────────────

**Titre :** Sécurité et intégrité des données

**Contenu (3 blocs) :**

Bloc 1 — Authentification :
```
🔐 Mots de passe
  → Hachage PBKDF2-HMAC-SHA256
  → 120 000 itérations (standard NIST 2023)
  → Sel aléatoire 32 octets par utilisateur
  → Réinitialisation avec token TTL 30 min

Preuve : services.py:220
PASSWORD_HASH_ITERATIONS = 120_000
```

Bloc 2 — Intégrité des scores :
```
🔏 Anti-triche leaderboard
  → Chaque score soumis est signé
    par un hash HMAC côté backend
  → Le score ne peut pas être falsifié
    sans la clé secrète
  → Validation côté backend à chaque soumission
```

Bloc 3 — Isolation des missions :
```
🗂️ Isolation par mission
  → Chaque mission a son propre répertoire
    cache/api_missions/{mission_id}/
  → Accès vérifiée par player_id
  → Pas de lecture croisée entre joueurs
```

**Notes orales :**
> "Sur la sécurité : les mots de passe utilisent PBKDF2 avec 120 000 itérations — conforme aux recommandations NIST 2023. Les scores du leaderboard sont signés par HMAC pour éviter les falsifications côté client. Chaque mission est isolée dans son propre répertoire."

---

## ──────────────────────────────────────────────
## SLIDE 24 — RÉSULTATS & BENCHMARKS
## Section : RÉSULTATS
## Durée : 1 minute
## ──────────────────────────────────────────────

**Titre :** Résultats — L'IA bat-elle le naïf ?

**Contenu :**

Bloc 1 — Baseline naïve (référence) :
```
📏 Baseline : tournée naïve séquentielle
  → Livraisons dans l'ordre 1..N
  → Répartition équilibrée entre les véhicules
  → Aucune optimisation
  → Calculée automatiquement par benchmark_engine.py
```

Bloc 2 — Résultats obtenus (tableau) :

| Métrique | Baseline naïve | Solution IA (Championne) | Gain |
|----------|---------------|--------------------------|------|
| Temps total | T_naif | T_opt | **-36.7%** |
| Distance totale | D_naif | D_opt | **-36.1%** |
| Émissions CO₂ | C_naif | C_opt | **-15% à -25%** |
| Clients livrés | 100% (souvent) | ≥ 95% | Similaire |
| Temps de calcul solveur | - | **< 30 secondes** | - |

Bloc 3 — Score final :
```
🏅 Formule de score (sur 100 points)

score_base = 0.45 × score_temps
           + 0.20 × score_co2
           + 0.10 × score_budget
           + 0.25 × score_couverture

Bonus cumulatifs :
  + difficulty_bonus × profil (2 à 10 pts)
  + 10 pts si incidents actifs
  + 5-8 pts selon météo difficile
  + 5 pts si humain bat l'IA en versus

score_final = clamp(score_base + bonus, 0, 100)
```

Bloc 4 — A* vs Dijkstra (perf) :
```
⚡ Performances algorithmiques
  A* : 20-40% de nœuds explorés en moins
  Robustesse graphe : 1% nœuds centraux supprimés
                    = 60% de connectivité perdue
  Taille graphe Paris 5ᵉ : 2 500 nœuds, 6 000 arêtes
  Matrices : 180 × 180 (32 400 valeurs par matrice)
```

**Notes orales :**
> "Les résultats parlent d'eux-mêmes. Le solveur IA réduit le temps de tournée de 36.7% et la distance de 36.1% par rapport à une approche naïve séquentielle. Les émissions CO₂ baissent de 15 à 25% selon les scénarios. Et tout ça en moins de 30 secondes de calcul — c'est la puissance des métaheuristiques modernes."

---

## ──────────────────────────────────────────────
## SLIDE 25 — LIMITES & AMÉLIORATIONS FUTURES
## Section : PERSPECTIVES
## Durée : 40 secondes
## ──────────────────────────────────────────────

**Titre :** Limites actuelles et perspectives d'amélioration

**Contenu (2 colonnes) :**

Colonne gauche — Limites actuelles :
```
⚠️ Limites

Scalabilité :
  → Testé jusqu'à 200 clients max
  → Au-delà : temps calcul matrices > 2 min
  → Graphe limité au 5ᵉ arrondissement de Paris

Temps de calcul :
  → Génération du graphe : 15-60 secondes
  → Si API OSM lente ou indisponible → timeout
  → Les matrices complètes : O(n²) nœuds

Données :
  → Météo en temps réel mais graphe figé
    (ne se met pas à jour après incidents réels)
  → Pas de données trafic temps réel (pas Waze)

IA :
  → Modèle bayésien = faible extrapolation
  → Froid (cold start) sur nouveaux contextes
  → Pas d'apprentissage par renforcement

UX :
  → Pas d'app mobile native
  → Pas de mode hors-ligne
```

Colonne droite — Améliorations futures :
```
🚀 Perspectives

Court terme :
  → Étendre à d'autres arrondissements / villes
  → Ajouter des données trafic (API Tomtom)
  → Optimisation par GPU (cuOpt de NVIDIA)

Moyen terme :
  → Apprentissage par renforcement (Q-Learning)
    pour adapter la route en cours de livraison
  → Multi-dépôt (plusieurs entrepôts de départ)
  → Contraintes de véhicules électriques
    (autonomie, bornes de recharge)

Long terme :
  → Déploiement cloud (AWS Lambda / GCP)
  → API REST publique pour intégration tiers
  → Jumeaux numériques de villes entières
```

**Notes orales :**
> "Les limites principales sont la scalabilité — au-delà de 200 clients, les temps de calcul deviennent pénalisants — et le cold start de l'IA sur de nouveaux contextes. La piste la plus prometteuse est l'apprentissage par renforcement pour adapter les tournées en cours de route, et l'utilisation de cuOpt de NVIDIA pour le calcul GPU des matrices."

---

## ──────────────────────────────────────────────
## SLIDE 26 — CONCLUSION
## Durée : 30 secondes
## ──────────────────────────────────────────────

**Titre :** Conclusion — Ce que nous avons construit

**Contenu (résumé visuel) :**

```
OPÉRATION NOËL — En chiffres

  5    sources Open Data intégrées
  7    profils IA paramétrés
  3    algorithmes de graphes (Dijkstra, A*, 2-opt)
  5    types de matrices de coût (temps, dist, CO₂, risque, composite)
  3    modes de transport multimodal (voiture, vélo, marche)
  40+  tests automatisés (unitaires + E2E)
  36.7% de réduction du temps vs baseline naïve
  < 30  secondes pour optimiser 50 clients

Et surtout :
  Un pipeline complet Open Data → Graphe → IA → Site web
  Zéro données propriétaires • Zéro serveur payant
  100% reproducible
```

**Visuel :**
- Fond : carte de Paris la nuit (même visuel que slide 1, cohérence).
- Les chiffres mis en grand, en doré sur fond sombre.
- En bas : "Questions ?"

**Notes orales :**
> "Opération Noël est un projet complet qui va de la donnée brute OpenStreetMap jusqu'à une interface web jouable, en passant par un pipeline ETL, des algorithmes de graphes, un solveur VRPTW et un système d'IA adaptatif. Tout est open-source, tout est gratuit, et tout est documenté. Je suis prêt pour vos questions."

---

---

# ══════════════════════════════════════════════
# SCRIPT DE PRÉSENTATION (pour le présentateur)
# Durées précises et repères
# ══════════════════════════════════════════════

## MINUTAGE GLOBAL

| Slide | Titre | Durée | Cumulé |
|-------|-------|-------|--------|
| 1 | Titre | 0:30 | 0:30 |
| 2 | Plan | 0:20 | 0:50 |
| 3 | Contexte & Problématique | 1:00 | 1:50 |
| 4 | Objectifs | 0:40 | 2:30 |
| 5 | Fonctionnalités site | 0:50 | 3:20 |
| 6 | Parcours utilisateur | 1:00 | 4:20 |
| 7 | Versus & Solver | 0:40 | 5:00 |
| 8 | Architecture globale | 1:00 | 6:00 |
| 9 | Stack technique | 0:30 | 6:30 |
| 10 | 5 sources Open Data | 1:30 | 8:00 |
| 11 | Pipeline ETL | 1:00 | 9:00 |
| 12 | Construction graphe | 1:00 | 10:00 |
| 13 | Dijkstra vs A* | 1:30 | 11:30 |
| 14 | VRPTW Modèle math. | 1:30 | 13:00 |
| 15 | OR-Tools & Métaheurist. | 1:00 | 14:00 |
| 16 | 2-opt & K-Means | 1:00 | 15:00 |
| 17 | Centralité & Robustesse | 0:45 | 15:45 |
| 18 | IA — Vue globale | 0:30 | 16:15 |
| 19 | 7 Profils IA | 1:00 | 17:15 |
| 20 | Modèle bayésien | 1:00 | 18:15 |
| 21 | Sleigh Search & Tuner | 1:00 | 19:15 |
| 22 | Choix techniques | 1:00 | 20:15 |
| 23 | Sécurité | 0:40 | 20:55 |
| 24 | Résultats | 1:00 | 21:55 |
| 25 | Limites & perspectives | 0:40 | 22:35 |
| 26 | Conclusion | 0:30 | 23:05 |

**Total présentation : ~23 minutes (marge pour les transitions/pauses)**

---

## OÙ SE TROUVENT LES PREUVES TECHNIQUES

Pendant les questions du jury, voici exactement où montrer les preuves :

### Preuves données & pipeline ETL
- **Fichier principal :** `scripts/generator_engine.py` (991 lignes)
  - Lignes 1-50 : Imports + constantes (modes, vitesses, CO₂, ADEME)
  - Lignes 147-189 : `_annotate_multimodal_edges()` → annotation arêtes
  - Lignes 542-576 : `_robust_scale()` + `_build_composite_cost_matrix()`
  - Ligne 37 : `GRAPH_PATH = core_data/paris5.graphml` (preuve fichier graphe)
  - Ligne 67 : `ADEME_CO2_API_URL` (preuve intégration ADEME)

- **Fichier graphe :** `core_data/paris5.graphml` (graphe Paris 5ᵉ)
- **Matrices :** `core_data/*.npy` (live_time_matrix.npy, matrix_5eme.npy, co2_matrix.npy, risk_matrix.npy, composite_cost_matrix.npy)

### Preuves solveur VRPTW
- **Fichier principal :** `final_scripts/solve_santa_final.py`
  - Lignes 7-8 : `from ortools.constraint_solver import ...` (preuve OR-Tools)
  - Lignes 30-42 : Dictionnaires stratégies + métaheuristiques
  - Ligne 149 : `def solve_vrp(...)` (fonction principale)

### Preuves profils IA
- **Fichier :** `backend/app/services.py`
  - Lignes 51-164 : `AI_PROFILE_PRESETS` (tous les 7 profils avec tous paramètres)
  - Ligne 166 : `AI_LEARNING_MODEL_FILE` (chemin du modèle bayésien)
  - Ligne 169 : `AI_LEARNING_SMOOTHING_ALPHA = 3.0`
  - Lignes 2938-2957 : `_sleigh_search_score()` (formule score flotte)

### Preuves K-Means maison
- **Fichier :** `scripts/zone_clustering.py`
  - Lignes 9-31 : `kmeans_spatial()` (implémentation from scratch commentée)
  - Ligne 13 : commentaire explicite "Prouve la maîtrise algorithmique pour la soutenance"

### Preuves 2-opt
- **Fichier :** `scripts/ro_improvements.py`
  - Lignes 68-121 : `two_opt_routes()` (2-opt sur routes humaines)
  - Ligne 435 : `dijkstra_steps()` (Dijkstra avec étapes visualisables)

### Preuves score & benchmark
- **Fichier :** `backend/app/services.py`
  - Ligne 2571 : formule score multi-critères (travel_time + return + wait + penalties)
  - Lignes 4833+ : `_score_of()` pour le classement versus

### Preuves sécurité
- **Fichier :** `backend/app/services.py`
  - Ligne 220 : `PASSWORD_HASH_ITERATIONS = 120_000`

### Preuves WebSocket (Versus)
- **Fichier :** `backend/app/main.py` (chercher `/ws/versus/` et `/ws/social/`)

### Preuves Open Data OSM
- **Code :** `scripts/generator_engine.py`, ligne 201 : `_fetch_overpass_pois()`
  - Overpass QL query complète pour shops + amenities

### Preuves tests
- **Dossier :** `tests/` (40+ fichiers)
  - `test_ai_profiles.py` — tests profils IA
  - `test_score.py` — tests formule de score
  - `test_ai_learning_service.py` — tests modèle bayésien
  - `test_multimodal_generator.py` — tests graphe multimodal
  - `test_solver_postprocess_integrity.py` — tests intégrité VRPTW

### Preuves configuration
- **Fichier :** `.env.example` (toutes les variables d'environnement)
  - `NOEL_SLEIGH_SEARCH_MAX_K=8`
  - `NOEL_ONE_NIGHT_DURATION_S=28800`
  - `NOEL_ADEME_CO2_API_URL`

---

## GUIDE DE DÉMONSTRATION LIVE (si demandée)

### Scénario de démo recommandé (5 minutes max) :

1. **Ouvrir la page d'accueil** (`/`) → montrer le visuel immersif et les modes

2. **Lancer une mission** (`/campaign`) :
   - Zone : "Paris 5e" (déjà en cache, rapide)
   - Nombre de clients : 15-20 (rapide à générer)
   - Météo : Rain (facteur ×1.35, plus intéressant)
   - Profil IA : Express

3. **Montrer le workspace** (`/mission/{id}`) :
   - La carte avec les points de livraison
   - Les 3 options de route proposées par A*
   - Les stats live (temps, distance, CO₂, budget)

4. **Lancer le solveur IA** :
   - Cliquer "Résoudre avec l'IA" → profil Express
   - Observer les routes optimisées s'afficher sur la carte
   - Montrer les gains : "X% de temps économisé vs baseline"

5. **Ouvrir le Debrief** (`/mission/{id}/debrief`) :
   - Score sur 100
   - Amélioration 2-opt possible
   - Analyse CO₂

6. **Bonus si temps disponible :** Ouvrir `/explore` et lancer une visualisation Dijkstra pas à pas

### Ce qu'il NE FAUT PAS montrer pendant la démo :
- Ne pas lancer une nouvelle zone (téléchargement OSM = 15-60 secondes d'attente)
- Ne pas lancer le profil "Championne (Zones)" (40 secondes de calcul)
- Préparer les données en cache AVANT la démo

---

# ══════════════════════════════════════════════
# FAQ — QUESTIONS FRÉQUENTES DU JURY
# Avec réponses détaillées
# ══════════════════════════════════════════════

## 🔵 QUESTIONS TECHNIQUES — ALGORITHMES

**Q1 : Pourquoi avez-vous utilisé OR-Tools plutôt que d'implémenter votre propre solveur VRP ?**

> R : OR-Tools est une bibliothèque open-source de Google, utilisée en production par des entreprises de logistique mondiale. Implémenter un solveur VRP compétitif from scratch demanderait des années de développement. OR-Tools nous donne accès à des métaheuristiques éprouvées (GLS, SA, Tabu Search) avec un backend C++ hautement optimisé. Notre valeur ajoutée est dans l'orchestration intelligente du solveur (7 profils, Sleigh Search, Auto-Tuner bayésien) et dans le pipeline de données, pas dans la réimplémentation de l'état de l'art algorithmique.

**Q2 : L'heuristique haversine est-elle réellement admissible pour A* ?**

> R : Oui, par définition. La distance haversine calcule la distance à vol d'oiseau entre deux points géographiques. La distance routière réelle est toujours supérieure ou égale à la distance à vol d'oiseau (les routes font des détours). Notre heuristique h(u,v) = haversine(u,v) / vitesse_max sous-estime donc toujours le temps réel. L'admissibilité h(n) ≤ h*(n) est garantie, ce qui assure l'optimalité de A*.

**Q3 : Quelle est la complexité exacte de votre pipeline de génération de matrice ?**

> R : Pour n points de livraison et G nœuds dans le graphe : O(G² log G) pour les n all-pairs shortest paths avec Dijkstra (on calcule un Dijkstra depuis chaque point de livraison vers tous les autres, et on garde les distances aux autres points de livraison). Avec n=180 points et G=2500 nœuds, c'est environ 180 × 2500 × log(2500) ≈ 3 millions d'opérations. C'est pourquoi la génération prend 15-60 secondes. On met ensuite ces matrices en cache NumPy .npy pour ne plus les recalculer.

**Q4 : Pourquoi K-Means et pas DBSCAN pour le clustering ?**

> R : K-Means est adapté à notre problème car on connaît à l'avance le nombre de véhicules k (= le nombre de secteurs désiré). DBSCAN aurait été pertinent si on ne connaissait pas k et qu'on cherchait des clusters de densité variable. Ici, on veut exactement k zones pour k véhicules. De plus, K-Means sur des coordonnées géographiques est simple, rapide et interprétable — les centroïdes correspondent aux barycentres géographiques des zones.

**Q5 : Comment prouvez-vous que votre 2-opt converge ?**

> R : L'algorithme 2-opt converge en un nombre fini d'itérations car : (1) chaque échange améliore strictement le coût (coût décroît strictement), (2) le nombre de tournées distinctes pour n points est fini (au plus n!/2 permutations). Donc la suite de coûts est strictement décroissante et bornée inférieurement par 0, elle converge nécessairement. En pratique, on converge en quelques dizaines d'itérations.

---

## 🟡 QUESTIONS DONNÉES & OPEN DATA

**Q6 : Vos données OpenStreetMap sont-elles fiables pour de vraies livraisons ?**

> R : OSM est produit collaborativement mais sa qualité en zone urbaine dense (Paris centre) est excellente — comparable à Google Maps pour le réseau routier. La bibliothèque OSMnx télécharge directement le graphe routier avec vitesses légales, types de voies, sens de circulation. Pour un projet académique, c'est une source de référence. En production réelle, on enrichirait avec des données de trafic temps réel (API TomTom, HERE) et des données d'incidents officielles.

**Q7 : Pourquoi les données ADEME plutôt que des constantes fixes pour le CO₂ ?**

> R : Les données ADEME sont les données officielles du gouvernement français utilisées pour les bilans carbone réglementaires. Utiliser l'API ADEME Impact CO₂ garantit que nos calculs d'émissions sont légalement référençables et mis à jour automatiquement si les facteurs évoluent. On garde un fallback local (120g/km voiture, 8g/km vélo) si l'API est indisponible, mais la source officielle prime.

**Q8 : Comment gérez-vous la qualité des données OSM (attributs manquants) ?**

> R : Deux stratégies. Pour les vitesses manquantes (`maxspeed` absent) : on utilise des vitesses par défaut selon le type de voie (`highway` tag) — 70 km/h pour une voie primaire, 30 km/h en résidentiel, etc. Pour les cas ambigus (listes de valeurs, unités mph) : un parser spécifique dans `_parse_speed_kph()` (generator_engine.py:101) gère toutes les variantes. Les valeurs aberrantes sont clampées à des plages réalistes.

---

## 🟠 QUESTIONS IA & APPRENTISSAGE

**Q9 : Votre modèle bayésien apprend-il vraiment ou c'est juste une moyenne ?**

> R : C'est une forme d'apprentissage statistique classique — l'inférence bayésienne avec prior. Au démarrage (cold start, 0 données), on recommande de façon aléatoire. Après 8+ résolutions dans un contexte donné, le modèle recommande avec confiance le meilleur profil pour ce contexte. Le lissage vers la moyenne globale (α=3.0) est exactement le mécanisme de régularisation bayésien — c'est la même logique que les modèles de langue de base ou les systèmes de recommandation. Ce n'est pas du deep learning, mais c'est de l'apprentissage statistique au sens strict.

**Q10 : Pourquoi 7 profils et pas plus ? Comment avez-vous choisi ces 7 ?**

> R : Les 7 profils couvrent l'espace des stratégies de résolution VRP selon deux axes : (1) l'objectif principal (temps vs distance) et (2) le niveau de risque acceptable. Express/Agressive maximisent la vitesse avec peu de marge. Écolo optimise la distance. Prudent privilégie la sécurité avec beaucoup de marges. Opportuniste est flexible. Championne et Championne(Zones) combinent tout. C'est une couverture raisonnée de l'espace des comportements utiles — ajouter un 8ème profil serait redondant.

**Q11 : Comment testez-vous que vos profils IA sont réellement différents ?**

> R : Deux méthodes. D'abord, les paramètres sont structurellement différents (stratégie initiale différente, métaheuristique différente, time limit différente). Ensuite, les tests automatisés `tests/test_ai_profiles.py` vérifient que chaque profil produit une solution différente sur les mêmes données. En pratique, on observe des écarts de 5-15% de temps ou de distance entre les profils sur les mêmes missions.

---

## 🔴 QUESTIONS PERFORMANCES & SCALABILITÉ

**Q12 : Que se passe-t-il si la mission a 500 clients ? Le système est-il scalable ?**

> R : Actuellement non. Deux goulots d'étranglement : (1) la matrice n×n devient 500×500 = 250 000 valeurs, et le calcul Dijkstra all-pairs prend plusieurs minutes ; (2) OR-Tools avec 500 clients et des fenêtres temporelles strictes devient très difficile à résoudre en < 60 secondes. Solutions envisagées : clustering K-Means automatique pour décomposer en sous-problèmes de 50 clients chacun, calcul parallèle des matrices, et utilisation de cuOpt (GPU) de NVIDIA pour les matrices.

**Q13 : Comment garantissez-vous que le solveur s'arrête en temps borné ?**

> R : OR-Tools a un paramètre `time_limit` strictement respecté. Au-delà de la limite (10 à 40 secondes selon le profil), il retourne la meilleure solution trouvée jusque-là. Si aucune solution n'est trouvée dans ce temps, il retourne `None` et on gère le fallback. La contrainte `drop_penalty` garantit qu'il y a toujours une solution valide (le dépôt seul est une solution — on abandonne tous les clients avec pénalité).

---

## 🟣 QUESTIONS BASE DE DONNÉES & SÉCURITÉ

**Q14 : Pourquoi SQLite en production ? C'est suffisant ?**

> R : Pour notre cas d'usage (quelques dizaines d'utilisateurs simultanés, pas d'écriture massivement concurrente), SQLite est parfaitement adapté. Il supporte les transactions ACID et les accès concurrents en lecture. La limite réelle est l'écriture concurrente — SQLite verrouille la base entière en écriture. Pour passer à l'échelle, on migrerait vers PostgreSQL en changeant uniquement la couche `repository.py` — l'architecture est prévue pour ça.

**Q15 : Comment protégez-vous les scores du leaderboard contre la triche ?**

> R : Les scores sont calculés entièrement côté serveur — le client ne soumet jamais directement un score, seulement l'état de sa mission (quels clients livrés, dans quel ordre, à quelle heure). Le serveur recalcule le score à partir de ces données via `services.py`. Chaque soumission est également signée par HMAC pour détecter toute falsification des données d'entrée.

---

## 🟢 QUESTIONS MÉTIER & USAGE RÉEL

**Q16 : Est-ce que ce système pourrait être utilisé par un vrai transporteur ?**

> R : Avec des adaptations. Les points forts pour un usage réel : pipeline Open Data gratuit, solveur OR-Tools éprouvé industriellement, modèles CO₂ officiels ADEME. Les limites à surmonter : intégrer un flux de données trafic temps réel (Waze/TomTom), passer à une vraie base de données distribuée, ajouter la gestion des retours de colis et des créneaux de chargement en entrepôt, et certifier la fiabilité des temps de trajet.

**Q17 : Comment comparez-vous votre solution à des outils existants comme OptimoRoute ou Routific ?**

> R : Ces outils commerciaux sont plus matures et supportent des milliers de clients. Notre valeur différenciatrice est : (1) zéro coût de licence, (2) données 100% ouvertes et traçables, (3) intégration native de métriques CO₂ officielles ADEME, (4) aspect éducatif et gamification. Ce n'est pas une concurrence directe mais une alternative académique et pédagogique open-source.

---

## ⚪ QUESTIONS ARCHITECTURE & CODE

**Q18 : Votre architecture est-elle testable ? Comment avez-vous testé le solveur ?**

> R : Oui, nous avons 40+ tests automatisés dans le dossier `tests/`. Les tests du solveur vérifient l'intégrité post-traitement : chaque client doit être visité au plus une fois, aucun client hors domaine valide, même couverture que la solution brute OR-Tools (`test_solver_postprocess_integrity.py`). Les tests E2E avec Playwright couvrent les parcours utilisateur complets depuis le frontend.

**Q19 : Pourquoi avoir séparé les services dans un seul gros fichier `services.py` (5 923 lignes) ?**

> R : C'est clairement une dette technique. Dans un projet en production, on découperait en modules thématiques : `solver_service.py`, `ai_service.py`, `graph_service.py`, `player_service.py`, etc. Le choix actuel résulte d'une croissance organique du projet — chaque feature a été ajoutée dans le même fichier pour maintenir la cohérence des imports. La refactorisation en modules est la première amélioration architecturale à prévoir.

**Q20 : Comment gérez-vous les erreurs quand une API externe (OSM, ADEME) est indisponible ?**

> R : Chaque appel externe a un fallback explicite. Pour OSMnx : timeout configuré, retry automatique. Pour Overpass POI (noms des commerces) : si indisponible, génération procédurale de noms (`_fetch_overpass_pois()` dans generator_engine.py). Pour ADEME CO₂ : fallback sur les constantes locales `MODE_CO2_G_PER_KM` (120g/km voiture). Pour Open-Meteo : fallback sur météo simulée pondérée. Le système est conçu pour être résilient — aucune API externe n'est critique.

---

# ══════════════════════════════════════════════
# NOTES DE STYLE POUR GEMINI (à appliquer à tous les slides)
# ══════════════════════════════════════════════

## Design général :
- Style : moderne, tech, festif (thème Noël discret mais présent)
- Fonds alternés : slides techniques = fond sombre (#0D1B2A), slides résultats = fond clair (#FAFAFA)
- Titres de section : banderoles colorées en haut (rouge festif)
- Code : toujours dans des blocs à fond sombre, monospace, colorisation syntaxique Python/SQL

## Animations suggérées (si la présentation le permet) :
- Slide 3 : Graphe de ville qui se dessine progressivement
- Slide 8 : Architecture qui se construit couche par couche
- Slide 11 : Pipeline ETL avec des flèches animées de haut en bas
- Slide 13 : Comparaison Dijkstra vs A* : deux animations côte à côte montrant l'exploration

## Images recommandées à intégrer :
1. Photo vue aérienne nocturne de Paris (droits libres : Unsplash)
2. Capture d'écran simulée d'une carte Leaflet avec des pins de livraison
3. Logo OSMnx / OpenStreetMap (logo officiel, licence libre)
4. Logo Google OR-Tools
5. Illustration réseau de graphe (nœuds et arêtes colorés)
6. Icon traîneau de Noël (SVG flat design)
7. Icône ADEME (logo officiel)
8. Schéma Dijkstra vs A* (cercles d'exploration)

## Polices et tailles :
- Titre de slide : 36-44pt, Bold
- Sous-titre : 24-28pt, SemiBold
- Corps de texte : 18-20pt, Regular
- Code : 14-16pt, Monospace
- Notes de bas de page : 12pt, Light Italic

## Structure de chaque slide :
```
[HEADER : Bandeau section (couleur par thème)]
[TITRE : Grand titre en haut]
[CONTENU PRINCIPAL : Texte / Schéma / Code]
[FOOTER : Numéro slide + barre de progression]
```

## Couleurs par section :
- Introduction : Bleu (#1565C0)
- Site web : Violet (#7B1FA2)
- Architecture : Teal (#00695C)
- La Donnée : Vert (#2E7D32)
- Graphes : Orange (#E65100)
- IA : Rouge (#C62828)
- Résultats : Doré (#F57F17)
- Conclusion : Gris foncé (#212121)
