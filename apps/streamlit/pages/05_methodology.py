import streamlit as st

st.set_page_config(page_title="Méthodologie — Sahel Flow", page_icon="🌾", layout="wide")

st.title("Méthodologie")
st.caption("Explication du modèle de score et de la stack technique")

# ── Formule du Risk Score ──────────────────────────────────────────────────────
st.header("Formule du Risk Score alimentaire")

st.latex(r"\text{risk\_score} = 0.6 \times \text{price\_trend\_score} + 0.4 \times \text{inflation\_score}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("price_trend_score (×0.6)")
    st.markdown(
        """
        Mesure la variation du prix USD moyen par rapport à une baseline de 3 mois glissants.

        ```
        baseline_3m  = moyenne des 3 mois précédents
        variation    = (prix_actuel / baseline_3m - 1) × 500
        score        = LEAST(100, GREATEST(0, variation))
        ```

        - **+20% de hausse → score = 100**
        - **Stable ou baisse → score = 0**
        - Normalisé entre 0 et 100 via `LEAST/GREATEST` en SQL (dbt)
        - Les 3 premiers mois par pays sont exclus (baseline non calculable)
        """
    )

with col2:
    st.subheader("inflation_score (×0.4)")
    st.markdown(
        """
        Mesure le taux d'inflation macro annuel (source : World Bank).

        ```
        inflation_rate  = FP.CPI.TOTL.ZG (% annuel)
        score           = LEAST(100, GREATEST(0, inflation_rate × 5))
        ```

        - **20% d'inflation → score = 100**
        - **0% d'inflation → score = 0**
        - Jointure mensuel × annuel : chaque mois WFP joint à l'année WB correspondante
        """
    )

st.markdown("---")

# ── Niveaux de risque ──────────────────────────────────────────────────────────
st.subheader("Niveaux de risque")

levels_col1, levels_col2, levels_col3, levels_col4 = st.columns(4)
levels_col1.metric("🟢 FAIBLE",    "0 – 24")
levels_col2.metric("🟡 MOYEN",     "25 – 49")
levels_col3.metric("🟠 ÉLEVÉ",     "50 – 74")
levels_col4.metric("🔴 CRITIQUE",  "75 – 100")

st.caption("Ces seuils sont définis dans `api/app/services/risk_score_service.py::_risk_level()`")

st.markdown("---")

# ── Sources de données ─────────────────────────────────────────────────────────
st.header("Sources de données")

src_col1, src_col2 = st.columns(2)

with src_col1:
    st.subheader("World Bank API")
    st.markdown(
        """
        - **Indicateur** : FP.CPI.TOTL.ZG (Inflation, indice des prix à la consommation)
        - **Granularité** : annuelle
        - **Pays** : SEN, CIV
        - **Endpoint** : `https://api.worldbank.org/v2/country/{code}/indicator/{ind}`
        - **Ingestion** : GitHub Actions — cron `0 6 1 * *` (1er du mois, cloud natif)
        """
    )

with src_col2:
    st.subheader("WFP VAM (Data Bridges)")
    st.markdown(
        """
        - **Dataset** : prix alimentaires par marché et par commodité
        - **Granularité** : mensuelle
        - **Pays** : SEN, CIV
        - **Endpoint** : `https://api.vam.wfp.org/...`
        - **Ingestion** : seed manuel (données test — WFP VAM prévu)
        - **Note** : couverture des marchés variable selon les mois
        """
    )

st.markdown("---")

# ── Diagramme de la stack ──────────────────────────────────────────────────────
st.header("Stack technique — bout en bout")

st.code(
    """
WB API (annuel)              WFP VAM API (mensuel)
       │                            │
       ▼                            ▼
GitHub Actions               Seed / futur DAG
ingest_worldbank.py         (données test WFP)
  (cron 1er/mois)                   │
       │                            │
       └──────────┬─────────────────┘
                  │
              Supabase
           schéma « marts »
    (mart__macro__indicators_annual,
     mart__food__prices_monthly,
     mart__risk__score_monthly)
                  │
              FastAPI
         /v1/risk-score
         /v1/food-prices
         /v1/inflation
         /v1/compare
                  │
            ┌─────┴──────────┐
            │                │
        Streamlit          Grafana
   (cette application)   (dashboards RED)
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
    | Carte satellite interactive | ✅ Disponible | Fond Esri WorldImagery + score de risque géolocalisé |
    | GitHub Actions pipeline | ✅ En prod | Ingestion World Bank mensuelle, cloud natif |
    | WFP VAM intégration live | 🔜 Prévu | Prix alimentaires en temps réel (actuellement : données test) |
    | Extension UEMOA | 🔜 Prévu | Mali, Burkina, Niger, Togo, Bénin, Guinée-Bissau |
    | Imagerie satellite NDVI | 🔮 Futur | Indices de végétation (Sentinel-2 via Copernicus) |
    | Alertes email/SMS | 🔮 Futur | Notification automatique quand score > seuil critique |
    | API publique documentée | 🔮 Futur | Swagger/OpenAPI pour partenaires institutionnels |
    """
)

st.markdown("---")

# ── Limites du modèle ──────────────────────────────────────────────────────────
st.header("Limites du modèle actuel")

st.markdown(
    """
    | Limite | Impact | Piste d'amélioration |
    |---|---|---|
    | Données WB annuelles vs WFP mensuelles | Le même score d'inflation est répété pour tous les mois d'une année | Intégrer les données BCEAO (mensuelles) en remplacement ou en complément |
    | Granularité marché WFP variable | Un pays avec peu de marchés actifs a un score moins représentatif | Pondérer par le nombre de marchés (`market_count`) |
    | Score normalisé empiriquement | Les coefficients 500 et 5 sont des approximations calibrées à la main | Calibration par régression sur des données historiques de crises alimentaires |
    | Seulement 2 pays (SEN + CIV) | Zone UEMOA = 8 pays | Extension possible sans changement de modèle — ajouter les ingestions |
    | BCEAO non intégrée | Données monétaires et de change absentes | Prévu en version 2 du modèle |
    | Pas de données de conflit / météo | Facteurs majeurs de crise alimentaire non couverts | Intégration ACLED (conflits) + CHIRPS (précipitations) |
    """
)
