# Guide de Soutenance & Preuves Techniques

Ce document récapitule les éléments clés pour ta soutenance de 20 minutes et pointe vers les fichiers du projet qui servent de preuves.

## 1. Structure de la Présentation (20 min)

| Temps | Section | Points Clés | Preuve Code (Fichier) |
| :--- | :--- | :--- | :--- |
| **0-3 min** | Intro & Enjeux | Problème VRPTW, complexité combinatoire. | `backend/app/services.py` (Constraints) |
| **3-6 min** | Données (Open Data) | OSM, Overpass (noms réels), ADEME (CO2). | `scripts/generator_engine.py` |
| **6-8 min** | Physique & Environnement | Relief SRTM, Trafic horaire, Météo. | `scripts/elevation_engine.py`, `scripts/weather_engine.py` |
| **8-11 min** | Le Solveur (Cœur) | OR-Tools, Contraintes TW et Capacité. | `final_scripts/solve_santa_final.py` |
| **11-14 min** | Optimisation Avancée | ALNS (Destroy/Repair), ILS, Post-processing. | `scripts/ro_improvements.py` |
| **14-16 min** | Intelligence Artificielle | Profils (Ecolo/Express), K-Means, Apprentissage. | `backend/app/services.py` (AI_PROFILE_PRESETS) |
| **16-18 min** | Architecture Web | FastAPI + Next.js, Leaflet, Recharts. | `frontend/app/page.tsx`, `backend/app/main.py` |
| **18-20 min** | Conclusion & FAQ | Formules, limites, scalabilité. | `README.md`, `GEMINI.md` |

---

## 2. Formules et Concepts Importants à Citer

### A. La Fonction Objectif Composite
Tu peux expliquer que le solveur ne minimise pas juste le temps, mais un score équilibré :
`Cost = Σ (w_i * normalized_matrix_i)`
- **w_time**: 0.55
- **w_dist**: 0.20
- **w_co2**: 0.15
- **w_risk**: 0.10
*Source : `scripts/generator_engine.py` (DEFAULT_OBJECTIVE_WEIGHTS)*

### B. ALNS (Adaptive Large Neighborhood Search)
Explique que pour sortir des minima locaux de OR-Tools, on utilise une boucle "Détruire et Réparer" :
1. **Destroy** : On retire des clients (Random, Worst Cost, ou Relatedness).
2. **Repair** : On les réinsère avec des heuristiques gourmandes ou de regret.
*Source : `scripts/ro_improvements.py`*

### C. Profils IA
- **Express** : `parallel_cheapest_insertion` (rapide) + `guided_local_search`.
- **Ecolo** : `savings` (regroupe les trajets) + `simulated_annealing` (exploration lente).
*Source : `backend/app/services.py` (AI_PROFILE_PRESETS)*

---

## 3. FAQ - Questions Probables du Jury

**Q : Pourquoi avoir utilisé OR-Tools plutôt que de coder ton propre algorithme génétique ?**
*R : OR-Tools est une bibliothèque de classe industrielle qui gère nativement les contraintes de fenêtres de temps (VRPTW) et de capacité avec une efficacité bien supérieure à un algo maison. Cela m'a permis de me concentrer sur l'enrichissement des données (Open Data) et le post-traitement ALNS.*

**Q : Comment garantissez-vous que les données CO2 sont exactes ?**
*R : Nous utilisons les facteurs d'émission officiels de l'ADEME via leur API Impact CO2. Si l'API est indisponible, nous avons des fallbacks basés sur les moyennes de l'ADEME par mode de transport (ex: 120g/km pour une voiture).*

**Q : Votre solveur est-il scalable à 1000 clients ?**
*R : Le VRPTW est NP-Hard. Pour 1000 clients, le temps de calcul exploserait. C'est pourquoi j'ai implémenté le profil "Championne (Secteurs)" qui utilise du Clustering Spatial (K-Means) pour découper la ville en sous-zones indépendantes, rendant le problème à nouveau soluble en quelques secondes.*

**Q : Quel est l'impact du relief sur vos tournées ?**
*R : Grâce aux données SRTM, nous calculons la pente entre chaque nœud. Un traîneau lourd en montée consomme plus d'énergie (distance effective augmentée) et ralentit (temps augmenté), ce qui force le solveur à préférer les routes plates ou les descentes.*

---

## 4. Où se trouvent les preuves ? (Checklist)

- [ ] **Sourcing OSM** : `scripts/generator_engine.py` (Ligne ~400, `ox.graph_from_place`)
- [ ] **Calcul CO2 ADEME** : `scripts/generator_engine.py` (Ligne ~150, `_fetch_ademe_factor_g_per_km`)
- [ ] **Moteur OR-Tools** : `final_scripts/solve_santa_final.py` (Ligne ~150, `pywrapcp.RoutingModel`)
- [ ] **Logique ALNS** : `scripts/ro_improvements.py` (Fonction `adaptive_large_neighborhood_search`)
- [ ] **Profils IA** : `backend/app/services.py` (Dictionnaire `AI_PROFILE_PRESETS`)
- [ ] **Front-end Map** : `frontend/components/campaign-map.tsx`
