import folium
import streamlit as st
from streamlit_folium import st_folium

from api_client import get_risk_scores

st.set_page_config(
    page_title="Carte satellite — Sahel Flow",
    page_icon="🛰️",
    layout="wide",
)

st.title("🛰️ Carte satellite — Risque alimentaire")
st.caption(
    "Fond Esri WorldImagery (gratuit, sans clé API) · "
    "Score de risque en temps réel · "
    "Principaux marchés alimentaires"
)

# ── Configuration géographique ─────────────────────────────────────────────────
_LEVEL_COLORS = {
    "low":      "#2ecc71",
    "medium":   "#f1c40f",
    "high":     "#e67e22",
    "critical": "#e74c3c",
}

_COUNTRIES: dict[str, dict] = {
    "SEN": {
        "name": "Sénégal",
        "flag": "🇸🇳",
        "center": [14.5, -14.5],
        "markets": [
            {"name": "Dakar",       "lat": 14.7167, "lon": -17.4677},
            {"name": "Thiès",       "lat": 14.7833, "lon": -16.9333},
            {"name": "Kaolack",     "lat": 14.1500, "lon": -16.0667},
            {"name": "Saint-Louis", "lat": 16.0333, "lon": -16.5000},
            {"name": "Ziguinchor",  "lat": 12.5833, "lon": -16.2667},
            {"name": "Tambacounda", "lat": 13.7667, "lon": -13.6667},
        ],
    },
    "CIV": {
        "name": "Côte d'Ivoire",
        "flag": "🇨🇮",
        "center": [7.5, -5.5],
        "markets": [
            {"name": "Abidjan",       "lat": 5.3600,  "lon": -4.0083},
            {"name": "Yamoussoukro", "lat": 6.8276,  "lon": -5.2893},
            {"name": "Bouaké",        "lat": 7.6833,  "lon": -5.0333},
            {"name": "Korhogo",       "lat": 9.4500,  "lon": -5.6333},
            {"name": "Man",           "lat": 7.4000,  "lon": -7.5500},
            {"name": "San Pédro",     "lat": 4.7500,  "lon": -6.6333},
        ],
    },
}

# ── Fetch risk scores ──────────────────────────────────────────────────────────
sen_records = get_risk_scores("SEN")
civ_records = get_risk_scores("CIV")
risk_by_country: dict[str, dict | None] = {
    "SEN": sen_records[0] if sen_records else None,
    "CIV": civ_records[0] if civ_records else None,
}

# ── Folium satellite map ───────────────────────────────────────────────────────
m = folium.Map(
    location=[9.5, -10.0],
    zoom_start=5,
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/services"
        "/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri WorldImagery",
)

# Labels overlay (noms de pays + villes) sur fond satellite
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
    attr="CartoDB",
    name="Étiquettes",
    overlay=True,
    control=True,
).add_to(m)

# Groupe principal : zones de risque
risk_group = folium.FeatureGroup(name="Zones de risque", show=True)
# Groupe marchés
market_group = folium.FeatureGroup(name="Marchés alimentaires", show=True)

for code, info in _COUNTRIES.items():
    record = risk_by_country.get(code)

    if record:
        score     = float(record["risk_score"])
        level     = record.get("risk_level", "low")
        color     = _LEVEL_COLORS.get(level, "#999999")
        period    = record.get("period", "—")
        inflation = float(record.get("inflation_score", 0))
        radius    = max(28, min(55, score / 1.5))

        popup_html = (
            f"<div style='font-family:sans-serif;min-width:190px;'>"
            f"<b style='font-size:1.1em'>{info['flag']} {info['name']}</b><br>"
            f"<hr style='margin:4px 0'>"
            f"<b>Risk Score :</b> {score:.1f} / 100<br>"
            f"<b>Niveau :</b> <span style='color:{color};font-weight:bold'>"
            f"{level.upper()}</span><br>"
            f"<b>Score inflation :</b> {inflation:.1f} / 100<br>"
            f"<b>Période :</b> {period}"
            f"</div>"
        )

        folium.CircleMarker(
            location=info["center"],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.35,
            weight=2.5,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{info['flag']} {info['name']} — {score:.1f} / 100  ({level.upper()})",
        ).add_to(risk_group)
    else:
        folium.CircleMarker(
            location=info["center"],
            radius=30,
            color="#aaaaaa",
            fill=True,
            fill_color="#aaaaaa",
            fill_opacity=0.25,
            weight=1.5,
            tooltip=f"{info['flag']} {info['name']} — données indisponibles",
        ).add_to(risk_group)

    # Market dots
    for market in info["markets"]:
        folium.CircleMarker(
            location=[market["lat"], market["lon"]],
            radius=5,
            color="white",
            fill=True,
            fill_color="#2471a3",
            fill_opacity=0.9,
            weight=1.5,
            tooltip=f"📍 {market['name']}",
        ).add_to(market_group)

risk_group.add_to(m)
market_group.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, use_container_width=True, height=520, returned_objects=[])

# ── Légende ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Légende — Niveaux de risque")

leg_cols = st.columns(4)
levels_info = [
    ("🟢 FAIBLE",   "0 – 24",   "#d5f5e3", "#1e8449"),
    ("🟡 MOYEN",    "25 – 49",  "#fef9e7", "#b7950b"),
    ("🟠 ÉLEVÉ",    "50 – 74",  "#fdf2e9", "#d35400"),
    ("🔴 CRITIQUE", "75 – 100", "#fdedec", "#c0392b"),
]
for col, (label, rng, bg, fg) in zip(leg_cols, levels_info):
    col.markdown(
        f"<div style='"
        f"background:{bg};padding:12px 8px;border-radius:8px;"
        f"text-align:center;border:1px solid {fg}20;'>"
        f"<b style='color:{fg};font-size:0.95em'>{label}</b><br>"
        f"<span style='color:#555;font-size:0.85em'>{rng}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Scores actuels ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Scores actuels")

score_cols = st.columns(2)
for col, code in zip(score_cols, ["SEN", "CIV"]):
    info   = _COUNTRIES[code]
    record = risk_by_country.get(code)
    with col:
        if record:
            score = float(record["risk_score"])
            level = record.get("risk_level", "low")
            infl  = float(record.get("inflation_score", 0))
            col.metric(
                label=f"{info['flag']} {info['name']}",
                value=f"{score:.1f} / 100",
                help=f"Période : {record.get('period', '—')} · Niveau : {level.upper()}",
            )
            col.caption(f"Score inflation : {infl:.1f}  |  Prix : {float(record.get('price_trend_score', 0)):.1f}")
        else:
            col.info(f"{info['flag']} {info['name']} — données indisponibles")

st.markdown("---")
st.caption(
    "🛰️ **Fond satellite** : Esri WorldImagery (gratuit, sans clé API) · "
    "📍 **Marchés** : principaux centres de collecte de prix alimentaires · "
    "⚪ **Cercles de risque** : taille proportionnelle au score"
)
