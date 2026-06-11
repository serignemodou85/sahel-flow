{{
    config(materialized='view')
}}

SELECT
    time,
    country_code,
    indicator_code,
    indicator_name,
    value,
    ingested_at
FROM {{ source('raw', 'ht_worldbank_indicators') }}
