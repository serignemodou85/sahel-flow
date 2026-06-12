import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_inflation

st.set_page_config(page_title="Inflation — Sahel Flow", page_icon="🌾", layout="wide")

st.title("Inflation Macro-économique")
st.caption("Source : /v1/inflation — indicateur FP.CPI.TOTL.ZG (World Bank)")

_INDICATOR = "FP.CPI.TOTL.ZG"

# ── Filtres ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    start_year = st.number_input("Année début", min_value=2000, max_value=2100, value=2010, step=1)
with col2:
    end_year = st.number_input("Année fin", min_value=2000, max_value=2100, value=2023, step=1)

sen_records = get_inflation("SEN", int(start_year), int(end_year))
civ_records = get_inflation("CIV", int(start_year), int(end_year))

# Filtre sur l'indicateur inflation — le service retourne tous les indicateurs WB
sen_cpi = [r for r in sen_records if r["indicator_code"] == _INDICATOR]
civ_cpi = [r for r in civ_records if r["indicator_code"] == _INDICATOR]

if not sen_cpi and not civ_cpi:
    st.info("Aucune donnée d'inflation disponible pour cette période.")
    st.stop()


def _to_df(records: list[dict], country: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["year"] = pd.to_datetime(df["period"]).dt.year
    df["country"] = country
    return df.sort_values("year")


sen_df = _to_df(sen_cpi, "SEN")
civ_df = _to_df(civ_cpi, "CIV")

# ── Graphe dual-line ───────────────────────────────────────────────────────────
fig = go.Figure()

for df, country, color in [(sen_df, "SEN", "#1f77b4"), (civ_df, "CIV", "#2ca02c")]:
    if df.empty:
        continue
    valid = df[df["indicator_value"].notna()]
    fig.add_trace(go.Scatter(
        x=valid["year"],
        y=valid["indicator_value"].astype(float),
        name=f"{country} — Inflation (%)",
        mode="lines+markers",
        line=dict(width=2, color=color),
        marker=dict(size=6),
    ))
    valid_yoy = df[df["yoy_change_pct"].notna()]
    if not valid_yoy.empty:
        fig.add_trace(go.Scatter(
            x=valid_yoy["year"],
            y=valid_yoy["yoy_change_pct"].astype(float),
            name=f"{country} — Variation YoY (%)",
            mode="lines+markers",
            line=dict(width=1, color=color, dash="dot"),
            marker=dict(size=4),
            opacity=0.75,
        ))

fig.add_hline(y=0, line_color="lightgray", line_width=0.8)
fig.update_layout(
    yaxis_title="Taux (%)",
    xaxis_title="Année",
    height=400,
    margin=dict(l=0, r=20, t=20, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig, use_container_width=True)

# ── Tableau comparatif par année ───────────────────────────────────────────────
st.markdown("---")
st.subheader("Tableau comparatif par année")

sen_by_year = {int(row["year"]): row for _, row in sen_df.iterrows()} if not sen_df.empty else {}
civ_by_year = {int(row["year"]): row for _, row in civ_df.iterrows()} if not civ_df.empty else {}
all_years = sorted(set(list(sen_by_year) + list(civ_by_year)), reverse=True)

rows = []
for year in all_years:
    row: dict = {"Année": year}
    if year in sen_by_year:
        v = sen_by_year[year]
        row["SEN Inflation (%)"]  = round(float(v["indicator_value"]), 2) if v["indicator_value"] is not None else None
        row["SEN Var YoY (%)"]    = round(float(v["yoy_change_pct"]), 2)  if v["yoy_change_pct"]  is not None else None
    if year in civ_by_year:
        v = civ_by_year[year]
        row["CIV Inflation (%)"]  = round(float(v["indicator_value"]), 2) if v["indicator_value"] is not None else None
        row["CIV Var YoY (%)"]    = round(float(v["yoy_change_pct"]), 2)  if v["yoy_change_pct"]  is not None else None
    rows.append(row)

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
