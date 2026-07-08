"""
Synchronise les marts locaux (TimescaleDB) vers Supabase.
Idempotent : ON CONFLICT DO UPDATE sur chaque table.

Usage :
    set DATABASE_URL_OVERRIDE=postgresql://postgres.xxx:pass@pooler.supabase.com:5432/postgres?sslmode=require
    python infra/supabase/sync_to_supabase.py
"""

import os
import psycopg2
from psycopg2.extras import execute_values

_SUPABASE = os.environ.get("DATABASE_URL_OVERRIDE")
if not _SUPABASE:
    raise ValueError("DATABASE_URL_OVERRIDE non défini")

_LOCAL = {
    "host":     os.environ.get("POSTGRES_HOST",     "localhost"),
    "port":     int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname":   os.environ.get("POSTGRES_DB",       "sahel_flow"),
    "user":     os.environ.get("POSTGRES_USER",     "sahel"),
    "password": os.environ.get("POSTGRES_PASSWORD", "sahel_secret"),
}


def _sync_food_prices(src, dst) -> int:
    with src.cursor() as cur:
        cur.execute("""
            SELECT period, country_code, commodity, unit, currency,
                   avg_price_local, avg_price_usd, market_count, null_price_count
            FROM marts.mart__food__prices_monthly
        """)
        rows = cur.fetchall()
    if not rows:
        print("  food_prices       : 0 ligne locale — skip")
        return 0
    with dst.cursor() as cur:
        execute_values(cur, """
            INSERT INTO marts.mart__food__prices_monthly
                (period, country_code, commodity, unit, currency,
                 avg_price_local, avg_price_usd, market_count, null_price_count)
            VALUES %s
            ON CONFLICT (period, country_code, commodity) DO UPDATE SET
                unit             = EXCLUDED.unit,
                currency         = EXCLUDED.currency,
                avg_price_local  = EXCLUDED.avg_price_local,
                avg_price_usd    = EXCLUDED.avg_price_usd,
                market_count     = EXCLUDED.market_count,
                null_price_count = EXCLUDED.null_price_count
        """, rows)
    dst.commit()
    print(f"  food_prices       : {len(rows)} lignes synchronisées")
    return len(rows)


def _sync_macro_indicators(src, dst) -> int:
    with src.cursor() as cur:
        cur.execute("""
            SELECT period, country_code, indicator_code, indicator_name,
                   indicator_value, yoy_change_pct
            FROM marts.mart__macro__indicators_annual
        """)
        rows = cur.fetchall()
    if not rows:
        print("  macro_indicators  : 0 ligne locale — skip")
        return 0
    with dst.cursor() as cur:
        execute_values(cur, """
            INSERT INTO marts.mart__macro__indicators_annual
                (period, country_code, indicator_code, indicator_name,
                 indicator_value, yoy_change_pct)
            VALUES %s
            ON CONFLICT (period, country_code, indicator_code) DO UPDATE SET
                indicator_name  = EXCLUDED.indicator_name,
                indicator_value = EXCLUDED.indicator_value,
                yoy_change_pct  = EXCLUDED.yoy_change_pct
        """, rows)
    dst.commit()
    print(f"  macro_indicators  : {len(rows)} lignes synchronisées")
    return len(rows)


def _sync_risk_scores(src, dst) -> int:
    with src.cursor() as cur:
        cur.execute("""
            SELECT period, country_code, price_trend_score, inflation_score, risk_score
            FROM marts.mart__risk__score_monthly
        """)
        rows = cur.fetchall()
    if not rows:
        print("  risk_scores       : 0 ligne locale — skip")
        return 0
    with dst.cursor() as cur:
        execute_values(cur, """
            INSERT INTO marts.mart__risk__score_monthly
                (period, country_code, price_trend_score, inflation_score, risk_score)
            VALUES %s
            ON CONFLICT (period, country_code) DO UPDATE SET
                price_trend_score = EXCLUDED.price_trend_score,
                inflation_score   = EXCLUDED.inflation_score,
                risk_score        = EXCLUDED.risk_score
        """, rows)
    dst.commit()
    print(f"  risk_scores       : {len(rows)} lignes synchronisées")
    return len(rows)


if __name__ == "__main__":
    print(f"Source  : {_LOCAL['host']}:{_LOCAL['port']}/{_LOCAL['dbname']}")
    print(f"Cible   : {_SUPABASE[:60]}...")

    src = psycopg2.connect(**_LOCAL)
    dst = psycopg2.connect(dsn=_SUPABASE)

    try:
        print("\nSynchronisation :")
        n1 = _sync_food_prices(src, dst)
        n2 = _sync_macro_indicators(src, dst)
        n3 = _sync_risk_scores(src, dst)
        print(f"\nTermine : {n1} prix | {n2} indicateurs macro | {n3} risk scores")
    finally:
        src.close()
        dst.close()
