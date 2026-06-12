import psycopg2.extensions

from shared.constants import UEMOA_COUNTRIES, UEMOA_CURRENCY
from app.schemas.countries import CountryResponse

# Métadonnées statiques enrichissant les codes retournés par la DB.
# La DB dit quels pays ont des données ; les constantes donnent nom et devise.
_COUNTRY_META: dict[str, dict] = {
    code: {"name": name, "currency": UEMOA_CURRENCY}
    for code, name in UEMOA_COUNTRIES.items()
}

_SQL = """
    SELECT DISTINCT country_code
    FROM (
        SELECT country_code FROM raw.ht_worldbank_indicators
        UNION
        SELECT country_code FROM raw.ht_wfp_food_prices
    ) sources
    ORDER BY country_code
"""


def get_countries(conn: psycopg2.extensions.connection) -> list[CountryResponse]:
    """Retourne les pays ayant des données dans au moins une source.

    UNION (pas UNION ALL) : déduplique les codes présents dans les deux tables.
    JOIN avec _COUNTRY_META : enrichit chaque code avec nom et devise.
    Si un code inconnu arrive (hors UEMOA_COUNTRIES), il est ignoré silencieusement.
    """
    with conn.cursor() as cur:
        cur.execute(_SQL)
        rows = cur.fetchall()

    result = []
    for (code,) in rows:
        meta = _COUNTRY_META.get(code)
        if meta:
            result.append(CountryResponse(code=code, **meta))
    return result
