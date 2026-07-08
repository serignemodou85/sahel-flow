#!/usr/bin/env python3
"""Peuple les tables marts de Supabase avec des données d'exemple réalistes.

Usage:
    DATABASE_URL_OVERRIDE=postgresql://user:pass@host:5432/postgres python infra/supabase/seed.py
"""

import math
import os
import random
from datetime import date

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ["DATABASE_URL_OVERRIDE"]

START_MONTH = date(2023, 1, 1)
END_MONTH   = date(2024, 12, 1)
COUNTRIES   = ["SEN", "CIV"]
XOF_PER_USD = 600.0

COMMODITIES = [
    ("Millet",      "KG", "XOF", {"SEN": 320.0, "CIV": 375.0}),
    ("Riz importe", "KG", "XOF", {"SEN": 485.0, "CIV": 515.0}),
    ("Mais",        "KG", "XOF", {"SEN": 270.0, "CIV": 305.0}),
    ("Sorgho",      "KG", "XOF", {"SEN": 295.0, "CIV": 325.0}),
]

INFLATION = {
    "SEN": {2022: 9.7, 2023: 5.9, 2024: 4.8},
    "CIV": {2022: 5.2, 2023: 4.4, 2024: 3.1},
}

random.seed(42)


def _months(start: date, end: date):
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        yield date(y, m, 1)
        m += 1
        if m > 12:
            m, y = 1, y + 1


def seed_food_prices(cur) -> int:
    rows = []
    for month in _months(START_MONTH, END_MONTH):
        trend_factor = ((month.year - 2023) * 12 + month.month - 1) * 0.003
        seasonal = 0.06 * math.sin(2 * math.pi * month.month / 12)
        for commodity, unit, currency, base_prices in COMMODITIES:
            for country in COUNTRIES:
                base = base_prices[country]
                noise = random.uniform(-0.04, 0.07)
                price_local = round(base * (1 + noise + seasonal + trend_factor), 2)
                price_usd   = round(price_local / XOF_PER_USD, 4)
                rows.append((month, country, commodity, unit, currency,
                              price_local, price_usd, 3, 0))
    execute_values(cur, """
        INSERT INTO marts.mart__food__prices_monthly
            (period, country_code, commodity, unit, currency,
             avg_price_local, avg_price_usd, market_count, null_price_count)
        VALUES %s
        ON CONFLICT (period, country_code, commodity) DO UPDATE SET
            avg_price_local  = EXCLUDED.avg_price_local,
            avg_price_usd    = EXCLUDED.avg_price_usd
    """, rows)
    return len(rows)


def seed_inflation(cur) -> int:
    rows = []
    for country in COUNTRIES:
        prev = None
        for year in [2022, 2023, 2024]:
            value = INFLATION[country][year]
            yoy   = round(value - prev, 4) if prev is not None else None
            rows.append((date(year, 1, 1), country, "FP.CPI.TOTL.ZG",
                         "Inflation, consumer prices (annual %)", value, yoy))
            prev = value
    execute_values(cur, """
        INSERT INTO marts.mart__macro__indicators_annual
            (period, country_code, indicator_code, indicator_name,
             indicator_value, yoy_change_pct)
        VALUES %s
        ON CONFLICT (period, country_code, indicator_code) DO UPDATE SET
            indicator_value = EXCLUDED.indicator_value,
            yoy_change_pct  = EXCLUDED.yoy_change_pct
    """, rows)
    return len(rows)


def seed_risk_scores(cur) -> int:
    rows = []
    for month in _months(START_MONTH, END_MONTH):
        trend_base = ((month.year - 2023) * 12 + month.month - 1) * 1.8
        for country in COUNTRIES:
            infl_rate     = INFLATION[country].get(month.year, 4.8)
            price_trend   = min(100.0, max(0.0, 18.0 + trend_base + random.uniform(-7, 7)))
            infl_score    = min(100.0, infl_rate * 5.0)
            risk          = round(0.6 * price_trend + 0.4 * infl_score, 2)
            rows.append((month, country,
                         round(price_trend, 2), round(infl_score, 2), risk))
    execute_values(cur, """
        INSERT INTO marts.mart__risk__score_monthly
            (period, country_code, price_trend_score, inflation_score, risk_score)
        VALUES %s
        ON CONFLICT (period, country_code) DO UPDATE SET
            price_trend_score = EXCLUDED.price_trend_score,
            inflation_score   = EXCLUDED.inflation_score,
            risk_score        = EXCLUDED.risk_score
    """, rows)
    return len(rows)


def main():
    print(f"Connexion : {DATABASE_URL[:40]}...")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            n1 = seed_food_prices(cur)
            n2 = seed_inflation(cur)
            n3 = seed_risk_scores(cur)
        conn.commit()
        print(f"Seed termine : {n1} prix  |  {n2} inflation  |  {n3} risk scores")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
