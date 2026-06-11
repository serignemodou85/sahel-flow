from __future__ import annotations

from datetime import date, datetime

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from shared.config import get_settings
from shared.constants import UEMOA_COUNTRIES, UEMOA_ISO2_CODES
from shared.logging import get_logger
from shared.utils import month_start


def _is_retriable(exc: BaseException) -> bool:
    # Même règle que WorldBankSource : retry sur 5xx + réseau, jamais sur 4xx.
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


class WfpVamSource:
    """Extrait les prix alimentaires depuis l'API WFP Data Bridges v2.

    Usage :
        with WfpVamSource() as source:
            records = source.fetch_all(
                start_date=date(2020, 1, 1),
                end_date=date(2024, 12, 31),
            )

    Différences vs WorldBankSource :
    - Authentification Bearer token obligatoire (fail fast dans __enter__)
    - Codes pays ISO2 requis par l'API (mapping via UEMOA_ISO2_CODES)
    - API moins stable : _parse_record est plus défensif
    - Dates en paramètre : datetime.date (mensuel) au lieu de int (annuel)
    """

    def __init__(
        self,
        settings=None,
        transport: httpx.BaseTransport | None = None,
        retry_wait=None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = get_logger(__name__)
        self._transport = transport
        self._retry_wait = retry_wait or wait_exponential(multiplier=1, min=2, max=30)
        self._client: httpx.Client | None = None

    def __enter__(self) -> WfpVamSource:
        # Fail fast : un token vide donne un 401 opaque difficile à diagnostiquer.
        # Un ValueError ici avec un message clair économise du temps de debug.
        # En tests, on injecte toujours un token non vide (ou on teste ce raise directement).
        if not self._settings.wfp_api_key:
            raise ValueError(
                "WFP_API_KEY est vide — inscription gratuite : https://api.wfpvam.org"
            )
        self._client = httpx.Client(
            base_url=self._settings.wfp_api_base_url,
            headers={"Authorization": f"Bearer {self._settings.wfp_api_key}"},
            timeout=30.0,
            transport=self._transport,
        )
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()

    # ── API publique ──────────────────────────────────────────────────────────

    def fetch_all(self, start_date: date, end_date: date) -> list[dict]:
        """Tous les pays UEMOA pour la plage de dates donnée."""
        results: list[dict] = []
        for country_code in UEMOA_COUNTRIES:
            records = self.fetch_country(country_code, start_date, end_date)
            results.extend(records)
            self._logger.info(
                "WFP country fetched",
                extra={"country": country_code, "count": len(records)},
            )
        return results

    def fetch_country(
        self,
        country_code: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Tous les prix pour un pays, toutes les pages.

        Filtre les None avant de retourner : le loader ne gère pas les
        enregistrements malformés (champs NOT NULL absents, date invalide).
        """
        iso2 = UEMOA_ISO2_CODES[country_code]
        params = {
            "CountryCode": iso2,
            "startDate":   start_date.isoformat(),   # "YYYY-MM-DD"
            "endDate":     end_date.isoformat(),
        }
        raw_records = self._get_all_pages("/MarketPrices/PriceMonthly", params)

        parsed = [self._parse_record(r, country_code) for r in raw_records]

        # country_code est passé au parser : on le connaît du contexte d'appel,
        # pas besoin de le lire dans l'enregistrement (champ absent ou incohérent possible).
        return [r for r in parsed if r is not None]

    # ── Méthodes internes ─────────────────────────────────────────────────────

    def _get_all_pages(self, url: str, params: dict) -> list[dict]:
        """Agrège toutes les pages de l'API WFP.

        Structure de pagination WFP (différente de WB) :
        { "records": [...], "current_page": 1, "total_count": 150, "requests_per_page": 50 }
        """
        all_records: list[dict] = []
        page = 1

        while True:
            data = self._fetch_page(url, {**params, "page": page})
            records = data.get("records", [])
            all_records.extend(records)

            # Arrêt : page vide OU tout est récupéré
            total = data.get("total_count", 0)
            if not records or len(all_records) >= total:
                break
            page += 1

        return all_records

    def _fetch_page(self, url: str, params: dict) -> dict:
        """Un seul appel HTTP avec retry — même pattern que WorldBankSource."""
        for attempt in Retrying(
            retry=retry_if_exception(_is_retriable),
            stop=stop_after_attempt(3),
            wait=self._retry_wait,
            reraise=True,
        ):
            with attempt:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response.json()

    def _parse_record(self, raw: dict, country_code: str) -> dict | None:
        """Transforme un enregistrement WFP brut en dict prêt pour la DB.

        Plus défensif que _parse_record de WorldBankSource : l'API WFP peut
        retourner des enregistrements avec des champs manquants sans avertissement.

        Retourne None si un champ NOT NULL de ht_wfp_food_prices est absent.
        price_local et price_usd sont nullable — conservés à None si manquants
        (rupture de collecte sur un marché = donnée utile à conserver).
        """
        # Champs obligatoires = colonnes NOT NULL dans ht_wfp_food_prices
        required_fields = ("cmName", "mktName", "umName", "currName", "date")
        if any(not raw.get(f) for f in required_fields):
            self._logger.warning(
                "WFP record ignoré — champ obligatoire absent",
                extra={"fields_present": sorted(raw.keys())},
            )
            return None

        try:
            # WFP retourne une date de collecte "YYYY-MM-DD" ou "YYYY-MM-DDTHH:MM:SS".
            # On tronque à 10 caractères pour ignorer la partie temps, puis on
            # normalise au 1er du mois — cohérence avec la granularité mensuelle.
            dt = datetime.strptime(raw["date"][:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            self._logger.warning(
                "WFP record ignoré — date non parseable",
                extra={"date_value": raw.get("date")},
            )
            return None

        return {
            "time":         month_start(dt),    # 1er du mois, UTC
            "country_code": country_code,        # injecté du contexte, pas lu dans raw
            "market_name":  raw["mktName"],
            "commodity":    raw["cmName"],
            "unit":         raw["umName"],
            "currency":     raw["currName"],
            "price_local":  raw.get("price"),    # None = rupture collecte, colonne nullable
            "price_usd":    raw.get("usdprice"),
        }
