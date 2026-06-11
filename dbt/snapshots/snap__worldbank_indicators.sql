{% snapshot snap__worldbank_indicators %}

{{
    config(
        target_schema='monitoring',
        unique_key='snap_id',
        strategy='check',
        check_cols=['indicator_value'],
    )
}}

-- snap_id : clé composite sérialisée — identifie une ligne (pays × indicateur × année).
-- strategy='check' sur indicator_value : dbt détecte si WB révise une valeur historique
-- ou si un opérateur corrige manuellement une ligne en DB.
-- Note : ON CONFLICT DO NOTHING dans le loader empêche les révisions automatiques d'atteindre
-- raw. Ce snapshot est surtout un audit trail pour les corrections manuelles.
-- Voir docs/decisions/adr_001_do_nothing_vs_snapshot.md
SELECT
    period::text || '_' || country_code || '_' || indicator_code AS snap_id,
    period,
    country_code,
    indicator_code,
    indicator_name,
    indicator_value,
    ingested_at
FROM {{ ref('core__worldbank_indicators') }}

{% endsnapshot %}
