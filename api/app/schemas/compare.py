from pydantic import BaseModel

from app.schemas.risk_score import RiskScoreRecord


class CompareResponse(BaseModel):
    countries: dict[str, list[RiskScoreRecord]]
