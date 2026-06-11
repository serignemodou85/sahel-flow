{{
    config(materialized='view')
}}

WITH source AS (
    SELECT * FROM {{ ref('raw__worldbank__indicators') }}
)

SELECT
    time            AS period,          -- renommé : "period" est plus sémantique que "time"
    country_code,
    indicator_code,
    indicator_name,
    value           AS indicator_value, -- renommé : distingue WB vs WFP dans les marts
    ingested_at
FROM source
-- NULLs conservés : la couche monitoring (étape 10) en a besoin pour détecter les lacunes.
-- Les marts filtrent naturellement via AVG() et SUM() qui ignorent les NULLs.
