from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.db.deps import get_conn
from app.schemas.risk_score import RiskScoreRecord
from app.services import risk_score_service

router = APIRouter(tags=["risk-score"])


@router.get("/risk-score", response_model=list[RiskScoreRecord])
def list_risk_scores(
    country: Literal["SEN", "CIV"] = Query(..., description="Code pays ISO3"),
    start_date: date | None = Query(None, description="Période début (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Période fin (YYYY-MM-DD)"),
    conn=Depends(get_conn),
) -> list[RiskScoreRecord]:
    """Score de risque alimentaire mensuel 0–100 avec décomposition.

    Source : marts.mart__risk__score_monthly (calculé par dbt).
    Formule : 0.6 × price_trend_score + 0.4 × inflation_score.
    risk_level : "low" (<25) | "medium" (<50) | "high" (<75) | "critical" (≥75).
    Les 3 premiers mois de chaque pays sont absents — baseline_3m non calculable.
    """
    return risk_score_service.get_risk_scores(conn, country, start_date, end_date)
