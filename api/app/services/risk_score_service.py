from datetime import date

import psycopg2.extensions
from psycopg2.extras import RealDictCursor

from app.schemas.risk_score import RiskScoreRecord

_SQL = """
    SELECT period, country_code, price_trend_score, inflation_score, risk_score
    FROM marts.mart__risk__score_monthly
    WHERE country_code = %(country)s
      AND (%(start_date)s IS NULL OR period >= %(start_date)s)
      AND (%(end_date)s IS NULL OR period <= %(end_date)s)
    ORDER BY period DESC
"""


def _risk_level(score: float) -> str:
    """Logique de présentation — appartient au service, pas à dbt.

    dbt calcule le score numérique (logique métier).
    Le service traduit ce score en label lisible (logique de présentation).
    Grafana peut filtrer par risk_level directement sans recalculer les seuils.
    """
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def get_risk_scores(
    conn: psycopg2.extensions.connection,
    country: str,
    start_date: date | None,
    end_date: date | None,
) -> list[RiskScoreRecord]:
    """Retourne les scores de risque depuis mart__risk__score_monthly.

    avg_price_usd, baseline_3m et inflation_rate ne sont pas exposés — colonnes
    intermédiaires de calcul internes au mart.
    risk_level est ajouté ici (pas dans dbt) : logique de présentation, pas métier.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(_SQL, {"country": country, "start_date": start_date, "end_date": end_date})
        rows = cur.fetchall()

    return [
        RiskScoreRecord(**row, risk_level=_risk_level(float(row["risk_score"])))
        for row in rows
    ]
