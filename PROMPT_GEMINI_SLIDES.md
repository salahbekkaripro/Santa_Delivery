# Prompt pour Gemini (Multimodal / Slide Creation)

Copie-colle ce prompt dans Gemini (ou un outil de génération de slides comme Gamma/Canva via Gemini) pour générer ta présentation.

---
**PROMPT :**

Agis en tant qu'expert en Recherche Opérationnelle et Ingénieur Data. Je dois préparer une soutenance de 20 minutes pour mon projet "Santa Router Optimizer", une application de logistique urbaine complexe.

Génère une structure de présentation de 20 slides (1 minute par slide) en suivant scrupuleusement ces éléments techniques issus de mon code source :

**Thème visuel :** Professionnel, Tech, Cartographique (fond sombre, accents vert émeraude pour l'écologie et rouge Noël pour le Père Noël).

**Contenu par Section :**

1. **Introduction & Problématique (Slides 1-3) :** Le défi du VRPTW (Vehicle Routing Problem with Time Windows). Pourquoi l'optimisation manuelle échoue en ville dense.
2. **Architecture & Tech Stack (Slide 4) :** FastAPI (Backend), Next.js/TypeScript (Frontend), Google OR-Tools (Solver).
3. **Data Sourcing (Open Data) (Slides 5-7) :**
    - Source : OpenStreetMap (OSM) via OSMnx.
    - Enrichissement : API Overpass pour les noms réels des POIs, API ADEME (Impact CO2) pour les facteurs d'émission réels.
    - Relief : Données SRTM (NASA) pour intégrer la pente dans les calculs d'effort.
    - Temps réel : Profils de trafic horaires (TRAFFIC_PROFILE) et météo dynamique.
4. **Data Transformation & Graphes (Slides 8-9) :**
    - Transformation du réseau routier en MultiDiGraph (NetworkX).
    - Génération de matrices Numpy NxN (Temps, Distance, CO2, Risque).
    - Calcul de la matrice Composite pondérée.
5. **Le Moteur d'Optimisation (Solver) (Slides 10-13) :**
    - Modèle : VRPTW (Constraints: Capacity, Time Windows).
    - Algorithmes : First Solution (Savings, Parallel Cheapest Insertion) + Metaheuristics (Guided Local Search, Tabu Search).
    - Post-traitement (le secret de la performance) : Utilisation de ALNS (Adaptive Large Neighborhood Search) et ILS (Iterated Local Search) pour raffiner les tournées OR-Tools.
6. **IA & Profiling (Slides 14-15) :**
    - Mode Express (Temps) vs Mode Écolo (Distance).
    - Mode Championne (Clustering Spatial K-Means pour sectoriser avant de résoudre).
    - Apprentissage : Modèle de recommandation basé sur l'historique des missions pour suggérer le meilleur profil.
7. **Démonstration Site & UX (Slides 16-17) :** Visualisation Leaflet, comparaison Humain vs IA, Dashboard de performance (Recharts).
8. **Choix Techniques & Formules (Slide 18) :**
    - Formule du coût composite : `Cost = W_t * Time + W_d * Dist + W_c * CO2 + W_r * Risk`.
    - Pourquoi OR-Tools ? Flexibilité des contraintes et robustesse industrielle.
9. **Conclusion & Perspectives (Slide 19) :** Passage au temps réel strict, intégration de flottes de drones.
10. **FAQ (Slide 20) :** Questions types sur la complexité (NP-Hard), la scalabilité et la précision des données OSM.

**Instructions spécifiques pour les visuels :**
- Utilise des icônes pour les modes de transport (Camion, Vélo, Marche).
- Pour le slide 12 (ALNS), montre un diagramme "Destroy & Repair".
- Pour le slide 9 (Matrices), montre un aperçu schématique d'une matrice de chaleur (Heatmap).

---
