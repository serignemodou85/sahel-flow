from __future__ import annotations

import psycopg2
import psycopg2.extensions
from psycopg2.extras import execute_values

from shared.config import get_settings
from shared.logging import get_logger


class TimescaleLoader:
    """Charge des enregistrements dans les tables raw de TimescaleDB.

    Usage :
        with TimescaleLoader() as loader:
            nb_wb  = loader.load_worldbank_indicators(wb_records)
            nb_wfp = loader.load_wfp_food_prices(wfp_records)

    Le paramètre schema vaut "raw" en production et "test_raw" dans les tests
    d'intégration — il permet d'isoler les insertions de test sans toucher
    aux vraies données.
    Note : schema est injecté depuis le code, jamais depuis une entrée utilisateur.
    """

    def __init__(self, settings=None, schema: str = "raw") -> None:
        self._settings = settings or get_settings()
        self._schema = schema
        self._logger = get_logger(__name__)
        self.conn: psycopg2.extensions.connection | None = None

    def __enter__(self) -> TimescaleLoader:
        # psycopg2 ouvre une transaction implicitement (autocommit=False par défaut).
        # __enter__ n'a pas besoin de faire autre chose que créer la connexion.
        self.conn = psycopg2.connect(
            host=self._settings.postgres_host,
            port=self._settings.postgres_port,
            dbname=self._settings.postgres_db,
            user=self._settings.postgres_user,
            password=self._settings.postgres_password,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self.conn.commit()   # tout s'est bien passé → persiste
        else:
            self.conn.rollback() # erreur → annule la transaction entière
        self.conn.close()
        return False  # ne pas supprimer l'exception — la propager au caller

    # ── API publique ──────────────────────────────────────────────────────────

    def load_worldbank_indicators(self, records: list[dict]) -> int:
        """Insère des indicateurs World Bank dans raw.ht_worldbank_indicators.

        Retourne le nombre de lignes réellement insérées (0 si toutes déjà présentes).
        """
        if not records:
            self._logger.info("load_worldbank_indicators appelé avec liste vide — skip")
            return 0

        sql = f"""
            INSERT INTO {self._schema}.ht_worldbank_indicators
                (time, country_code, indicator_code, indicator_name, value)
            VALUES %s
            ON CONFLICT (time, country_code, indicator_code) DO NOTHING
            RETURNING time
        """
        rows = [
            (
                r["time"],
                r["country_code"],
                r["indicator_code"],
                r["indicator_name"],
                r["value"],          # None → NULL en DB (colonne nullable)
            )
            for r in records
        ]
        inserted = self._insert_batch(sql, rows)
        self._logger.info(
            "Worldbank indicators chargés",
            extra={"submitted": len(records), "inserted": inserted, "skipped": len(records) - inserted},
        )
        return inserted

    def load_wfp_food_prices(self, records: list[dict]) -> int:
        """Insère des prix alimentaires WFP dans raw.ht_wfp_food_prices.

        Retourne le nombre de lignes réellement insérées.
        """
        if not records:
            self._logger.info("load_wfp_food_prices appelé avec liste vide — skip")
            return 0

        sql = f"""
            INSERT INTO {self._schema}.ht_wfp_food_prices
                (time, country_code, market_name, commodity, unit, currency, price_local, price_usd)
            VALUES %s
            ON CONFLICT (time, country_code, market_name, commodity) DO NOTHING
            RETURNING time
        """
        rows = [
            (
                r["time"],
                r["country_code"],
                r["market_name"],
                r["commodity"],
                r["unit"],
                r["currency"],
                r["price_local"],   # None → NULL (rupture de collecte)
                r["price_usd"],
            )
            for r in records
        ]
        inserted = self._insert_batch(sql, rows)
        self._logger.info(
            "WFP food prices chargés",
            extra={"submitted": len(records), "inserted": inserted, "skipped": len(records) - inserted},
        )
        return inserted

    # ── Méthode interne ───────────────────────────────────────────────────────

    def _insert_batch(self, sql: str, rows: list[tuple]) -> int:
        """Batch insert avec execute_values. Retourne le nombre de lignes insérées.

        fetch=True : execute_values agrège les résultats RETURNING de toutes les
        pages internes — fiable même si le volume dépasse page_size.
        Avec DO NOTHING, seules les lignes réellement insérées sont retournées.
        """
        with self.conn.cursor() as cur:
            returned = execute_values(
                cur,
                sql,
                rows,
                page_size=10_000,
                fetch=True,   # retourne les lignes RETURNING de toutes les pages
            )
            return len(returned)
