from typing import Generator

import psycopg2.extensions

from app.db.pool import get_pool


def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Dependency FastAPI : fournit une connexion du pool, la rend après la réponse.

    Le yield sépare le "avant" (getconn) du "après" (putconn).
    Le finally garantit que la connexion est rendue même si la route lève une exception.

    Usage dans une route :
        @router.get("/endpoint")
        def endpoint(conn = Depends(get_conn)):
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
    """
    conn = get_pool().getconn()
    try:
        yield conn
    finally:
        get_pool().putconn(conn)
