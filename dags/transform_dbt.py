from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.operators.bash import BashOperator

# Chemin absolu dans le container — dbt/ est monté sur /opt/airflow/dbt.
# --profiles-dir et --project-dir doivent toujours être précisés explicitement :
# sans ça, dbt cherche ~/.dbt/ qui n'existe pas dans le container Airflow.
_DBT_DIR = "/opt/airflow/dbt"
_DBT_CMD = f"dbt --no-use-colors --profiles-dir {_DBT_DIR} --project-dir {_DBT_DIR}"

_DEFAULT_ARGS = {
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="transform_dbt",
    schedule=None,  # déclenché par ingestion_monthly via TriggerDagRunOperator
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=_DEFAULT_ARGS,
    tags=["transform", "dbt"],
)
def transform_dbt() -> None:
    """Pipeline dbt complet : raw → core → snapshot → marts → monitoring → tests.

    schedule=None : ce DAG n'a pas de schedule propre.
    Il est toujours déclenché par ingestion_monthly après les quality checks.

    Ordre impératif :
        dbt run (raw + core)         — crée les vues sur les données fraîches
        dbt snapshot                 — capture l'état core (hors graphe dbt run)
        dbt run (marts + monitoring) — tables finales + vues observabilité
        dbt test (marts)             — assertions qualité
    """

    run_raw_core = BashOperator(
        task_id="dbt_run_raw_core",
        bash_command=f"{_DBT_CMD} run --select raw core",
    )

    snapshot = BashOperator(
        task_id="dbt_snapshot",
        # dbt snapshot est hors du graphe dbt run — commande séparée obligatoire.
        # Si absente, aucune erreur n'est levée : le snapshot ne tourne jamais silencieusement.
        bash_command=f"{_DBT_CMD} snapshot",
    )

    run_marts_monitoring = BashOperator(
        task_id="dbt_run_marts_monitoring",
        bash_command=f"{_DBT_CMD} run --select marts monitoring",
    )

    test_marts = BashOperator(
        task_id="dbt_test_marts",
        # Tests uniquement sur les marts (pas sur les monitoring models).
        # Les tests singuliers (dbt/tests/) sont inclus automatiquement.
        bash_command=f"{_DBT_CMD} test --select marts",
    )

    run_raw_core >> snapshot >> run_marts_monitoring >> test_marts


transform_dbt()
