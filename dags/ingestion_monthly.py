from __future__ import annotations

from datetime import date, datetime, timedelta

import psycopg2
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.operators.python import get_current_context
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from ingestion.loaders.timescaledb import TimescaleLoader
from ingestion.sources.world_bank import WorldBankSource
from ingestion.sources.wfp_vam import WfpVamSource
from shared.config import get_settings
from shared.constants import UEMOA_COUNTRIES
from shared.logging import get_logger

_logger = get_logger(__name__)

_DEFAULT_ARGS = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _row_count(table: str, since: datetime) -> int:
    """Compte les lignes dans une table raw depuis une date donnée.

    Ouvre et ferme sa propre connexion — appelée uniquement depuis les
    tâches quality_check qui s'exécutent en sous-processus séparés.
    table est toujours un littéral interne (jamais une entrée utilisateur).
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE time >= %s", (since,))
            return cur.fetchone()[0]
    finally:
        conn.close()


@dag(
    dag_id="ingestion_monthly",
    schedule="@monthly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=_DEFAULT_ARGS,
    tags=["ingestion", "monthly"],
)
def ingestion_monthly() -> None:
    """Ingestion mensuelle : WorldBank + WFP → raw.TimescaleDB.

    Deux chaînes parallèles indépendantes convergent sur trigger_transform_dbt :
        extract_worldbank → load_worldbank → quality_check_worldbank ──┐
        extract_wfp       → load_wfp       → quality_check_wfp       ──┴── trigger_transform_dbt

    Fenêtre glissante 2 ans : fetch year-1 à year courant à chaque run.
    DO NOTHING garantit 0 doublon en cas de réingestion.
    """

    # ── Chaîne WorldBank ──────────────────────────────────────────────────────

    @task
    def extract_worldbank() -> list[dict]:
        logical_date = get_current_context()["logical_date"]
        start_year = logical_date.year - 1
        end_year = logical_date.year
        with WorldBankSource(settings=get_settings()) as src:
            records = src.fetch_all(start_year, end_year)
        _logger.info(
            "WorldBank extrait",
            extra={"count": len(records), "start_year": start_year, "end_year": end_year},
        )
        return records

    @task
    def load_worldbank(records: list[dict]) -> int:
        with TimescaleLoader(settings=get_settings()) as loader:
            return loader.load_worldbank_indicators(records)

    @task
    def quality_check_worldbank(inserted: int) -> None:
        logical_date = get_current_context()["logical_date"]
        since = datetime(logical_date.year - 1, 1, 1)
        count = _row_count("raw.ht_worldbank_indicators", since)
        if count == 0:
            raise AirflowException(
                f"WorldBank : aucune donnée en base depuis {since.year}"
            )
        _logger.info(
            "Quality check WorldBank OK",
            extra={"this_run_inserted": inserted, "total_rows": count},
        )

    # ── Chaîne WFP ────────────────────────────────────────────────────────────

    @task
    def extract_wfp() -> list[dict]:
        logical_date = get_current_context()["logical_date"]
        start_date = date(logical_date.year - 1, 1, 1)
        end_date = date(logical_date.year, logical_date.month, 1)
        records: list[dict] = []
        with WfpVamSource(settings=get_settings()) as src:
            for country_code in UEMOA_COUNTRIES:
                records.extend(src.fetch_country(country_code, start_date, end_date))
        _logger.info(
            "WFP extrait",
            extra={"count": len(records), "start": str(start_date), "end": str(end_date)},
        )
        return records

    @task
    def load_wfp(records: list[dict]) -> int:
        with TimescaleLoader(settings=get_settings()) as loader:
            return loader.load_wfp_food_prices(records)

    @task
    def quality_check_wfp(inserted: int) -> None:
        logical_date = get_current_context()["logical_date"]
        since = datetime(logical_date.year - 1, 1, 1)
        count = _row_count("raw.ht_wfp_food_prices", since)
        if count == 0:
            raise AirflowException(
                f"WFP : aucune donnée en base depuis {since.year}"
            )
        _logger.info(
            "Quality check WFP OK",
            extra={"this_run_inserted": inserted, "total_rows": count},
        )

    # ── Wiring ────────────────────────────────────────────────────────────────
    wb_records  = extract_worldbank()
    wb_inserted = load_worldbank(wb_records)
    wb_qc       = quality_check_worldbank(wb_inserted)

    wfp_records  = extract_wfp()
    wfp_inserted = load_wfp(wfp_records)
    wfp_qc       = quality_check_wfp(wfp_inserted)

    # Les deux quality checks doivent réussir avant de lancer les transformations.
    # wait_for_completion=False : ingestion_monthly se termine dès le trigger envoyé.
    trigger = TriggerDagRunOperator(
        task_id="trigger_transform_dbt",
        trigger_dag_id="transform_dbt",
        wait_for_completion=False,
    )
    [wb_qc, wfp_qc] >> trigger


# Instanciation du DAG — requis pour qu'Airflow découvre le DAG au parse du fichier.
ingestion_monthly()
