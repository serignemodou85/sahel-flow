import os

import httpx
import streamlit as st

_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Exceptions à intercepter dans chaque appel :
# - httpx.RequestError    : erreur réseau (DNS, timeout, connexion refusée)
# - httpx.HTTPStatusError : réponse HTTP 4xx / 5xx (levée par raise_for_status)
# - ValueError            : parent de json.JSONDecodeError — corps vide ou non-JSON
_HTTP_ERRORS = (httpx.RequestError, httpx.HTTPStatusError, ValueError)


@st.cache_data(ttl=300)
def get_health() -> dict:
    try:
        r = httpx.get(f"{_BASE}/v1/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except _HTTP_ERRORS:
        return {}


@st.cache_data(ttl=300)
def get_countries() -> list[dict]:
    try:
        r = httpx.get(f"{_BASE}/v1/countries", timeout=5)
        r.raise_for_status()
        return r.json()
    except _HTTP_ERRORS:
        return []


@st.cache_data(ttl=300)
def get_food_prices(
    country: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    try:
        params: dict = {"country": country}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        r = httpx.get(f"{_BASE}/v1/food-prices", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except _HTTP_ERRORS:
        return []


@st.cache_data(ttl=300)
def get_inflation(
    country: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    try:
        params: dict = {"country": country}
        if start_year is not None:
            params["start_year"] = start_year
        if end_year is not None:
            params["end_year"] = end_year
        r = httpx.get(f"{_BASE}/v1/inflation", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except _HTTP_ERRORS:
        return []


@st.cache_data(ttl=300)
def get_risk_scores(
    country: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    try:
        params: dict = {"country": country}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        r = httpx.get(f"{_BASE}/v1/risk-score", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except _HTTP_ERRORS:
        return []


@st.cache_data(ttl=300)
def get_compare(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Retourne {"SEN": [...], "CIV": [...]} — inner dict extrait de CompareResponse."""
    try:
        params: dict = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        r = httpx.get(f"{_BASE}/v1/compare", params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("countries", {"SEN": [], "CIV": []})
    except _HTTP_ERRORS:
        return {"SEN": [], "CIV": []}
