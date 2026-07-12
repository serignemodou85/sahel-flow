from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_compare, get_risk_scores
from utils import alert_banner, pour_comprendre

st.set_page_config(page_title="Comparaison SEN vs CIV — Sahel Flow", page_icon="🔄", layout="wide")

# ── Bannière d'alerte ──────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")
alert_banner(sen_records, civ_records)

st.title("🔄 Sénégal vs Côte d'Ivoire")
st.caption("Comparaison des scores de risque et des composantes sur une période choisie")

pour_comprendre(
    "Comment lire cette comparaison ?",
    """
Ces 3 graphiques comparent les deux pays sur la **même période** :

- **Score de risque** (à gauche) : indicateur global de 0 à 100 — le plus important pour la décision
- **Tendance des prix** (au centre) : hausse des prix alimentaires sur les marchés locaux (source WFP)
- **Score d'inflation** (à droite) : pression inflationniste nationale (source Banque Mondiale)

Si les deux courbes se croisent, cela indique un **changement de rapport** entre les deux pays :
l'un dépasse l'autre en termes de risque.

Un pays avec un **score de risque élevé mais une tendance prix faible** a essentiellement
un problème d'inflation macroéconomique plutôt qu'une crise sur les marchés alimentaires locaux.
    """,
)

st.markdown("---")

# ── Sélecteurs de période ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Période début", value=date(2023, 1, 1))
with col2:
    end_date = st.date_input("Période fin", value=date.today())

compare_data = get_compare(start_date.isoformat(), end_date.isoformat())

sen_data = compare_data.get("SEN", [])
civ_data = compare_data.get("CIV", [])

if not sen_data and not civ_data:
    st.info("Aucune donnée disponible pour la période sélectionnée.")
    st.stop()

sen_asc = sorted(sen_data, key=lambda x: x["period"])
civ_asc = sorted(civ_data, key=lambda x: x["period"])


def _dual_chart(metric_key: str, title: str, y_label: str) -> go.Figure:
    fig = go.Figure()
    for records, country, color in [
        (sen_asc, "🇸🇳 Sénégal", "#1f77b4"),
        (civ_asc, "🇨🇮 Côte d'Ivoire", "#2ca02c"),
    ]:
        if records:
            fig.add_trace(go.Scatter(
                x=[r["period"] for r in records],
                y=[float(r[metric_key]) for r in records],
                name=country,
                mode="lines+markers",
                line=dict(width=2, color=color),
                marker=dict(size=4),
            ))
    fig.update_layout(
        title=title,
        yaxis=dict(range=[0, 100], title=y_label),
        height=280,
        margin=dict(l=0, r=20, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


c1, c2, c3 = st.columns(3)
c1.plotly_chart(_dual_chart("risk_score",        "Score de risque global",  "Score / 100"), use_container_width=True)
c2.plotly_chart(_dual_chart("price_trend_score", "Tendance des prix",       "Score / 100"), use_container_width=True)
c3.plotly_chart(_dual_chart("inflation_score",   "Score d'inflation macro", "Score / 100"), use_container_width=True)

st.markdown("---")

# ── Tableau récapitulatif ─────────────────────────────────────────────────────
st.subheader("Dernière période disponible — résumé")

_LEVEL_LABELS = {
    "low": "🟢 FAIBLE", "medium": "🟡 MOYEN",
    "high": "🟠 ÉLEVÉ", "critical": "🔴 CRITIQUE",
}

rows = []
for country, records in [("🇸🇳 Sénégal", sen_data), ("🇨🇮 Côte d'Ivoire", civ_data)]:
    if records:
        latest = records[0]
        rows.append({
            "Pays":              country,
            "Période":           latest["period"],
            "Score de risque":   round(float(latest["risk_score"]), 2),
            "Tendance des prix": round(float(latest["price_trend_score"]), 2),
            "Score inflation":   round(float(latest["inflation_score"]), 2),
            "Niveau":            _LEVEL_LABELS.get(latest.get("risk_level", ""), "—"),
        })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇️ Exporter en CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"comparaison_SEN_CIV_{start_date}_{end_date}.csv",
        mime="text/csv",
    )
