from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db.deps import get_conn
from app.schemas.compare import CompareResponse
from app.services import risk_score_service
from shared.constants import UEMOA_COUNTRIES

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareResponse)
def compare_countries(
    start_date: date | None = Query(None, description="Période début (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Période fin (YYYY-MM-DD)"),
    conn=Depends(get_conn),
) -> CompareResponse:
    """Compare le risk score entre tous les pays UEMOA sur la même période.

    Retourne un dict pays → liste de scores pour itération parallèle en Grafana/Streamlit.
    metric n'est pas encore un paramètre — cet endpoint compare toujours risk_score.
    Les autres métriques (food_prices, inflation) seront ajoutées avec le paramètre
    metric quand leurs services seront prêts.
    """
    countries = {
        code: risk_score_service.get_risk_scores(conn, code, start_date, end_date)
        for code in UEMOA_COUNTRIES
    }
    return CompareResponse(countries=countries)
