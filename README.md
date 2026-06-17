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
| API | FastAPI + psycopg2 | Endpoints REST consommant les marts |
| Monitoring | Grafana 10 | Dashboards prix, inflation, risk score, pipeline |
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
         │                     │
      FastAPI               Grafana
  /v1/risk-score         (4 dashboards,
  /v1/food-prices         provisioning auto)
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

28 tests — 18 ingestion + 10 API.

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
│   └── tests/                 # 10 tests (TestClient + dependency_overrides)
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

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/v1/health` | Statut API + DB |
| GET | `/v1/metrics` | Version + uptime |
| GET | `/v1/countries` | Pays disponibles (SEN, CIV) |
| GET | `/v1/food-prices` | Prix alimentaires mensuels par commodité |
| GET | `/v1/inflation` | Indicateurs macro annuels (World Bank) |
| GET | `/v1/risk-score` | Score de risque mensuel 0–100 |
| GET | `/v1/compare` | Comparaison SEN vs CIV sur une même période |

Documentation interactive : http://localhost:8000/docs

---

## Dashboards Grafana

Provisionnés automatiquement au démarrage — aucune configuration manuelle requise.

| Dashboard | Source dbt | Contenu |
|---|---|---|
| Prix Alimentaires | `mart__food__prices_monthly` | Évolution des prix, marchés actifs, drill-down par pays |
| Inflation | `mart__macro__indicators_annual` | Taux FP.CPI.TOTL.ZG SEN vs CIV, variation YoY |
| Risk Score | `mart__risk__score_monthly` | Score mensuel, jauge actuelle, décomposition |
| Pipeline Freshness | `mon__pipeline_freshness` + `mon__null_rates` + `mon__row_counts` | Fraîcheur, volume, qualité des données |

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
- [x] Phase 4 — Jenkins CI/CD (Groupe 1 : service + Jenkinsfile)
- [ ] Phase 5 (prevue) — Prometheus, JWT, déploiement cloud
