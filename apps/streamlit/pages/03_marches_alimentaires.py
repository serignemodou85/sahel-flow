from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get_food_prices, get_risk_scores
from utils import alert_banner, commodity_feu_tricolore, pour_comprendre

st.set_page_config(page_title="Marchés alimentaires — Sahel Flow", page_icon="🌾", layout="wide")

# ── Données bannière ───────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")
alert_banner(sen_records, civ_records)

st.title("🌾 Marchés alimentaires")
st.caption("Prix par produit — variation 3 mois — source : WFP HDX")

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

flag = "🇸🇳" if country == "SEN" else "🇨🇮"
country_name = "Sénégal" if country == "SEN" else "Côte d'Ivoire"

# ── Feu tricolore — vue principale ────────────────────────────────────────────
st.subheader(f"{flag} {country_name} — Situation des prix ce mois")

feu_df = commodity_feu_tricolore(records)

if feu_df is not None and not feu_df.empty:
    st.dataframe(
        feu_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Statut": st.column_config.TextColumn("Statut", width="medium"),
            "Variation 3 mois": st.column_config.TextColumn("Variation 3 mois", width="small"),
        },
    )
else:
    st.info("Données insuffisantes pour calculer la variation 3 mois (moins de 2 mois disponibles).")

pour_comprendre(
    "Comment lire ce tableau ?",
    """
Ce tableau montre chaque **produit alimentaire** suivi sur les marchés locaux
et indique si son prix a augmenté ou baissé par rapport aux **3 derniers mois**.

| Statut | Signification |
|---|---|
| 🔴 Hausse forte | Prix en hausse de +10% ou plus — signal d'alerte |
| 🟡 Hausse modérée | Prix en hausse de +5 à +10% — à surveiller |
| 🟢 Stable | Variation inférieure à ±5% — situation normale |
| 🟢 Baisse | Prix en baisse de plus de 5% — bonne nouvelle |
| ⚪ Données insuffisantes | Pas assez d'historique pour calculer |

Les prix sont en **FCFA** (Franc CFA de l'Afrique de l'Ouest, monnaie commune UEMOA).
La variation compare le mois actuel à la **moyenne des 3 mois précédents**.
    """,
)

# ── Métriques du mois ─────────────────────────────────────────────────────────
st.markdown("---")
latest_period = df["period"].max()
latest_df     = df[df["period"] == latest_period]

m1, m2, m3 = st.columns(3)
m1.metric("Marchés actifs (dernier mois)", int(latest_df["market_count"].sum()))
m2.metric("Dernier mois disponible",       latest_period.strftime("%B %Y"))
m3.metric("Produits suivis",               len(df["commodity"].unique()))

# ── Graphe historique ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Évolution des prix dans le temps")

all_commodities = sorted(df["commodity"].unique().tolist())
n_default       = min(4, len(all_commodities))
selected        = st.multiselect(
    "Sélectionnez les produits à afficher",
    options=all_commodities,
    default=all_commodities[:n_default],
)

if selected:
    filtered = df[df["commodity"].isin(selected)]
    fig = go.Figure()
    for commodity in selected:
        sub = filtered[filtered["commodity"] == commodity].sort_values("period")
        if sub.empty or sub["avg_price_local"].isna().all():
            continue
        fig.add_trace(go.Scatter(
            x=sub["period"],
            y=sub["avg_price_local"].astype(float),
            name=commodity,
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=5),
        ))
    fig.update_layout(
        yaxis_title="Prix moyen (FCFA)",
        xaxis_title="Période",
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
Ce graphique montre l'évolution du **prix moyen** de chaque produit au fil du temps,
en **FCFA** (Franc CFA).

- Chaque ligne correspond à un produit alimentaire (mil, riz, sorgho, maïs…)
- Une **ligne qui monte** = le produit est devenu plus cher
- Une **ligne qui descend** = le produit est moins cher
- Les prix proviennent des marchés locaux suivis par le **WFP** (Programme Alimentaire Mondial)
  et sont agrégés par commodité et par mois

Survolez les points pour voir le prix exact à une date donnée.
        """,
    )

# ── Tableau détail dernier mois ────────────────────────────────────────────────
st.markdown("---")
st.subheader(f"Détail des prix — {latest_period.strftime('%B %Y')}")

detail = latest_df[["commodity", "unit", "avg_price_local", "market_count"]].copy()
detail = detail.sort_values("commodity")
detail.columns = ["Produit", "Unité", "Prix moyen (FCFA)", "Nombre de marchés"]
st.dataframe(detail, use_container_width=True, hide_index=True)

st.download_button(
    label="⬇️ Exporter en CSV",
    data=detail.to_csv(index=False).encode("utf-8"),
    file_name=f"prix_alimentaires_{country}_{date.today().strftime('%Y_%m')}.csv",
    mime="text/csv",
)
