{{
    config(materialized='table')
}}

WITH source AS (
    SELECT * FROM {{ ref('core__worldbank_indicators') }}
),

-- LAG() calcule la valeur de l'année précédente pour chaque pays × indicateur.
-- Permet le calcul de yoy_change_pct sans jointure sur soi-même.
with_lag AS (
    SELECT
        *,
        LAG(indicator_value) OVER (
            PARTITION BY country_code, indicator_code
            ORDER BY period
        ) AS prev_year_value
    FROM source
)

SELECT
    period,
    country_code,
    indicator_code,
    indicator_name,
    indicator_value,
    prev_year_value,
    ROUND(
        CAST(
            (indicator_value / NULLIF(prev_year_value, 0) - 1) * 100
        AS NUMERIC), 2
    ) AS yoy_change_pct,  -- NULL si indicator_value ou prev_year_value est NULL
    ingested_at
FROM with_lag
