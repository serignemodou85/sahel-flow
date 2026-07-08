import plotly.graph_objects as go
import streamlit as st

from api_client import get_health, get_risk_scores

st.set_page_config(
    page_title="Sahel Flow — Sécurité Alimentaire UEMOA",
    page_icon="🌍",
    layout="wide",
)

# ── Sidebar commercial ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 Sahel Flow")
    st.caption("Surveillance de la sécurité alimentaire")
    st.markdown("---")

    health = get_health()
    api_ok = health.get("status") == "ok" and health.get("db") == "ok"
    if api_ok:
        st.success("Système opérationnel", icon="✅")
    else:
        st.warning("Service dégradé", icon="⚠️")

    st.markdown("---")
    st.markdown("**Zone couverte**")
    st.markdown("UEMOA — Afrique de l'Ouest")
    st.markdown("🇸🇳 Sénégal &nbsp;·&nbsp; 🇨🇮 Côte d'Ivoire")
    st.markdown("---")
    st.markdown("**Mise à jour des données**")
    st.caption("Indicateurs macro : mensuelle via GitHub Actions + World Bank")
    st.caption("Prix alimentaires : mensuelle (WFP VAM)")
    st.markdown("---")
    st.markdown("**Partenaires visés**")
    st.markdown("ONGs · Gouvernements · Bailleurs")
    st.markdown("---")
    st.markdown(
        "[GitHub](https://github.com/serignemodou85/sahel-flow) · "
        "[Contact](mailto:tellofall@gmail.com)"
    )

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #0d1b2a 0%, #1b4f72 60%, #2980b9 100%);
        padding: 2.2rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        border: 1px solid #1a5276;
    ">
        <h1 style="color: white; margin: 0; font-size: 2rem; letter-spacing: -0.5px;">
            🌍 Sahel Flow
        </h1>
        <p style="color: #aed6f1; margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: 500;">
            Surveillance en temps réel de la sécurité alimentaire — Zone UEMOA
        </p>
        <p style="color: #85c1e9; margin: 0.8rem 0 0 0; font-size: 0.9rem;">
            Indicateurs macro · Prix alimentaires · Score de risque · Cartographie satellite
        </p>
        <p style="color: #5dade2; margin: 0.6rem 0 0 0; font-size: 0.82rem; font-style: italic;">
            Conçu pour les ONGs, gouvernements et institutions de recherche actifs en Afrique de l'Ouest
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Live risk gauges ───────────────────────────────────────────────────────────
st.subheader("État actuel du risque alimentaire")

sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")

_LEVEL_BADGE = {
    "low":      "🟢 FAIBLE",
    "medium":   "🟡 MOYEN",
    "high":     "🟠 ÉLEVÉ",
    "critical": "🔴 CRITIQUE",
}


def _gauge(score: float, title: str) -> go.Figure:
    if score < 25:
        color = "#2ecc71"
    elif score < 50:
        color = "#f1c40f"
    elif score < 75:
        color = "#e67e22"
    else:
        color = "#e74c3c"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": title, "font": {"size": 15}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.28},
            "steps": [
                {"range": [0, 25],   "color": "#d5f5e3"},
                {"range": [25, 50],  "color": "#fef9e7"},
                {"range": [50, 75],  "color": "#fdf2e9"},
                {"range": [75, 100], "color": "#fdedec"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
        number={"suffix": " / 100", "font": {"size": 30}},
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


col1, col2 = st.columns(2)

with col1:
    if sen_records:
        r = sen_records[0]
        score = float(r["risk_score"])
        level = r.get("risk_level", "low")
        st.plotly_chart(_gauge(score, "🇸🇳 Sénégal"), use_container_width=True)
        st.caption(
            f"Période : {r.get('period', '—')} &nbsp;|&nbsp; "
            f"Niveau : **{_LEVEL_BADGE.get(level, level.upper())}**"
        )
    else:
        st.info("🇸🇳 Sénégal — données indisponibles")

with col2:
    if civ_records:
        r = civ_records[0]
        score = float(r["risk_score"])
        level = r.get("risk_level", "low")
        st.plotly_chart(_gauge(score, "🇨🇮 Côte d'Ivoire"), use_container_width=True)
        st.caption(
            f"Période : {r.get('period', '—')} &nbsp;|&nbsp; "
            f"Niveau : **{_LEVEL_BADGE.get(level, level.upper())}**"
        )
    else:
        st.info("🇨🇮 Côte d'Ivoire — données indisponibles")

st.markdown("---")

# ── Navigation cards ───────────────────────────────────────────────────────────
st.subheader("Explorer les données")

cards = [
    ("📊", "Vue d'ensemble",     "Risk score actuel SEN vs CIV · évolution 12 mois"),
    ("🔄", "Comparaison",        "SEN vs CIV côte à côte sur une période choisie"),
    ("🌾", "Prix Alimentaires",  "Prix par commodité, marché et période"),
    ("📈", "Inflation",          "Indicateurs macro World Bank 2000 – 2024"),
    ("🛰️", "Carte satellite",    "Visualisation géographique du risque"),
    ("📐", "Méthodologie",       "Formule du score, sources et limites du modèle"),
]

c1, c2, c3 = st.columns(3)
for i, (icon, title, desc) in enumerate(cards):
    with [c1, c2, c3][i % 3]:
        st.markdown(
            f"<div style='background:#f8f9fa;padding:14px;border-radius:10px;"
            f"border-left:4px solid #2980b9;margin-bottom:12px;'>"
            f"<span style='font-size:1.4em'>{icon}</span> "
            f"<b style='font-size:1em'>{title}</b><br>"
            f"<span style='color:#666;font-size:0.85em'>{desc}</span></div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── KPI strip ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Pays couverts",      "2",          "SEN + CIV")
k2.metric("Indicateurs WB",     "5",          "2000 – 2024")
k3.metric("Mise à jour",        "Mensuelle",  "1er du mois")
k4.metric("Pipeline",           "GitHub Actions", "cloud natif")
