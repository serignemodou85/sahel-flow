from datetime import date

from pydantic import BaseModel


class FoodPriceRecord(BaseModel):
    period: date
    country_code: str
    commodity: str
    unit: str
    currency: str
    avg_price_local: float | None
    avg_price_usd: float | None
    market_count: int
    null_price_count: int
