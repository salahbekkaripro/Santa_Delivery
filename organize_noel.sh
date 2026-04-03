#!/bin/bash

# 1. CRÉATION DES DOSSIERS PROPRES
mkdir -p core_data
mkdir -p final_scripts
mkdir -p production_output

# 2. CONSERVATION DE LA "CRÈME DE LA CRÈME"
# Déplacement des données sources
mv livraisons_5eme.csv core_data/ 2>/dev/null
mv matrix_5eme.npy core_data/ 2>/dev/null

# Déplacement des scripts finaux
mv generate_final_map.py final_scripts/ 2>/dev/null
mv solve_santa_final.py final_scripts/ 2>/dev/null

# Déplacement et renommage de l'output
mv resultats_finaux.json production_output/ 2>/dev/null
if [ -f "CARTE_FINALE_SANTA.html" ]; then
    mv CARTE_FINALE_SANTA.html production_output/output_final.html
fi

# 3. SUPPRESSION RADICALE (Tout ce qui reste à la racine)
echo "Nettoyage des fichiers obsolètes..."
rm -f compute_local_matrix.py debug_santa.py extract_1000_paris.py \
      extract_deliveries.py extract_only_5eme.py santa_v2_resilient.py \
      solve_santa_5eme.py visualize_points.py diagnose_vrp.py \
      santa_dynamic_map.py visualize_final_routes.py visualize_santa_pro.py \
      santa_final_fixed.py santa_final_moving.py santa_final_glisse.py 2>/dev/null

rm -f visualisation_noel.html santa_tour_dynamic.html santa_final_fixed.html \
      santa_fixed_moving.html santa_glisse_final.html 2>/dev/null

rm -f livraisons_1000.csv livraisons.csv matrix_local.npy 2>/dev/null

# 4. AJUSTEMENT DES CHEMINS (Scripts finaux)
echo "Ajustement des chemins dans les scripts..."

# Pour generate_final_map.py
sed -i "s/'livraisons_5eme.csv'/'..\/core_data\/livraisons_5eme.csv'/g" final_scripts/generate_final_map.py
sed -i "s/'resultats_finaux.json'/'..\/production_output\/resultats_finaux.json'/g" final_scripts/generate_final_map.py
sed -i "s/'CARTE_FINALE_SANTA.html'/'..\/production_output\/output_final.html'/g" final_scripts/generate_final_map.py

# (Optionnel mais recommandé) Pour solve_santa_final.py
sed -i "s/'livraisons_5eme.csv'/'..\/core_data\/livraisons_5eme.csv'/g" final_scripts/solve_santa_final.py
sed -i "s/'matrix_5eme.npy'/'..\/core_data\/matrix_5eme.npy'/g" final_scripts/solve_santa_final.py
sed -i "s/'resultats_finaux.json'/'..\/production_output\/resultats_finaux.json'/g" final_scripts/solve_santa_final.py

echo "Organisation terminée avec succès ! 🎅"
echo "Structure actuelle :"
ls -R core_data final_scripts production_output
