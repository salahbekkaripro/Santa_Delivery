import streamlit as st
import os
import sys
import json
import datetime

import plotly.graph_objects as go

# ── Project root on sys.path ──────────────────────────────────────────────────
PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.dirname(PAGES_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.ui_theme import apply_theme

BASE_DIR        = ROOT_DIR
RESULTS_FILE    = os.path.join(BASE_DIR, "production_output", "resultats_finaux.json")
BENCHMARK_FILE  = os.path.join(BASE_DIR, "core_data", "benchmark_results.json")
HIGH_SCORES_FILE= os.path.join(BASE_DIR, "core_data", "high_scores.json")

st.set_page_config(
    page_title="🏆 Debriefing",
    page_icon="🏆",
    layout="wide",
)

apply_theme()

# ── Guard: need results ───────────────────────────────────────────────────────
if not (os.path.exists(RESULTS_FILE) and os.path.exists(BENCHMARK_FILE)):
    st.error("❌ Aucun résultat disponible. Lancez d'abord une mission au Quartier Général.")
    if st.button("← Retour au QG"):
        st.switch_page("pages/1_Quartier_General.py")
    st.stop()

with open(RESULTS_FILE, "r") as fh:
    res = json.load(fh)
with open(BENCHMARK_FILE, "r") as fh:
    bench = json.load(fh)

mission = st.session_state.get("mission", {})

# ── Score & rank computation ──────────────────────────────────────────────────
time_saved_pct      = bench["savings"]["time_saved_pct"]
co2_saved_kg        = bench["savings"]["co2_saved_kg"]
budget_remaining_pct= bench.get("budget", {}).get("remaining_pct", 50.0)

# Normalize CO2 to 0-100 (cap at 20 kg as reference for a Paris zone)
co2_score = min(co2_saved_kg / 20.0 * 100.0, 100.0)

final_score = (
    0.60 * time_saved_pct
    + 0.25 * co2_score
    + 0.15 * budget_remaining_pct
)

# Incident bonus
incidents_active = mission.get("random_incidents", False)
if incidents_active:
    final_score = min(final_score + 10.0, 100.0)

# Human beat AI bonus
human_time_s = st.session_state.get("human_time_s", None)
human_beat_ai = human_time_s is not None and human_time_s < res["total_time_s"]
if human_beat_ai:
    final_score = min(final_score + 5.0, 100.0)

final_score = round(final_score, 1)


def compute_rank(score: float) -> tuple[str, str, str]:
    if score >= 85:
        return "S", "🥇 Éco-Livreur Légendaire", "#f1c40f"
    elif score >= 70:
        return "A", "🥈 Chef Logisticien",        "#95a5a6"
    elif score >= 50:
        return "B", "🥉 Livreur Efficace",        "#cd7f32"
    elif score >= 30:
        return "C", "🎖️ Apprenti Père Noël",     "#3498db"
    else:
        return "D", "🎅 En formation…",           "#e74c3c"


rank, rank_title, rank_color = compute_rank(final_score)

# ── Persist high score ────────────────────────────────────────────────────────
def save_high_score():
    try:
        with open(HIGH_SCORES_FILE, "r") as fh:
            hs = json.load(fh)
    except (json.JSONDecodeError, FileNotFoundError):
        hs = {"1": [], "2": [], "3": [], "libre": []}

    level_key = str(mission.get("level")) if mission.get("level") else "libre"
    if level_key not in hs:
        hs[level_key] = []

    entry = {
        "score": final_score,
        "rank": rank,
        "zone": mission.get("zone", "?"),
        "time_saved_pct": time_saved_pct,
        "co2_saved_kg": co2_saved_kg,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    hs[level_key].append(entry)
    hs[level_key] = sorted(hs[level_key], key=lambda x: x["score"], reverse=True)[:5]

    with open(HIGH_SCORES_FILE, "w") as fh:
        json.dump(hs, fh, indent=2, ensure_ascii=False)

    return hs, level_key


if "score_saved" not in st.session_state:
    high_scores, level_key = save_high_score()
    st.session_state["score_saved"] = True
    st.session_state["high_scores"] = high_scores
    st.session_state["hs_level_key"] = level_key
else:
    try:
        with open(HIGH_SCORES_FILE, "r") as fh:
            high_scores = json.load(fh)
    except (json.JSONDecodeError, FileNotFoundError):
        high_scores = {"1": [], "2": [], "3": [], "libre": []}
    level_key = st.session_state.get("hs_level_key", "libre")

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d1b2a,#1b2838,#0d1b2a);
            border:1px solid {rank_color};border-radius:16px;
            padding:30px;text-align:center;margin-bottom:24px;">
  <h1 style="color:{rank_color};font-size:2.5em;margin:0;">🏆 Debriefing Mission</h1>
  <p style="color:#95a5a6;margin:6px 0 0;">
    Zone : <strong style="color:#ecf0f1">{mission.get('zone','?')}</strong>
    &nbsp;|&nbsp;
    Mode : <strong style="color:#ecf0f1">{('Niveau ' + str(mission.get('level'))) if mission.get('level') else 'Partie Libre'}</strong>
  </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# RANK CARD
# ═══════════════════════════════════════════════════════════════════════════════
rc1, rc2, rc3 = st.columns([1, 2, 1])
with rc2:
    st.markdown(f"""
    <div style="background:#1a1a2e;border:3px solid {rank_color};border-radius:16px;
                padding:30px;text-align:center;">
      <div style="font-size:5em;line-height:1;">{rank}</div>
      <div style="color:{rank_color};font-size:1.6em;font-weight:bold;margin:10px 0 6px;">
        {rank_title}
      </div>
      <div style="color:#ecf0f1;font-size:2em;font-weight:bold;">{final_score} pts</div>
      <div style="color:#95a5a6;font-size:0.85em;margin-top:8px;">
        {"⚡ Bonus : Incidents survécus (+10 pts)" if incidents_active else ""}
        {"&nbsp;|&nbsp;" if incidents_active and human_beat_ai else ""}
        {"🧑 Bonus : Vous avez battu l'IA (+5 pts)" if human_beat_ai else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# KEY METRICS
# ═══════════════════════════════════════════════════════════════════════════════
m1, m2, m3, m4 = st.columns(4)
m1.metric("⏱️ Temps Optimisé",   f"{res['total_time_s'] // 60} min")
m2.metric("⚡ Gain vs Naïf",    f"+{bench['savings']['time_saved_min']} min", f"{time_saved_pct}%")
m3.metric("🌱 CO₂ Économisé",   f"{co2_saved_kg} kg",
          f"≈ {co2_saved_kg / 21.0:.1f} arbres/an")
m4.metric("💰 Budget Restant",
          f"{bench.get('budget',{}).get('remaining', '?')}€",
          f"{budget_remaining_pct:.1f}%")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# AI vs HUMAN COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🤖 IA Santa vs 🧑 Vous")

ai_time_min  = res["total_time_s"] // 60
naive_time_min = bench["naive"]["total_time_s"] // 60

aic, hc = st.columns(2)

with aic:
    ai_wins = human_time_s is None or res["total_time_s"] <= human_time_s
    border  = "#2ecc71" if ai_wins else "#e74c3c"
    crown   = " 👑" if ai_wins else ""
    st.markdown(f"""
    <div style="background:#1a1a2e;border:2px solid {border};
                border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:2.5em;">🤖{crown}</div>
      <div style="color:#ecf0f1;font-size:1.2em;font-weight:bold;margin:8px 0;">IA Santa</div>
      <div style="color:{border};font-size:1.8em;font-weight:bold;">{ai_time_min} min</div>
      <div style="color:#95a5a6;font-size:0.85em;margin-top:4px;">
        {bench['savings']['co2_saved_kg']} kg CO₂ économisé
      </div>
      {"<div style='color:#2ecc71;margin-top:8px;font-weight:bold;'>✅ VICTOIRE !</div>" if ai_wins else ""}
    </div>
    """, unsafe_allow_html=True)

with hc:
    if human_time_s is not None:
        h_time_min = human_time_s // 60
        h_wins  = human_time_s < res["total_time_s"]
        h_border= "#2ecc71" if h_wins else "#e74c3c"
        h_crown = " 👑" if h_wins else ""
        st.markdown(f"""
        <div style="background:#1a1a2e;border:2px solid {h_border};
                    border-radius:12px;padding:20px;text-align:center;">
          <div style="font-size:2.5em;">🧑{h_crown}</div>
          <div style="color:#ecf0f1;font-size:1.2em;font-weight:bold;margin:8px 0;">Vous</div>
          <div style="color:{h_border};font-size:1.8em;font-weight:bold;">{h_time_min} min</div>
          <div style="color:#95a5a6;font-size:0.85em;margin-top:4px;">Route manuelle</div>
          {"<div style='color:#2ecc71;margin-top:8px;font-weight:bold;'>🏆 Incroyable ! Vous avez battu l'IA !</div>" if h_wins else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#1a1a2e;border:2px solid #444;
                    border-radius:12px;padding:20px;text-align:center;opacity:0.5;">
          <div style="font-size:2.5em;">🧑</div>
          <div style="color:#ecf0f1;font-size:1.2em;margin:8px 0;">Vous</div>
          <div style="color:#95a5a6;">Pas d'essai humain</div>
          <div style="color:#666;font-size:0.8em;margin-top:8px;">
            Retournez au QG pour tenter votre chance !
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE CHART
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Analyse des Performances")

naive_dist_km = bench["naive"]["total_dist_m"] / 1000.0
opt_dist_km   = bench["optimized"]["total_dist_m"] / 1000.0

categories = ["Temps (min)", "Distance (km)"]
naive_vals  = [naive_time_min, round(naive_dist_km, 1)]
opt_vals    = [ai_time_min,    round(opt_dist_km,   1)]

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Naïf (sans IA)",
    x=categories,
    y=naive_vals,
    marker_color="#e74c3c",
    text=[f"{v}" for v in naive_vals],
    textposition="outside",
))
fig.add_trace(go.Bar(
    name="IA Optimisé",
    x=categories,
    y=opt_vals,
    marker_color="#2ecc71",
    text=[f"{v}" for v in opt_vals],
    textposition="outside",
))
if human_time_s is not None:
    fig.add_trace(go.Bar(
        name="Vous",
        x=["Temps (min)"],
        y=[human_time_s // 60],
        marker_color="#3498db",
        text=[f"{human_time_s // 60}"],
        textposition="outside",
    ))

fig.update_layout(
    barmode="group",
    template="plotly_dark",
    title="Naïf vs IA vs Humain",
    yaxis_title="Valeur",
    showlegend=True,
    height=400,
    margin=dict(t=40, b=20),
)
st.plotly_chart(fig, use_container_width=True)

# CO2 context
trees = co2_saved_kg / 21.0
st.info(
    f"🌳 **Impact environnemental :** En économisant **{co2_saved_kg} kg de CO₂**, "
    f"c'est l'équivalent de **{trees:.1f} arbres** qui absorbent du CO₂ pendant 1 an. "
    f"(1 arbre ≈ 21 kg CO₂/an)"
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# HIGH SCORES BOARD
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🏅 Classement des Meilleurs Scores")

level_label = f"Niveau {mission.get('level')}" if mission.get("level") else "Partie Libre"
st.caption(f"Top 5 — {level_label}")

level_scores = high_scores.get(level_key, [])
if level_scores:
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, entry in enumerate(level_scores):
        is_current = (
            entry["score"] == final_score
            and entry["date"] == level_scores[idx].get("date", "")
            and idx == 0
        )
        bg      = "#1a2e1a" if is_current else "#1a1a2e"
        border  = "#2ecc71" if is_current else "#333"
        you_tag = " ← **Vous**" if is_current else ""
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {border};
                    border-radius:8px;padding:12px 16px;margin-bottom:8px;
                    display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:1.4em;">{medals[idx]}</span>
          <span style="color:#ecf0f1;font-weight:bold;font-size:1.1em;">{entry['score']} pts</span>
          <span style="color:#95a5a6;font-size:0.85em;">{entry['rank']} — {entry['zone'].split(',')[0]}</span>
          <span style="color:#666;font-size:0.8em;">{entry['date']}</span>
        </div>
        """, unsafe_allow_html=True)
        if is_current:
            st.markdown(f"*← Votre score actuel*")
else:
    st.info("Pas encore de scores enregistrés pour ce niveau.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION BUTTONS
# ═══════════════════════════════════════════════════════════════════════════════
col_a, col_b = st.columns(2)
with col_a:
    if st.button("🔄 REJOUER cette mission", width="stretch"):
        st.session_state.pop("score_saved", None)
        st.session_state.pop("human_time_s", None)
        st.session_state.pop("incidents_blocked", None)
        st.session_state["zone_generated"] = True  # zone already downloaded
        st.switch_page("pages/1_Quartier_General.py")
with col_b:
    if st.button("🏠 MENU PRINCIPAL", type="primary", width="stretch"):
        for key in ["mission", "zone_generated", "score_saved", "human_time_s",
                    "incidents_blocked", "last_config", "hs_level_key", "high_scores"]:
            st.session_state.pop(key, None)
        st.switch_page("app.py")

st.markdown("---")
st.caption("🎅 Opération Noël — Santa Strategy | Propulsé par OSMnx, OSRM & Google OR-Tools | 2026")
