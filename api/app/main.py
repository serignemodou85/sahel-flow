import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.pool import close_pool, init_pool
from app.routers import compare, countries, food_prices, health, inflation, risk_score


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Démarrage ──────────────────────────────────────────────────────────────
    # init_pool() ouvre les connexions DB. Si TimescaleDB est indisponible,
    # l'app échoue ici avec un message clair — pas à la première requête.
    init_pool()
    app.state.startup_time = time.time()   # base pour uptime_seconds dans /metrics
    yield
    # ── Arrêt propre ───────────────────────────────────────────────────────────
    close_pool()


app = FastAPI(
    title="sahel-flow API",
    description="Surveillance de la sécurité alimentaire — Zone UEMOA (SEN + CIV)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/v1")
app.include_router(countries.router, prefix="/v1")
app.include_router(food_prices.router, prefix="/v1")
app.include_router(inflation.router, prefix="/v1")
app.include_router(risk_score.router, prefix="/v1")
app.include_router(compare.router, prefix="/v1")
