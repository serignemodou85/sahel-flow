import psycopg2
import pytest

from shared.config import get_settings

# ── Fixture : connexion TimescaleDB de dev ────────────────────────────────────


@pytest.fixture(scope="session")
def db_conn():
    """Connexion à TimescaleDB dev avec schema test_raw isolé.

    Skip automatiquement si la DB n'est pas accessible (make db-only non lancé).
    Utilisée par test_loader.py et les futurs tests bout en bout (étape 12).
    scope="session" : une seule connexion pour toute la session pytest.
    """
    settings = get_settings()
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
    except psycopg2.OperationalError:
        pytest.skip("TimescaleDB non accessible — lancer 'make db-only' d'abord")

    # Créer le schema test_raw avec les mêmes tables que raw.
    # Tables ordinaires (pas de hypertable) : ON CONFLICT DO NOTHING est une
    # fonctionnalité PostgreSQL standard — pas besoin de TimescaleDB pour le tester.
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS test_raw")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_raw.ht_worldbank_indicators (
                time            timestamptz     NOT NULL,
                country_code    char(3)         NOT NULL,
                indicator_code  varchar(50)     NOT NULL,
                indicator_name  varchar(200)    NOT NULL,
                value           numeric(15, 4),
                ingested_at     timestamptz     NOT NULL DEFAULT now(),
                CONSTRAINT uq_test_wb_indicators
                    UNIQUE (time, country_code, indicator_code)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_raw.ht_wfp_food_prices (
                time            timestamptz     NOT NULL,
                country_code    char(3)         NOT NULL,
                market_name     varchar(100)    NOT NULL,
                commodity       varchar(100)    NOT NULL,
                unit            varchar(50)     NOT NULL,
                currency        char(3)         NOT NULL,
                price_local     numeric(12, 4),
                price_usd       numeric(12, 4),
                ingested_at     timestamptz     NOT NULL DEFAULT now(),
                CONSTRAINT uq_test_wfp_food_prices
                    UNIQUE (time, country_code, market_name, commodity)
            )
        """)
    conn.autocommit = False

    yield conn

    # Teardown session : supprime le schema entier (tables + contraintes)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS test_raw CASCADE")
    conn.close()


@pytest.fixture
def clean_tables(db_conn):
    """Vide les tables test_raw après chaque test pour garantir l'isolation.

    autouse=False : déclarée explicitement dans la signature des tests qui écrivent
    en DB. Les tests qui n'insèrent rien (liste vide, mocks purs) n'en ont pas besoin.
    Source unique : définie ici, réutilisée dans test_loader.py et test_pipeline_e2e.py.
    """
    yield
    # Rollback toute transaction non fermée avant de tronquer
    db_conn.rollback()
    db_conn.autocommit = True
    with db_conn.cursor() as cur:
        cur.execute("TRUNCATE test_raw.ht_worldbank_indicators")
        cur.execute("TRUNCATE test_raw.ht_wfp_food_prices")
    db_conn.autocommit = False


# ── Fixtures : réponses simulées de l'API World Bank ─────────────────────────

# Reproduisent exactement la structure réelle : [metadata, [records]]
# Utilisées dans plusieurs tests → centralisées ici plutôt que dupliquées.


@pytest.fixture
def wb_single_page_response() -> list:
    """Réponse WB valide, une page, deux pays, valeurs numériques."""
    return [
        {
            "page": 1,
            "pages": 1,
            "per_page": "1000",
            "total": 2,
            "sourceid": "2",
            "lastupdated": "2024-01-01",
        },
        [
            {
                "indicator": {
                    "id": "FP.CPI.TOTL.ZG",
                    "value": "Inflation, consumer prices (annual %)",
                },
                "country":        {"id": "SN", "value": "Senegal"},
                "countryiso3code": "SEN",
                "date":           "2023",
                "value":          5.9,
                "unit":           "",
                "obs_status":     "",
                "decimal":        1,
            },
            {
                "indicator": {
                    "id": "FP.CPI.TOTL.ZG",
                    "value": "Inflation, consumer prices (annual %)",
                },
                "country":        {"id": "CI", "value": "Cote d'Ivoire"},
                "countryiso3code": "CIV",
                "date":           "2023",
                "value":          4.2,
                "unit":           "",
                "obs_status":     "",
                "decimal":        1,
            },
        ],
    ]


@pytest.fixture
def wb_null_value_response() -> list:
    """Réponse WB avec value=null (lacune de données — cas fréquent)."""
    return [
        {"page": 1, "pages": 1, "per_page": "1000", "total": 1},
        [
            {
                "indicator":       {"id": "FP.CPI.TOTL.ZG", "value": "Inflation..."},
                "countryiso3code": "SEN",
                "date":            "2015",
                "value":           None,   # WB n'a pas de donnée pour cette année
            }
        ],
    ]


@pytest.fixture
def wb_two_pages_response() -> list[list]:
    """Deux pages de réponse — une ligne par page pour forcer la pagination."""
    page1 = [
        {"page": 1, "pages": 2, "per_page": "1", "total": 2},
        [
            {
                "indicator":       {"id": "FP.CPI.TOTL.ZG", "value": "Inflation..."},
                "countryiso3code": "SEN",
                "date":            "2023",
                "value":           5.9,
            }
        ],
    ]
    page2 = [
        {"page": 2, "pages": 2, "per_page": "1", "total": 2},
        [
            {
                "indicator":       {"id": "FP.CPI.TOTL.ZG", "value": "Inflation..."},
                "countryiso3code": "CIV",
                "date":            "2023",
                "value":           4.2,
            }
        ],
    ]
    return [page1, page2]


# ── Fixtures : réponses simulées de l'API WFP Data Bridges ───────────────────
# Structure WFP : {"records": [...], "current_page": N, "total_count": N, "requests_per_page": N}
# Différente de WB ([metadata, [records]]) — chaque API a sa propre pagination.


@pytest.fixture
def wfp_single_page_response() -> dict:
    """Réponse WFP valide : deux enregistrements, prix renseignés."""
    return {
        "records": [
            {
                "date":     "2024-03-15",
                "mktName":  "Dakar",
                "cmName":   "Millet",
                "umName":   "KG",
                "currName": "XOF",
                "price":    350.0,
                "usdprice": 0.57,
            },
            {
                "date":     "2024-03-20",
                "mktName":  "Abidjan",
                "cmName":   "Riz importé",
                "umName":   "KG",
                "currName": "XOF",
                "price":    600.0,
                "usdprice": 0.98,
            },
        ],
        "current_page":     1,
        "total_count":      2,
        "requests_per_page": 200,
    }


@pytest.fixture
def wfp_missing_required_field_response() -> dict:
    """Enregistrement WFP avec cmName absent — champ NOT NULL dans la DB."""
    return {
        "records": [
            {
                "date":     "2024-03-15",
                "mktName":  "Dakar",
                # cmName manquant — doit être filtré par _parse_record
                "umName":   "KG",
                "currName": "XOF",
                "price":    350.0,
            }
        ],
        "current_page":     1,
        "total_count":      1,
        "requests_per_page": 200,
    }


@pytest.fixture
def wfp_null_price_response() -> dict:
    """Enregistrement WFP avec prix null — rupture de collecte sur le marché."""
    return {
        "records": [
            {
                "date":     "2024-03-15",
                "mktName":  "Dakar",
                "cmName":   "Millet",
                "umName":   "KG",
                "currName": "XOF",
                "price":    None,     # collecte interrompue ce mois
                "usdprice": None,
            }
        ],
        "current_page":     1,
        "total_count":      1,
        "requests_per_page": 200,
    }


@pytest.fixture
def wfp_two_pages_response() -> list[dict]:
    """Deux pages WFP — une ligne par page pour forcer la pagination."""
    page1 = {
        "records": [
            {
                "date":     "2024-01-15",
                "mktName":  "Dakar",
                "cmName":   "Millet",
                "umName":   "KG",
                "currName": "XOF",
                "price":    340.0,
                "usdprice": 0.56,
            }
        ],
        "current_page":      1,
        "total_count":       2,
        "requests_per_page": 1,
    }
    page2 = {
        "records": [
            {
                "date":     "2024-02-15",
                "mktName":  "Dakar",
                "cmName":   "Millet",
                "umName":   "KG",
                "currName": "XOF",
                "price":    360.0,
                "usdprice": 0.59,
            }
        ],
        "current_page":      2,
        "total_count":       2,
        "requests_per_page": 1,
    }
    return [page1, page2]
