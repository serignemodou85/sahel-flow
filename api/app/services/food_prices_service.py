from datetime import date

import psycopg2.extensions
from psycopg2.extras import RealDictCursor

from app.schemas.food_prices import FoodPriceRecord

_SQL = """
    SELECT period, country_code, commodity, unit, currency,
           avg_price_local, avg_price_usd, market_count, null_price_count
    FROM marts.mart__food__prices_monthly
    WHERE country_code = %(country)s
      AND (%(start_date)s IS NULL OR period >= %(start_date)s)
      AND (%(end_date)s IS NULL OR period <= %(end_date)s)
    ORDER BY period DESC, commodity
"""


def get_food_prices(
    conn: psycopg2.extensions.connection,
    country: str,
    start_date: date | None,
    end_date: date | None,
) -> list[FoodPriceRecord]:
    """Retourne les prix alimentaires agrégés depuis mart__food__prices_monthly.

    Filtres optionnels : IS NULL OR évite la construction de SQL dynamique.
    Une seule requête paramétrée couvre tous les cas (avec ou sans dates).
    RealDictCursor : rows arrivent comme dicts → FoodPriceRecord(**row) sans mapping manuel.
    Pydantic convertit Decimal → float et datetime → date automatiquement.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(_SQL, {"country": country, "start_date": start_date, "end_date": end_date})
        rows = cur.fetchall()
    return [FoodPriceRecord(**row) for row in rows]
