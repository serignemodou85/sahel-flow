import psycopg2.extensions
from psycopg2.extras import RealDictCursor

from app.schemas.inflation import InflationRecord

_SQL = """
    SELECT period, country_code, indicator_code, indicator_name,
           indicator_value, yoy_change_pct
    FROM marts.mart__macro__indicators_annual
    WHERE country_code = %(country)s
      AND (%(start_year)s IS NULL OR EXTRACT(YEAR FROM period) >= %(start_year)s)
      AND (%(end_year)s IS NULL OR EXTRACT(YEAR FROM period) <= %(end_year)s)
    ORDER BY period DESC, indicator_code
"""


def get_inflation(
    conn: psycopg2.extensions.connection,
    country: str,
    start_year: int | None,
    end_year: int | None,
) -> list[InflationRecord]:
    """Retourne les indicateurs macro depuis mart__macro__indicators_annual.

    prev_year_value et ingested_at ne sont pas exposés — colonnes internes du mart.
    yoy_change_pct est NULL pour la première année de chaque indicateur (pas de LAG).
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(_SQL, {"country": country, "start_year": start_year, "end_year": end_year})
        rows = cur.fetchall()
    return [InflationRecord(**row) for row in rows]
