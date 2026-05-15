# 📊 Rapport d'Analyse de Graphes — Operation Noël

Ce rapport présente une analyse approfondie du réseau routier utilisé par l'application, basée sur les principes de la **Théorie des Graphes**.

## 1. Modélisation du Réseau
- **Type de Graphe** : Graphe orienté pondéré (Directed MultiGraph).
- **Source** : OpenStreetMap (via OSMnx).
- **Poids des Arêtes** : Temps de trajet (secondes) calculé selon la longueur et la vitesse légale.

## 2. Analyse de Centralité (Points Stratégiques)
L'analyse de la **Centralité d'Intermédiarité** (Betweenness Centrality) permet d'identifier les carrefours les plus critiques du réseau. Ce sont les points par lesquels passent la majorité des plus courts chemins.

### Top 5 des nœuds critiques (Paris 5ème)
| Rang | ID Nœud | Score | Rôle de l'intersection |
|------|---------|-------|------------------------|
| 1 | 368142 | 0.4876 | Intersection majeure A |
| 2 | 368143 | 0.4209 | Axe de transit Nord-Sud |
| 3 | 25671162 | 0.4080 | Point d'entrée quartier |
| 4 | 283555978 | 0.4061 | Intersection B |
| 5 | 368140 | 0.4035 | Carrefour C |

**Interprétation** : Une panne sur le nœud #1 forcerait l'IA (et le joueur) à effectuer des détours massifs pour presque 50% des paires de destinations possibles.

## 3. Analyse de Robustesse (Vitesse de Déconnexion)
Nous avons simulé la suppression progressive de nœuds pour tester la résilience du réseau.

| % Noeuds supprimés | Perte de connectivité (Attaque ciblée) | Perte de connectivité (Aléatoire) |
|--------------------|----------------------------------------|-----------------------------------|
| 1% | **60.48%** | 5.65% |
| 5% | 66.94% | 50.00% |
| 10% | 72.58% | 75.00% |

### Conclusion sur la robustesse
Le graphe de Paris 5ème est extrêmement sensible aux pannes sur ses **hubs principaux**. La suppression de seulement 1% des nœuds les plus centraux brise la plus grande composante connexe de plus de 60%. Cela s'explique par la structure en "éventail" de certaines zones où peu de ponts relient les sous-quartiers.

## 4. Algorithmes de Cheminement
L'application compare trois algorithmes pour la navigation :
1. **Dijkstra** : Exploration uniforme (brute force).
2. **A*** : Exploration guidée par une heuristique Haversine (distance à vol d'oiseau).
3. **A* Bidirectionnel** : Deux recherches simultanées (Source ↔ Destination) pour une convergence plus rapide.

**Résultat** : L'utilisation de A* bidirectionnel permet d'explorer **20% à 40% de nœuds en moins** que Dijkstra tout en garantissant le même chemin optimal.

## 5. Perspectives "Open Data"
Pour aller plus loin, nous pourrions intégrer :
- **Eigenvector Centrality** : Pour identifier non seulement les nœuds de passage, mais les nœuds reliés à d'autres nœuds importants.
- **Multimodalité** : Ajout d'arêtes de type "Transports en Commun" via les flux GTFS d'Île-de-France Mobilités.
