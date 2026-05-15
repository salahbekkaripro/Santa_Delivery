# 🧠 Analyse Algorithmique : Clustering & Sectorisation

Ce rapport explique l'implémentation du clustering spatial pour optimiser la logistique à grande échelle dans le projet **Operation Noël**.

## 1. Problématique : La complexité du VRP
Le problème de tournées de véhicules (VRP) est **NP-difficile**. Plus le nombre de clients augmente, plus le temps de calcul du solveur (OR-Tools) croît de manière exponentielle. Pour une flotte de 1000 clients, une résolution globale peut prendre plusieurs heures.

## 2. Solution : L'approche "Divide & Conquer"
Pour garantir la scalabilité du système, nous avons implémenté une étape de **sectorisation spatiale** avant l'optimisation des tournées :
1.  **Clustering** : Division de la zone géographique en $K$ secteurs (un par traîneau).
2.  **Optimisation Locale** : Résolution d'un TSP (Traveling Salesman Problem) indépendant à l'intérieur de chaque secteur.

## 3. Algorithme : K-Means Spatial (Implémentation Custom)
Nous avons implémenté l'algorithme des **K-Moyennes** (K-Means) à l'aide de `NumPy`. L'algorithme fonctionne par itérations successives :
-   **Initialisation** : Choix aléatoire de $K$ centroïdes.
-   **Attribution** : Chaque client est assigné au secteur dont le centre est le plus proche.
-   **Mise à jour** : Le centre de chaque secteur est recalculé en prenant la moyenne des positions de ses clients.
-   **Convergence** : On s'arrête quand les zones ne bougent plus.

## 4. Résultats du Clustering (Paris 5ème)
Sur un échantillon de mission standard, la sectorisation permet une répartition équilibrée de la charge :
-   **Zone 0** (Nord-Ouest) : 2 clients.
-   **Zone 1** (Est) : 5 clients.
-   **Zone 2** (Sud-Est) : 3 clients.

*Note : Une carte interactive `production_output/clustering_map.html` est générée automatiquement pour visualiser ces secteurs.*

## 5. Avantages pour la Soutenance
-   **Maîtrise Algorithmique** : Preuve que l'équipe sait implémenter des algorithmes de Data Science sans dépendre uniquement de bibliothèques tierces (scikit-learn).
-   **Scalabilité** : Capacité à traiter des milliers de points en parallélisant les calculs par secteur.
-   **Interprétabilité** : Les zones de livraison sont logiques et stables, ce qui facilite le travail des livreurs sur le terrain.
