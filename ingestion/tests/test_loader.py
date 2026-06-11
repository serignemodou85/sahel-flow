from datetime import datetime, timezone

from ingestion.loaders.timescaledb import TimescaleLoader
from shared.config import get_settings


# ── Fixtures : données de test ────────────────────────────────────────────────

import pytest


@pytest.fixture
def wb_records() -> list[dict]:
    """Deux enregistrements World Bank — SEN et CIV, même indicateur, même année."""
    t = datetime(2023, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "time":           t,
            "country_code":   "SEN",
            "indicator_code": "FP.CPI.TOTL.ZG",
            "indicator_name": "Inflation, consumer prices (annual %)",
            "value":          5.9,
        },
        {
            "time":           t,
            "country_code":   "CIV",
            "indicator_code": "FP.CPI.TOTL.ZG",
            "indicator_name": "Inflation, consumer prices (annual %)",
            "value":          4.2,
        },
    ]


@pytest.fixture
def wfp_record_null_price() -> list[dict]:
    """Un enregistrement WFP avec price_local=None — rupture de collecte."""
    return [
        {
            "time":         datetime(2024, 3, 1, tzinfo=timezone.utc),
            "country_code": "SEN",
            "market_name":  "Dakar",
            "commodity":    "Millet",
            "unit":         "KG",
            "currency":     "XOF",
            "price_local":  None,   # rupture collecte → NULL en DB
            "price_usd":    None,
        }
    ]


# ── Helper : loader pointant vers test_raw ────────────────────────────────────

def _loader() -> TimescaleLoader:
    return TimescaleLoader(settings=get_settings(), schema="test_raw")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_load_worldbank_returns_count(clean_tables, wb_records):
    """2 enregistrements soumis → retourne 2 (tous insérés, aucun conflit)."""
    with _loader() as loader:
        inserted = loader.load_worldbank_indicators(wb_records)

    assert inserted == 2


def test_load_worldbank_idempotent(clean_tables, wb_records):
    """Même batch inséré deux fois → 2ème appel retourne 0 (tout skippé par DO NOTHING).

    C'est la propriété fondamentale du loader : rejouer une ingestion mensuelle
    ne crée aucun doublon et ne modifie pas les données existantes.
    """
    with _loader() as loader:
        first  = loader.load_worldbank_indicators(wb_records)
        second = loader.load_worldbank_indicators(wb_records)

    assert first  == 2   # première insertion : tout passe
    assert second == 0   # deuxième insertion : tout skippé par ON CONFLICT DO NOTHING


def test_load_empty_list():
    """Liste vide → retourne 0 sans SQL exécuté."""
    with _loader() as loader:
        inserted = loader.load_worldbank_indicators([])

    assert inserted == 0


def test_load_wfp_null_price_accepted(clean_tables, wfp_record_null_price):
    """price_local=None est inséré sans erreur — la colonne est nullable.

    La rupture de collecte (absence de prix) est une information utile à conserver.
    Ce test vérifie que le loader ne rejette pas les enregistrements avec prix null.
    """
    with _loader() as loader:
        inserted = loader.load_wfp_food_prices(wfp_record_null_price)

    assert inserted == 1
