#!/bin/bash

# Script de nettoyage des anciens rapports et fichiers temporaires LaTeX
# Projet : Santa Router Optimizer

echo "🚀 Début du nettoyage approfondi du système de reporting..."

# 1. SUPPRESSION DES ANCIENS PDF/TEX À LA RACINE
echo "📄 Suppression des fichiers .tex et .pdf à la racine du projet..."
rm -f ./*.tex ./*.pdf

# 2. VIDAGE DU DOSSIER daily_reports/
if [ -d "daily_reports" ]; then
    echo "🧹 Vidage du dossier daily_reports/ pour repartir sur une base neuve..."
    rm -rf daily_reports/*
else
    echo "📁 Dossier daily_reports/ non trouvé, création d'une structure propre..."
    mkdir -p daily_reports
fi

# 3. NETTOYAGE RÉCURSIF DES FICHIERS TEMPORAIRES LATEX
echo "📝 Suppression récursive des fichiers temporaires (.aux, .log, .out, .toc, .synctex.gz)..."
find . -type f \( -name "*.aux" -o -name "*.log" -o -name "*.out" -o -name "*.toc" -o -name "*.synctex.gz" \) -delete

# 4. MESSAGE DE SUCCÈS ET MISE À JOUR DU CONTEXTE
echo ""
echo "✅ NETTOYAGE TERMINÉ AVEC SUCCÈS !"
echo "--------------------------------------------------------"
echo "ℹ️  Rappel de la nouvelle structure de reporting :"
echo "   - Générateur : scripts/daily_reporter.py"
echo "   - Destination : daily_reports/"
echo "   - Référence  : Seul le rapport détaillé est désormais valide."
echo "--------------------------------------------------------"
echo "Le dossier 'Noel' est maintenant parfaitement propre. ✨"
