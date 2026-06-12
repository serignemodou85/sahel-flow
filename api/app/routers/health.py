import time

import psycopg2
from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse, MetricsResponse
from shared.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Ping de l'API et de la connexion DB.

    Retourne toujours HTTP 200 — c'est l'API qui répond, pas la DB.
    Le champ "db" indique si TimescaleDB est joignable.
    Standard utilisé par les load balancers et Kubernetes.

    N'utilise pas Depends(get_conn) intentionnellement : si le pool échoue,
    Depends lèverait une exception avant la route → HTTP 500. Ce endpoint doit
    rester résilient et toujours répondre, même quand la DB est down.
    """
    db_status = "ok"
    try:
        s = get_settings()
        conn = psycopg2.connect(
            host=s.postgres_host,
            port=s.postgres_port,
            dbname=s.postgres_db,
            user=s.postgres_user,
            password=s.postgres_password,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "unreachable"

    return HealthResponse(status="ok", db=db_status)


@router.get("/metrics", response_model=MetricsResponse)
def metrics(request: Request) -> MetricsResponse:
    """Informations runtime de l'API.

    startup_time est stocké dans app.state par le lifespan au démarrage.
    request.app donne accès à l'instance FastAPI depuis n'importe quelle route.
    """
    uptime = round(time.time() - request.app.state.startup_time)
    return MetricsResponse(version="1.0.0", uptime_seconds=uptime)
