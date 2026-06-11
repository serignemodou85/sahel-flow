{{
    config(materialized='view')
}}

SELECT
    time,
    country_code,
    market_name,
    commodity,
    unit,
    currency,
    price_local,
    price_usd,
    ingested_at
FROM {{ source('raw', 'ht_wfp_food_prices') }}
