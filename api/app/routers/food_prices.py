from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.auth.service import get_current_user
from app.db.deps import get_conn
from app.schemas.food_prices import FoodPriceRecord
from app.services import food_prices_service

router = APIRouter(tags=["food-prices"], dependencies=[Depends(get_current_user)])


@router.get("/food-prices", response_model=list[FoodPriceRecord])
def list_food_prices(
    country: Literal["SEN", "CIV"] = Query(..., description="Code pays ISO3"),
    start_date: date | None = Query(None, description="Période début (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Période fin (YYYY-MM-DD)"),
    conn=Depends(get_conn),
) -> list[FoodPriceRecord]:
    """Prix alimentaires mensuels agrégés par commodité.

    Source : marts.mart__food__prices_monthly (calculé par dbt).
    Filtres start_date / end_date optionnels — sans filtres, retourne tout l'historique.
    """
    return food_prices_service.get_food_prices(conn, country, start_date, end_date)
