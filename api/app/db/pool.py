from psycopg2 import pool as pg_pool

from shared.config import get_settings

_pool: pg_pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    """Ouvre le pool au démarrage de l'app (appelé depuis lifespan dans main.py).

    Échoue immédiatement si TimescaleDB est indisponible — l'app ne démarre pas
    silencieusement avec une DB inaccessible. Plus détectable qu'une lazy init
    qui échouerait à la première requête.
    """
    global _pool
    s = get_settings()
    _pool = pg_pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        host=s.postgres_host,
        port=s.postgres_port,
        dbname=s.postgres_db,
        user=s.postgres_user,
        password=s.postgres_password,
    )


def close_pool() -> None:
    """Ferme toutes les connexions à l'arrêt de l'app (appelé depuis lifespan)."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def get_pool() -> pg_pool.ThreadedConnectionPool:
    """Retourne le pool initialisé. Lève RuntimeError si init_pool() n'a pas été appelé."""
    if _pool is None:
        raise RuntimeError("Pool non initialisé — init_pool() doit être appelé au démarrage")
    return _pool
