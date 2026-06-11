from datetime import date, datetime, timezone

import httpx
import pytest
from tenacity import wait_none

from ingestion.sources.wfp_vam import WfpVamSource
from shared.config import Settings


def _make_transport(responses: list) -> httpx.MockTransport:
    """Même helper que dans test_world_bank.py : distribue les réponses dans l'ordre."""
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return next(iterator)

    return httpx.MockTransport(handler)


def _settings(**overrides) -> Settings:
    """Settings minimaux pour les tests WFP — token non vide par défaut."""
    base = dict(
        wfp_api_base_url="http://mock-wfp",
        wfp_api_key="test-token-valid",
        postgres_password="test",
    )
    base.update(overrides)
    return Settings(**base)


# ── Test 1 : cas nominal ──────────────────────────────────────────────────────
def test_parse_nominal(wfp_single_page_response):
    """Réponse WFP valide → dicts corrects, time normalisé au 1er du mois UTC."""
    transport = _make_transport([httpx.Response(200, json=wfp_single_page_response)])

    with WfpVamSource(settings=_settings(), transport=transport, retry_wait=wait_none()) as src:
        records = src.fetch_country("SEN", date(2024, 3, 1), date(2024, 3, 31))

    assert len(records) == 2

    dakar = next(r for r in records if r["market_name"] == "Dakar")
    assert dakar["commodity"]    == "Millet"
    assert dakar["price_local"]  == 350.0
    assert dakar["country_code"] == "SEN"
    # Peu importe que l'API retourne le 15 ou le 20 — on normalise au 1er du mois
    assert dakar["time"] == datetime(2024, 3, 1, tzinfo=timezone.utc)


# ── Test 2 : champ obligatoire absent → enregistrement filtré ─────────────────
def test_parse_missing_required_field(wfp_missing_required_field_response):
    """cmName absent → _parse_record retourne None → liste vide après filtre.

    Le loader ne reçoit jamais de None : la responsabilité du filtre est
    dans fetch_country, pas dans le loader (étape 6).
    """
    transport = _make_transport([
        httpx.Response(200, json=wfp_missing_required_field_response)
    ])

    with WfpVamSource(settings=_settings(), transport=transport, retry_wait=wait_none()) as src:
        records = src.fetch_country("SEN", date(2024, 3, 1), date(2024, 3, 31))

    assert records == []


# ── Test 3 : price=null → enregistrement conservé ────────────────────────────
def test_parse_null_price(wfp_null_price_response):
    """price=null (rupture de collecte) → enregistrement GARDÉ avec price_local=None.

    Différence clé avec le champ obligatoire :
    - cmName=None     → filtré  (on ne peut pas stocker sans nom de commodité)
    - price=None      → conservé (la colonne est nullable, l'absence de prix est une info)
    """
    transport = _make_transport([httpx.Response(200, json=wfp_null_price_response)])

    with WfpVamSource(settings=_settings(), transport=transport, retry_wait=wait_none()) as src:
        records = src.fetch_country("SEN", date(2024, 3, 1), date(2024, 3, 31))

    assert len(records) == 1
    assert records[0]["price_local"] is None
    assert records[0]["price_usd"]   is None


# ── Test 4 : token vide → ValueError dans __enter__, pas dans __init__ ────────
def test_fail_fast_empty_token():
    """WFP_API_KEY vide → ValueError levé dans __enter__, pas à l'instanciation.

    Vérification explicite que c'est bien le context manager qui fail,
    et non le constructeur — sinon le test passe en vert pour la mauvaise raison.
    """
    settings = _settings(wfp_api_key="")

    # __init__ ne lève rien — l'objet est créé sans problème
    source = WfpVamSource(settings=settings)

    # C'est __enter__ (le "with") qui doit lever ValueError
    with pytest.raises(ValueError, match="WFP_API_KEY"):
        with source:
            pass  # ne doit jamais être atteint


# ── Test 5 : pagination deux pages ───────────────────────────────────────────
def test_pagination_two_pages(wfp_two_pages_response):
    """2 pages → toutes les lignes agrégées, 2 appels HTTP effectués."""
    page1, page2 = wfp_two_pages_response
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=page1 if call_count == 1 else page2)

    transport = httpx.MockTransport(handler)

    with WfpVamSource(settings=_settings(), transport=transport, retry_wait=wait_none()) as src:
        records = src.fetch_country("CIV", date(2024, 1, 1), date(2024, 2, 28))

    assert len(records) == 2
    assert call_count == 2
