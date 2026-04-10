import streamlit as st
import os, sys

# ── Project root ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.ui_theme import apply_theme

st.set_page_config(
    page_title="🎅 Briefing Mission",
    page_icon="🎅",
    layout="centered"
)

# Thème visuel chaleureux (plus plaisant, moins "IA")
apply_theme()

# ── Navigation / state ─────────────────────────────────────────────────────────
def start_mission(m: dict) -> None:
    st.session_state["mission"] = m
    st.session_state["zone_generated"] = False

    # Reset états de run précédents (évite bugs quand on relance une mission)
    for k in (
        "human_routes",
        "assigned_clients",
        "current_sleigh",
        "route_sleigh_count",
        "last_map_click",
        "human_done",
        "incidents_blocked",
        "human_time_s",
        "last_config",
    ):
        st.session_state.pop(k, None)

    # Ne pas naviguer directement dans un callback (Streamlit: rerun() no-op)
    st.session_state["__nav_to_qg"] = True


# Navigation différée (hors callback)
if st.session_state.pop("__nav_to_qg", False):
    st.switch_page("pages/1_Quartier_General.py")
    st.stop()

# CSS Spécifique pour la neige et le titre
st.markdown("""
<style>
/* Animation Neige */
body {
    background-color: #0b1c2c;
    background-image: radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px),
                      radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 30px),
                      radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 40px),
                      radial-gradient(rgba(255,255,255,.4), rgba(255,255,255,.1) 2px, transparent 30px);
    background-size: 550px 550px, 350px 350px, 250px 250px, 150px 150px;
    animation: snow 10s linear infinite;
}
@keyframes snow {
    0% { background-position: 0px 0px, 0px 0px, 0px 0px, 0px 0px; }
    100% { background-position: 500px 1000px, 400px 400px, 300px 300px, 200px 200px; }
}

.title-box {
    background: linear-gradient(135deg, #c0392b, #e74c3c);
    border-radius: 16px;
    padding: 30px;
    text-align: center;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    margin-bottom: 30px;
}
.title-box h1 {
    color: white !important;
    margin: 0;
    font-size: 2.8em;
    font-weight: 900;
}
.level-card {
    background: white;
    border: 2px solid #EEE5DD;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 15px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.level-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    border-color: #E74C3C;
}
</style>
""", unsafe_allow_html=True)

# ── En-tête ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-box">
    <h1>🎅 Opération Noël</h1>
    <p style="font-size: 1.2em; opacity: 0.9; margin-top: 10px;">
        Directeur Logistique, le Pôle Nord a besoin de vous.<br>
        Choisissez votre mission et sauvez le réveillon !
    </p>
</div>
""", unsafe_allow_html=True)

# ── Configuration de la Mission ───────────────────────────────────────────────
mode = st.radio("Sélectionnez un mode de jeu :", ["🏆 Mode Campagne", "🌍 Partie Libre (Sandbox)"], horizontal=True)

mission = {}

if mode == "🏆 Mode Campagne":
    st.markdown("### Sélectionnez un niveau")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="level-card">
            <h3 style="color:#27AE60;">Niveau 1</h3>
            <h4>Paris (Le Marais)</h4>
            <p>☀️ Beau temps<br>👥 10 clients<br>💰 Budget : 1500€<br>❌ Pas d'incidents</p>
        </div>
        """, unsafe_allow_html=True)
        st.button(
            "Jouer Niveau 1",
            key="btn_lvl1",
            width="stretch",
            on_click=start_mission,
            args=(
                {
                    "level": 1,
                    "zone": "Le Marais, Paris",
                    "num_clients": 10,
                    "budget": 1500,
                    "sleigh_cost": 500,
                    "weather_key": "Clear",
                    "random_incidents": False,
                },
            ),
        )
            
    with col2:
        st.markdown("""
        <div class="level-card">
            <h3 style="color:#F39C12;">Niveau 2</h3>
            <h4>Berlin (Mitte)</h4>
            <p>🌧️ Pluie<br>👥 30 clients<br>💰 Budget : 2500€<br>❌ Pas d'incidents</p>
        </div>
        """, unsafe_allow_html=True)
        st.button(
            "Jouer Niveau 2",
            key="btn_lvl2",
            width="stretch",
            on_click=start_mission,
            args=(
                {
                    "level": 2,
                    "zone": "Mitte, Berlin",
                    "num_clients": 30,
                    "budget": 2500,
                    "sleigh_cost": 600,
                    "weather_key": "Rain",
                    "random_incidents": False,
                },
            ),
        )
            
    with col3:
        st.markdown("""
        <div class="level-card">
            <h3 style="color:#E74C3C;">Niveau 3</h3>
            <h4>Montréal (Plateau)</h4>
            <p>❄️ Blizzard<br>👥 50 clients<br>💰 Budget : 4000€<br>🚨 Incidents routiers</p>
        </div>
        """, unsafe_allow_html=True)
        st.button(
            "Jouer Niveau 3",
            key="btn_lvl3",
            width="stretch",
            on_click=start_mission,
            args=(
                {
                    "level": 3,
                    "zone": "Le Plateau-Mont-Royal, Montréal, Québec, Canada",
                    "num_clients": 50,
                    "budget": 4000,
                    "sleigh_cost": 800,
                    "weather_key": "Snow",
                    "random_incidents": True,
                },
            ),
        )

else:
    st.markdown("### Configurez votre partie libre")
    with st.container():
        zone_name = st.text_input("Ville ou quartier (ex: Bordeaux, Tokyo)", "Bordeaux")
        colA, colB = st.columns(2)
        with colA:
            nb_clients = st.slider("Nombre de clients", 10, 100, 40)
            budget = st.slider("Budget de départ (€)", 1000, 10000, 3000, step=500)
        with colB:
            weather_opts = {"Aléatoire": "random", "Soleil ☀️": "Clear", "Pluie 🌧️": "Rain", "Neige ❄️": "Snow", "Tempête ⛈️": "Thunderstorm"}
            w_choice = st.selectbox("Météo", list(weather_opts.keys()))
            incidents = st.toggle("Activer les incidents aléatoires (rues bloquées)", value=False)
            
        st.button(
            "🚀 Créer la mission personnalisée",
            type="primary",
            width="stretch",
            on_click=start_mission,
            args=(
                {
                    "level": None,
                    "zone": zone_name,
                    "num_clients": nb_clients,
                    "budget": budget,
                    "sleigh_cost": 500,
                    "weather_key": weather_opts[w_choice],
                    "random_incidents": incidents,
                },
            ),
        )

st.markdown("---")
st.caption("Pôle Nord Logistics Tech | 2026")
