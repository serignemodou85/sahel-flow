from __future__ import annotations

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from shared.config import get_settings
from shared.constants import UEMOA_COUNTRIES, WB_INDICATORS
from shared.logging import get_logger
from shared.utils import year_start


def _is_retriable(exc: BaseException) -> bool:
    # Retry uniquement sur : erreurs serveur (5xx) et problèmes réseau/timeout.
    # JAMAIS sur les 4xx : une erreur client (mauvais paramètre, 404) ne se corrige
    # pas en retentant — ça ne ferait que répéter la même erreur.
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


class WorldBankSource:
    """Extrait les indicateurs macro depuis l'API World Bank v2.

    Usage :
        with WorldBankSource() as source:
            records = source.fetch_all(start_year=2000, end_year=2024)
    """

    def __init__(
        self,
        settings=None,
        transport: httpx.BaseTransport | None = None,
        retry_wait=None,
    ) -> None:
        # transport et retry_wait sont None en production.
        # En tests : on injecte MockTransport + wait_none() pour ne pas toucher le réseau
        # et ne pas attendre entre les tentatives.
        self._settings = settings or get_settings()
        self._logger = get_logger(__name__)
        self._transport = transport
        self._retry_wait = retry_wait or wait_exponential(multiplier=1, min=2, max=30)
        self._client: httpx.Client | None = None

    def __enter__(self) -> WorldBankSource:
        self._client = httpx.Client(
            base_url=self._settings.wb_api_base_url,
            timeout=30.0,
            # params communs à tous les appels : format JSON, max de résultats par page
            params={"format": "json", "per_page": 1000},
            transport=self._transport,   # None = transport réel
        )
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()

    # ── API publique ──────────────────────────────────────────────────────────

    def fetch_all(self, start_year: int, end_year: int) -> list[dict]:
        """Point d'entrée principal : tous les indicateurs, les deux pays."""
        results: list[dict] = []
        for indicator_code in WB_INDICATORS:
            records = self.fetch_indicator(indicator_code, start_year, end_year)
            results.extend(records)
            self._logger.info(
                "Indicator fetched",
                extra={"indicator": indicator_code, "count": len(records)},
            )
        return results

    def fetch_indicator(
        self,
        indicator_code: str,
        start_year: int,
        end_year: int,
    ) -> list[dict]:
        """Fetches one indicator for all UEMOA countries, all pages.

        Garantit que la liste retournée ne contient aucun None :
        le loader (étape 6) ne gère pas les enregistrements malformés.
        """
        # "SEN;CIV" — l'API WB accepte plusieurs pays séparés par ";"
        # → un seul appel HTTP pour les deux pays
        country_param = ";".join(UEMOA_COUNTRIES.keys())
        url = f"/country/{country_param}/indicator/{indicator_code}"
        params = {"date": f"{start_year}:{end_year}"}

        raw_records = self._get_all_pages(url, params)

        parsed = [self._parse_record(r) for r in raw_records]

        # Filtre explicite ici — _parse_record retourne None pour les enregistrements
        # malformés (date manquante, country_code absent). Les enregistrements avec
        # value=None (données manquantes chez WB) sont GARDÉS : la colonne est nullable.
        return [r for r in parsed if r is not None]

    # ── Méthodes internes ─────────────────────────────────────────────────────

    def _get_all_pages(self, url: str, params: dict) -> list[dict]:
        """Agrège toutes les pages de résultats pour un endpoint donné."""
        page = 1
        all_records: list[dict] = []

        while True:
            data = self._fetch_page(url, {**params, "page": page})
            # La réponse WB est toujours [metadata, [records]]
            metadata, records = data[0], data[1]
            all_records.extend(records)

            if page >= metadata["pages"]:
                break
            page += 1

        return all_records

    def _fetch_page(self, url: str, params: dict) -> list:
        """Un seul appel HTTP avec retry.

        Utilise le context manager Retrying de tenacity plutôt qu'un décorateur,
        ce qui permet d'injecter _retry_wait depuis le constructeur (testabilité).
        """
        for attempt in Retrying(
            retry=retry_if_exception(_is_retriable),
            stop=stop_after_attempt(3),
            wait=self._retry_wait,
            reraise=True,   # si les 3 tentatives échouent, propage l'exception
        ):
            with attempt:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response.json()

    def _parse_record(self, raw: dict) -> dict | None:
        """Transforme un enregistrement brut WB en dict prêt pour la DB.

        Retourne None uniquement si l'enregistrement est malformé (date ou
        country_code absents). Les enregistrements avec value=None sont valides :
        WB a des lacunes, on les stocke comme NULL dans la colonne nullable.
        """
        date_str = raw.get("date")
        country_code = raw.get("countryiso3code")

        if not date_str or not country_code:
            self._logger.warning(
                "Skipping malformed WB record",
                extra={"reason": "missing date or country_code", "raw": str(raw)},
            )
            return None

        try:
            year = int(date_str)
        except ValueError:
            self._logger.warning(
                "Unparseable year in WB record",
                extra={"date": date_str},
            )
            return None

        indicator = raw.get("indicator", {})

        return {
            "time":           year_start(year),        # 2023-01-01 00:00:00+UTC
            "country_code":   country_code,
            "indicator_code": indicator.get("id", ""),
            "indicator_name": indicator.get("value", ""),
            "value":          raw.get("value"),        # None = NULL en DB, valide
        }
