from datetime import datetime, timezone

import httpx
import pytest
from tenacity import wait_none

from ingestion.sources.world_bank import WorldBankSource


def _make_transport(responses: list) -> httpx.MockTransport:
    """Retourne un transport qui distribue les réponses dans l'ordre de la liste."""
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return next(iterator)

    return httpx.MockTransport(handler)


# ── Test 1 : cas nominal ──────────────────────────────────────────────────────
def test_parse_response_nominal(wb_single_page_response):
    """Une réponse WB valide produit des dicts corrects avec les bons types."""
    transport = _make_transport([
        httpx.Response(200, json=wb_single_page_response),
    ])

    with WorldBankSource(transport=transport, retry_wait=wait_none()) as source:
        records = source.fetch_indicator("FP.CPI.TOTL.ZG", 2023, 2023)

    assert len(records) == 2

    sen = next(r for r in records if r["country_code"] == "SEN")
    assert sen["value"] == 5.9
    assert sen["indicator_code"] == "FP.CPI.TOTL.ZG"
    # time doit être le 1er janvier de l'année, timezone UTC
    assert sen["time"] == datetime(2023, 1, 1, tzinfo=timezone.utc)

    civ = next(r for r in records if r["country_code"] == "CIV")
    assert civ["value"] == 4.2


# ── Test 2 : value=null → dict conservé, pas filtré ──────────────────────────
def test_parse_response_null_value(wb_null_value_response):
    """Un enregistrement avec value=null est GARDÉ (colonne nullable).

    _parse_record ne retourne None que pour les enregistrements malformés
    (date ou country_code absents). Une valeur manquante chez WB est une
    donnée valide à stocker — on veut savoir que la donnée n'existe pas.
    """
    transport = _make_transport([
        httpx.Response(200, json=wb_null_value_response),
    ])

    with WorldBankSource(transport=transport, retry_wait=wait_none()) as source:
        records = source.fetch_indicator("FP.CPI.TOTL.ZG", 2015, 2015)

    # L'enregistrement est présent dans la liste (non filtré)
    assert len(records) == 1
    assert records[0]["country_code"] == "SEN"
    # value=None → sera stocké comme NULL dans ht_worldbank_indicators
    assert records[0]["value"] is None


# ── Test 3 : pagination deux pages ───────────────────────────────────────────
def test_pagination_two_pages(wb_two_pages_response):
    """Toutes les pages sont agrégées : le résultat contient les lignes des deux pages."""
    page1, page2 = wb_two_pages_response
    transport = _make_transport([
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ])

    with WorldBankSource(transport=transport, retry_wait=wait_none()) as source:
        records = source.fetch_indicator("FP.CPI.TOTL.ZG", 2023, 2023)

    assert len(records) == 2
    assert {r["country_code"] for r in records} == {"SEN", "CIV"}


# ── Test 4 : retry sur 503 ────────────────────────────────────────────────────
def test_retry_on_503(wb_single_page_response):
    """Un 503 déclenche une nouvelle tentative ; le 2ème appel réussit."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # 1ère tentative : erreur serveur temporaire
            return httpx.Response(503, text="Service Unavailable")
        # 2ème tentative : succès
        return httpx.Response(200, json=wb_single_page_response)

    transport = httpx.MockTransport(handler)

    # wait_none() : pas d'attente entre tentatives → test rapide
    with WorldBankSource(transport=transport, retry_wait=wait_none()) as source:
        records = source.fetch_indicator("FP.CPI.TOTL.ZG", 2023, 2023)

    assert call_count == 2          # 1 échec + 1 succès
    assert len(records) == 2        # les données sont bien retournées
