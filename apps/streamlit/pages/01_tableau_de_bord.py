from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st

from api_client import get_health, get_risk_scores
from utils import alert_banner, pour_comprendre

st.set_page_config(page_title="Tableau de bord — Sahel Flow", page_icon="📊", layout="wide")

_LEVEL_BADGE = {
    "low":      "🟢 FAIBLE",
    "medium":   "🟡 MOYEN",
    "high":     "🟠 ÉLEVÉ",
    "critical": "🔴 CRITIQUE",
}

# ── Données ────────────────────────────────────────────────────────────────────
health      = get_health()
api_ok      = health.get("status") == "ok"
db_ok       = health.get("db") == "ok"
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")

# ── Bannière d'alerte ──────────────────────────────────────────────────────────
alert_banner(sen_records, civ_records)

# ── Statut système ─────────────────────────────────────────────────────────────
if api_ok and db_ok:
    st.success("API opérationnelle  |  Base de données connectée", icon="✅")
elif api_ok:
    st.warning("API opérationnelle  |  Base de données inaccessible", icon="⚠️")
else:
    st.error("API indisponible — données en cache affichées si disponibles", icon="🔴")

st.title("📊 Tableau de bord — État actuel")

# ── Monitoring strip ───────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)

if now.month == 12:
    _next = datetime(now.year + 1, 1, 1, 6, 0, tzinfo=timezone.utc)
else:
    _next = datetime(now.year, now.month + 1, 1, 6, 0, tzinfo=timezone.utc)
if now.day == 1 and now.hour < 6:
    _next = datetime(now.year, now.month, 1, 6, 0, tzinfo=timezone.utc)

days_until     = (_next.date() - now.date()).days
next_run_label = _next.strftime("%d/%m/%Y 06h00 UTC")

last_wb = sen_records[0]["period"] if sen_records else (
    civ_records[0]["period"] if civ_records else "—"
)

m1, m2, m3 = st.columns(3)
m1.metric(
    label="Statut système",
    value="✅ Opérationnel" if (api_ok and db_ok) else ("⚠️ Dégradé" if api_ok else "❌ Hors ligne"),
    help="Résultat du GET /v1/health — vérifie l'API et la base de données",
)
m2.metric(
    label="Dernière ingestion",
    value=last_wb,
    help="Période la plus récente disponible dans la base de données",
)
m3.metric(
    label="Prochain run pipeline",
    value=f"J-{days_until}",
    delta=next_run_label,
    delta_color="off",
    help="GitHub Actions déclenche l'ingestion automatiquement le 1er du mois à 06h00 UTC",
)

st.markdown("---")

# ── Jauges de risque ───────────────────────────────────────────────────────────
col1, col2 = st.columns(2)


def _risk_gauge(score: float, delta_amount: float | None, title: str, level: str) -> go.Figure:
    bar_color = (
        "#2ecc71" if score < 25 else
        "#f1c40f" if score < 50 else
        "#e67e22" if score < 75 else
        "#e74c3c"
    )
    mode = "gauge+number+delta" if delta_amount is not None else "gauge+number"

    kwargs: dict = dict(
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
                {"range": [0,  25], "color": "#d5f5e3"},
                {"range": [25, 50], "color": "#fef9e7"},
                {"range": [50, 75], "color": "#fdf2e9"},
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
        kwargs["delta"] = {
            "reference": score - delta_amount,
            "increasing": {"color": "#e74c3c"},
            "decreasing": {"color": "#2ecc71"},
        }

    fig = go.Figure(go.Indicator(**kwargs))
    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=70, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _render_country(col, flag: str, name: str, records: list) -> None:
    with col:
        st.subheader(f"{flag} {name}")
        if not records:
            st.info("Données indisponibles")
            return

        current = records[0]
        prev    = records[1] if len(records) > 1 else None
        score   = float(current["risk_score"])
        delta   = round(score - float(prev["risk_score"]), 2) if prev else None
        level   = current.get("risk_level", "low")
        period  = current.get("period", "—")

        st.plotly_chart(
            _risk_gauge(score, delta, f"{flag} {name} — {period}", level),
            use_container_width=True,
        )

        sub1, sub2 = st.columns(2)
        sub1.metric(
            "Tendance des prix",
            f"{float(current['price_trend_score']):.1f}",
            help="Hausse des prix alimentaires sur les marchés locaux (0 = stable, 100 = hausse de 20%+)",
        )
        sub2.metric(
            "Score inflation",
            f"{float(current['inflation_score']):.1f}",
            help="Taux d'inflation national (source : Banque Mondiale — FP.CPI.TOTL.ZG)",
        )
        if delta is not None:
            st.caption(
                f"Variation vs période précédente : "
                f"**{'↑' if delta > 0 else '↓'} {abs(delta):.2f} pts**"
            )


_render_country(col1, "🇸🇳", "Sénégal (SEN)", sen_records)
_render_country(col2, "🇨🇮", "Côte d'Ivoire (CIV)", civ_records)

pour_comprendre(
    "Comment lire ces jauges ?",
    """
Chaque jauge montre le **score de risque alimentaire** du pays, de 0 à 100.

- La **barre colorée** indique le niveau actuel. Elle pointe dans la zone correspondante.
- Les **zones de couleur** montrent les seuils : vert (faible), jaune (moyen), orange (élevé), rouge (critique).
- Le **delta** (↑ ou ↓) sous le chiffre montre l'évolution par rapport au mois précédent.
- **Tendance des prix** : hausse des prix sur les marchés WFP. 0 = stable, 100 = +20% ou plus en 3 mois.
- **Score inflation** : basé sur l'inflation nationale Banque Mondiale. 0 = 0%, 100 = 20%+ d'inflation.
    """,
)

st.markdown("---")

# ── Évolution 12 derniers mois ─────────────────────────────────────────────────
st.subheader("Évolution du risque — 12 derniers mois")

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
        yaxis=dict(range=[0, 100], title="Score de risque"),
        xaxis_title="Période",
        height=350,
        margin=dict(l=0, r=80, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    pour_comprendre(
        "Comment lire ce graphique ?",
        """
Ce graphique montre l'évolution du **score de risque** sur les 12 derniers mois.

- **Courbe bleue** = Sénégal, **courbe verte** = Côte d'Ivoire
- Une **courbe qui monte** indique une dégradation de la situation alimentaire
- Les **lignes pointillées** marquent les seuils d'alerte :
  - Jaune = MOYEN (25), Orange = ÉLEVÉ (50), Rouge = CRITIQUE (75)
- Survolez les points pour voir les valeurs exactes par mois
        """,
    )
else:
    st.info("Aucune donnée de risk score disponible.")
