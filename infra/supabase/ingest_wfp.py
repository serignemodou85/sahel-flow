"""
Ingestion WFP HDX → Supabase.
Tables mises à jour :
    1. mart__food__prices_monthly  (agrégation marchés → commodité-mois)
    2. mart__risk__score_monthly   (score complet : 0.6 × price_trend + 0.4 × inflation)

Standalone : stdlib + psycopg2 uniquement. Zéro clé API (HDX = données publiques WFP).

Prérequis :
    pip install psycopg2-binary
    export DATABASE_URL_OVERRIDE="postgresql://..."

Usage :
    python infra/supabase/ingest_wfp.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.request
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2.extras import execute_values

_SUPABASE = os.environ.get("DATABASE_URL_OVERRIDE")
if not _SUPABASE:
    raise ValueError("DATABASE_URL_OVERRIDE non défini")

_HDX_CKAN     = "https://data.humdata.org/api/3/action"
_HDX_DATASETS = {
    "SEN": "wfp-food-prices-for-senegal",
    "CIV": "wfp-food-prices-for-cote-d-ivoire",
}
# Filtre temporel : évite d'upserter 20 ans d'historique à chaque run
_FILTER_YEAR = 2020


# ── Fetch CSV depuis HDX (CKAN API) ───────────────────────────────────────────

def _hdx_csv_url(dataset_slug: str) -> str:
    """Résoud dynamiquement l'URL du CSV via l'API CKAN d'HDX.
    Plus robuste qu'une URL hardcodée (les resource_id HDX peuvent changer).
    """
    url = f"{_HDX_CKAN}/package_show?id={dataset_slug}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        pkg = json.loads(resp.read())

    resources = pkg["result"]["resources"]
    csvs = [r for r in resources if r.get("format", "").upper() == "CSV"]
    if not csvs:
        raise ValueError(f"Aucune ressource CSV trouvée dans le dataset HDX '{dataset_slug}'")

    return csvs[0]["url"]


def _fetch_rows(country_code: str) -> list[dict]:
    """Télécharge le CSV HDX et filtre les lignes >= _FILTER_YEAR.

    HDX peut utiliser deux variantes de colonnes (selon la version du dataset) :
    - "date" (YYYY-MM-DD)  ou  "mp_year" + "mp_month"
    - "cm_name"            ou  "cmName"
    - "mkt_name"           ou  "mktName"
    - "um_name"            ou  "umName"
    - "cur_name"           ou  "currName"
    - "mp_price"           ou  "price"
    Le parser essaie les deux variantes pour chaque colonne.
    """
    dataset = _HDX_DATASETS[country_code]
    csv_url = _hdx_csv_url(dataset)
    print(f"  GET {csv_url}")

    with urllib.request.urlopen(csv_url, timeout=120) as resp:
        # utf-8-sig gère le BOM éventuel en tête de fichier CSV
        content = resp.read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict] = []

    for row in reader:
        # ── Date ──────────────────────────────────────────────────────────────
        date_str = row.get("date") or ""
        if not date_str:
            mp_year  = row.get("mp_year", "")
            mp_month = row.get("mp_month", "")
            if mp_year and mp_month:
                date_str = f"{mp_year}-{int(mp_month):02d}-01"
        if not date_str:
            continue
        try:
            year, month = int(date_str[:4]), int(date_str[5:7])
        except ValueError:
            continue
        if year < _FILTER_YEAR:
            continue

        # ── Champs principaux (deux variantes de nommage) ─────────────────────
        commodity = (row.get("cm_name")  or row.get("cmName")   or "").strip()
        market    = (row.get("mkt_name") or row.get("mktName")  or "").strip()
        unit      = (row.get("um_name")  or row.get("umName")   or "").strip()
        currency  = (row.get("cur_name") or row.get("currName") or "XOF").strip()
        price_raw = (row.get("mp_price") or row.get("price")    or "").strip()

        if not commodity or not market or not price_raw:
            continue

        try:
            price = Decimal(price_raw)
        except InvalidOperation:
            continue

        rows.append({
            "period":       date(year, month, 1),
            "country_code": country_code,
            "commodity":    commodity,
            "market":       market,
            "unit":         unit,
            "currency":     currency,
            "price_local":  price,
        })

    print(f"  {country_code} : {len(rows)} lignes >= {_FILTER_YEAR}")
    return rows


# ── Agrégation marchés → commodité ────────────────────────────────────────────

def _aggregate(rows: list[dict]) -> list[dict]:
    """AVG(price_local) par (period, country_code, commodity).

    WFP fournit un prix par marché.
    mart__food__prices_monthly attend une valeur agrégée par commodité.
    """
    price_groups: dict[tuple, list[Decimal]] = defaultdict(list)
    meta: dict[tuple, dict] = {}

    for r in rows:
        key = (r["period"], r["country_code"], r["commodity"])
        price_groups[key].append(r["price_local"])
        if key not in meta:
            meta[key] = {"unit": r["unit"], "currency": r["currency"]}

    result = []
    for key, prices in price_groups.items():
        period, country_code, commodity = key
        avg = sum(prices) / len(prices)
        result.append({
            "period":          period,
            "country_code":    country_code,
            "commodity":       commodity,
            "unit":            meta[key]["unit"],
            "currency":        meta[key]["currency"],
            "avg_price_local": round(Decimal(str(avg)), 4),
            # avg_price_usd non calculé : le ratio price/baseline est currency-agnostique
            "avg_price_usd":   None,
            "market_count":    len(prices),
        })

    return result


# ── Price trend score ──────────────────────────────────────────────────────────

def _compute_price_trend(aggregated: list[dict]) -> list[dict]:
    """price_trend_score par (period, country_code, commodity).

    Formule :
        baseline_3m      = AVG des 3 mois précédents (même country × commodity)
        variation        = (price_current / baseline_3m - 1) × 500
        price_trend_score = LEAST(100, GREATEST(0, variation))

    Équivalent Python de :
        LAG() OVER (PARTITION BY country_code, commodity ORDER BY period
                    ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)

    Même pattern que _compute_yoy dans ingest_worldbank.py :
    defaultdict groupé par (country_code, commodity), trié par period,
    fenêtre glissante group[i-3:i].
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in aggregated:
        key = (r["country_code"], r["commodity"])
        groups[key].append(r)

    result = []
    for group in groups.values():
        group.sort(key=lambda x: x["period"])
        for i, r in enumerate(group):
            prev_prices = [
                g["avg_price_local"]
                for g in group[max(0, i - 3):i]
                if g["avg_price_local"] is not None
            ]
            baseline_3m = (
                Decimal(str(sum(prev_prices) / len(prev_prices)))
                if prev_prices else None
            )
            cur = r["avg_price_local"]

            price_trend = None
            if cur is not None and baseline_3m is not None and baseline_3m != 0:
                try:
                    variation   = (float(cur) / float(baseline_3m) - 1) * 500
                    price_trend = round(Decimal(str(min(100.0, max(0.0, variation)))), 2)
                except (InvalidOperation, ZeroDivisionError):
                    price_trend = None

            result.append({**r, "price_trend_score": price_trend})

    return result


# ── Risk scores complets ───────────────────────────────────────────────────────

def _fetch_inflation(conn) -> dict[tuple, float]:
    """Charge les taux d'inflation depuis mart__macro__indicators_annual (déjà en base).
    Clé : (country_code, year) → inflation_rate (%).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_code,
                   EXTRACT(YEAR FROM period)::int AS year,
                   indicator_value::float
            FROM   marts.mart__macro__indicators_annual
            WHERE  indicator_code = 'FP.CPI.TOTL.ZG'
              AND  indicator_value IS NOT NULL
        """)
        return {(row[0], int(row[1])): row[2] for row in cur.fetchall()}


def _compute_full_risk_scores(
    price_rows: list[dict],
    inflation_map: dict[tuple, float],
) -> list[dict]:
    """risk_score = 0.6 × price_trend_score + 0.4 × inflation_score.

    price_trend_score ici = moyenne des commodités disponibles ce mois-là
    (agrégation de l'indicateur par commodité → indicateur pays-mois).
    Jointure mensuel × annuel sur (country_code, year).
    """
    monthly_trends: dict[tuple, list[float]] = defaultdict(list)
    for r in price_rows:
        if r["price_trend_score"] is not None:
            key = (r["period"], r["country_code"])
            monthly_trends[key].append(float(r["price_trend_score"]))

    result = []
    for (period, country_code), trends in monthly_trends.items():
        avg_trend       = sum(trends) / len(trends)
        inflation_rate  = inflation_map.get((country_code, period.year), 0.0)
        inflation_score = min(100.0, max(0.0, inflation_rate * 5))
        risk_score      = 0.6 * avg_trend + 0.4 * inflation_score

        result.append({
            "period":             period,
            "country_code":       country_code,
            "price_trend_score":  round(Decimal(str(avg_trend)),      2),
            "inflation_score":    round(Decimal(str(inflation_score)), 2),
            "risk_score":         round(Decimal(str(risk_score)),      2),
        })

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Cible : {_SUPABASE[:60]}...")

    all_rows: list[dict] = []
    for country_code in _HDX_DATASETS:
        raw       = _fetch_rows(country_code)
        agg       = _aggregate(raw)
        with_trend = _compute_price_trend(agg)
        all_rows.extend(with_trend)
        print(f"  {country_code} : {len(agg)} lignes agrégées commodité-mois")

    print(f"\nTotal : {len(all_rows)} lignes à upserter dans mart__food__prices_monthly")

    conn = psycopg2.connect(dsn=_SUPABASE)
    try:
        # ── 1. mart__food__prices_monthly ─────────────────────────────────────
        price_tuples = [
            (
                r["period"],
                r["country_code"],
                r["commodity"],
                r["unit"],
                r["currency"],
                r["avg_price_local"],
                r["avg_price_usd"],
                r["market_count"],
            )
            for r in all_rows
        ]
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO marts.mart__food__prices_monthly
                    (period, country_code, commodity, unit, currency,
                     avg_price_local, avg_price_usd, market_count)
                VALUES %s
                ON CONFLICT (period, country_code, commodity) DO UPDATE SET
                    avg_price_local = EXCLUDED.avg_price_local,
                    avg_price_usd   = EXCLUDED.avg_price_usd,
                    market_count    = EXCLUDED.market_count
            """, price_tuples)

        # ── 2. mart__risk__score_monthly (score complet avec price_trend réel) ─
        inflation_map = _fetch_inflation(conn)
        risk_rows     = _compute_full_risk_scores(all_rows, inflation_map)

        score_tuples = [
            (
                r["period"],
                r["country_code"],
                r["price_trend_score"],
                r["inflation_score"],
                r["risk_score"],
            )
            for r in risk_rows
        ]
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO marts.mart__risk__score_monthly
                    (period, country_code, price_trend_score, inflation_score, risk_score)
                VALUES %s
                ON CONFLICT (period, country_code) DO UPDATE SET
                    price_trend_score = EXCLUDED.price_trend_score,
                    inflation_score   = EXCLUDED.inflation_score,
                    risk_score        = EXCLUDED.risk_score
            """, score_tuples)

        conn.commit()
        print(
            f"Terminé : {len(price_tuples)} prix alimentaires | "
            f"{len(score_tuples)} risk scores (score complet) insérés"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
