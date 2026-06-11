-- =============================================================================
-- init.sql — exécuté UNE SEULE FOIS à la création du volume TimescaleDB
-- Connexion par défaut : database "sahel_flow" (= valeur de POSTGRES_DB)
-- =============================================================================


-- =============================================================================
-- PARTIE 1 : Extension TimescaleDB
-- =============================================================================

-- Active l'extension TimescaleDB sur la database sahel_flow.
-- Doit être fait AVANT de créer les hypertables.
CREATE EXTENSION IF NOT EXISTS timescaledb;


-- =============================================================================
-- PARTIE 2 : Database Airflow
-- =============================================================================

-- Crée une database séparée pour les métadonnées Airflow.
-- Airflow n'a pas besoin de TimescaleDB — c'est du PostgreSQL standard.
-- Cette database est vide ; Airflow la peuple lui-même via "airflow db migrate".
CREATE DATABASE airflow;


-- =============================================================================
-- PARTIE 3 : Schemas PostgreSQL
-- =============================================================================
-- On crée les 4 schemas de l'architecture dbt.
-- raw     → données brutes ingérées (peuplé par Python/ingestion)
-- core    → nettoyage + normalisation (peuplé par dbt)
-- marts   → tables métier, risk score (peuplé par dbt)
-- monitoring → qualité pipeline, freshness (peuplé par dbt)
--
-- core, marts et monitoring sont vides ici : dbt les peuplera.
-- On les crée maintenant pour que les permissions et la structure soient
-- documentées dès le départ, et pour éviter une erreur si dbt cherche
-- un schema existant avant de le créer.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS monitoring;


-- =============================================================================
-- PARTIE 4 : Tables raw + Hypertables
-- =============================================================================
-- Convention : les tables hypertables reçoivent le préfixe "ht_"
-- pour les distinguer des tables PostgreSQL ordinaires.
--
-- Règle d'idempotence : chaque table a une contrainte UNIQUE sur
-- (time, clés métier) → le loader peut faire ON CONFLICT DO NOTHING
-- sans créer de doublons si on rejoue une ingestion.


-- ── 4.1 World Bank — Indicateurs macro ──────────────────────────────────────
-- Données annuelles (CPI inflation, PIB/habitant, malnutrition…)
-- Granularité : 1 point par (année, pays, indicateur)
-- Stockage de "time" : premier jour de l'année → 2023-01-01 00:00:00+00

CREATE TABLE raw.ht_worldbank_indicators (
    -- Colonne de partition (obligatoire pour create_hypertable)
    time            timestamptz     NOT NULL,

    -- Identifiants métier
    country_code    char(3)         NOT NULL,   -- ISO 3166-1 alpha-3 : SEN, CIV
    indicator_code  varchar(50)     NOT NULL,   -- ex : 'FP.CPI.TOTL.ZG'
    indicator_name  varchar(200)    NOT NULL,   -- ex : 'Inflation, consumer prices (annual %)'

    -- Valeur : nullable car World Bank a des lacunes (données manquantes courantes)
    value           numeric(15, 4),

    -- Traçabilité : quand cette ligne a été ingérée
    ingested_at     timestamptz     NOT NULL    DEFAULT now()
);

-- Contrainte d'unicité : empêche les doublons, permet ON CONFLICT DO NOTHING.
-- TimescaleDB exige que la colonne de partition (time) soit dans la contrainte UNIQUE.
ALTER TABLE raw.ht_worldbank_indicators
    ADD CONSTRAINT uq_worldbank_indicators
    UNIQUE (time, country_code, indicator_code);

-- Convertit la table en hypertable partitionnée par "time".
-- chunk_time_interval = 1 an : données annuelles → 1 chunk par année.
-- Sans ça, TimescaleDB utiliserait 7 jours par défaut → centaines de chunks vides.
SELECT create_hypertable(
    'raw.ht_worldbank_indicators',
    'time',
    chunk_time_interval => INTERVAL '1 year'
);

-- Index secondaire pour les requêtes filtrées par pays + indicateur.
-- "time DESC" : optimise les requêtes "dernière valeur connue".
CREATE INDEX idx_ht_worldbank_indicators_country_indicator
    ON raw.ht_worldbank_indicators (country_code, indicator_code, time DESC);


-- ── 4.2 WFP VAM — Prix alimentaires ─────────────────────────────────────────
-- Données mensuelles : prix par marché, commodité, pays
-- Granularité : 1 point par (mois, pays, marché, commodité)
-- Stockage de "time" : premier jour du mois → 2024-03-01 00:00:00+00

CREATE TABLE raw.ht_wfp_food_prices (
    -- Colonne de partition
    time            timestamptz     NOT NULL,

    -- Identifiants métier
    country_code    char(3)         NOT NULL,   -- SEN ou CIV
    market_name     varchar(100)    NOT NULL,   -- ex : 'Dakar', 'Abidjan'
    commodity       varchar(100)    NOT NULL,   -- ex : 'Millet', 'Riz importé'
    unit            varchar(50)     NOT NULL,   -- ex : 'KG'

    -- Devise : XOF = Franc CFA (zone UEMOA, taux fixe EUR)
    currency        char(3)         NOT NULL,

    -- Prix : nullable car WFP peut avoir des ruptures de collecte sur certains marchés
    price_local     numeric(12, 4),             -- prix en devise locale (XOF)
    price_usd       numeric(12, 4),             -- prix USD (WFP fournit la conversion)

    -- Traçabilité
    ingested_at     timestamptz     NOT NULL    DEFAULT now()
);

-- Contrainte d'unicité sur les 4 clés métier + time.
ALTER TABLE raw.ht_wfp_food_prices
    ADD CONSTRAINT uq_wfp_food_prices
    UNIQUE (time, country_code, market_name, commodity);

-- Convertit en hypertable.
-- chunk_time_interval = 1 mois : données mensuelles → 1 chunk par mois.
SELECT create_hypertable(
    'raw.ht_wfp_food_prices',
    'time',
    chunk_time_interval => INTERVAL '1 month'
);

-- Index secondaire pour les requêtes filtrées par pays + commodité.
CREATE INDEX idx_ht_wfp_food_prices_country_commodity
    ON raw.ht_wfp_food_prices (country_code, commodity, time DESC);
