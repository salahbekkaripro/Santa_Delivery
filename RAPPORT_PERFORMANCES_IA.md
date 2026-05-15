# 📊 Rapport de Performance IA vs Humain (TSP 1 véhicule)
Généré le 15/05/2026

Ce benchmark compare l'algorithme **Google OR-Tools** (IA) à une approche **Gloutonne** (Humain) sur un échantillon de 5 missions de 20 clients.

| Métrique | Humain (Glouton) | IA Optimisée | Gain |
| :--- | :--- | :--- | :--- |
| **Temps de trajet** | 1972.3s | **1249.0s** | **36.7%** |
| **Distance totale** | 10.86km | **6.94km** | **36.1%** |

## Analyse des résultats
Contrairement à l'approche gloutonne qui choisit le client le plus proche à chaque étape, l'IA d'OR-Tools utilise des métaheuristiques (Guided Local Search) pour explorer des milliers de combinaisons. Elle évite ainsi les "pièges" topologiques où un humain se retrouverait obligé de faire un long trajet de retour en fin de mission.

## Conclusion pour la soutenance
L'optimisation mathématique permet de réduire les coûts opérationnels de **36.7%** en moyenne. Sur une flotte logistique réelle, cela représente des économies majeures de carburant et de temps de travail.
