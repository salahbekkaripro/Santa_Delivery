# 🎅 Santa Router Optimizer (Pro Edition)

Application de logistique urbaine optimisée utilisant **FastAPI**, **Next.js**, et le moteur de recherche opérationnelle **Google OR-Tools**.

## 🚀 Architecture Moderne

### Backend (FastAPI + Python)
- **Moteur d'Optimisation** : Utilise `OR-Tools` pour résoudre des problèmes de type **VRPTW** (Vehicle Routing Problem with Time Windows).
- **Profils IA** : 
  - ⚡ **Express** : Minimise le temps total de tournée.
  - 🌱 **Écolo** : Minimise la distance totale parcourue.
- **Auto-Suggestion** : Algorithme glouton temps-réel pour aider le joueur à choisir son prochain point de livraison en fonction des contraintes de temps et de charge.
- **Météo Dynamique** : Système de pénalités locales simulant des zones de tempête.
- **Persistence** : SQLite pour le Panthéon (Leaderboard) et le cache des missions.

### Frontend (Next.js + TypeScript)
- **Cartographie** : Leaflet.js pour une visualisation précise des rues OSM.
- **Dashboard** : Graphiques Recharts pour comparer les performances Humain vs IA.
- **Robustesse** : Typage TypeScript strict pour toutes les communications API.

## 🛠️ Installation & Développement

### Prérequis
- Python 3.10+
- Node.js 20+
- Docker & Docker Compose (optionnel)

### Backend
```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🧠 Moteur VRPTW (Constraints)
1. **Capacité** : Chaque traîneau a une charge max (kg).
2. **Fenêtres de Temps** : Certains colis doivent être livrés dans des créneaux horaires stricts.
3. **Incidents** : Des axes routiers peuvent être bloqués aléatoirement.
4. **Météo** : La vitesse est réduite globalement et localement selon les conditions.

## 🏆 Gamification
Le Panthéon enregistre les meilleurs scores basés sur :
- Le gain de temps vs benchmark naïf.
- Les économies de CO2.
- Le respect des délais et du budget.

---
*Dernière mise à jour : Avril 2026*
