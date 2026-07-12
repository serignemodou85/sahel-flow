"""Utilitaires partagés pour toutes les pages Streamlit."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

_LEVEL_LABELS = {
    "low":      "🟢 FAIBLE",
    "medium":   "🟡 MOYEN",
    "high":     "🟠 ÉLEVÉ",
    "critical": "🔴 CRITIQUE",
}
_LEVEL_COLORS = {
    "low":      "#2ecc71",
    "medium":   "#f1c40f",
    "high":     "#e67e22",
    "critical": "#e74c3c",
}
_LEVEL_BG = {
    "low":      "#d5f5e3",
    "medium":   "#fef9e7",
    "high":     "#fdf2e9",
    "critical": "#fdedec",
}
_SITUATIONS = {
    "low":      "Situation alimentaire stable. Les marchés fonctionnent normalement.",
    "medium":   "Situation sous surveillance. Les prix montrent une légère tension.",
    "high":     "Alerte alimentaire. Les prix sont en hausse significative.",
    "critical": "Crise alimentaire. Une intervention urgente est recommandée.",
}
_RECOMMENDATIONS = {
    "low":      "Maintenir la surveillance de routine.",
    "medium":   "Surveiller l'évolution des prix hebdomadairement. Vérifier les stocks tampons.",
    "high":     "Activer les mécanismes d'alerte. Évaluer les besoins en assistance alimentaire.",
    "critical": "Déclencher les protocoles d'urgence. Mobiliser les partenaires humanitaires.",
}


def alert_banner(sen_records: list, civ_records: list) -> None:
    """Bannière d'alerte rouge/orange si un pays est en niveau ÉLEVÉ ou CRITIQUE.
    Affichée en haut de chaque page — décideur voit l'urgence sans naviguer.
    """
    alerts = []
    for flag, name, records in [
        ("🇸🇳", "Sénégal", sen_records),
        ("🇨🇮", "Côte d'Ivoire", civ_records),
    ]:
        if not records:
            continue
        score = float(records[0]["risk_score"])
        level = records[0].get("risk_level", "low")
        if level not in ("high", "critical"):
            continue
        prev_score = float(records[1]["risk_score"]) if len(records) > 1 else score
        delta = score - prev_score
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        label = "CRITIQUE" if level == "critical" else "ÉLEVÉ"
        period = records[0].get("period", "")
        alerts.append(
            f"**{flag} {name} — Niveau {label}** "
            f"| Score : {score:.1f} / 100 ({delta_str} pts vs mois dernier) "
            f"| Période : {period}"
        )

    if not alerts:
        return

    icon = "🔴" if any("CRITIQUE" in a for a in alerts) else "🟠"
    st.error("\n\n".join(alerts), icon=icon)


def risk_card(flag: str, country_name: str, records: list) -> None:
    """Carte de situation par pays — langage décideur, pas de jargon technique."""
    if not records:
        st.info(f"{flag} {country_name} — données indisponibles")
        return

    r = records[0]
    score       = float(r["risk_score"])
    level       = r.get("risk_level", "low")
    period      = r.get("period", "—")
    price_trend = float(r.get("price_trend_score", 0))
    inflation_s = float(r.get("inflation_score", 0))

    prev  = records[1] if len(records) > 1 else None
    delta = round(score - float(prev["risk_score"]), 1) if prev else None

    color = _LEVEL_COLORS.get(level, "#95a5a6")
    bg    = _LEVEL_BG.get(level, "#f8f9fa")
    label = _LEVEL_LABELS.get(level, level.upper())

    if price_trend > inflation_s + 5:
        attention = f"Prix alimentaires en tension ({price_trend:.0f} / 100)"
    elif inflation_s > price_trend + 5:
        attention = f"Pression inflationniste ({inflation_s:.0f} / 100)"
    elif score < 10:
        attention = "Aucune composante préoccupante"
    else:
        attention = "Composantes équilibrées — surveiller les deux indicateurs"

    delta_html = ""
    if delta is not None:
        arrow   = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        d_color = "#e74c3c" if delta > 0 else ("#2ecc71" if delta < 0 else "#999")
        delta_html = (
            f"&nbsp;<span style='color:{d_color};font-size:0.8em'>"
            f"{arrow} {abs(delta):.1f} pts</span>"
        )

    st.markdown(
        f"""
        <div style="background:{bg};border-left:5px solid {color};border-radius:10px;
                    padding:18px 20px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;
                        align-items:flex-start;flex-wrap:wrap;gap:8px;">
                <span style="font-size:1.15em;font-weight:bold">{flag} {country_name}</span>
                <span style="background:{color};color:white;padding:3px 14px;
                              border-radius:20px;font-weight:bold;
                              font-size:0.85em;white-space:nowrap">{label}</span>
            </div>
            <p style="font-size:1.9em;font-weight:bold;margin:10px 0 0 0;line-height:1">
                {score:.1f}
                <span style="font-size:0.42em;color:#666;font-weight:normal"> / 100</span>
                {delta_html}
            </p>
            <p style="color:#888;font-size:0.78em;margin:3px 0 14px 0">Période : {period}</p>
            <hr style="border:none;border-top:1px solid {color}55;margin:8px 0">
            <p style="margin:6px 0;font-size:0.9em">
                <b>Situation :</b> {_SITUATIONS.get(level, '')}
            </p>
            <p style="margin:6px 0;font-size:0.9em">
                ⚠️ <b>Point d'attention :</b> {attention}
            </p>
            <p style="margin:6px 0;font-size:0.88em;color:#555">
                📌 <b>Recommandation :</b> {_RECOMMENDATIONS.get(level, '')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def commodity_feu_tricolore(records: list) -> pd.DataFrame | None:
    """DataFrame avec variation 3 mois et statut feu tricolore par commodité.

    Retourne None si données insuffisantes (moins de 2 mois de données).
    Variation calculée sur avg_price_local (FCFA) — currency-agnostic.
    """
    if not records:
        return None

    df = pd.DataFrame(records)
    df["period"] = pd.to_datetime(df["period"])
    df = df.sort_values("period")

    latest  = df["period"].max()
    cutoff  = latest - pd.DateOffset(months=4)

    latest_df   = df[df["period"] == latest].copy()
    baseline_df = df[(df["period"] >= cutoff) & (df["period"] < latest)]

    if baseline_df.empty or latest_df.empty:
        return None

    baseline_avg = baseline_df.groupby("commodity")["avg_price_local"].mean()

    rows = []
    for _, row in latest_df.sort_values("commodity").iterrows():
        commodity   = row["commodity"]
        price_local = row.get("avg_price_local")
        if price_local is None:
            continue
        price_local = float(price_local)

        if commodity in baseline_avg.index and float(baseline_avg[commodity]) > 0:
            pct = (price_local / float(baseline_avg[commodity]) - 1) * 100
        else:
            pct = None

        if pct is None:
            status = "⚪ Données insuffisantes"
        elif pct > 10:
            status = "🔴 Hausse forte"
        elif pct > 5:
            status = "🟡 Hausse modérée"
        elif pct < -5:
            status = "🟢 Baisse"
        else:
            status = "🟢 Stable"

        rows.append({
            "Commodité":           commodity,
            "Unité":               row.get("unit", ""),
            "Prix actuel (FCFA)":  f"{price_local:,.0f}",
            "Variation 3 mois":    f"{pct:+.1f}%" if pct is not None else "—",
            "Statut":              status,
        })

    return pd.DataFrame(rows) if rows else None


def faits_marquants(sen_prices: list, civ_prices: list) -> list[str]:
    """Génère des bullets en langage naturel depuis les variations de prix.

    Retourne une liste de strings markdown (avec **gras**).
    Algorithme : commodité avec la plus forte variation absolue vs baseline 3 mois.
    """
    bullets: list[str] = []

    for flag, country, prices in [
        ("🇸🇳", "Sénégal", sen_prices),
        ("🇨🇮", "Côte d'Ivoire", civ_prices),
    ]:
        if not prices:
            bullets.append(f"→ {flag} **{country}** : données de marché indisponibles ce mois")
            continue

        df = pd.DataFrame(prices)
        df["period"] = pd.to_datetime(df["period"])
        df = df.sort_values("period")

        latest  = df["period"].max()
        cutoff  = latest - pd.DateOffset(months=4)

        latest_df   = df[df["period"] == latest]
        baseline_df = df[(df["period"] >= cutoff) & (df["period"] < latest)]

        if baseline_df.empty:
            bullets.append(f"→ {flag} **{country}** : données insuffisantes pour calculer la tendance")
            continue

        baseline_avg = baseline_df.groupby("commodity")["avg_price_local"].mean()

        changes: list[tuple[str, float]] = []
        for commodity in latest_df["commodity"].unique():
            curr_rows = latest_df[latest_df["commodity"] == commodity]
            if curr_rows.empty or commodity not in baseline_avg.index:
                continue
            curr_price = float(curr_rows["avg_price_local"].mean())
            base_price = float(baseline_avg[commodity])
            if base_price > 0:
                pct = (curr_price / base_price - 1) * 100
                changes.append((commodity, pct))

        if not changes:
            bullets.append(f"→ {flag} **{country}** : aucune variation calculable")
            continue

        changes.sort(key=lambda x: abs(x[1]), reverse=True)
        top_commodity, top_pct = changes[0]

        if top_pct > 10:
            bullets.append(
                f"↑ {flag} **{country}** : {top_commodity} en hausse de **{top_pct:.0f}%** sur 3 mois"
            )
        elif top_pct > 5:
            bullets.append(
                f"↑ {flag} **{country}** : {top_commodity} en légère hausse de **{top_pct:.0f}%** sur 3 mois"
            )
        elif top_pct < -5:
            bullets.append(
                f"↓ {flag} **{country}** : {top_commodity} en baisse de **{abs(top_pct):.0f}%** sur 3 mois"
            )
        else:
            bullets.append(f"→ {flag} **{country}** : marchés alimentaires **stables** ce mois")

    return bullets


def rapport_texte(sen_records: list, civ_records: list, bullets: list[str]) -> str:
    """Génère un rapport de situation en texte brut téléchargeable."""
    today = date.today().strftime("%d/%m/%Y")

    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_run = datetime(now.year + 1, 1, 1, 6, 0, tzinfo=timezone.utc)
    else:
        next_run = datetime(now.year, now.month + 1, 1, 6, 0, tzinfo=timezone.utc)

    level_names = {"low": "FAIBLE", "medium": "MOYEN", "high": "ÉLEVÉ", "critical": "CRITIQUE"}

    lines = [
        "SAHEL FLOW — RAPPORT DE SITUATION ALIMENTAIRE",
        f"Zone UEMOA | Sénégal + Côte d'Ivoire",
        f"Rapport du {today}",
        "=" * 52,
        "",
    ]

    for flag, country, records in [
        ("SEN", "Sénégal", sen_records),
        ("CIV", "Côte d'Ivoire", civ_records),
    ]:
        if not records:
            lines += [f"{flag} {country} : données indisponibles", ""]
            continue
        r     = records[0]
        score = float(r["risk_score"])
        level = r.get("risk_level", "low")
        prev  = records[1] if len(records) > 1 else None
        delta = round(score - float(prev["risk_score"]), 1) if prev else None

        lines += [
            f"{flag}  {country}",
            "-" * 30,
            f"  Niveau de risque   : {level_names.get(level, level.upper())}",
            f"  Score              : {score:.1f} / 100"
            + (f"  ({'+' if delta and delta >= 0 else ''}{delta} pts)" if delta else ""),
            f"  Période            : {r.get('period', '—')}",
            f"  Tendance des prix  : {float(r.get('price_trend_score', 0)):.1f} / 100",
            f"  Score inflation    : {float(r.get('inflation_score', 0)):.1f} / 100",
            "",
            f"  Situation          : {_SITUATIONS.get(level, '')}",
            f"  Recommandation     : {_RECOMMENDATIONS.get(level, '')}",
            "",
        ]

    lines += [
        "FAITS MARQUANTS CE MOIS",
        "-" * 30,
    ]
    for b in bullets:
        clean = b.replace("**", "").replace("*", "")
        lines.append(f"  {clean}")

    lines += [
        "",
        "PROCHAIN POINT DE DONNÉES",
        "-" * 30,
        f"  {next_run.strftime('%1er %B %Y')} à 06h00 UTC",
        "  (GitHub Actions — World Bank + WFP HDX)",
        "",
        "=" * 52,
        "Source : Sahel Flow — https://github.com/serignemodou85/sahel-flow",
        "Données : World Bank API (annuel) + HDX WFP (mensuel, public)",
    ]

    return "\n".join(lines)


def pour_comprendre(titre: str, texte: str) -> None:
    """Encadré collapsible 'Pour comprendre ce graphique' sur chaque page."""
    with st.expander(f"❓ {titre}"):
        st.markdown(texte)
