# sahel-flow

Système de surveillance de la sécurité alimentaire pour la zone UEMOA pour l'instant on a utiliser seulement deux payx (Sénégal + Côte d'Ivoire).

Pipeline de données de bout en bout : ingestion → transformation → API REST → dashboards → vitrine analytics.

---

## Stack

| Couche | Technologie | Rôle |
|---|---|---|
| Stockage | TimescaleDB (PostgreSQL 15) | Data warehouse + metadata Airflow |
| Orchestration | Apache Airflow (LocalExecutor) | DAGs d'ingestion mensuelle + dbt |
| Transformation | dbt | raw → core → marts → monitoring |
| API | FastAPI + psycopg2 | Endpoints REST protégés par JWT (HS256) |
| Observabilité | Prometheus + Grafana 10 | Métriques RED + dashboards provisionnés |
| Vitrine | Streamlit | App analytics consommant l'API FastAPI |
| CI/CD | Jenkins LTS + Docker CLI | Lint (flake8) + Tests (pytest) + Build Docker |

---

## Sources de données

- **World Bank API** — indicateur `FP.CPI.TOTL.ZG` (inflation annuelle) pour SEN et CIV
- **WFP VAM Data Bridges** — prix alimentaires mensuels par marché et par commodité

---

## Architecture

```
World Bank API      WFP VAM API
       │                  │
       └────────┬──────────┘
                │
          Airflow DAG
      (ingestion mensuelle)
                │
                ▼
          TimescaleDB
           schéma raw
                │
                ▼
              dbt
    raw → core → marts
                │
         ┌──────┴──────────────┐
         │                     │                    │
      FastAPI               Grafana           Prometheus
  /v1/auth/token       (5 dashboards,       ← /metrics
  /v1/risk-score        provisioning         (RED metrics)
  /v1/food-prices       auto)
  /v1/inflation
  /v1/compare
         │
         ▼
      Streamlit
   (5 pages analytics)
```

---

## Modèle de risk score

```
risk_score = 0.6 × price_trend_score + 0.4 × inflation_score
```

- **price_trend_score** : variation du prix USD vs baseline 3 mois glissants, normalisée 0–100
- **inflation_score** : taux d'inflation annuel World Bank, normalisé 0–100
- **Niveaux** : Faible (0–24) · Moyen (25–49) · Élevé (50–74) · Critique (75–100)

---

## Lancement local

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
| Airflow | http://localhost:8080 | Orchestration DAGs (admin / admin) |
| FastAPI | http://localhost:8000/docs | Swagger UI — tous les endpoints |
| Grafana | http://localhost:3000 | Dashboards (anonyme ou admin / admin) |
| Prometheus | http://localhost:9090 | Métriques RED — targets + alertes |
| Streamlit | http://localhost:8501 | Vitrine analytics |
| Jenkins | http://localhost:8082 | CI/CD — pipeline lint → tests → build |

### Démarrer uniquement la base de données

```bash
make db-only
```

### Tests

```bash
python -m pytest ingestion/tests/ api/tests/ -v
```

33 tests — 18 ingestion + 15 API (dont 5 auth JWT).

---

## Structure du projet

```
sahel-flow/
├── shared/                    # Package Python partagé (config, constants, utils)
├── ingestion/                 # Extracteurs World Bank + WFP + loader TimescaleDB
│   └── tests/                 # 18 tests d'intégration
├── dags/                      # DAGs Airflow (ingestion + transform dbt)
├── dbt/                       # Modèles dbt
│   └── models/
│       ├── raw/               # Wrappers sur les tables sources
│       ├── core/              # Nettoyage, types, normalisation
│       ├── marts/             # Tables métier (food prices, inflation, risk score)
│       └── monitoring/        # Vues d'observabilité (freshness, null rates, row counts)
├── api/                       # FastAPI
│   ├── app/
│   │   ├── routers/           # 6 endpoints : health, countries, food-prices, inflation, risk-score, compare
│   │   ├── services/          # Logique SQL isolée du router
│   │   └── schemas/           # Modèles Pydantic
│   ├── app/
│   │   ├── auth/              # JWT : schemas, service (OAuth2PasswordBearer), router
│   │   ├── routers/           # 7 endpoints : health, auth, countries, food-prices, inflation, risk-score, compare
│   │   ├── services/          # Logique SQL isolée du router
│   │   └── schemas/           # Modèles Pydantic
│   └── tests/                 # 15 tests (TestClient + dependency_overrides)
├── monitoring/
│   └── grafana/
│       ├── provisioning/      # Datasource + dashboard auto-provisionnés au démarrage
│       └── dashboards/        # food_prices.json, inflation.json, risk_score.json, pipeline_freshness.json
├── apps/
│   └── streamlit/             # Vitrine analytics (5 pages)
│       ├── api_client.py      # Wrapper httpx + cache
│       ├── app.py             # Point d'entrée
│       └── pages/             # Vue d'ensemble, Comparaison, Prix, Inflation, Méthodologie
├── infra/
│   ├── timescaledb/init.sql   # Création des schemas + hypertables
│   └── airflow/Dockerfile     # Image Airflow custom
├── docker-compose.yml         # 7 services orchestrés
├── Makefile                   # make up / down / db-only / logs / fernet-key
└── pyproject.toml             # Configuration pytest
```

---

## API — Endpoints disponibles

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/v1/health` | Public | Statut API + DB |
| GET | `/v1/metrics` | Public | Version + uptime |
| GET | `/v1/countries` | Public | Pays disponibles (SEN, CIV) |
| POST | `/v1/auth/token` | Public | OAuth2 password grant → JWT Bearer 30 min |
| GET | `/v1/food-prices` | JWT | Prix alimentaires mensuels par commodité |
| GET | `/v1/inflation` | JWT | Indicateurs macro annuels (World Bank) |
| GET | `/v1/risk-score` | JWT | Score de risque mensuel 0–100 |
| GET | `/v1/compare` | JWT | Comparaison SEN vs CIV sur une même période |

Documentation interactive : http://localhost:8000/docs

---

## Dashboards Grafana

Provisionnés automatiquement au démarrage — aucune configuration manuelle requise.

| Dashboard | Source | Contenu |
|---|---|---|
| Prix Alimentaires | `mart__food__prices_monthly` (TimescaleDB) | Évolution des prix, marchés actifs, drill-down par pays |
| Inflation | `mart__macro__indicators_annual` (TimescaleDB) | Taux FP.CPI.TOTL.ZG SEN vs CIV, variation YoY |
| Risk Score | `mart__risk__score_monthly` (TimescaleDB) | Score mensuel, jauge actuelle, décomposition |
| Pipeline Freshness | `mon__pipeline_freshness` + `mon__null_rates` (TimescaleDB) | Fraîcheur, volume, qualité des données |
| API Performance | `/metrics` (Prometheus) | Taux req/s, latence P95, erreurs 5xx, total par endpoint |

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

- [x] Phase 1 — Pipeline de données (18 tests)
- [x] Phase 2 — API FastAPI (10 tests)
- [x] Phase 3 — Monitoring Grafana + Streamlit
- [x] Phase 4 — Jenkins CI/CD (Groupes 1-5 : service, agents Docker, JCasC, parallélisation, pre-commit, shared lib, multibranch)
- [ ] Phase 5 — Observabilité + Sécurité + Déploiement
  - [x] Étape 33 — Prometheus (métriques RED, dashboard API Performance)
  - [x] Étape 34 — JWT (OAuth2 password grant, HS256, 15 tests)
  - [ ] Étape 35 — Déploiement Render + Supabase
  - [ ] Étape 37 — Scraping BCEAO HTML
