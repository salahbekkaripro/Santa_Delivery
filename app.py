import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pandas as pd

# Import des modules du projet
from scripts.weather_engine import get_simulated_weather
from scripts.generator_engine import generate_new_zone
from final_scripts.solve_santa_final import solve_vrp
from final_scripts.main_visualizer import generate_map
from scripts.benchmark_engine import calculate_benchmark

# Configuration de la page
st.set_page_config(page_title="Santa-Route Optimizer Pro", page_icon="🎅", layout="wide")

# Chemins des fichiers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')
RESULTS_FILE = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')
MAP_FILE = os.path.join(BASE_DIR, 'production_output', 'output_final.html')
BENCHMARK_FILE = os.path.join(BASE_DIR, 'core_data', 'benchmark_results.json')
DATA_FILE = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')

# --- Header ---
st.title("🎅 Santa-Route Optimizer Pro")
st.markdown("---")

# --- Sidebar (Paramètres personnalisés) ---
st.sidebar.header("⚙️ Configuration Totale")

# 1. Zone & Clients
st.sidebar.subheader("📍 Zone & Clients")
zone_name = st.sidebar.text_input("Quelle zone livrer ?", "Le Marais, Paris")
nb_clients = st.sidebar.slider("Nombre de clients à générer", 10, 100, 30)

if st.sidebar.button("🌍 GÉNÉRER LA ZONE"):
    with st.spinner(f"🌐 Téléchargement de la carte de {zone_name}..."):
        success = generate_new_zone(zone_name, nb_clients)
        if success:
            st.sidebar.success(f"✅ Zone {zone_name} prête !")
            # On force une première optimisation pour avoir un visuel
            solve_vrp(num_vehicles=3, vehicle_capacity=200)
            calculate_benchmark(num_vehicles=3)
            generate_map()
            st.rerun()
        else:
            st.error("❌ Erreur lors de la génération de la zone. Vérifiez le nom.")

st.sidebar.markdown("---")

# 2. Configuration de la Flotte
st.sidebar.subheader("🚚 Flotte de Traîneaux")
nb_traineaux = st.sidebar.slider("Nombre de traîneaux", 1, 10, 3, key="nb_v")
capacite = st.sidebar.slider("Capacité de charge (kg)", 50, 500, 200, key="capa")
vitesse_label = st.sidebar.selectbox("Vitesse moyenne", ["Lent", "Normal", "Rapide"], index=1, key="vitesse")
speed_map = {"Lent": 0.7, "Normal": 1.0, "Rapide": 1.5}
speed_val = speed_map[vitesse_label]

# 3. Configuration Météo
st.sidebar.subheader("🌦️ Conditions Météo")
override_weather = st.sidebar.checkbox("Forcer une météo spécifique ?")
weather_choice = None
if override_weather:
    weather_type = st.sidebar.selectbox("Scénario", ["Soleil", "Pluie", "Neige", "Tempête"])
    weather_data_map = {
        "Soleil": {"condition": "Clear", "desc": "Ciel dégagé", "factor": 1.0},
        "Pluie": {"condition": "Rain", "desc": "Pluie modérée", "factor": 1.3},
        "Neige": {"condition": "Snow", "desc": "Tempête de neige", "factor": 2.0},
        "Tempête": {"condition": "Thunderstorm", "desc": "Orage violent", "factor": 2.5}
    }
    weather_choice = weather_data_map[weather_type]

# 4. Configuration Visuelle
st.sidebar.subheader("🎨 Personnalisation Visuelle")
line_thickness = st.sidebar.slider("Épaisseur des traits", 1, 10, 4)
show_names = st.sidebar.toggle("Afficher les noms des clients", value=True)

# Choix des couleurs
custom_colors = []
default_colors = ['#FF0000', '#00FFFF', '#32CD32', '#FF00FF', '#FFFF00', '#FFA500', '#800080', '#0000FF', '#008000', '#A52A2A']
for i in range(nb_traineaux):
    color = st.sidebar.color_picker(f"Traîneau #{i+1}", default_colors[i % len(default_colors)], key=f"color_{i}")
    custom_colors.append(color)

# --- Bouton de Recalcul ---
if st.sidebar.button("🚀 RECALCULER L'OPTIMISATION"):
    with st.spinner("🎅 Calcul en cours..."):
        try:
            if override_weather:
                with open(WEATHER_FILE, 'w', encoding='utf-8') as f:
                    json.dump(weather_choice, f, indent=4, ensure_ascii=False)
            else:
                get_simulated_weather()
            
            solve_vrp(num_vehicles=nb_traineaux, vehicle_capacity=capacite, speed_multiplier=speed_val)
            calculate_benchmark(num_vehicles=nb_traineaux)
            generate_map(custom_colors=custom_colors, line_weight=line_thickness, show_names=show_names)
            
            st.sidebar.success("✅ Calcul terminé !")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors de l'optimisation : {e}")

if st.sidebar.button("🔄 RAZ"):
    st.session_state.clear()
    st.rerun()

# --- Affichage des Résultats ---
def display_weather_widget():
    if os.path.exists(WEATHER_FILE):
        with open(WEATHER_FILE, 'r', encoding='utf-8') as f:
            w = json.load(f)
            icon = "❄️" if w['factor'] >= 2.0 else ("🌧️" if w['factor'] >= 1.3 else "☀️")
            st.info(f"**Météo actuelle :** {icon} {w['desc']} | **Impact :** x{w['factor']} | **Vitesse Saisie :** {vitesse_label}")

display_weather_widget()

if os.path.exists(RESULTS_FILE) and os.path.exists(BENCHMARK_FILE):
    with open(RESULTS_FILE, 'r') as f:
        res = json.load(f)
    with open(BENCHMARK_FILE, 'r') as f:
        bench = json.load(f)
    
    # Métriques
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Temps Total", f"{res['total_time_s'] // 60} min")
    m2.metric("Poids Livré", f"{res['total_weight_kg']} kg")
    m3.metric("Gain Temps", f"+{bench['savings']['time_saved_min']} min", f"{bench['savings']['time_saved_pct']}%")
    m4.metric("CO2 Évité", f"{bench['savings']['co2_saved_kg']} kg", "🌱")

    # Carte
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
            components.html(html_content, height=600)
    
    st.success(f"🚀 **Performance IA :** {bench['savings']['score']}% d'efficacité.")
    
    if res['dropped_points']:
        st.error(f"⚠️ {len(res['dropped_points'])} colis non livrés. Ajustez la capacité ou le nombre de traîneaux.")
else:
    st.info("👋 Prêt pour une nouvelle tournée ? Configurez une zone et cliquez sur 'Générer la zone'.")

st.markdown("---")
st.caption("Santa-Route Optimizer Pro | Propulsé par OSMnx & OSRM | 2026")
