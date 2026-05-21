# 🎤 Script Oral de Soutenance (20 Minutes) & Guide Q&A

Ce document contient ton script minuté pour ta soutenance de 20 minutes, basé sur ta présentation "Opération Noël", ainsi qu'une liste de questions probables du jury avec les réponses techniques associées.

---

## 📅 Chronologie de la Soutenance (20 min)

### 1. Introduction & Contexte (2 min)
*   **Discours** : "Bonjour à tous. Je vais vous présenter Opération Noël, un projet de logistique urbaine optimisée. Au-delà de l'aspect ludique, ce projet traite un problème réel et complexe : le **VRPTW** (Vehicle Routing Problem with Time Windows). Le défi ? Livrer des milliards de colis en une seule nuit avec des traîneaux à capacité limitée, sous des fenêtres de temps strictes, une météo changeante et des incidents imprévus."
*   **Point clé** : Insiste sur la complexité **NP-difficile** qui rend l'humain moins efficace que l'algorithme.

### 2. Open Data : Le socle du projet (3 min)
*   **Discours** : "Pour ce projet, nous ne sommes pas partis de données fictives. Nous avons exploité 5 sources Open Data majeures : **OpenStreetMap** (via OSMnx) pour le réseau routier réel du Paris 5ème, **Open-Meteo** pour l'impact climatique sur la vitesse, **SRTM NASA** pour le relief (altitudes), et l'**ADEME** pour les facteurs d'émission CO2."
*   **Technique** : Mentionne le pipeline automatisé qui transforme les coordonnées GPS en matrices de coût binaire `.npy` via NumPy pour la performance.

### 3. Théorie des Graphes : Analyse structurelle (3 min)
*   **Discours** : "Nous modélisons Paris comme un **graphe orienté pondéré**. Mais nous sommes allés plus loin que la simple carte. Nous avons analysé la **Centralité d'Intermédiarité** (Betweenness). Nous avons identifié des hubs critiques comme le **Pont Marie**."
*   **Le chiffre choc** : "Nos tests de robustesse montrent que supprimer seulement **1% de ces hubs** paralyse **60,5% de la connectivité** du quartier. C'est ce qu'on appelle une structure en éventail, très vulnérable."

### 4. Algorithmes de Cheminement (3 min)
*   **Discours** : "Pour la navigation, nous comparons Dijkstra, A* et **A* Bidirectionnel**. Le choix de l'algorithme bidirectionnel avec heuristique Haversine nous a permis de réduire l'exploration des nœuds de **43%** par rapport à un Dijkstra classique. C'est une optimisation invisible pour l'utilisateur mais cruciale pour la fluidité du backend."

### 5. Résolution VRPTW & OR-Tools (4 min)
*   **Discours** : "Pour la tournée globale, nous utilisons **Google OR-Tools**. Nous appliquons une stratégie en deux phases : d'abord une solution initiale rapide par `Path Cheapest Arc`, puis une amélioration via des métaheuristiques comme le **Guided Local Search**. Nous avons également implémenté des post-traitements comme le **ALNS** pour peaufiner les tournées."
*   **Technique** : Mentionne le **K-Means spatial custom** (développé avec NumPy) pour sectoriser la ville avant l'optimisation, garantissant que le système peut passer à l'échelle (Divide & Conquer).

### 6. Résolution IA vs Humain & Rigueur (3 min)
*   **Discours** : "Les résultats sont sans appel : l'IA réduit le temps de trajet de **36,7%** et la distance de **36,1%** par rapport à une approche gloutonne humaine. Mais la performance ne vaut rien sans rigueur. Nous avons mis en place un pipeline de **reproductibilité** (make repro-check) qui utilise des signatures **SHA-256** pour garantir que nos résultats sont 100% déterministes."

### 7. Conclusion & Perspectives (2 min)
*   **Discours** : "Opération Noël prouve que le mélange de Recherche Opérationnelle et d'Open Data peut transformer la logistique urbaine. Nos perspectives ? Intégrer les flux **GTFS** d'Île-de-France Mobilités pour une livraison multimodale (véhicule + métro) et tester des approches de **Reinforcement Learning**."

---

## ❓ Guide Q&A (Questions & Réponses)

### Q1 : "Pourquoi avoir réimplémenté K-Means alors que Scikit-Learn le fait très bien ?"
*   **RÉPONSE** : "Pour une maîtrise totale de la chaîne de calcul et pour éviter d'alourdir les dépendances du backend. L'implémentation en NumPy nous permet de manipuler directement les matrices de distance du projet et de prouver la compréhension algorithmique de l'étape de sectorisation."

### Q2 : "Votre heuristique A* est-elle admissible ? Pourquoi ?"
*   **RÉPONSE** : "Oui, elle est admissible car nous utilisons la distance Haversine divisée par la vitesse maximale autorisée (50 km/h). La distance à vol d'oiseau étant toujours inférieure ou égale à la distance routière réelle, l'heuristique ne surestime jamais le coût restant, ce qui garantit l'optimalité du chemin trouvé."

### Q3 : "Comment gérez-vous le non-déterminisme des métaheuristiques dans OR-Tools ?"
*   **RÉPONSE** : "Nous fixons une **seed aléatoire stable** dérivée du contexte de la mission. De plus, nous avons développé un script `repro_solver_pipeline.py` qui compare les signatures SHA-256 des solutions sur deux passes. Si les signatures divergent, le pipeline échoue, nous forçant à isoler les sources de non-déterminisme."

### Q4 : "Pourquoi le Pont Marie ressort-il comme le nœud le plus critique ?"
*   **RÉPONSE** : "Topologiquement, il sert de 'pont' unique reliant l'Île de la Cité au reste du 5ème arrondissement dans notre périmètre d'extraction. C'est un 'goulot d'étranglement' : une grande partie des plus courts chemins Nord-Sud est contrainte d'emprunter cet arc."

### Q5 : "Quel est l'impact réel de la météo sur vos calculs ?"
*   **RÉPONSE** : "Nous appliquons un `weather_factor` sur la vitesse légale des arcs. Par exemple, un code météo 'Neige' réduit la vitesse de 30%. Cela modifie non seulement le temps total, mais peut changer complètement la structure de la tournée optimale si un axe secondaire devient plus rapide qu'un axe principal congestionné ou glissant."
