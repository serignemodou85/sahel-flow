{{
    config(materialized='table')
}}

-- Score de risque alimentaire 0-100 par pays et mois.
-- Formule : 0.6 * price_trend_score + 0.4 * inflation_score
--
-- price_trend_score : variation du prix moyen USD vs baseline 3 mois glissants.
--   +20% de hausse → 100, stable ou baisse → 0. Normalisation : variation * 500.
--
-- inflation_score : taux d'inflation annuel WB (FP.CPI.TOTL.ZG).
--   20% → 100, 0% → 0. Normalisation : inflation_rate * 5.
--
-- Jointure granularité : WFP mensuel × WB annuel — clé : country_code + YEAR(period).
-- Les 3 premiers mois par pays sont exclus (baseline_3m non calculable).

WITH food_prices AS (
    SELECT
        period,
        country_code,
        AVG(price_usd) AS avg_price_usd
    FROM {{ ref('core__wfp_food_prices') }}
    WHERE price_usd IS NOT NULL
    GROUP BY period, country_code
),

price_trend AS (
    SELECT
        period,
        country_code,
        avg_price_usd,
        AVG(avg_price_usd) OVER (
            PARTITION BY country_code
            ORDER BY period
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS baseline_3m
    FROM food_prices
),

inflation AS (
    SELECT
        country_code,
        EXTRACT(YEAR FROM period)::int AS year,
        indicator_value               AS inflation_rate
    FROM {{ ref('mart__macro__indicators_annual') }}
    WHERE indicator_code  = 'FP.CPI.TOTL.ZG'
      AND indicator_value IS NOT NULL
),

combined AS (
    SELECT
        pt.period,
        pt.country_code,
        pt.avg_price_usd,
        pt.baseline_3m,
        LEAST(100, GREATEST(0,
            (pt.avg_price_usd / NULLIF(pt.baseline_3m, 0) - 1) * 500
        ))                              AS price_trend_score,
        inf.inflation_rate,
        LEAST(100, GREATEST(0,
            COALESCE(inf.inflation_rate, 0) * 5
        ))                              AS inflation_score
    FROM price_trend pt
    LEFT JOIN inflation inf
        ON  pt.country_code              = inf.country_code
        AND EXTRACT(YEAR FROM pt.period)::int = inf.year
    WHERE pt.baseline_3m IS NOT NULL    -- exclut les 3 premiers mois sans historique
)

SELECT
    period,
    country_code,
    avg_price_usd,
    baseline_3m,
    price_trend_score,
    inflation_rate,
    inflation_score,
    ROUND(
        CAST(0.6 * price_trend_score + 0.4 * inflation_score AS NUMERIC), 2
    ) AS risk_score
FROM combined
