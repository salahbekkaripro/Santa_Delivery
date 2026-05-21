# 🎓 Plan de Soutenance : Opération Noël (Graphes & Open Data)

Ce document contient la structure détaillée, les arguments techniques, les choix d'ingénierie et les formules pour ta présentation PowerPoint.

---

## 📅 Structure de la Présentation (20 min)

### 1. Introduction & Problématique (2 min)
*   **Titre** : Opération Noël : Optimisation de Logistique Urbaine Massive.
*   **Le Défi** : Livrer des centaines de colis en une seule nuit (22h - 06h) sous contraintes de temps, capacité, météo et incidents.
*   **Le Problème Mathématique** : VRPTW (Vehicle Routing Problem with Time Windows) - Un problème NP-Difficile.

### 2. Architecture & Choix Technologiques (2 min)
*   **Backend (Python/FastAPI)** : Choisi pour la richesse des bibliothèques de RO (Google OR-Tools) et de traitement de données (Pandas, NumPy, NetworkX).
*   **Frontend (Next.js/TypeScript)** : Pour une interface réactive, typée et une cartographie fluide (Leaflet).
*   **Moteur de calcul** : Google OR-Tools (solveur de contraintes par métaheuristiques).
*   **Automation & Reporting** : Utilisation d'un script **Python-PPTX** (`generate_pptx.py`) pour générer automatiquement les slides de résultats et de performances, garantissant des KPI fiables sans erreur humaine.

### 3. Open Data : Le Carburant du Projet (3 min)
*   **Réseau Routier** : **OpenStreetMap** (via OSMnx). On modélise un graphe orienté pondéré.
*   **Points d'Intérêt (POI)** : **Overpass API** pour injecter des commerces réels comme points de livraison.
*   **Météo** : **Open-Meteo** (données réelles vs simulées) pour impacter la vitesse de circulation.
*   **Relief** : **OpenTopoData (SRTM NASA)** pour calculer l'effort énergétique et l'impact de la pente sur le temps.
*   **CO2** : **ADEME Impact CO2** pour obtenir des facteurs d'émissions officiels par mode de transport.

### 4. Ingénierie des Données & Graphes (3 min)
*   **Traitement du Graphe** :
    *   Extraction de la "Largest Strongly Connected Component" pour éviter les impasses.
    *   Calcul de **Centralité d'Intermédiarité** (Betweenness) : identification des carrefours critiques (hubs).
    *   **Analyse de Robustesse** : Nous avons prouvé que le réseau est fragile : supprimer **1% des hubs centraux** provoque une perte de connectivité de **60%** (structure en éventail).
*   **Le Pipeline de Données** :
    1.  Projection des coordonnées sur le nœud OSM le plus proche.
    2.  Calcul massif de matrices de coûts (Dijkstra source-unique).
    3.  Génération de la **Matrice Composite**.

### 5. Algorithmes : Pourquoi ces choix ? (4 min)
*   **Pathfinding Segmentaire** : 
    *   **Dijkstra** (Exploration uniforme) vs **A*** (Heuristique Haversine). 
    *   *Choix* : A* Bidirectionnel pour gagner 30% de temps de calcul sur les routes individuelles.
    *   *Formule Heuristique* : $h(u, v) = \frac{\text{haversine}(u, v)}{13.89 \text{ m/s}}$ (vitesse max admissible).
*   **Scalabilité (Divide & Conquer)** : 
    *   **K-Means Spatial (Custom)** : Implémentation "from scratch" avec NumPy (sans scikit-learn) pour prouver la maîtrise algorithmique.
    *   *Formule K-Means* : Minimisation de l'inertie intra-classe $J = \sum_{i=1}^{k} \sum_{x \in S_i} ||x - \mu_i||^2$.
*   **Optimisation de Tournée (Moteur Principal)** :
    *   **OR-Tools (VRPTW)** : Utilise des métaheuristiques (Large Neighborhood Search).
    *   **Heuristiques Avancées "Hand-made" (Post-process)** :
        *   **ILS (Iterated Local Search)** : Utilise une perturbation **Double-Bridge** (4-opt non-séquentiel) pour sortir des optima locaux.
        *   **ALNS (Adaptive Large Neighborhood Search)** : Système de "Destruction/Réparation" adaptatif avec sélection par roulette.

### 6. Deep Dive Technique : Qualité & Performance (2 min)
*   **Borne Inférieure & Gap d'Optimalité** :
    *   Comment savoir si l'IA est bonne ? On calcule la **Borne 1-Arbre** (MST sur les clients + les 2 arcs les plus courts vers le dépôt).
    *   **Formule du Gap** : $Gap(\%) = \frac{Coût(IA) - Borne}{Borne} \times 100$.
    *   *Résultat* : Nos tournées ont un gap < 15% par rapport à l'optimum théorique.
*   **Local Search Inter-Routes** :
    *   **Or-Opt** : Relocalisation de blocs de 1, 2 ou 3 clients entre traîneaux.
    *   **2-Opt*** : Échange de suffixes de tournées pour réduire les croisements de routes entre véhicules.

### 7. La Formule Magique : La Matrice Composite (2 min)
Pour chaque arc $(i, j)$, le coût est une somme pondérée normalisée :
$$Cost(i,j) = w_{time} \cdot \overline{T_{ij}} + w_{dist} \cdot \overline{D_{ij}} + w_{co2} \cdot \overline{C_{ij}} + w_{risk} \cdot \overline{R_{ij}}$$
*   **Normalisation** : Utilisation de la médiane pour écraser les outliers de distance/temps.
*   **Poids par défaut** : Temps (55%), Distance (20%), CO2 (15%), Risque (10%).

### 7. Gamification & Score (2 min)
Le score final ($S \in [0, 100]$) récompense l'efficience :
1.  **Temps** ($60\%$) : $Score_T = \min(100, \text{gain\_temps\_pct} \times 2.5)$.
2.  **CO2** ($25\%$) : $Score_{CO2} = \min(100, \frac{\text{CO2\_saved\_kg}}{\text{nb\_clients} \times 0.1} \times 100)$.
3.  **Budget** ($15\%$) : Pourcentage du budget restant.
*   **Bonus Cumulables** :
    *   **Profil IA** : Jusqu'à $+10$ pts (ex: Mode "Championne Secteurs").
    *   **Incidents** : $+10$ pts si des blocages routiers sont activés.
    *   **Météo** : Jusqu'à $+8$ pts pour les conditions extrêmes (tempêtes).
    *   **Performance Humaine** : $+5$ pts si le joueur bat le temps de l'IA.
*   **Contrainte "Une Nuit"** : Horizon de 8h (28800s) imposé; priorité à la **couverture colis** (livrer un maximum) plutôt qu'à la minimisation pure du coût.

### 8. Validation & Tests (1 min)
*   **Tests Unitaires** : Validation de l'intégrité des tournées (aucun client oublié, respect des capacités).
*   **Benchmarks Réels** : Gain moyen mesuré de **36.7% en temps** et **36.1% en distance** par rapport à une approche humaine (Gloutonne).
*   **Analyse de Robustesse** : Simulation de pannes sur les nœuds centraux (attaque ciblée vs aléatoire).

### 9. Conclusion (1 min)
*   Une plateforme hybride mêlant **Recherche Opérationnelle** et **Data Science**.
*   Capacité à passer à l'échelle grâce au clustering.
*   Ouverture vers la multimodalité (Vélos vs Camions).

---

## 🛠️ Chiffres Clés à Citer (Engineering)
*   **A* Bidirectionnel** : 20 à 40% de nœuds explorés en moins.
*   **Robustesse du Graphe** : Supprimer 1% des nœuds critiques brise 60% de la connectivité (réseau fragile).
*   **Impact CO2** : Moyenne de 15% d'économie entre le trajet humain intuitif et l'optimisation IA.
*   **Performance** : Résolution VRPTW sous les 30 secondes pour 50 clients.

---

## 💡 Conseils pour les Slides
1.  **Slide Graphes** : Montre une carte de chaleur (heatmap) de la centralité entre Paris 5ème et une autre zone.
2.  **Slide Algorithme** : Fais un schéma "Avant/Après" Clustering (K-Means).
3.  **Slide Score** : Affiche clairement la formule du score, c'est ce que les jurys adorent ("C'est quoi votre KPI ?").
4.  **Slide Démo** : Si possible, montre le dashboard de comparaison Humain vs IA.
ns).
3.  **Slide Score** : Affiche clairement la formule du score, c'est ce que les jurys adorent ("C'est quoi votre KPI ?").
4.  **Slide Démo** : Si possible, montre le dashboard de comparaison Humain vs IA.
