"""
Page 2 — Le Quartier Général
L'utilisateur trace ses routes en cliquant sur la carte,
puis l'IA révèle la solution optimale.
"""
import streamlit as st
import streamlit.components.v1 as components
import os, sys, json, random
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium

# ── Project root ──────────────────────────────────────────────────────────────
PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.dirname(PAGES_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BASE_DIR         = ROOT_DIR
DATA_FILE        = os.path.join(BASE_DIR, "core_data", "livraisons_5eme.csv")
WEATHER_FILE     = os.path.join(BASE_DIR, "core_data", "weather_status.json")
RESULTS_FILE     = os.path.join(BASE_DIR, "production_output", "resultats_finaux.json")
MAP_FILE         = os.path.join(BASE_DIR, "production_output", "output_final.html")
BENCHMARK_FILE   = os.path.join(BASE_DIR, "core_data", "benchmark_results.json")
TIME_MATRIX_PATH = os.path.join(BASE_DIR, "core_data", "live_time_matrix.npy")
INCIDENT_MATRIX  = os.path.join(BASE_DIR, "core_data", "live_time_matrix_incident.npy")

from scripts.weather_engine   import get_simulated_weather
from scripts.generator_engine import generate_new_zone
from final_scripts.solve_santa_final import solve_vrp
from final_scripts.main_visualizer   import generate_map
from scripts.benchmark_engine        import calculate_benchmark
from scripts.ui_theme import apply_theme

st.set_page_config(page_title="🗺️ Quartier Général", page_icon="🗺️", layout="wide")

apply_theme()

# ── Constantes ────────────────────────────────────────────────────────────────
WEATHER_MAP = {
    "Clear":        {"condition": "Clear",        "desc": "Ciel dégagé",      "factor": 1.0},
    "Rain":         {"condition": "Rain",          "desc": "Pluie modérée",    "factor": 1.3},
    "Snow":         {"condition": "Snow",          "desc": "Tempête de neige", "factor": 2.0},
    "Thunderstorm": {"condition": "Thunderstorm",  "desc": "Orage violent",    "factor": 2.5},
}
WEATHER_ICONS = {"Clear": "☀️", "Rain": "🌧️", "Snow": "❄️", "Thunderstorm": "⛈️"}

SLEIGH_COLORS = [
    "#E74C3C", "#3498DB", "#27AE60", "#F39C12",
    "#9B59B6", "#1ABC9C", "#E67E22", "#2C3E50",
    "#E91E63", "#795548",
]

# ── Guard ─────────────────────────────────────────────────────────────────────
if "mission" not in st.session_state:
    st.error("❌ Pas de mission configurée. Retournez au Briefing.")
    if st.button("← Retour au Briefing"):
        st.switch_page("app.py")
    st.stop()

mission = st.session_state["mission"]

# ── Budget HUD ────────────────────────────────────────────────────────────────
def render_budget_hud(budget: int, sleigh_cost: int, num_sleighs: int) -> int:
    spent     = num_sleighs * sleigh_cost
    remaining = budget - spent
    pct = max(0.0, min(100.0, remaining / budget * 100)) if budget > 0 else 0.0
    color  = "#27AE60" if pct > 60 else ("#F39C12" if pct > 30 else "#E74C3C")
    pulse  = "animation: pulse-b .8s infinite;" if pct < 20 else ""
    st.markdown(f"""
    <style>
    @keyframes pulse-b {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.35; }} }}
    </style>
    <div style="background:white; padding:14px 22px; border-radius:16px;
                margin-bottom:18px; box-shadow:0 2px 14px rgba(0,0,0,0.07);
                border-left:5px solid {color};">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:800; color:#333; font-size:1em;">💰 Budget Mission</span>
        <span style="font-size:1.5em; font-weight:900; color:{color}; {pulse}">
          {remaining} €
        </span>
      </div>
      <div style="background:#F0E8E0; border-radius:6px; height:10px; margin:10px 0 5px;">
        <div style="background:{color}; width:{pct:.0f}%; height:100%; border-radius:6px;
                    transition:width .4s;"></div>
      </div>
      <span style="color:#999; font-size:.8em;">
        {num_sleighs} traîneau(x) × {sleigh_cost} € = <strong style="color:{color};">{spent} €</strong>
        utilisés / {budget} €
      </span>
    </div>
    """, unsafe_allow_html=True)
    return remaining

# ── En-tête de page ───────────────────────────────────────────────────────────
wkey  = mission.get("weather_key", "?")
wicon = WEATHER_ICONS.get(wkey, "🌦️") if wkey != "random" else "🌦️"
level_str = f"Niveau {mission['level']} · " if mission.get("level") else ""
st.markdown(f"""
<div style="background: linear-gradient(135deg, #FFF3EE, #FFE8DD);
            border-radius:16px; padding:22px 28px; margin-bottom:18px;
            border:1px solid #F0DDD0;">
  <h2 style="margin:0; color:#C0392B; font-size:1.7em;">🗺️ Quartier Général</h2>
  <p style="margin:5px 0 0; color:#888; font-size:.95em;">
    {level_str}{mission.get('zone','?').split(',')[0]}
    &nbsp;·&nbsp; {wicon} {wkey if wkey != 'random' else 'Météo aléatoire'}
    &nbsp;·&nbsp; 👥 {mission.get('num_clients','?')} livraisons
  </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="background:linear-gradient(135deg,#C0392B,#E74C3C); border-radius:12px;
            padding:12px; margin-bottom:14px; text-align:center;">
  <span style="color:white; font-size:1.1em; font-weight:800;">⚙️ Configuration</span>
</div>
""", unsafe_allow_html=True)

max_affordable  = max(1, mission["budget"] // mission["sleigh_cost"])
nb_traineaux    = st.sidebar.slider(
    "Traîneaux", 1, min(10, max_affordable), min(3, max_affordable),
    key="nb_v", help=f"{mission['sleigh_cost']} € / traîneau",
)
st.sidebar.caption(f"💸 {nb_traineaux * mission['sleigh_cost']} € / {mission['budget']} €")
capacite        = st.sidebar.slider("Capacité (kg)", 50, 500, 200, key="capa")
vitesse_label   = st.sidebar.selectbox(
    "Vitesse", ["🐢 Prudent", "🦌 Normal", "🚀 Turbo"], index=1, key="vitesse"
)
speed_map = {"🐢 Prudent": 0.7, "🦌 Normal": 1.0, "🚀 Turbo": 1.5}
speed_val = speed_map[vitesse_label]

st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Couleurs des traîneaux")
line_thickness = st.sidebar.slider("Épaisseur traits", 1, 10, 4)
show_names     = st.sidebar.toggle("Noms clients sur carte IA", value=True)
custom_colors  = []
for i in range(nb_traineaux):
    c = st.sidebar.color_picker(
        f"Traîneau #{i+1}", SLEIGH_COLORS[i % len(SLEIGH_COLORS)], key=f"color_{i}"
    )
    custom_colors.append(c)

st.sidebar.markdown("---")
if st.sidebar.button("🏠 Menu Principal"):
    st.switch_page("app.py")

# ── Budget HUD ────────────────────────────────────────────────────────────────
budget_remaining = render_budget_hud(mission["budget"], mission["sleigh_cost"], nb_traineaux)
can_launch = budget_remaining >= 0

# ── Auto-génération de la zone ────────────────────────────────────────────────
if not st.session_state.get("zone_generated", False):
    with st.spinner(f"🌍 Téléchargement de la zone « {mission['zone']} »…"):
        success, gen_msg = generate_new_zone(mission["zone"], mission["num_clients"])
    if success:
        if gen_msg:
            st.warning(gen_msg)
        with st.spinner("⚙️ Calcul des données de référence…"):
            solve_vrp(num_vehicles=3, vehicle_capacity=200)
            calculate_benchmark(num_vehicles=3)
            generate_map()
        st.session_state["zone_generated"] = True
        st.rerun()
    else:
        st.error("❌ Génération de zone impossible.")
        if gen_msg:
            st.info(gen_msg)
        if st.button("← Retour"):
            st.switch_page("app.py")
        st.stop()

# ── Chargement des données ────────────────────────────────────────────────────
if not os.path.exists(DATA_FILE):
    st.error("❌ Fichier de données introuvable.")
    st.stop()

df          = pd.read_csv(DATA_FILE)
clients_df  = df[df["id"] != 0].reset_index(drop=True)
depot_row   = df[df["id"] == 0].iloc[0]
num_clients = len(clients_df)

# ── Initialisation état routes humaines ──────────────────────────────────────
if (
    "human_routes" not in st.session_state
    or st.session_state.get("route_sleigh_count") != nb_traineaux
):
    st.session_state["human_routes"]      = {i: [] for i in range(nb_traineaux)}
    st.session_state["assigned_clients"]  = set()
    st.session_state["current_sleigh"]    = 0
    st.session_state["route_sleigh_count"]= nb_traineaux
    st.session_state["last_map_click"]    = None
    st.session_state["human_done"]        = False

human_routes   = st.session_state["human_routes"]
assigned       = st.session_state["assigned_clients"]
current_sleigh = min(st.session_state["current_sleigh"], nb_traineaux - 1)
human_done     = st.session_state.get("human_done", False)

# Alerte incidents
if st.session_state.get("incidents_blocked", 0) > 0:
    st.warning(
        f"🚨 **{st.session_state['incidents_blocked']} axe(s) bloqué(s) !** "
        "L'IA recalcule les itinéraires de secours."
    )

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — TRACÉ INTERACTIF DES ROUTES
# ══════════════════════════════════════════════════════════════════════════════
if not human_done:

    n_assigned   = len(assigned)
    n_unassigned = num_clients - n_assigned
    pct_done     = int(n_assigned / num_clients * 100) if num_clients > 0 else 0

    # Instructions
    active_col = custom_colors[current_sleigh % len(custom_colors)]
    st.markdown(f"""
    <div style="background:white; border-radius:14px; padding:14px 20px;
                margin-bottom:14px; box-shadow:0 2px 10px rgba(0,0,0,0.07);
                border-left:5px solid #F39C12;">
      <strong style="color:#E67E22;">📋 Comment jouer</strong>
      &nbsp;—&nbsp;
      <span style="color:#555;">
        Cliquez sur les cercles de la carte pour les ajouter à votre traîneau actif.
        Changez de traîneau avec le sélecteur. Quand vous avez terminé, cliquez sur
        <em>« Voir la solution IA »</em> pour comparer vos itinéraires.
      </span>
    </div>
    """, unsafe_allow_html=True)

    # Sélecteur de traîneau + indicateur de progression
    sel_col, prog_col, badge_col = st.columns([4, 1, 1])

    with sel_col:
        def sleigh_label(i):
            n = len(human_routes[i])
            tick = "✅ " if n > 0 else ""
            arrow = "▶ " if i == current_sleigh else "   "
            return f"{arrow}{tick}🛷 Traîneau #{i+1}  ({n} stops)"

        new_sel = st.selectbox(
            "Traîneau actif",
            range(nb_traineaux),
            format_func=sleigh_label,
            index=current_sleigh,
            key="sleigh_sel",
        )
        if new_sel != current_sleigh:
            st.session_state["current_sleigh"] = new_sel
            current_sleigh = new_sel

    with prog_col:
        col_p = "#27AE60" if pct_done == 100 else ("#F39C12" if pct_done > 50 else "#E74C3C")
        st.markdown(f"""
        <div style="background:white; border-radius:12px; padding:10px 8px;
                    text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08);
                    border:1px solid #EEE5DD; margin-top:4px;">
          <div style="color:{col_p}; font-size:1.5em; font-weight:900;">
            {n_assigned}/{num_clients}
          </div>
          <div style="color:#888; font-size:.72em; line-height:1.2;">clients<br>assignés</div>
        </div>
        """, unsafe_allow_html=True)

    with badge_col:
        st.markdown(f"""
        <div style="background:{active_col}; border-radius:12px; padding:10px 8px;
                    text-align:center; box-shadow:0 2px 10px rgba(0,0,0,0.14);
                    margin-top:4px;">
          <div style="color:white; font-size:1.4em;">🛷</div>
          <div style="color:white; font-size:.72em; font-weight:700; line-height:1.2;">
            Traîneau<br>#{current_sleigh+1}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Construction de la carte Folium ───────────────────────────────────────
    center_lat = float(depot_row["lat"])
    center_lon = float(depot_row["lon"])

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles="CartoDB positron",
    )

    # Tracé des routes existantes
    for sid, route_ids in human_routes.items():
        if route_ids:
            col_r = custom_colors[sid % len(custom_colors)]
            coords = [[center_lat, center_lon]]
            for rid in route_ids:
                r = df[df["id"] == rid]
                if not r.empty:
                    coords.append([float(r.iloc[0]["lat"]), float(r.iloc[0]["lon"])])
            if len(coords) > 1:
                folium.PolyLine(
                    coords,
                    color=col_r,
                    weight=5,
                    opacity=0.85,
                    tooltip=f"🛷 Traîneau #{sid + 1}",
                ).add_to(m)

    # Dépôt
    folium.CircleMarker(
        location=[center_lat, center_lon],
        radius=18,
        color="white",
        weight=3,
        fill=True,
        fill_color="#2C3E50",
        fill_opacity=1.0,
        tooltip="🏠 DÉPÔT CENTRAL — départ et retour de tous les traîneaux",
        popup=folium.Popup("🏠 <b>Dépôt Central</b>", max_width=160),
    ).add_to(m)
    # Emoji home sur le dépôt (non-interactif)
    folium.Marker(
        location=[center_lat, center_lon],
        icon=folium.DivIcon(
            html='<div style="font-size:14px;line-height:1;pointer-events:none;'
                 'margin-top:-6px;margin-left:-5px;">🏠</div>',
            icon_size=(20, 20),
            icon_anchor=(10, 10),
        ),
    ).add_to(m)

    # Marqueurs clients
    for _, row in clients_df.iterrows():
        cid    = int(row["id"])
        lat    = float(row["lat"])
        lon    = float(row["lon"])
        name   = str(row.get("nom_client", f"Client {cid}"))
        weight = int(row.get("poids_colis", 0))

        if cid in assigned:
            # Trouver le traîneau propriétaire
            owner_sid, order_n = current_sleigh, 0
            for sid, route in human_routes.items():
                if cid in route:
                    owner_sid = sid
                    order_n   = route.index(cid) + 1
                    break
            fill_c    = custom_colors[owner_sid % len(custom_colors)]
            tooltip_t = f"✅ Stop #{order_n} — {name} (Traîneau #{owner_sid + 1})"
            radius    = 13
        else:
            fill_c    = "#E74C3C"
            tooltip_t = f"📦 #{cid} · {name} · {weight} kg  — cliquer pour ajouter"
            radius    = 11

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="white",
            weight=2,
            fill=True,
            fill_color=fill_c,
            fill_opacity=0.92,
            tooltip=tooltip_t,
            popup=folium.Popup(
                f"<b>#{cid} {name}</b><br>📦 {weight} kg", max_width=180
            ),
        ).add_to(m)

        # Numéro ou icône au centre du cercle
        if cid in assigned:
            label_html = (
                f'<div style="color:white;font-weight:900;font-size:11px;'
                f'text-align:center;line-height:1;pointer-events:none;'
                f'margin-top:-5px;margin-left:-5px;">{order_n}</div>'
            )
        else:
            label_html = (
                '<div style="font-size:11px;text-align:center;line-height:1;'
                'pointer-events:none;margin-top:-5px;margin-left:-5px;">📦</div>'
            )
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=label_html, icon_size=(10, 10), icon_anchor=(5, 5)
            ),
        ).add_to(m)

    # ── Affichage interactif ───────────────────────────────────────────────────
    map_result = st_folium(m, height=540, key="human_map",
                           returned_objects=["last_object_clicked"])

    # ── Traitement des clics ───────────────────────────────────────────────────
    clicked = map_result.get("last_object_clicked") if map_result else None
    if clicked:
        lat_c = clicked.get("lat")
        lng_c = clicked.get("lng")
        if lat_c is not None:
            click_key = f"{lat_c:.5f},{lng_c:.5f}"
            if click_key != st.session_state.get("last_map_click"):
                st.session_state["last_map_click"] = click_key
                # Client le plus proche (distance L1 en degrés)
                min_dist, nearest_id = float("inf"), None
                for _, row in df.iterrows():
                    cid = int(row["id"])
                    if cid == 0:
                        continue
                    d = abs(float(row["lat"]) - lat_c) + abs(float(row["lon"]) - lng_c)
                    if d < min_dist:
                        min_dist, nearest_id = d, cid
                # Seuil ~400 m en degrés
                if nearest_id is not None and min_dist < 0.005:
                    if nearest_id not in assigned:
                        st.session_state["human_routes"][current_sleigh].append(nearest_id)
                        st.session_state["assigned_clients"].add(nearest_id)
                        st.rerun()

    # ── Contrôles des routes ───────────────────────────────────────────────────
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        if st.button("↩️ Annuler le dernier point", width="stretch"):
            if human_routes[current_sleigh]:
                removed = human_routes[current_sleigh].pop()
                st.session_state["assigned_clients"].discard(removed)
                st.session_state["human_routes"] = human_routes
                st.session_state["last_map_click"] = None
                st.rerun()
    with rc2:
        if st.button("🗑️ Vider ce traîneau", width="stretch"):
            for cid in list(human_routes[current_sleigh]):
                st.session_state["assigned_clients"].discard(cid)
            st.session_state["human_routes"][current_sleigh] = []
            st.session_state["last_map_click"] = None
            st.rerun()
    with rc3:
        if st.button("🔄 Tout réinitialiser", width="stretch"):
            st.session_state["human_routes"]     = {i: [] for i in range(nb_traineaux)}
            st.session_state["assigned_clients"] = set()
            st.session_state["last_map_click"]   = None
            st.rerun()

    # Affichage de la route courante
    if human_routes[current_sleigh]:
        labels = []
        for rid in human_routes[current_sleigh]:
            r = df[df["id"] == rid]
            labels.append(f"#{rid} {r.iloc[0]['nom_client']}" if not r.empty else f"#{rid}")
        route_str = " → ".join(labels)
        st.markdown(f"""
        <div style="background:white; border-left:5px solid {active_col};
                    border-radius:12px; padding:12px 18px; margin-top:10px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);">
          <strong style="color:{active_col};">🛷 Traîneau #{current_sleigh + 1}</strong>
          <span style="color:#555; font-size:.88em;">
            &nbsp;: Dépôt → {route_str} → Dépôt
          </span>
        </div>
        """, unsafe_allow_html=True)

    # Progression
    st.markdown(f"""
    <div style="background:#F0E8E0; border-radius:8px; height:8px; margin:14px 0 8px;">
      <div style="background:{'#27AE60' if pct_done==100 else '#E74C3C'};
                  width:{pct_done}%; height:100%; border-radius:8px;
                  transition:width .4s;"></div>
    </div>
    """, unsafe_allow_html=True)

    if n_unassigned > 0:
        st.caption(f"⚠️ {n_unassigned} client(s) pas encore assigné(s) — vous pouvez quand même lancer l'IA")
    else:
        st.success("✅ Tous les clients sont assignés !")

    # ── Bouton principal ───────────────────────────────────────────────────────
    st.markdown("---")
    if not can_launch:
        st.error(f"❌ Budget insuffisant — réduisez le nombre de traîneaux (max : {max_affordable})")
    else:
        if st.button(
            "🤖 J'ai terminé — Lancer l'IA et voir la solution optimale !",
            type="primary", width="stretch",
        ):
            # Calcul du temps humain
            if os.path.exists(TIME_MATRIX_PATH):
                matrix    = np.load(TIME_MATRIX_PATH)
                total_h   = 0
                for sid, route in human_routes.items():
                    if route:
                        r = [0] + route + [0]
                        total_h += sum(matrix[r[i]][r[i + 1]] for i in range(len(r) - 1))
                st.session_state["human_time_s"] = int(total_h)

            # Météo
            if mission["weather_key"] == "random":
                get_simulated_weather()
                forced_weather = None
            else:
                forced_weather = WEATHER_MAP.get(mission["weather_key"])
                with open(WEATHER_FILE, "w", encoding="utf-8") as fh:
                    json.dump(forced_weather, fh, indent=4, ensure_ascii=False)

            # Incidents aléatoires
            incident_path = None
            if mission.get("random_incidents") and os.path.exists(TIME_MATRIX_PATH):
                bm      = np.load(TIME_MATRIX_PATH)
                n       = len(bm)
                nb      = random.randint(2, 4)
                pairs   = [(i, j) for i in range(1, n) for j in range(1, n) if i != j]
                blocked = random.sample(pairs, min(nb, len(pairs)))
                mm      = bm.copy()
                for (i, j) in blocked:
                    mm[i][j] = min(float(bm[i][j]) * 6.0, 999_999.0)
                np.save(INCIDENT_MATRIX, mm)
                incident_path                        = INCIDENT_MATRIX
                st.session_state["incidents_blocked"] = nb
            else:
                st.session_state["incidents_blocked"] = 0

            # Résolution IA
            with st.spinner("🤖 L'IA optimise les itinéraires…"):
                solve_vrp(
                    num_vehicles=nb_traineaux,
                    vehicle_capacity=capacite,
                    speed_multiplier=speed_val,
                    forced_weather=forced_weather,
                    incident_matrix_path=incident_path,
                )
                budget_spent = nb_traineaux * mission["sleigh_cost"]
                calculate_benchmark(
                    num_vehicles=nb_traineaux,
                    budget_initial=mission["budget"],
                    budget_spent=budget_spent,
                )

            # Génération carte
            with st.spinner("🗺️ Génération de la carte IA…"):
                generate_map(
                    custom_colors=custom_colors,
                    line_weight=line_thickness,
                    show_names=show_names,
                )

            st.session_state["human_done"]  = True
            st.session_state["last_config"] = {
                "nb_traineaux": nb_traineaux,
                "capacite":     capacite,
                "vitesse":      vitesse_label,
                "budget_spent": nb_traineaux * mission["sleigh_cost"],
            }
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — RÉSULTATS : VOTRE ROUTE vs SOLUTION IA
# ══════════════════════════════════════════════════════════════════════════════
else:
    if not (os.path.exists(RESULTS_FILE) and os.path.exists(BENCHMARK_FILE)):
        st.error("❌ Résultats non disponibles.")
        st.stop()

    with open(RESULTS_FILE, "r") as fh:
        res = json.load(fh)
    with open(BENCHMARK_FILE, "r") as fh:
        bench = json.load(fh)

    # Bannière de succès
    st.markdown("""
    <div style="background:linear-gradient(135deg, #27AE60, #2ECC71);
                border-radius:16px; padding:22px 28px; margin-bottom:20px;
                text-align:center; box-shadow:0 4px 20px rgba(39,174,96,.3);">
      <h2 style="color:white; margin:0; font-size:1.9em;">✅ Mission accomplie !</h2>
      <p style="color:rgba(255,255,255,.85); margin:5px 0 0;">
        L'IA a trouvé la solution optimale — comparez avec votre itinéraire.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Météo
    if os.path.exists(WEATHER_FILE):
        with open(WEATHER_FILE, "r") as fh:
            w = json.load(fh)
        wi = "❄️" if w["factor"] >= 2.0 else ("🌧️" if w["factor"] >= 1.3 else "☀️")
        st.info(f"{wi} **{w['desc']}** (×{w['factor']})  ·  **Vitesse :** {vitesse_label}")

    # Métriques
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏱️ Temps IA",      f"{res['total_time_s'] // 60} min")
    m2.metric("📦 Poids livré",   f"{res['total_weight_kg']} kg")
    m3.metric("⚡ Gain vs naïf",
              f"+{bench['savings']['time_saved_min']} min",
              f"{bench['savings']['time_saved_pct']}%")
    m4.metric("🌱 CO₂ économisé", f"{bench['savings']['co2_saved_kg']} kg")

    if res.get("dropped_points"):
        st.error(
            f"⚠️ {len(res['dropped_points'])} colis non livrés — "
            "augmentez la capacité ou le nombre de traîneaux, puis rejouez."
        )

    # ── Votre route vs IA ─────────────────────────────────────────────────────
    human_time_s = st.session_state.get("human_time_s")
    if human_time_s:
        st.markdown("### 🧑 Votre itinéraire  vs  🤖 Solution IA")
        hc1, hc2 = st.columns(2)
        human_min = human_time_s // 60
        ai_min    = res["total_time_s"] // 60
        human_wins = human_time_s < res["total_time_s"]

        def result_card(emoji, label, time_min, wins):
            border = "#27AE60" if wins else "#E74C3C"
            crown  = " 👑" if wins else ""
            win_tag = (
                '<div style="color:#27AE60;font-weight:800;margin-top:10px;font-size:1.05em;">'
                + ("🏆 Vous gagnez !" if emoji == "🧑" else "🏆 L'IA gagne !")
                + "</div>"
            ) if wins else ""
            return f"""
            <div style="background:white; border:3px solid {border}; border-radius:18px;
                        padding:28px 20px; text-align:center;
                        box-shadow:0 6px 24px rgba(0,0,0,0.09);">
              <div style="font-size:3em; line-height:1;">{emoji}{crown}</div>
              <div style="font-weight:800; font-size:1.15em; margin:10px 0 4px; color:#333;">
                {label}
              </div>
              <div style="font-size:2.2em; font-weight:900; color:{border};">{time_min} min</div>
              {win_tag}
            </div>
            """

        with hc1:
            st.markdown(result_card("🧑", "Votre route", human_min, human_wins),
                        unsafe_allow_html=True)
        with hc2:
            st.markdown(result_card("🤖", "Solution IA", ai_min, not human_wins),
                        unsafe_allow_html=True)

        if human_wins:
            st.balloons()

    # ── Carte IA ─────────────────────────────────────────────────────────────
    st.markdown("### 🗺️ Carte de la solution optimale IA")
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, "r", encoding="utf-8") as fh:
            components.html(fh.read(), height=560)

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("---")
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("🔄 Refaire ma route", width="stretch"):
            st.session_state["human_done"]       = False
            st.session_state["human_routes"]     = {i: [] for i in range(nb_traineaux)}
            st.session_state["assigned_clients"] = set()
            st.session_state["last_map_click"]   = None
            st.rerun()
    with nav2:
        if st.button("🏆 VOIR LE DEBRIEFING", type="primary", width="stretch"):
            st.switch_page("pages/2_Debriefing.py")
