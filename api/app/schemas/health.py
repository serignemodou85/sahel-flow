from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db: str


class MetricsResponse(BaseModel):
    version: str
    uptime_seconds: int
