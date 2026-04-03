🎅 Project : Santa Router Optimizer (Dynamic Edition)

Ce document décrit le fonctionnement de l'application de livraison optimisée utilisant des données réelles issues d'OpenStreetMap et des algorithmes de théorie des graphes.

🛠️ 1. Concept de l'Application

L'utilisateur définit deux paramètres :
- La Ville : (ex: "Paris", "Lyon", "Tokyo") récupérée via l'API Nominatim.
- Le Nombre de Colis : Une quantité N de points de livraison générés aléatoirement sur des adresses réelles de la ville.

🏗️ 2. Architecture des Données

Puisque le dataset est dynamique, nous utilisons une structure de données hybride :
A. Extraction (OpenStreetMap / Overpass API)
Nous interrogeons OSM pour extraire les nœuds possédant des tags spécifiques :
- addr:housenumber (Maisons)
- building=residential (Immeubles)

B. Stockage Temporaire (SQLite / Mémoire)
Pour chaque session, une base de données est créée pour générer la Matrice des Coûts.
Table	Colonne	Type
Points	id, lat, lon, est_depot	Float / Bool
Graphe	source_id, target_id, distance_m	Integer / Float

🧠 3. Moteur d'Optimisation (Le Graphe)

Pour transformer la ville en itinéraire, le système suit ces étapes :
- Génération du Graphe Routier : Utilisation de la bibliothèque OSMnx pour modéliser les rues réelles du 5ème arrondissement.
- Calcul de la Matrice de Distances : Utilisation de l'algorithme de Dijkstra pour calculer les distances réelles par les rues entre chaque point.
- Résolution du VRP : Le moteur Google OR-Tools optimise les tournées en se basant sur ces distances réelles.
- Contrainte de Capacité (VRP) : Si le traîneau est plein, l'algorithme force un retour au nœud marqué comme est_depot avant de repartir.

🌐 4. Interface Dynamique (Frontend)

L'affichage repose sur Leaflet.js (via Folium) :
- Tracé Réel : Les itinéraires (AntPath) suivent précisément les rues grâce aux nœuds du graphe OSMnx.
- Marqueurs : Icônes de maison noire pour le dépôt, CircleMarkers colorés pour les livraisons réussies, et avertissements gris pour les points ignorés.

🚦 5. Workflow de Développement

- Input : City_Name + Package_Count.
- Geocoding : Convertir le nom de la ville en boîte de coordonnées (Bounding Box).
- Sampling : Tirer au sort N adresses dans la zone.
- Solveur : Lancer l'algorithme d'optimisation en Python.
- Render : Envoyer le JSON des coordonnées à la carte web pour l'animation.

📂 6. Organisation des Fichiers (Post-Nettoyage)
- core_data/ : Contient 'livraisons_5eme.csv' et 'matrix_5eme.npy'.
- final_scripts/ : 
    - 'solve_santa_final.py' (Moteur d'optimisation OR-Tools).
    - 'main_visualizer.py' (Générateur de carte Folium AntPath).
- production_output/ : 'resultats_finaux.json' et 'output_final.html'.

🚀 7. Instructions d'Exécution
1. Calculer la tournée : python3 final_scripts/solve_santa_final.py
2. Générer la visualisation : python3 final_scripts/main_visualizer.py

📅 8. Améliorations Futures
- [ ] Gestion du trafic en temps réel.
- [ ] Prise en compte de la météo (neige = vitesse réduite).
- [ ] Mode "Multitraineau" (plusieurs livreurs en parallèle).
