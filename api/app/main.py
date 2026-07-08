import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.pool import close_pool, init_pool
from app.routers import auth, compare, countries, food_prices, health, inflation, risk_score


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    app.state.startup_time = time.time()
    yield
    close_pool()


app = FastAPI(
    title="sahel-flow API",
    description="Surveillance de la sécurité alimentaire — Zone UEMOA (SEN + CIV)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(countries.router, prefix="/v1")
app.include_router(food_prices.router, prefix="/v1")
app.include_router(inflation.router, prefix="/v1")
app.include_router(risk_score.router, prefix="/v1")
app.include_router(compare.router, prefix="/v1")

# /metrics — format Prometheus (texte OpenMetrics), distinct du /v1/metrics JSON.
# excluded_handlers=["/metrics"] évite que Prometheus se scrape lui-même.
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app)
