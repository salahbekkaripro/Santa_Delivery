import json
import os
import subprocess
from datetime import datetime

# --- CONFIGURATION DES CHEMINS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(BASE_DIR, "production_output", "resultats_finaux.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "daily_reports")

# Génération d'un nom de fichier unique par minute pour éviter d'écraser
timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")
OUTPUT_TEX = os.path.join(OUTPUT_DIR, f"memoire_technique_{timestamp}.tex")

def load_stats():
    """Charge les données réelles issues de la dernière simulation."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ Erreur : {INPUT_FILE} introuvable. Vérifiez que le solveur a tourné.")
        return None
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    # On compte le nombre total de points à partir des tournées et des points droppés
    points_livres = sum(len(t['route_ids']) - 2 for t in data.get("tours", [])) # -2 pour le dépôt (départ et arrivée)
    dropped = len(data.get("dropped_points", []))
    total_points = points_livres + dropped

    return {
        "distance": data.get("total_distance_km", 0.0),
        "dropped": dropped,
        "points_total": total_points,
        "vehicules": len(data.get("tours", [])),
        "capacite_max": 150  # Capacité par traîneau mise à jour
    }

def generate_master_latex(stats):
    """Génère le contenu LaTeX ultra-détaillé du projet."""
    template = rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[french]{{babel}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{xcolor}}
\usepackage{{listings}}
\usepackage{{geometry}}
\usepackage{{hyperref}}
\usepackage{{titlesec}}

% Configuration de la page
\geometry{{margin=2.5cm}}
\definecolor{{santa-red}}{{RGB}}{{195, 13, 35}}
\definecolor{{dark-blue}}{{RGB}}{{32, 56, 100}}

\title{{
    \huge \textbf{{\textcolor{{santa-red}}{{Rapport d'Expertise Logistique}}}} \\
    \vspace{{0.3cm}}
    \large Optimisation Dynamique sur Graphe Routier Réel
}}
\author{{
    \textbf{{Bekkari}} (Ingénierie sur Acer Nitro AN515) \\
    \textit{{En collaboration avec Gemini 1.5 Pro}}
}}
\date{{\today}}

\begin{{document}}

\maketitle
\newpage

\section{{Résumé Exécutif}}
Ce document retrace le cycle de vie complet du projet \texttt{{Santa Router Optimizer}}. Parti d'une simple idée de distribution de cadeaux, le projet a évolué vers une application complexe de \textbf{{Recherche Opérationnelle}} utilisant des données géospatiales massives. Nous détaillons ici le passage d'une vision globale à une exécution locale de haute précision.

\section{{Évolution de la Portée du Projet}}
\subsection{{Flotte de Noël : Passage au Multi-Traîneau}}
Pour répondre à l'augmentation de la demande dans le 5ème arrondissement, nous avons déployé une flotte de \textbf{{{stats['vehicules']} traîneaux}} travaillant en parallèle. 
\textbf{{Optimisation :}} L'utilisation d'une fonction d'équilibrage (\textit{{Global Span Cost}}) permet de répartir équitablement la distance entre les Pères Noël, évitant ainsi qu'un seul livreur ne supporte toute la charge de travail.

\section{{Gestion de la Complexité Routière}}
\subsection{{Le Père Noël au volant : Intégration du Réseau Viaire}}
L'innovation majeure réside dans l'abandon de la distance euclidienne. Pour un réalisme total, le traîneau est désormais soumis aux contraintes de la voirie parisienne.
\begin{{itemize}}
    \item \textbf{{Le Graphe Routier :}} Utilisation d'\texttt{{OSMnx}} pour charger le réseau d'OpenStreetMap.
    \item \textbf{{Algorithme de Dijkstra :}} Chaque trajet entre deux clients est le résultat d'un calcul de "plus court chemin" sur graphe. Le véhicule respecte les sens uniques et la topologie réelle.
\end{{itemize}}

\section{{Analyse des Résultats Algorithmés}}
\begin{{table}}[h]
\centering
\begin{{tabular}}{{lll}}
\toprule
\textbf{{Paramètre}} & \textbf{{Statut}} & \textbf{{Détail}} \\
\midrule
Distance Totale Flotte & {stats['distance']} km & Calculée sur Réseau Routier \\
Nombre de Traîneaux & {stats['vehicules']} & Flotte Parallèle \\
Capacité Max / Traîneau & {stats['capacite_max']} kg & Contrainte de charge \\
Points Livrés & {stats['points_total'] - stats['dropped']} / {stats['points_total']} & Taux de réussite global \\
Points Droppés & {stats['dropped']} & Volume excédant la capacité totale \\
\bottomrule
\end{{tabular}}
\caption{{Indicateurs de performance de la flotte de 3 traîneaux}}
\end{{table}}

\section{{Conclusion}}
Le projet se conclut par une infrastructure logicielle stable capable de gérer une flotte multi-véhicules sur le réseau routier réel de Paris 5e. La robustesse du modèle permet d'envisager une extension à d'autres arrondissements ou l'intégration de contraintes temporelles strictes.

\enddocument
"""
    return template

def save_and_compile(content):
    """Sauvegarde et tente de compiler le PDF."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(OUTPUT_TEX, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"📝 Fichier LaTeX généré : {OUTPUT_TEX}")

    try:
        print("🚀 Compilation PDF en cours (pdflatex)...")
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", OUTPUT_DIR, OUTPUT_TEX],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            print(f"✅ SUCCÈS : Ton mémoire technique est prêt dans {OUTPUT_DIR}")
        else:
            print("❌ Erreur lors de la compilation LaTeX.")
            print(result.stdout[-500:])
    except Exception as e:
        print(f"❌ Erreur lors de la compilation : {e}")

if __name__ == "__main__":
    stats = load_stats()
    if stats:
        latex_content = generate_master_latex(stats)
        save_and_compile(latex_content)