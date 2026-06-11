{{
    config(materialized='view')
}}

-- Nombre de lignes ingérées par source, période et pays.
-- Alerter si un pays disparaît d'un mois sur l'autre (count = 0 non représenté →
-- utiliser une série temporelle complète en dehors de dbt pour détecter les absences).
SELECT
    'worldbank_indicators'          AS source,
    DATE_TRUNC('year', time)        AS period,
    country_code,
    COUNT(*)                        AS row_count
FROM {{ source('raw', 'ht_worldbank_indicators') }}
GROUP BY DATE_TRUNC('year', time), country_code

UNION ALL

SELECT
    'wfp_food_prices'               AS source,
    DATE_TRUNC('month', time)       AS period,
    country_code,
    COUNT(*)                        AS row_count
FROM {{ source('raw', 'ht_wfp_food_prices') }}
GROUP BY DATE_TRUNC('month', time), country_code
