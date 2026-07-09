# sahel-flow

Système de surveillance de la sécurité alimentaire pour la zone UEMOA — Sénégal (SEN) + Côte d'Ivoire (CIV).

Pipeline de données de bout en bout : ingestion → transformation → API REST → dashboards → vitrine analytics.

---

## Ce qui tourne en production (cloud)

```
World Bank API (annuel)          HDX WFP (mensuel, public, sans clé)
        │                               │
        ▼                               ▼
 GitHub Actions                  GitHub Actions
ingest_worldbank.py              ingest_wfp.py
  cron "0 6 1 * *"               cron "0 7 1 * *"
        │                               │
        └──────────────┬────────────────┘
                       │
                   Supabase
               schéma « marts »
      mart__macro__indicators_annual   ← 250 lignes réelles WB 2000–2024
       mart__food__prices_monthly      ← prix HDX réels >= 2020 (SEN + CIV)
        mart__risk__score_monthly      ← score complet 0.6×price_trend + 0.4×inflation
                       │
                   FastAPI
                (Render — free)
           /v1/health  /v1/countries
           /v1/risk-score  /v1/food-prices
           /v1/inflation  /v1/compare
                       │
              ┌────────┴─────────┐
              │                  │
          Streamlit          GitHub Actions
        (Render — free)      keep_alive.yml
        6 pages publiques    ping /v1/health
                             toutes les 14 min
```

**Pourquoi GitHub Actions et non Airflow en prod :** Airflow est un service local (docker compose) — il ne peut pas tourner sur le cloud gratuit. GitHub Actions est une infrastructure cloud native, gratuite sur repo public, avec `workflow_dispatch` pour déclencher manuellement. Un script Python standalone remplace toute la couche dbt + TimescaleDB + sync.

---

## Stack

| Couche | **Production** | Dev local | Rôle |
|---|---|---|---|
| Stockage | **Supabase** (PostgreSQL managé) | TimescaleDB | Data warehouse — marts uniquement |
| Ingestion | **GitHub Actions** (3 workflows) | Apache Airflow LocalExecutor | Ingestion mensuelle WB + WFP + keep-alive |
| Transformation | **Python** (ingest_worldbank.py + ingest_wfp.py) | dbt (raw → core → marts) | Calcul YoY, price_trend, risk score |
| API | **FastAPI** (Render free) | FastAPI (Docker) | Endpoints REST — JWT HS256 |
| Vitrine | **Streamlit** (Render free) | Streamlit (Docker) | 6 pages analytics |
| CI/CD | — | Jenkins LTS (Docker) | Lint + 33 tests + Docker build |
| Observabilité | **Monitoring Streamlit** (01_overview) | Grafana + Prometheus | Statut API, dernière ingestion, prochain run |

---

## Sources de données

| Source | Indicateurs | Granularité | Pays | Méthode |
|---|---|---|---|---|
| **World Bank API** | FP.CPI.TOTL.ZG · NY.GDP.PCAP.CD · SN.ITK.DEFC.ZS · AG.PRD.FOOD.XD · SP.POP.TOTL | Annuelle | SEN · CIV | GitHub Actions — `ingest_worldbank.py` cron 1er/mois 06h00 UTC |
| **HDX WFP** (Humanitarian Data Exchange) | Prix alimentaires par marché et commodité | Mensuelle | SEN · CIV | GitHub Actions — `ingest_wfp.py` cron 1er/mois 07h00 UTC |

---

## Modèle de risk score

```
risk_score = 0.6 × price_trend_score + 0.4 × inflation_score

price_trend_score : (prix_actuel / moyenne_3m - 1) × 500  → borné [0, 100]
inflation_score   : inflation_rate × 5  → borné [0, 100]

État actuel prod : price_trend_score = 0 (pas de données WFP live)
                   risk_score = 0.4 × inflation_score uniquement
```

| Niveau | Score | Badge |
|---|---|---|
| FAIBLE | 0 – 24 | 🟢 |
| MOYEN | 25 – 49 | 🟡 |
| ÉLEVÉ | 50 – 74 | 🟠 |
| CRITIQUE | 75 – 100 | 🔴 |

---

## Vitrine Streamlit — 6 pages

| Page | Description |
|---|---|
| **app.py** | Landing page commerciale — gauges live SEN/CIV, navigation, KPIs |
| **01 Vue d'ensemble** | Risk score actuel + monitoring strip (statut API, dernière ingestion WB, prochain run) |
| **02 Comparaison** | SEN vs CIV côte à côte sur une période choisie |
| **03 Prix Alimentaires** | Prix par commodité, marché et période |
| **04 Inflation** | Indicateurs macro WB 2000 – 2024 + export CSV |
| **05 Méthodologie** | Formule, stack, roadmap, limites du modèle |
| **06 Carte satellite** | Fond Esri WorldImagery + cercles de risque + 12 marchés alimentaires |

---

## GitHub Actions — 3 workflows

| Workflow | Déclenchement | Rôle |
|---|---|---|
| `ingest_worldbank.yml` | Cron `0 6 1 * *` + `workflow_dispatch` | Ingestion World Bank → Supabase (250 lignes réelles, 5 indicateurs) |
| `ingest_wfp.yml` | Cron `0 7 1 * *` + `workflow_dispatch` | Ingestion WFP HDX → Supabase (prix >= 2020 + risk score complet) |
| `keep_alive.yml` | Cron `*/14 * * * *` + `workflow_dispatch` | Ping `/v1/health` — empêche Render free tier de s'endormir |

**Ordre d'exécution le 1er du mois :** WB à 06h00 → WFP à 07h00 (inflation déjà en base pour le calcul du risk score complet)

**Secrets requis :**
- `DATABASE_URL_OVERRIDE` : DSN Supabase (pour ingest_worldbank.yml + ingest_wfp.yml)
- `API_BASE_URL` : URL Render de l'API (pour keep_alive.yml)

---

## API — Endpoints

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/v1/health` | Public | Statut API + DB |
| GET | `/v1/countries` | Public | Pays disponibles (SEN, CIV) |
| POST | `/v1/auth/token` | Public | OAuth2 password grant → JWT Bearer 30 min |
| GET | `/v1/food-prices` | JWT | Prix alimentaires mensuels par commodité |
| GET | `/v1/inflation` | JWT | Indicateurs macro annuels (World Bank) |
| GET | `/v1/risk-score` | JWT | Score de risque 0–100 |
| GET | `/v1/compare` | JWT | Comparaison SEN vs CIV |

---

## Lancement local (développement)

### Prérequis

- Docker Desktop
- Fichier `.env` à la racine (copier depuis `.env.example`)

```bash
cp .env.example .env
```

### Démarrer tous les services

```bash
docker compose up -d
```

| Service | URL | Description |
|---|---|---|
| FastAPI | http://localhost:8000/docs | Swagger UI — tous les endpoints |
| Streamlit | http://localhost:8501 | Vitrine analytics (6 pages) |
| Airflow | http://localhost:8080 | DAGs locaux (admin / admin) |
| Grafana | http://localhost:3000 | Dashboards (admin / admin) |
| Prometheus | http://localhost:9090 | Métriques RED |
| Jenkins | http://localhost:8082 | CI/CD |

### Tests

```bash
python -m pytest ingestion/tests/ api/tests/ -v
```

33 tests — 18 ingestion + 15 API (dont 5 auth JWT).

---

## Structure du projet

```
sahel-flow/
├── .github/workflows/
│   ├── ingest_worldbank.yml   # Ingestion WB mensuelle → Supabase
│   └── keep_alive.yml         # Ping API toutes les 14 min (anti-sleep Render)
├── shared/                    # Package Python partagé (config, constants, utils)
├── ingestion/                 # Extracteurs WB + WFP + loader TimescaleDB
│   └── tests/                 # 18 tests d'intégration
├── dags/                      # DAGs Airflow (local uniquement)
├── dbt/                       # Modèles dbt (local uniquement — doc de la logique)
├── api/                       # FastAPI
│   ├── app/
│   │   ├── auth/              # JWT OAuth2 HS256
│   │   ├── routers/           # 7 endpoints
│   │   ├── services/          # Logique SQL isolée du router
│   │   └── schemas/           # Modèles Pydantic
│   └── tests/                 # 15 tests (TestClient + dependency_overrides)
├── monitoring/grafana/        # Dashboards Grafana (local)
├── apps/streamlit/            # Vitrine analytics (6 pages)
│   ├── api_client.py          # Wrapper httpx + @st.cache_data
│   ├── app.py                 # Landing page commerciale + gauges live
│   └── pages/
│       ├── 01_overview.py     # Risk score + monitoring strip
│       ├── 02_comparaison.py  # SEN vs CIV
│       ├── 03_food_prices.py  # Prix par commodité
│       ├── 04_inflation.py    # Macro WB + export CSV
│       ├── 05_methodology.py  # Formule + stack + roadmap
│       └── 06_carte.py        # Carte satellite Esri + choroplèthe risque
├── infra/
│   ├── timescaledb/init.sql   # Schémas + hypertables (local)
│   ├── supabase/
│   │   ├── seed.py              # Données de démonstration (192 prix + 48 scores)
│   │   ├── ingest_worldbank.py  # Script standalone WB → Supabase (prod)
│   │   └── ingest_wfp.py        # Script standalone WFP HDX → Supabase (prod)
│   └── airflow/Dockerfile     # Image Airflow custom (local)
├── render.yaml                # IaC Render — 2 services (api + streamlit)
├── docker-compose.yml         # 7 services locaux orchestrés
└── pyproject.toml             # Configuration pytest
```

---

## Décisions d'architecture

8 ADRs documentés dans [`docs/decisions/`](docs/decisions/index.md) :

- ADR-001 : Snapshot SCD Type 2 vs do-nothing
- ADR-002 : Airflow LocalExecutor vs CeleryExecutor
- ADR-003 : Instance TimescaleDB unique (deux databases)
- ADR-004 : Dockerfile custom vs `_PIP_ADDITIONAL_REQUIREMENTS`
- ADR-005 : Loader idempotent avec `ON CONFLICT DO UPDATE`
- ADR-006 : Couplage faible DAG ↔ ingestion
- ADR-007 : `generate_schema_name` macro dbt
- ADR-008 : Schéma `test_raw` pour les tests

---

## Roadmap

- [x] Phase 1 — Pipeline de données local (18 tests, TimescaleDB + Airflow + dbt)
- [x] Phase 2 — API FastAPI (15 tests, JWT HS256, 7 endpoints)
- [x] Phase 3 — Observabilité Grafana + Streamlit (5 dashboards + 5 pages)
- [x] Phase 4 — Jenkins CI/CD (Agents Docker, JCasC, pre-commit, Shared Library, Multibranch)
- [x] Phase 5 — Déploiement cloud + données réelles
  - [x] Étape 33 — Prometheus (métriques RED, dashboard API Performance)
  - [x] Étape 34 — JWT OAuth2 HS256 (15 tests)
  - [x] Étape 35 — Déploiement Render + Supabase (seed 246 lignes)
  - [x] Étape 36 — Données réelles en prod (GitHub Actions → World Bank → 250 lignes)
  - [x] Étape 37 — UI commerciale Streamlit (gauges, carte satellite, monitoring strip, keep-alive)
  - [x] Étape 38 — Ingestion WFP HDX live (prix réels >= 2020 + risk score complet 0.6×price_trend + 0.4×inflation)
- [ ] Extension UEMOA 8 pays (Mali, Burkina, Niger, Togo, Bénin, Guinée-Bissau)
