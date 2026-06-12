"""Tests pour les endpoints business : countries, food-prices, inflation, risk-score, compare.

Tous utilisent Depends(get_conn) → dependency_overrides suffit (conftest.py).
mock_cur.fetchall.return_value configure les données retournées par le curseur.
"""
from datetime import date


# ── /v1/countries ─────────────────────────────────────────────────────────────

def test_countries_empty_db(client):
    """DB vide → liste vide. L'API reflète la réalité de la DB, pas de hardcode."""
    resp = client.get("/v1/countries")

    assert resp.status_code == 200
    assert resp.json() == []


# ── /v1/food-prices ───────────────────────────────────────────────────────────

def test_food_prices_invalid_country(client):
    """country=XXX → 422 avant d'entrer dans la route.

    Literal["SEN", "CIV"] + FastAPI valide automatiquement — pas de code métier
    dans le service pour rejeter un pays inconnu.
    """
    resp = client.get("/v1/food-prices?country=XXX")

    assert resp.status_code == 422


# ── /v1/inflation ─────────────────────────────────────────────────────────────

def test_inflation_invalid_year(client):
    """start_year=1999 → 422 — Query(ge=2000) validé par FastAPI avant la route."""
    resp = client.get("/v1/inflation?country=SEN&start_year=1999")

    assert resp.status_code == 422


# ── /v1/risk-score ────────────────────────────────────────────────────────────

def test_risk_score_returns_risk_level(client, mock_cur):
    """risk_level est calculé dans le service — présent dans chaque record.

    score=65 → [50, 75) → "high". Vérifie que _risk_level() est bien appliqué.
    """
    mock_cur.fetchall.return_value = [
        {
            "period":            date(2024, 1, 1),
            "country_code":      "SEN",
            "risk_score":        65.0,
            "price_trend_score": 80.0,
            "inflation_score":   42.5,
        }
    ]

    resp = client.get("/v1/risk-score?country=SEN")

    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    assert records[0]["risk_level"] == "high"
    assert records[0]["risk_score"] == 65.0
    assert records[0]["price_trend_score"] == 80.0


def test_risk_score_level_boundaries(client, mock_cur):
    """Vérifie les quatre niveaux de risk_level sur les valeurs limites."""
    mock_cur.fetchall.return_value = [
        {"period": date(2024, 1, 1), "country_code": "SEN",
         "risk_score": 10.0, "price_trend_score": 0.0, "inflation_score": 0.0},
        {"period": date(2024, 2, 1), "country_code": "SEN",
         "risk_score": 30.0, "price_trend_score": 0.0, "inflation_score": 0.0},
        {"period": date(2024, 3, 1), "country_code": "SEN",
         "risk_score": 60.0, "price_trend_score": 0.0, "inflation_score": 0.0},
        {"period": date(2024, 4, 1), "country_code": "SEN",
         "risk_score": 90.0, "price_trend_score": 0.0, "inflation_score": 0.0},
    ]

    resp = client.get("/v1/risk-score?country=SEN")
    records = resp.json()

    assert records[0]["risk_level"] == "low"       # 10 < 25
    assert records[1]["risk_level"] == "medium"    # 25 ≤ 30 < 50
    assert records[2]["risk_level"] == "high"      # 50 ≤ 60 < 75
    assert records[3]["risk_level"] == "critical"  # 90 ≥ 75


# ── /v1/compare ───────────────────────────────────────────────────────────────

def test_compare_has_both_countries(client):
    """La réponse contient SEN et CIV — tous les pays UEMOA_COUNTRIES."""
    resp = client.get("/v1/compare")

    assert resp.status_code == 200
    data = resp.json()
    assert "countries" in data
    assert "SEN" in data["countries"]
    assert "CIV" in data["countries"]


def test_compare_empty_db(client):
    """DB vide → {"countries": {"SEN": [], "CIV": []}} — structure correcte."""
    resp = client.get("/v1/compare")

    data = resp.json()
    assert data["countries"]["SEN"] == []
    assert data["countries"]["CIV"] == []
