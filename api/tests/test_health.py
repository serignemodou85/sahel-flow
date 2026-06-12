"""Tests pour /v1/health et /v1/metrics.

health() n'utilise pas Depends(get_conn) — dependency_overrides ne suffit pas.
On patche psycopg2.connect directement (là où il est utilisé).
Règle : patcher le symbole dans le module qui l'utilise, pas là où il est défini.
"""
from unittest.mock import MagicMock, patch


def test_health_ok(client):
    """/v1/health → 200, db=ok quand la connexion réussit."""
    mock_conn_obj = MagicMock()
    mock_cur_obj = MagicMock()
    mock_cur_obj.__enter__ = MagicMock(return_value=mock_cur_obj)
    mock_cur_obj.__exit__ = MagicMock(return_value=False)
    mock_conn_obj.cursor.return_value = mock_cur_obj

    with patch("psycopg2.connect", return_value=mock_conn_obj):
        resp = client.get("/v1/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_health_db_unreachable(client):
    """/v1/health → toujours 200, db=unreachable si la connexion échoue.

    Vérifie la décision de l'étape 14 : le health check ne retourne jamais 500,
    même quand la DB est down. Le load balancer doit recevoir 200 — c'est l'API
    qui répond, pas la DB.
    """
    with patch("psycopg2.connect", side_effect=Exception("DB down")):
        resp = client.get("/v1/health")

    assert resp.status_code == 200
    assert resp.json()["db"] == "unreachable"
    assert resp.json()["status"] == "ok"


def test_metrics_shape(client):
    """/v1/metrics → version et uptime_seconds présents."""
    resp = client.get("/v1/metrics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert isinstance(data["uptime_seconds"], int)
    assert data["uptime_seconds"] >= 0
