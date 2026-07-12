import streamlit as st

from api_client import get_risk_scores
from utils import alert_banner

st.set_page_config(page_title="À propos — Sahel Flow", page_icon="📐", layout="wide")

# ── Bannière d'alerte ──────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")
alert_banner(sen_records, civ_records)

st.title("📐 À propos du système")
st.caption("Formule du score de risque, sources de données, stack technique et limites du modèle")

# ── Formule ────────────────────────────────────────────────────────────────────
st.header("Comment est calculé le score de risque ?")

st.markdown(
    """
    Le score de risque alimentaire combine deux indicateurs en temps réel :

    > **score = 60% × tendance des prix + 40% × score d'inflation**
    """
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Tendance des prix (×60%)")
    st.markdown(
        """
        Mesure la **hausse des prix alimentaires** sur les marchés locaux
        par rapport à la moyenne des 3 mois précédents.

        ```
        baseline_3m  = moyenne des 3 mois précédents
        variation    = (prix actuel / baseline) - 1) × 500
        score        = entre 0 et 100
        ```

        - **+20% de hausse → score = 100**
        - **Stable ou baisse → score = 0**
        - Source : WFP HDX (données publiques mensuelles)
        """
    )

with col2:
    st.subheader("Score d'inflation (×40%)")
    st.markdown(
        """
        Mesure le **taux d'inflation national annuel**
        fourni par la Banque Mondiale.

        ```
        inflation_rate  = indicateur FP.CPI.TOTL.ZG (% annuel)
        score           = inflation_rate × 5  (borné 0–100)
        ```

        - **20% d'inflation → score = 100**
        - **0% d'inflation → score = 0**
        - Source : World Bank API (annuel)
        """
    )

st.markdown("---")

# ── Niveaux ────────────────────────────────────────────────────────────────────
st.subheader("Niveaux de risque — seuils de décision")

l1, l2, l3, l4 = st.columns(4)
for col, badge, rng, bg, fg, action in [
    (l1, "🟢 FAIBLE",   "0 – 24",   "#d5f5e3", "#1e8449", "Surveillance de routine"),
    (l2, "🟡 MOYEN",    "25 – 49",  "#fef9e7", "#b7950b", "Surveiller les prix hebdo"),
    (l3, "🟠 ÉLEVÉ",    "50 – 74",  "#fdf2e9", "#d35400", "Évaluer les besoins d'aide"),
    (l4, "🔴 CRITIQUE", "75 – 100", "#fdedec", "#c0392b", "Activer les protocoles d'urgence"),
]:
    col.markdown(
        f"<div style='background:{bg};padding:14px 10px;border-radius:8px;"
        f"text-align:center;border:1px solid {fg}30;margin-bottom:8px;'>"
        f"<b style='color:{fg};font-size:1em'>{badge}</b><br>"
        f"<span style='color:#555;font-size:0.85em'>{rng}</span><br>"
        f"<span style='color:#666;font-size:0.78em;font-style:italic'>{action}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Sources ────────────────────────────────────────────────────────────────────
st.header("Sources de données")

s1, s2 = st.columns(2)
with s1:
    st.subheader("🌐 World Bank API")
    st.markdown(
        """
        - **Indicateur** : FP.CPI.TOTL.ZG — Inflation IPC (% annuel)
        - **Granularité** : annuelle (2000 – 2024)
        - **Pays** : Sénégal (SEN), Côte d'Ivoire (CIV)
        - **Accès** : public, sans clé API
        - **Ingestion** : automatique le 1er du mois à 06h00 UTC
        """
    )
with s2:
    st.subheader("📦 WFP HDX (Humanitarian Data Exchange)")
    st.markdown(
        """
        - **Dataset** : prix alimentaires par marché et commodité
        - **Granularité** : mensuelle (depuis 2020)
        - **Pays** : Sénégal (SEN), Côte d'Ivoire (CIV)
        - **Accès** : public, plateforme officielle WFP, sans clé API
        - **Ingestion** : automatique le 1er du mois à 07h00 UTC
        """
    )

st.markdown("---")

# ── Stack technique ─────────────────────────────────────────────────────────────
st.header("Stack technique — architecture en production")

st.code(
    """
World Bank API (annuel)          HDX WFP (mensuel, public)
        │                               │
        ▼                               ▼
 GitHub Actions                  GitHub Actions
ingest_worldbank.py              ingest_wfp.py
  cron 0 6 1 * *                  cron 0 7 1 * *
        │                               │
        └──────────────┬────────────────┘
                       │
                   Supabase (PostgreSQL managé)
               schéma « marts »
      mart__macro__indicators_annual   ← 250 lignes WB 2000–2024
       mart__food__prices_monthly      ← prix réels HDX >= 2020
        mart__risk__score_monthly      ← score = 0.6×price_trend + 0.4×inflation
                       │
                   FastAPI (Render — free tier)
           /v1/health  /v1/countries  /v1/risk-score
           /v1/food-prices  /v1/inflation  /v1/compare
                       │
              ┌────────┴────────────┐
              │                     │
          Streamlit            GitHub Actions
        (Render — free)        keep_alive.yml
        cette application      ping /v1/health
                               toutes les 14 min
""",
    language="text",
)

st.markdown("---")

# ── Roadmap ────────────────────────────────────────────────────────────────────
st.header("Roadmap — Prochaines évolutions")

st.markdown(
    """
    | Fonctionnalité | Statut | Description |
    |---|---|---|
    | Pipeline World Bank mensuel | ✅ En production | Ingestion automatique GitHub Actions |
    | WFP HDX mensuel | ✅ En production | Prix alimentaires réels depuis 2020 |
    | Carte satellite interactive | ✅ Disponible | Fond Esri + score géolocalisé |
    | Dashboard décideur | ✅ Disponible | Cards, feu tricolore, faits marquants |
    | Extension UEMOA 8 pays | 🔜 Prévu | Mali, Burkina, Niger, Togo, Bénin, Guinée-Bissau |
    | Alertes email/SMS | 🔮 Futur | Notification si score > seuil critique |
    | API publique documentée | 🔮 Futur | Swagger/OpenAPI pour partenaires institutionnels |
    | Imagerie satellite NDVI | 🔮 Futur | Indices végétation (Sentinel-2 / Copernicus) |
    """
)

st.markdown("---")

# ── Limites ────────────────────────────────────────────────────────────────────
st.header("Limites du modèle actuel")

st.markdown(
    """
    | Limite | Impact | Piste d'amélioration |
    |---|---|---|
    | Données WB annuelles | Le même score d'inflation est répété pour tous les mois d'une année | Intégrer les données BCEAO (mensuelles) |
    | 2 pays seulement | Zone UEMOA = 8 pays | Extension sans changement de modèle |
    | Coefficients empiriques | 500 et 5 calibrés à la main | Calibration par régression sur historiques de crises |
    | Pas de données météo/conflit | Facteurs majeurs de crise non couverts | ACLED (conflits) + CHIRPS (précipitations) |
    | avg_price_usd non calculé | Comparaison inter-pays en USD non disponible | Intégrer le taux ECB ou WB |
    """
)
