{{
    config(materialized='view')
}}

WITH source AS (
    SELECT * FROM {{ ref('raw__wfp__food_prices') }}
)

SELECT
    time            AS period,  -- renommé pour cohérence avec core__worldbank_indicators
    country_code,
    market_name,
    commodity,
    unit,
    currency,
    price_local,                -- NULL conservé (rupture de collecte = information utile)
    price_usd,
    ingested_at
FROM source
