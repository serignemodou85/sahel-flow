from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_compare

st.set_page_config(page_title="Comparaison — Sahel Flow", page_icon="🌾", layout="wide")

st.title("Comparaison SEN vs CIV")
st.caption("Source : /v1/compare — risk score et composantes sur la même période")

# ── Sélecteurs de période ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Période début", value=date(2022, 1, 1))
with col2:
    end_date = st.date_input("Période fin", value=date.today())

compare_data = get_compare(start_date.isoformat(), end_date.isoformat())

sen_records = compare_data.get("SEN", [])
civ_records = compare_data.get("CIV", [])

if not sen_records and not civ_records:
    st.info("Aucune donnée disponible pour la période sélectionnée.")
    st.stop()

# Tri chronologique pour les graphes (API retourne DESC)
sen_asc = sorted(sen_records, key=lambda x: x["period"])
civ_asc = sorted(civ_records, key=lambda x: x["period"])


# ── Graphes ────────────────────────────────────────────────────────────────────
def _dual_chart(metric_key: str, title: str) -> go.Figure:
    fig = go.Figure()
    for records, country, color in [
        (sen_asc, "SEN", "#1f77b4"),
        (civ_asc, "CIV", "#2ca02c"),
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
        yaxis=dict(range=[0, 100]),
        height=280,
        margin=dict(l=0, r=20, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


c1, c2, c3 = st.columns(3)
c1.plotly_chart(_dual_chart("risk_score", "Risk Score"),             use_container_width=True)
c2.plotly_chart(_dual_chart("price_trend_score", "Tendance prix"),   use_container_width=True)
c3.plotly_chart(_dual_chart("inflation_score", "Score inflation"),   use_container_width=True)

# ── Tableau récapitulatif — dernière période ───────────────────────────────────
st.markdown("---")
st.subheader("Dernière période disponible — toutes les composantes")

rows = []
for country, records in [("🇸🇳 SEN", sen_records), ("🇨🇮 CIV", civ_records)]:
    if records:
        latest = records[0]  # ORDER BY period DESC
        rows.append({
            "Pays":           country,
            "Période":        latest["period"],
            "Risk Score":     round(float(latest["risk_score"]), 2),
            "Tendance prix":  round(float(latest["price_trend_score"]), 2),
            "Inflation":      round(float(latest["inflation_score"]), 2),
            "Niveau":         latest.get("risk_level", "").upper(),
        })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
