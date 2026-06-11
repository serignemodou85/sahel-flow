"""Tests bout en bout Phase 1 — source.fetch() → loader.load() → vérification DB.

Ces tests valident l'assemblage des composants : un enregistrement extrait d'une
source (mock HTTP) traverse tout le pipeline Python et arrive en DB avec les bonnes
valeurs. Ce qu'ils testent que les tests unitaires ne testent pas :
- L'interface source → loader (formats de dict compatibles)
- La transformation None → NULL à travers les deux couches
- L'idempotence DO NOTHING en conditions réelles (pas juste au niveau loader)

DB : schema test_raw (make db-only requis). HTTP : MockTransport.
"""
from __future__ import annotations

from datetime import date

import httpx
import pytest
from tenacity import wait_none

from ingestion.loaders.timescaledb import TimescaleLoader
from ingestion.sources.world_bank import WorldBankSource
from ingestion.sources.wfp_vam import WfpVamSource
from shared.config import Settings, get_settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock(response_data) -> httpx.MockTransport:
    """Transport qui retourne toujours la même réponse JSON 200."""
    return httpx.MockTransport(lambda req: httpx.Response(200, json=response_data))


def _wfp_settings() -> Settings:
    """Settings avec token WFP non vide — les autres valeurs viennent de .env."""
    return Settings(wfp_api_key="e2e-test-token")


def _loader() -> TimescaleLoader:
    return TimescaleLoader(settings=get_settings(), schema="test_raw")


# ── Test 1 — WorldBank : pipeline nominal ─────────────────────────────────────

def test_e2e_worldbank_pipeline(clean_tables, db_conn, wb_single_page_response):
    """fetch_indicator() → load_worldbank_indicators() → valeurs exactes en DB.

    Vérifie que les 3 étapes s'assemblent correctement : parse, binding psycopg2,
    insert. country_code et value sont vérifiés directement en DB (pas juste COUNT).
    """
    with WorldBankSource(
        settings=get_settings(),
        transport=_mock(wb_single_page_response),
        retry_wait=wait_none(),
    ) as src:
        records = src.fetch_indicator("FP.CPI.TOTL.ZG", 2023, 2023)

    assert len(records) == 2  # parse : SEN + CIV

    with _loader() as loader:
        inserted = loader.load_worldbank_indicators(records)

    assert inserted == 2  # load : 2 nouvelles lignes

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT country_code, indicator_code, value::float
            FROM test_raw.ht_worldbank_indicators
            ORDER BY country_code
        """)
        rows = cur.fetchall()

    assert rows[0] == ("CIV", "FP.CPI.TOTL.ZG", 4.2)
    assert rows[1] == ("SEN", "FP.CPI.TOTL.ZG", 5.9)


# ── Test 2 — WFP : pipeline nominal ──────────────────────────────────────────

def test_e2e_wfp_pipeline(clean_tables, db_conn, wfp_single_page_response):
    """fetch_country() → load_wfp_food_prices() → valeurs exactes en DB."""
    with WfpVamSource(
        settings=_wfp_settings(),
        transport=_mock(wfp_single_page_response),
        retry_wait=wait_none(),
    ) as src:
        records = src.fetch_country("SEN", date(2024, 3, 1), date(2024, 3, 31))

    assert len(records) == 2

    with _loader() as loader:
        inserted = loader.load_wfp_food_prices(records)

    assert inserted == 2

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT commodity, price_local::float
            FROM test_raw.ht_wfp_food_prices
            WHERE market_name = 'Dakar'
        """)
        row = cur.fetchone()

    assert row == ("Millet", 350.0)


# ── Test 3 — WorldBank : idempotence de bout en bout ─────────────────────────

def test_e2e_worldbank_idempotence(clean_tables, db_conn, wb_single_page_response):
    """Rejouer le même pipeline deux fois → 0 doublon, DB inchangée.

    Valide DO NOTHING en conditions réelles : source → loader → DB.
    Différent de test_load_worldbank_idempotent qui teste le loader seul.
    """
    with WorldBankSource(
        settings=get_settings(),
        transport=_mock(wb_single_page_response),
        retry_wait=wait_none(),
    ) as src:
        records = src.fetch_indicator("FP.CPI.TOTL.ZG", 2023, 2023)

    with _loader() as loader:
        first = loader.load_worldbank_indicators(records)

    with _loader() as loader:
        second = loader.load_worldbank_indicators(records)  # mêmes données

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_raw.ht_worldbank_indicators")
        count = cur.fetchone()[0]

    assert first  == 2  # premier run : 2 insertions
    assert second == 0  # deuxième run : tout ignoré par DO NOTHING
    assert count  == 2  # DB inchangée — aucun doublon


# ── Test 4 — WorldBank : value=None survit à tout le pipeline ─────────────────

def test_e2e_worldbank_null_value(clean_tables, db_conn, wb_null_value_response):
    """value=None dans la réponse WB → value IS NULL en DB.

    Vérifie que None n'est pas converti ou filtré à aucune des trois étapes :
    _parse_record (conserve None), psycopg2 binding (None → NULL), execute_values.
    """
    with WorldBankSource(
        settings=get_settings(),
        transport=_mock(wb_null_value_response),
        retry_wait=wait_none(),
    ) as src:
        records = src.fetch_indicator("FP.CPI.TOTL.ZG", 2015, 2015)

    assert len(records) == 1
    assert records[0]["value"] is None  # _parse_record conserve None

    with _loader() as loader:
        inserted = loader.load_worldbank_indicators(records)

    assert inserted == 1

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT value FROM test_raw.ht_worldbank_indicators
            WHERE country_code = 'SEN'
        """)
        row = cur.fetchone()

    assert row is not None
    assert row[0] is None  # NULL conservé à travers tout le pipeline


# ── Test 5 — WFP : price=None survit à tout le pipeline ──────────────────────

def test_e2e_wfp_null_price(clean_tables, db_conn, wfp_null_price_response):
    """price=None dans la réponse WFP → price_local IS NULL en DB.

    Même vérification que test 4 pour WFP — deux points de défaillance distincts
    (parsers différents, tables différentes, bindings différents).
    """
    with WfpVamSource(
        settings=_wfp_settings(),
        transport=_mock(wfp_null_price_response),
        retry_wait=wait_none(),
    ) as src:
        records = src.fetch_country("SEN", date(2024, 3, 1), date(2024, 3, 31))

    assert len(records) == 1
    assert records[0]["price_local"] is None

    with _loader() as loader:
        inserted = loader.load_wfp_food_prices(records)

    assert inserted == 1

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT price_local FROM test_raw.ht_wfp_food_prices
            WHERE market_name = 'Dakar'
        """)
        row = cur.fetchone()

    assert row is not None
    assert row[0] is None  # NULL conservé à travers tout le pipeline
