{{
    config(materialized='table')
}}

WITH source AS (
    SELECT * FROM {{ ref('core__wfp_food_prices') }}
)

SELECT
    period,
    country_code,
    commodity,
    unit,
    currency,
    AVG(price_local)                            AS avg_price_local,
    AVG(price_usd)                              AS avg_price_usd,
    COUNT(DISTINCT market_name)                 AS market_count,
    COUNT(*) FILTER (WHERE price_local IS NULL) AS null_price_count,
    MAX(ingested_at)                            AS last_ingested_at
FROM source
GROUP BY period, country_code, commodity, unit, currency
