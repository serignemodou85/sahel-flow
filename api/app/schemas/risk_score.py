from datetime import date

from pydantic import BaseModel


class RiskScoreRecord(BaseModel):
    period: date
    country_code: str
    risk_score: float
    price_trend_score: float
    inflation_score: float
    risk_level: str          # "low" | "medium" | "high" | "critical" — calculé dans le service
