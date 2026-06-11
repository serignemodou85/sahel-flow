{{
    config(materialized='view')
}}

-- Taux de NULL par colonne clé, agrégé par période.
-- WB : colonne value (lacunes attendues). WFP : colonne price_local (ruptures de collecte).
-- Permet de détecter une dégradation progressive de la qualité des sources.
SELECT
    'worldbank_indicators'              AS source,
    'value'                             AS monitored_column,
    DATE_TRUNC('year', time)            AS period,
    COUNT(*)                            AS total_rows,
    COUNT(*) FILTER (WHERE value IS NULL) AS null_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE value IS NULL) / NULLIF(COUNT(*), 0),
        2
    )                                   AS null_rate_pct
FROM {{ source('raw', 'ht_worldbank_indicators') }}
GROUP BY DATE_TRUNC('year', time)

UNION ALL

SELECT
    'wfp_food_prices'                   AS source,
    'price_local'                       AS monitored_column,
    DATE_TRUNC('month', time)           AS period,
    COUNT(*)                            AS total_rows,
    COUNT(*) FILTER (WHERE price_local IS NULL) AS null_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE price_local IS NULL) / NULLIF(COUNT(*), 0),
        2
    )                                   AS null_rate_pct
FROM {{ source('raw', 'ht_wfp_food_prices') }}
GROUP BY DATE_TRUNC('month', time)
