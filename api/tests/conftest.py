"""Fixtures partagées pour les tests API FastAPI.

Deux problèmes à résoudre :
1. TestClient(app) déclenche le lifespan → init_pool() → appel DB réel.
   Solution : patcher init_pool et close_pool pour que le lifespan ne touche pas la DB.
2. Les routes business utilisent Depends(get_conn) → appel DB réel.
   Solution : dependency_overrides remplace get_conn par mock_conn.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.service import get_current_user
from app.db.deps import get_conn
from app.main import app


@pytest.fixture
def mock_cur():
    """Curseur psycopg2 factice — fetchall() retourne [] par défaut."""
    cur = MagicMock()
    cur.fetchall.return_value = []
    return cur


@pytest.fixture
def mock_conn(mock_cur):
    """Connexion psycopg2 factice.

    conn.cursor(cursor_factory=...) utilisé comme context manager :
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
    MagicMock gère __enter__/__exit__ automatiquement.
    On pointe __enter__ vers mock_cur pour que les services reçoivent le bon curseur.
    """
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = mock_cur
    conn.cursor.return_value.__exit__.return_value = False
    return conn


@pytest.fixture
def client(mock_conn):
    """TestClient avec :
    - init_pool / close_pool patchés → lifespan ne touche pas la DB
    - get_conn overridé → routes reçoivent mock_conn
    app.state.startup_time est quand même défini par le lifespan (pas dans init_pool).
    """
    def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_current_user] = lambda: "test-user"

    with patch("app.main.init_pool"), patch("app.main.close_pool"):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
