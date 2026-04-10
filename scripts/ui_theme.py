import streamlit as st


def apply_theme() -> None:
    """
    Applique un thème global lisible (contraste) sur toutes les pages Streamlit.
    Objectif: éviter le texte blanc sur fond clair quand du CSS "Noël" persiste
    d'une page à l'autre.
    """
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

:root{
  --bg: #FFF9F5;
  --sidebar: #FFF3EE;
  --card: #FFFFFF;
  --border: #EEE5DD;
  --text: #1F2937;
  --muted: #6B7280;
  --accent: #E74C3C;
}

html, body, [class*="css"]{
  font-family: 'Nunito', sans-serif !important;
}

/* Containers */
[data-testid="stAppViewContainer"], .stApp{
  background: var(--bg) !important;
}
[data-testid="stSidebar"], .stSidebar > div{
  background: var(--sidebar) !important;
}

/* Global text (laisse les styles inline/custom gagner) */
[data-testid="stMarkdownContainer"]{
  color: var(--text);
}
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6{
  color: var(--text);
  text-shadow: none;
}
label, .stCaption, [data-testid="stWidgetLabel"]{
  color: var(--text);
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea{
  background: var(--card) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stMultiSelect"] > div > div{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}

/* Buttons */
.stButton > button{
  border-radius: 14px !important;
  font-weight: 800 !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
}
.stButton > button:focus:not(:focus-visible){
  box-shadow: none !important;
}

/* Metrics + alerts */
[data-testid="stMetric"]{
  background: var(--card) !important;
  border-radius: 16px !important;
  padding: 16px 20px !important;
  box-shadow: 0 2px 14px rgba(0,0,0,0.07) !important;
  border: 1px solid var(--border) !important;
}
[data-testid="stMetricLabel"]{
  color: var(--muted) !important;
  font-weight: 800 !important;
}
[data-testid="stMetricValue"]{
  font-weight: 900 !important;
  color: var(--text) !important;
}
.stAlert, [data-testid="stInfo"], [data-testid="stSuccess"], [data-testid="stWarning"], [data-testid="stError"]{
  border-radius: 14px !important;
}

/* Links + code */
a, a:visited{
  color: #B91C1C !important;
}
a:hover{
  color: #7F1D1D !important;
}
code{
  background: rgba(0,0,0,0.05) !important;
  color: var(--text) !important;
  border-radius: 6px !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )
