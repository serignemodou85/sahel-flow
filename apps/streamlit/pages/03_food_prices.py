from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_food_prices

st.set_page_config(page_title="Prix Alimentaires — Sahel Flow", page_icon="🌾", layout="wide")

st.title("Prix Alimentaires")
st.caption("Source : /v1/food-prices — prix agrégés par commodité et par mois")

# ── Filtres ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    country = st.selectbox(
        "Pays",
        ["SEN", "CIV"],
        format_func=lambda x: "🇸🇳 Sénégal" if x == "SEN" else "🇨🇮 Côte d'Ivoire",
    )
with col2:
    start_date = st.date_input("Période début", value=date.today() - timedelta(days=730))
with col3:
    end_date = st.date_input("Période fin", value=date.today())

records = get_food_prices(country, start_date.isoformat(), end_date.isoformat())

if not records:
    st.info("Aucune donnée disponible pour ce pays et cette période.")
    st.stop()

df = pd.DataFrame(records)
df["period"] = pd.to_datetime(df["period"])
df = df.sort_values("period")

# ── Sélection des commodités ───────────────────────────────────────────────────
all_commodities = sorted(df["commodity"].unique().tolist())
n_default = min(5, len(all_commodities))
selected = st.multiselect(
    "Commodités",
    options=all_commodities,
    default=all_commodities[:n_default],
)

if not selected:
    st.info("Sélectionnez au moins une commodité.")
    st.stop()

# ── Graphe prix USD ────────────────────────────────────────────────────────────
filtered = df[df["commodity"].isin(selected)]

fig = go.Figure()
for commodity in selected:
    sub = filtered[filtered["commodity"] == commodity].sort_values("period")
    fig.add_trace(go.Scatter(
        x=sub["period"],
        y=sub["avg_price_usd"],
        name=commodity,
        mode="lines+markers",
        line=dict(width=2),
        marker=dict(size=5),
    ))

fig.update_layout(
    yaxis_title="Prix moyen USD",
    xaxis_title="Période",
    height=430,
    margin=dict(l=0, r=20, t=20, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig, use_container_width=True)

# ── Métriques ──────────────────────────────────────────────────────────────────
latest_period = df["period"].max()
latest_df = df[df["period"] == latest_period]

m1, m2, m3 = st.columns(3)
m1.metric("Marchés actifs (dernier mois)", int(latest_df["market_count"].sum()))
m2.metric("Dernier mois disponible", latest_period.strftime("%Y-%m"))
m3.metric("Commodités disponibles", len(all_commodities))

# ── Tableau détail — dernier mois ─────────────────────────────────────────────
st.markdown("---")
st.subheader(f"Détail des prix — {latest_period.strftime('%B %Y')}")

detail = latest_df[["commodity", "unit", "avg_price_local", "avg_price_usd", "market_count", "null_price_count"]].copy()
detail = detail.sort_values("commodity")
detail.columns = ["Commodité", "Unité", "Prix local (FCFA)", "Prix USD", "Marchés", "Prix manquants"]
st.dataframe(detail, use_container_width=True, hide_index=True)
