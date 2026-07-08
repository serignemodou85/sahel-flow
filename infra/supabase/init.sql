-- Supabase init — schéma marts uniquement (PostgreSQL standard, sans TimescaleDB)
-- À exécuter une fois dans l'éditeur SQL Supabase (Settings > SQL Editor)

CREATE SCHEMA IF NOT EXISTS marts;

-- ── Prix alimentaires mensuels ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS marts.mart__food__prices_monthly (
    period            DATE          NOT NULL,
    country_code      CHAR(3)       NOT NULL,
    commodity         VARCHAR(100)  NOT NULL,
    unit              VARCHAR(50)   NOT NULL,
    currency          CHAR(3)       NOT NULL,
    avg_price_local   NUMERIC(12,4),
    avg_price_usd     NUMERIC(12,4),
    market_count      INTEGER       NOT NULL DEFAULT 0,
    null_price_count  INTEGER       NOT NULL DEFAULT 0,
    PRIMARY KEY (period, country_code, commodity)
);

-- ── Indicateurs macro annuels (World Bank) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS marts.mart__macro__indicators_annual (
    period           DATE          NOT NULL,
    country_code     CHAR(3)       NOT NULL,
    indicator_code   VARCHAR(50)   NOT NULL,
    indicator_name   VARCHAR(200)  NOT NULL,
    indicator_value  NUMERIC(15,4),
    yoy_change_pct   NUMERIC(10,4),
    PRIMARY KEY (period, country_code, indicator_code)
);

-- ── Score de risque alimentaire mensuel ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS marts.mart__risk__score_monthly (
    period              DATE          NOT NULL,
    country_code        CHAR(3)       NOT NULL,
    price_trend_score   NUMERIC(6,2)  NOT NULL,
    inflation_score     NUMERIC(6,2)  NOT NULL,
    risk_score          NUMERIC(6,2)  NOT NULL,
    PRIMARY KEY (period, country_code)
);
