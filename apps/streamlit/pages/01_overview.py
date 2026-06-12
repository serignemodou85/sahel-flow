import plotly.graph_objects as go
import streamlit as st

from api_client import get_health, get_risk_scores

st.set_page_config(page_title="Vue d'ensemble — Sahel Flow", layout="wide")

_LEVEL_BADGE = {
    "low":      "🟢 FAIBLE",
    "medium":   "🟡 MOYEN",
    "high":     "🟠 ÉLEVÉ",
    "critical": "🔴 CRITIQUE",
}

_LEVEL_LINE_COLOR = {
    "low": "green",
    "medium": "gold",
    "high": "orange",
    "critical": "red",
}

# ── Statut API ─────────────────────────────────────────────────────────────────
health = get_health()
api_ok = health.get("status") == "ok"
db_ok  = health.get("db") == "ok"

if api_ok and db_ok:
    st.success("API opérationnelle  |  Base de données connectée")
elif api_ok:
    st.warning("API opérationnelle  |  Base de données inaccessible")
else:
    st.error("API indisponible — données en cache affichées si disponibles")

st.title("Vue d'ensemble — État actuel")
st.markdown("---")

# ── Risk scores ────────────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")

col1, col2 = st.columns(2)


def _render_country(col, flag: str, name: str, records: list[dict]) -> None:
    with col:
        st.subheader(f"{flag} {name}")

        if not records:
            st.info("Pas de données disponibles")
            return

        current = records[0]   # ORDER BY period DESC → index 0 = plus récent
        prev    = records[1] if len(records) > 1 else None

        score = float(current["risk_score"])
        delta = round(score - float(prev["risk_score"]), 2) if prev else None
        level = current.get("risk_level", "low")

        st.metric(
            label=f"Risk Score — {current['period']}",
            value=f"{score:.1f} / 100",
            delta=f"{delta:+.1f} vs mois précédent" if delta is not None else None,
            delta_color="inverse",   # hausse du risque = rouge
        )
        st.markdown(f"Niveau : **{_LEVEL_BADGE.get(level, level.upper())}**")

        inner_c1, inner_c2 = st.columns(2)
        inner_c1.metric("Tendance prix", f"{float(current['price_trend_score']):.1f}")
        inner_c2.metric("Score inflation", f"{float(current['inflation_score']):.1f}")


_render_country(col1, "🇸🇳", "Sénégal (SEN)", sen_records)
_render_country(col2, "🇨🇮", "Côte d'Ivoire (CIV)", civ_records)

# ── Mini chart — 12 derniers mois ──────────────────────────────────────────────
st.markdown("---")
st.subheader("Évolution du Risk Score — 12 derniers mois")

chart_records = (
    [{"country": "SEN", **r} for r in sen_records[:12]]
    + [{"country": "CIV", **r} for r in civ_records[:12]]
)

if chart_records:
    fig = go.Figure()

    for country, color in [("SEN", "#1f77b4"), ("CIV", "#2ca02c")]:
        subset = sorted(
            [r for r in chart_records if r["country"] == country],
            key=lambda x: x["period"],
        )
        fig.add_trace(go.Scatter(
            x=[r["period"] for r in subset],
            y=[float(r["risk_score"]) for r in subset],
            name=country,
            mode="lines+markers",
            line=dict(width=2, color=color),
            marker=dict(size=6),
        ))

    for y_val, color, label in [(25, "gold", "MOYEN"), (50, "orange", "ÉLEVÉ"), (75, "red", "CRITIQUE")]:
        fig.add_hline(
            y=y_val, line_dash="dash", line_color=color, line_width=1,
            annotation_text=label, annotation_position="right",
        )

    fig.update_layout(
        yaxis=dict(range=[0, 100], title="Risk Score"),
        xaxis_title="Période",
        height=350,
        margin=dict(l=0, r=80, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée de risk score disponible.")
