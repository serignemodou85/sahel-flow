"""Tests JWT — endpoint /v1/auth/token + protection des routes."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.deps import get_conn
from app.main import app


@pytest.fixture
def raw_client():
    """Client SANS override get_current_user — teste vraiment l'auth."""
    with patch("app.main.init_pool"), patch("app.main.close_pool"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


def test_login_returns_token(raw_client):
    resp = raw_client.post(
        "/v1/auth/token",
        data={"username": "admin", "password": "change_me_in_production"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(raw_client):
    resp = raw_client.post(
        "/v1/auth/token",
        data={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_wrong_username(raw_client):
    resp = raw_client.post(
        "/v1/auth/token",
        data={"username": "hacker", "password": "change_me_in_production"},
    )
    assert resp.status_code == 401


def test_protected_no_token(raw_client):
    """/v1/food-prices sans Authorization header → 401."""
    resp = raw_client.get("/v1/food-prices?country=SEN")
    assert resp.status_code == 401


def test_protected_with_valid_token(raw_client, mock_conn):
    """/v1/food-prices avec token valide → 200."""
    def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    try:
        login = raw_client.post(
            "/v1/auth/token",
            data={"username": "admin", "password": "change_me_in_production"},
        )
        token = login.json()["access_token"]
        resp = raw_client.get(
            "/v1/food-prices?country=SEN",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_conn, None)
