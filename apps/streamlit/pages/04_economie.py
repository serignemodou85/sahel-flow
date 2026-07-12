import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_inflation, get_risk_scores
from utils import alert_banner, pour_comprendre

st.set_page_config(page_title="Économie & inflation — Sahel Flow", page_icon="📈", layout="wide")

# ── Bannière d'alerte ──────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")
alert_banner(sen_records, civ_records)

st.title("📈 Économie & inflation")
st.caption("Source : Banque Mondiale — indicateur FP.CPI.TOTL.ZG (inflation en %)")

pour_comprendre(
    "Qu'est-ce que le taux d'inflation ?",
    """
Le **taux d'inflation** mesure combien les prix ont augmenté en moyenne sur une année.

**Exemple concret :**
- 5% d'inflation = ce qui coûtait **1 000 FCFA** l'année dernière coûte maintenant **1 050 FCFA**
- 10% d'inflation = ce qui coûtait 1 000 FCFA coûte maintenant **1 100 FCFA**
- 0% = les prix n'ont pas changé

Une inflation élevée réduit le pouvoir d'achat des ménages les plus vulnérables,
qui consacrent une grande part de leurs revenus à l'alimentation.

Dans le score de risque Sahel Flow, l'inflation contribue à **40%** du score final.
    """,
)

st.markdown("---")

# ── Filtres ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    start_year = st.number_input("Année début", min_value=2000, max_value=2100, value=2010, step=1)
with col2:
    end_year = st.number_input("Année fin", min_value=2000, max_value=2100, value=2024, step=1)

_INDICATOR = "FP.CPI.TOTL.ZG"

sen_data = get_inflation("SEN", int(start_year), int(end_year))
civ_data = get_inflation("CIV", int(start_year), int(end_year))

sen_cpi = [r for r in sen_data if r["indicator_code"] == _INDICATOR]
civ_cpi = [r for r in civ_data if r["indicator_code"] == _INDICATOR]

if not sen_cpi and not civ_cpi:
    st.info("Aucune donnée disponible pour cette période.")
    st.stop()


def _to_df(records: list[dict], country: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["year"]    = pd.to_datetime(df["period"]).dt.year
    df["country"] = country
    return df.sort_values("year")


sen_df = _to_df(sen_cpi, "SEN")
civ_df = _to_df(civ_cpi, "CIV")

# ── Graphe ────────────────────────────────────────────────────────────────────
fig = go.Figure()
for df, country, color in [(sen_df, "🇸🇳 Sénégal", "#1f77b4"), (civ_df, "🇨🇮 Côte d'Ivoire", "#2ca02c")]:
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
            name=f"{country} — Variation annuelle (%)",
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
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

pour_comprendre(
    "Comment lire ce graphique ?",
    """
Ce graphique montre deux informations par pays :

- **Ligne pleine** : le **taux d'inflation annuel** en pourcentage. Un pic en 2022–2023 correspond au choc des prix mondiaux après la guerre en Ukraine.
- **Ligne pointillée** : la **variation d'une année sur l'autre**. Elle indique si l'inflation accélère (hausse) ou ralentit (baisse).

**À retenir :** une inflation élevée plusieurs années de suite érode durablement le pouvoir d'achat alimentaire.
    """,
)

st.markdown("---")

# ── Tableau comparatif ─────────────────────────────────────────────────────────
st.subheader("Comparatif annuel — Sénégal vs Côte d'Ivoire")

sen_by_year = {int(row["year"]): row for _, row in sen_df.iterrows()} if not sen_df.empty else {}
civ_by_year = {int(row["year"]): row for _, row in civ_df.iterrows()} if not civ_df.empty else {}
all_years   = sorted(set(list(sen_by_year) + list(civ_by_year)), reverse=True)

rows = []
for year in all_years:
    row: dict = {"Année": year}
    if year in sen_by_year:
        v = sen_by_year[year]
        row["🇸🇳 Inflation (%)"] = round(float(v["indicator_value"]), 2) if v["indicator_value"] is not None else None
        row["🇸🇳 Var. annuelle (%)"] = round(float(v["yoy_change_pct"]), 2) if v["yoy_change_pct"] is not None else None
    if year in civ_by_year:
        v = civ_by_year[year]
        row["🇨🇮 Inflation (%)"] = round(float(v["indicator_value"]), 2) if v["indicator_value"] is not None else None
        row["🇨🇮 Var. annuelle (%)"] = round(float(v["yoy_change_pct"]), 2) if v["yoy_change_pct"] is not None else None
    rows.append(row)

if rows:
    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇️ Exporter en CSV",
        data=df_table.to_csv(index=False).encode("utf-8"),
        file_name=f"inflation_{int(start_year)}_{int(end_year)}.csv",
        mime="text/csv",
    )
