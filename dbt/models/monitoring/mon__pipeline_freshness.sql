{{
    config(materialized='view')
}}

-- Vue d'observabilité : fraîcheur de chaque table source.
-- source() direct — on observe l'état brut du warehouse, pas les modèles transformés.
-- Requêtable par Grafana pour un panel "dernière ingestion".
SELECT
    'ht_worldbank_indicators'   AS source_table,
    MAX(ingested_at)            AS last_ingested_at,
    now() - MAX(ingested_at)    AS age,
    COUNT(*)                    AS total_rows
FROM {{ source('raw', 'ht_worldbank_indicators') }}

UNION ALL

SELECT
    'ht_wfp_food_prices'        AS source_table,
    MAX(ingested_at)            AS last_ingested_at,
    now() - MAX(ingested_at)    AS age,
    COUNT(*)                    AS total_rows
FROM {{ source('raw', 'ht_wfp_food_prices') }}
