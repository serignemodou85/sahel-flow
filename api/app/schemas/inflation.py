from datetime import date

from pydantic import BaseModel


class InflationRecord(BaseModel):
    period: date
    country_code: str
    indicator_code: str
    indicator_name: str
    indicator_value: float | None
    yoy_change_pct: float | None
