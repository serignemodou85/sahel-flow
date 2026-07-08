"""
Ingestion World Bank → Supabase (mart__macro__indicators_annual).
Script standalone : stdlib + psycopg2 uniquement.

Prérequis :
    pip install psycopg2-binary
    export DATABASE_URL_OVERRIDE="postgresql://postgres.xxx:pass@pooler.supabase.com:5432/postgres?sslmode=require"

Usage :
    python infra/supabase/ingest_worldbank.py
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2.extras import execute_values

_SUPABASE = os.environ.get("DATABASE_URL_OVERRIDE")
if not _SUPABASE:
    raise ValueError("DATABASE_URL_OVERRIDE non défini")

_WB_BASE = "https://api.worldbank.org/v2"
_COUNTRIES = "SEN;CIV"
_INDICATORS = {
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "NY.GDP.PCAP.CD":  "GDP per capita (current USD)",
    "SN.ITK.DEFC.ZS":  "Prevalence of undernourishment (% of population)",
    "AG.PRD.FOOD.XD":  "Food production index",
    "SP.POP.TOTL":     "Population, total",
}
_START_YEAR = 2000
_END_YEAR   = 2024


def _fetch_indicator(code: str) -> list[dict]:
    """Récupère toutes les pages d'un indicateur pour SEN+CIV."""
    url = (
        f"{_WB_BASE}/country/{_COUNTRIES}/indicator/{code}"
        f"?format=json&per_page=1000&date={_START_YEAR}:{_END_YEAR}"
    )
    records: list[dict] = []
    page = 1
    while True:
        paged = url + f"&page={page}"
        with urllib.request.urlopen(paged, timeout=30) as resp:
            data = json.loads(resp.read())
        meta, rows = data[0], data[1] or []
        records.extend(rows)
        if page >= meta["pages"]:
            break
        page += 1
    return records


def _parse(raw: dict, indicator_name: str) -> dict | None:
    date_str = raw.get("date")
    country  = raw.get("countryiso3code")
    if not date_str or not country:
        return None
    try:
        year = int(date_str)
    except ValueError:
        return None
    value = raw.get("value")
    return {
        "period":         date(year, 1, 1),
        "country_code":   country,
        "indicator_code": raw.get("indicator", {}).get("id", ""),
        "indicator_name": indicator_name,
        "indicator_value": Decimal(str(value)) if value is not None else None,
    }


def _compute_yoy(records: list[dict]) -> list[dict]:
    """Ajoute yoy_change_pct par (country_code, indicator_code), trié par period."""
    from collections import defaultdict
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[(r["country_code"], r["indicator_code"])].append(r)

    result: list[dict] = []
    for group in groups.values():
        group.sort(key=lambda x: x["period"])
        for i, r in enumerate(group):
            prev = group[i - 1]["indicator_value"] if i > 0 else None
            cur  = r["indicator_value"]
            yoy  = None
            if cur is not None and prev is not None and prev != 0:
                try:
                    yoy = round((cur / prev - 1) * 100, 4)
                except (InvalidOperation, ZeroDivisionError):
                    yoy = None
            result.append({**r, "yoy_change_pct": yoy})
    return result


def _compute_risk_scores(enriched: list[dict]) -> list[dict]:
    """Risk score simplifié sans WFP : price_trend_score=0, basé sur inflation seule.
    Formule : risk_score = 0.4 * inflation_score  (0.6 * 0 + 0.4 * inflation_score)
    """
    inflation_rows = [
        r for r in enriched
        if r["indicator_code"] == "FP.CPI.TOTL.ZG"
        and r["indicator_value"] is not None
    ]
    result = []
    for r in inflation_rows:
        rate = float(r["indicator_value"])
        inflation_score = min(100.0, max(0.0, rate * 5))
        result.append({
            "period":             r["period"],
            "country_code":       r["country_code"],
            "price_trend_score":  Decimal("0.00"),
            "inflation_score":    round(Decimal(str(inflation_score)), 2),
            "risk_score":         round(Decimal(str(0.4 * inflation_score)), 2),
        })
    return result


def main() -> None:
    print(f"Cible : {_SUPABASE[:60]}...")

    all_records: list[dict] = []
    for code, name in _INDICATORS.items():
        raw_rows = _fetch_indicator(code)
        parsed   = [_parse(r, name) for r in raw_rows]
        cleaned  = [r for r in parsed if r is not None]
        all_records.extend(cleaned)
        print(f"  {code} : {len(cleaned)} enregistrements")

    enriched     = _compute_yoy(all_records)
    risk_rows    = _compute_risk_scores(enriched)
    print(f"\nTotal : {len(enriched)} macro | {len(risk_rows)} risk scores à upsert")

    conn = psycopg2.connect(dsn=_SUPABASE)
    try:
        macro_rows = [
            (
                r["period"],
                r["country_code"],
                r["indicator_code"],
                r["indicator_name"],
                r["indicator_value"],
                r["yoy_change_pct"],
            )
            for r in enriched
        ]
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO marts.mart__macro__indicators_annual
                    (period, country_code, indicator_code, indicator_name,
                     indicator_value, yoy_change_pct)
                VALUES %s
                ON CONFLICT (period, country_code, indicator_code) DO UPDATE SET
                    indicator_name  = EXCLUDED.indicator_name,
                    indicator_value = EXCLUDED.indicator_value,
                    yoy_change_pct  = EXCLUDED.yoy_change_pct
            """, macro_rows)

        score_rows = [
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
            """, score_rows)

        conn.commit()
        print(f"Terminé : {len(macro_rows)} macro | {len(score_rows)} risk scores insérés")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
