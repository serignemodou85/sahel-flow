from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st

from api_client import get_health, get_risk_scores

st.set_page_config(page_title="Vue d'ensemble — Sahel Flow", page_icon="📊", layout="wide")

_LEVEL_BADGE = {
    "low":      "🟢 FAIBLE",
    "medium":   "🟡 MOYEN",
    "high":     "🟠 ÉLEVÉ",
    "critical": "🔴 CRITIQUE",
}

# ── Data fetch (en haut pour le monitoring strip) ──────────────────────────────
health      = get_health()
api_ok      = health.get("status") == "ok"
db_ok       = health.get("db") == "ok"
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")

# ── Statut API ─────────────────────────────────────────────────────────────────
if api_ok and db_ok:
    st.success("API opérationnelle  |  Base de données connectée", icon="✅")
elif api_ok:
    st.warning("API opérationnelle  |  Base de données inaccessible", icon="⚠️")
else:
    st.error("API indisponible — données en cache affichées si disponibles", icon="🔴")

st.title("📊 Vue d'ensemble — État actuel")

# ── Monitoring strip ───────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)

# Prochain run GitHub Actions WB : 1er du mois suivant à 06h00 UTC
if now.month == 12:
    _next = datetime(now.year + 1, 1, 1, 6, 0, tzinfo=timezone.utc)
else:
    _next = datetime(now.year, now.month + 1, 1, 6, 0, tzinfo=timezone.utc)
if now.day == 1 and now.hour < 6:
    _next = datetime(now.year, now.month, 1, 6, 0, tzinfo=timezone.utc)

days_until      = (_next.date() - now.date()).days
next_run_label  = _next.strftime("%d/%m/%Y 06h00 UTC")

# Dernière ingestion WB = period du record le plus récent (déjà trié DESC)
last_wb = sen_records[0]["period"] if sen_records else (
    civ_records[0]["period"] if civ_records else "—"
)

m1, m2, m3 = st.columns(3)
m1.metric(
    label="Statut système",
    value="✅ Opérationnel" if (api_ok and db_ok) else ("⚠️ Dégradé" if api_ok else "❌ Hors ligne"),
    help="GET /v1/health — API + Supabase",
)
m2.metric(
    label="Dernière ingestion WB",
    value=last_wb,
    help="Période la plus récente dans mart__macro__indicators_annual",
)
m3.metric(
    label="Prochain run pipeline",
    value=f"J-{days_until}",
    delta=next_run_label,
    delta_color="off",
    help="GitHub Actions ingest_worldbank.yml — cron 0 6 1 * *",
)

st.markdown("---")

# ── Risk score gauges ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)


def _risk_gauge(score: float, delta_amount: float | None, title: str, level: str) -> go.Figure:
    if score < 25:
        bar_color = "#2ecc71"
    elif score < 50:
        bar_color = "#f1c40f"
    elif score < 75:
        bar_color = "#e67e22"
    else:
        bar_color = "#e74c3c"

    mode = "gauge+number+delta" if delta_amount is not None else "gauge+number"

    indicator_kwargs: dict = dict(
        mode=mode,
        value=score,
        title={
            "text": (
                f"{title}<br>"
                f"<span style='font-size:0.8em;color:gray'>"
                f"{_LEVEL_BADGE.get(level, level.upper())}</span>"
            ),
            "font": {"size": 16},
        },
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#555"},
            "bar": {"color": bar_color, "thickness": 0.25},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#ddd",
            "steps": [
                {"range": [0, 25],   "color": "#d5f5e3"},
                {"range": [25, 50],  "color": "#fef9e7"},
                {"range": [50, 75],  "color": "#fdf2e9"},
                {"range": [75, 100], "color": "#fdedec"},
            ],
            "threshold": {
                "line": {"color": bar_color, "width": 4},
                "thickness": 0.75,
                "value": score,
            },
        },
        number={"suffix": " / 100", "font": {"size": 34}},
    )

    if delta_amount is not None:
        indicator_kwargs["delta"] = {
            "reference": score - delta_amount,
            "increasing": {"color": "#e74c3c"},
            "decreasing": {"color": "#2ecc71"},
        }

    fig = go.Figure(go.Indicator(**indicator_kwargs))
    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=70, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _render_country(col, flag: str, name: str, records: list[dict]) -> None:
    with col:
        st.subheader(f"{flag} {name}")

        if not records:
            st.info("Pas de données disponibles")
            return

        current = records[0]
        prev    = records[1] if len(records) > 1 else None

        score  = float(current["risk_score"])
        delta  = round(score - float(prev["risk_score"]), 2) if prev else None
        level  = current.get("risk_level", "low")
        period = current.get("period", "—")

        st.plotly_chart(
            _risk_gauge(score, delta, f"{flag} {name} — {period}", level),
            use_container_width=True,
        )

        sub_c1, sub_c2 = st.columns(2)
        sub_c1.metric(
            "Tendance prix",
            f"{float(current['price_trend_score']):.1f}",
            help="Composante WFP (prix alimentaires)",
        )
        sub_c2.metric(
            "Score inflation",
            f"{float(current['inflation_score']):.1f}",
            help="Composante World Bank (FP.CPI.TOTL.ZG)",
        )
        if delta is not None:
            st.caption(
                f"Variation vs période précédente : "
                f"**{'↑' if delta > 0 else '↓'} {abs(delta):.2f} pts**"
            )


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

    for y_val, color, label in [
        (25, "gold",   "MOYEN"),
        (50, "orange", "ÉLEVÉ"),
        (75, "red",    "CRITIQUE"),
    ]:
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
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée de risk score disponible.")
