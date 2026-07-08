from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.auth.service import get_current_user
from app.db.deps import get_conn
from app.schemas.inflation import InflationRecord
from app.services import inflation_service

router = APIRouter(tags=["inflation"], dependencies=[Depends(get_current_user)])


@router.get("/inflation", response_model=list[InflationRecord])
def list_inflation(
    country: Literal["SEN", "CIV"] = Query(..., description="Code pays ISO3"),
    start_year: int | None = Query(None, description="Année début (ex: 2020)", ge=2000),
    end_year: int | None = Query(None, description="Année fin (ex: 2024)", le=2100),
    conn=Depends(get_conn),
) -> list[InflationRecord]:
    """Indicateurs macro-économiques annuels World Bank.

    Source : marts.mart__macro__indicators_annual (calculé par dbt).
    Inclut yoy_change_pct (variation annuelle %) — NULL pour la première année de chaque indicateur.
    """
    return inflation_service.get_inflation(conn, country, start_year, end_year)
