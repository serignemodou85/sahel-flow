from datetime import date, datetime, timedelta, timezone

import streamlit as st

from api_client import get_food_prices, get_health, get_risk_scores
from utils import alert_banner, faits_marquants, pour_comprendre, rapport_texte, risk_card

st.set_page_config(
    page_title="Sahel Flow — Sécurité Alimentaire UEMOA",
    page_icon="🌍",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
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
    st.caption("World Bank : 1er du mois via GitHub Actions")
    st.caption("WFP HDX : 1er du mois via GitHub Actions")
    st.markdown("---")
    st.markdown("**Partenaires visés**")
    st.markdown("ONGs · Gouvernements · Bailleurs")
    st.markdown("---")
    st.markdown(
        "[GitHub](https://github.com/serignemodou85/sahel-flow) · "
        "[Contact](mailto:tellofall@gmail.com)"
    )

# ── Données ────────────────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")

six_months_ago = (date.today() - timedelta(days=180)).isoformat()
sen_prices = get_food_prices("SEN", start_date=six_months_ago)
civ_prices = get_food_prices("CIV", start_date=six_months_ago)

# ── Bannière d'alerte (visible en haut avant tout le reste) ────────────────────
alert_banner(sen_records, civ_records)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #0d1b2a 0%, #1b4f72 60%, #2980b9 100%);
        padding: 2rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        border: 1px solid #1a5276;
    ">
        <h1 style="color: white; margin: 0; font-size: 2rem; letter-spacing: -0.5px;">
            🌍 Sahel Flow
        </h1>
        <p style="color: #aed6f1; margin: 0.5rem 0 0 0; font-size: 1.05rem; font-weight: 500;">
            Surveillance de la sécurité alimentaire — Zone UEMOA
        </p>
        <p style="color: #85c1e9; margin: 0.6rem 0 0 0; font-size: 0.88rem;">
            Indicateurs macro · Prix alimentaires · Score de risque · Cartographie satellite
        </p>
        <p style="color: #5dade2; margin: 0.5rem 0 0 0; font-size: 0.82rem; font-style: italic;">
            Conçu pour les ONGs, gouvernements et institutions de recherche actifs en Afrique de l'Ouest
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Situation actuelle — cards décideur ────────────────────────────────────────
st.subheader("Situation actuelle")

col1, col2 = st.columns(2)
with col1:
    risk_card("🇸🇳", "Sénégal", sen_records)
with col2:
    risk_card("🇨🇮", "Côte d'Ivoire", civ_records)

pour_comprendre(
    "Comment lire les scores de situation ?",
    """
Le **score de risque** va de **0** (aucun risque) à **100** (crise alimentaire critique).

Il combine deux indicateurs :
- **60%** — Tendance des prix alimentaires sur les marchés locaux (source : WFP HDX)
- **40%** — Taux d'inflation national annuel (source : Banque Mondiale)

| Niveau | Score | Signification |
|---|---|---|
| 🟢 FAIBLE | 0 – 24 | Situation normale, surveillance de routine |
| 🟡 MOYEN | 25 – 49 | Tension légère, à surveiller |
| 🟠 ÉLEVÉ | 50 – 74 | Alerte — des mesures peuvent être nécessaires |
| 🔴 CRITIQUE | 75 – 100 | Urgence — intervention recommandée |

La flèche (↑ ↓) indique l'évolution par rapport au mois précédent.
    """,
)

st.markdown("---")

# ── Faits marquants ce mois ────────────────────────────────────────────────────
st.subheader("Ce mois — Faits marquants")

bullets = faits_marquants(sen_prices, civ_prices)
for b in bullets:
    st.markdown(f"- {b}")

now = datetime.now(timezone.utc)
if now.month == 12:
    next_run = datetime(now.year + 1, 1, 1, 6, 0, tzinfo=timezone.utc)
else:
    next_run = datetime(now.year, now.month + 1, 1, 6, 0, tzinfo=timezone.utc)
st.markdown(
    f"- 📊 Prochain point de données : "
    f"**{next_run.strftime('%d/%m/%Y')} à 06h00 UTC** "
    f"(GitHub Actions — World Bank + WFP HDX)"
)

# ── Bouton rapport téléchargeable ──────────────────────────────────────────────
rapport = rapport_texte(sen_records, civ_records, bullets)
st.download_button(
    label="⬇️ Télécharger le rapport mensuel (.txt)",
    data=rapport.encode("utf-8"),
    file_name=f"sahel_flow_rapport_{date.today().strftime('%Y_%m')}.txt",
    mime="text/plain",
)

st.markdown("---")

# ── Navigation ─────────────────────────────────────────────────────────────────
st.subheader("Explorer les données")

cards = [
    ("📊", "Tableau de bord",          "Risk score détaillé · évolution 12 mois · monitoring système"),
    ("🔄", "Comparaison SEN vs CIV",   "Les deux pays côte à côte sur une période choisie"),
    ("🌾", "Marchés alimentaires",      "Prix par produit et variation 3 mois · feu tricolore"),
    ("📈", "Économie & inflation",      "Indicateurs macro Banque Mondiale 2000 – 2024"),
    ("🛰️", "Carte de situation",        "Visualisation géographique du risque alimentaire"),
    ("📐", "À propos du système",       "Formule du score, sources de données et limites"),
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
k1.metric("Pays couverts",       "2",              "Sénégal + Côte d'Ivoire")
k2.metric("Indicateurs WB",      "5",              "2000 – 2024")
k3.metric("Mise à jour",         "Mensuelle",      "1er du mois — automatique")
k4.metric("Infrastructure",      "GitHub Actions", "cloud natif, zéro serveur")
