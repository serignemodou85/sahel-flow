#!/usr/bin/env python3
"""Génère sahel-flow-notes.pdf — Phase 1 à Phase 5."""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY       = (26,  41,  66)
SECTION_C  = (44,  95, 138)
CODE_BG    = (245, 245, 245)
RET_BG     = (232, 244, 248)
RET_BRD    = (44,  95, 138)
GRAY       = (120, 120, 120)
DARK       = (30,  30,  30)
WHITE      = (255, 255, 255)
ACCENT     = (100, 149, 200)
PHASE_GOLD = (195, 160,  60)

LM, RM = 18, 18
PW = 210 - LM - RM  # 174 mm


# ── Fonts helper ──────────────────────────────────────────────────────────────
def _load_fonts(pdf: FPDF):
    """Charge Segoe UI (Windows 11) pour Unicode complet; fallback Helvetica."""
    win_fonts = r"C:\Windows\Fonts"
    seg = os.path.join(win_fonts, "segoeui.ttf")
    segb = os.path.join(win_fonts, "segoeuib.ttf")
    segi = os.path.join(win_fonts, "segoeuii.ttf")
    segbi = os.path.join(win_fonts, "segoeuiz.ttf")
    con = os.path.join(win_fonts, "consola.ttf")
    conb = os.path.join(win_fonts, "consolab.ttf")
    if all(os.path.exists(f) for f in [seg, segb, segi, con]):
        pdf.add_font("body", "",   seg)
        pdf.add_font("body", "B",  segb)
        pdf.add_font("body", "I",  segi)
        pdf.add_font("body", "BI", segbi)
        pdf.add_font("mono", "",   con)
        if os.path.exists(conb):
            pdf.add_font("mono", "B", conb)
        return "body", "mono"
    return "helvetica", "courier"


# ── PDF class ─────────────────────────────────────────────────────────────────
class SahelPDF(FPDF):

    def setup(self):
        self.BF, self.MF = _load_fonts(self)
        self.set_margins(LM, 22, RM)
        self.set_auto_page_break(auto=True, margin=15)

    def _f(self, style="", size=10):
        self.set_font(self.BF, style, size)

    def _m(self, style="", size=8.5):
        self.set_font(self.MF, style, size)

    # ── Header / Footer ───────────────────────────────────────────────────────
    def header(self):
        if self.page_no() <= 1:
            return
        self.set_y(8)
        self._f("I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 4, "sahel-flow — Notes de compréhension Phase 1 à Phase 5", align="C")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.25)
        self.line(LM, 13.5, 210 - RM, 13.5)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.25)
        self.line(LM, self.get_y(), 210 - RM, self.get_y())
        self._f("I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 7, f"Page {self.page_no()}", align="C")

    # ── Title page ────────────────────────────────────────────────────────────
    def title_page(self):
        self.add_page()
        # Navy header block
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 90, "F")
        # Gold accent line
        self.set_fill_color(*PHASE_GOLD)
        self.rect(0, 90, 210, 1.5, "F")

        self.set_y(25)
        self._f("B", 38)
        self.set_text_color(*WHITE)
        self.cell(0, 18, "sahel-flow", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self._f("", 13)
        self.set_text_color(190, 215, 240)
        self.cell(0, 8, "Notes de compréhension — Phase 1 à Phase 5",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)
        self._f("I", 10)
        self.set_text_color(160, 190, 220)
        self.cell(0, 6,
                  "Pipeline : Ingestion -> dbt -> FastAPI (JWT) -> Grafana + Prometheus + Streamlit -> Jenkins",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Phase summary table
        self.set_y(100)
        phases = [
            ("Phase 1", "Pipeline de données",
             "Docker Compose, TimescaleDB, Airflow, dbt, Tests (18 tests)"),
            ("Phase 2", "API FastAPI",
             "Architecture en couches, Pydantic, TestClient (10 tests)"),
            ("Phase 3", "Observabilité",
             "Grafana (provisioning as code), Streamlit (5 pages)"),
            ("Phase 4", "Jenkins CI/CD",
             "Agents Docker, JCasC, pre-commit, Shared Library, Multibranch"),
            ("Phase 5", "Securite + Cloud",
             "Prometheus RED, JWT OAuth2 (HS256), Render + Supabase (en cours)"),
        ]
        for tag, title, desc in phases:
            y = self.get_y()
            # tag pill
            self.set_fill_color(*NAVY)
            self.rect(LM, y, 28, 10, "F")
            self._f("B", 8.5)
            self.set_text_color(*WHITE)
            self.set_xy(LM + 1, y + 2)
            self.cell(26, 6, tag, align="C")
            # title + desc
            self._f("B", 10)
            self.set_text_color(*DARK)
            self.set_xy(LM + 31, y + 1)
            self.cell(PW - 31, 5, title)
            self._f("", 9)
            self.set_text_color(*GRAY)
            self.set_xy(LM + 31, y + 6)
            self.cell(PW - 31, 4, desc)
            self.set_xy(LM, y + 13)

        # Date + test count
        self.set_y(260)
        self._f("", 9)
        self.set_text_color(*GRAY)
        self.cell(0, 5, "33 tests en vert -- Juillet 2026", align="C")

    # ── Block elements ────────────────────────────────────────────────────────
    def phase_header(self, title):
        """Nouvelle page + bandeau couleur pour chaque phase."""
        self.add_page()
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self._f("B", 14)
        self.cell(PW, 13, f"  {title}",
                  fill=True, align="L",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_fill_color(*PHASE_GOLD)
        y = self.get_y()
        self.rect(LM, y, PW, 1.2, "F")
        self.set_text_color(*DARK)
        self.ln(6)

    def section(self, title):
        self.ln(5)
        if self.get_y() > 250:
            self.add_page()
        self._f("B", 11)
        self.set_text_color(*SECTION_C)
        self.multi_cell(PW, 6.5, title,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y = self.get_y()
        self.set_draw_color(*SECTION_C)
        self.set_line_width(0.4)
        self.line(LM, y, LM + PW, y)
        self.set_line_width(0.2)
        self.set_text_color(*DARK)
        self.ln(3)

    def subsection(self, title):
        self.ln(3)
        self._f("B", 10)
        self.set_text_color(*DARK)
        self.multi_cell(PW, 5.5, title,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def label(self, text):
        self.ln(1)
        self._f("BI", 9.5)
        self.set_text_color(*SECTION_C)
        self.multi_cell(PW, 5.5, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._f("", 10)
        self.set_text_color(*DARK)
        self.ln(1)

    def body(self, text):
        self._f("", 10)
        self.set_text_color(*DARK)
        self.multi_cell(PW, 5.5, text, align="J",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def bullets(self, items, indent=0):
        self._f("", 10)
        self.set_text_color(*DARK)
        off = indent * 5
        bw = 5
        tw = PW - off - bw
        for item in items:
            if self.get_y() > self.h - self.b_margin - 8:
                self.add_page()
            self.set_x(LM + off)
            self.cell(bw, 5.5, "-")
            self.set_x(LM + off + bw)
            self.multi_cell(tw, 5.5, item,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def code(self, code_text):
        self.ln(2)
        lines = code_text.split("\n")
        lh = 4.3
        pad = 3.5
        box_h = len(lines) * lh + 2 * pad

        if self.get_y() + box_h > self.h - self.b_margin:
            self.add_page()

        y0 = self.get_y()
        self.set_fill_color(*CODE_BG)
        self.rect(LM, y0, PW, box_h, "F")
        self.set_fill_color(*SECTION_C)
        self.rect(LM, y0, 2.2, box_h, "F")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.2)
        self.line(LM, y0, LM + PW, y0)
        self.line(LM, y0 + box_h, LM + PW, y0 + box_h)

        self._m("", 8.5)
        self.set_text_color(35, 35, 35)
        self.set_xy(LM + 4.5, y0 + pad)

        for line in lines:
            if self.get_y() + lh > self.h - self.b_margin:
                self.add_page()
                y0 = self.get_y()
                self.set_fill_color(*CODE_BG)
                self.rect(LM, y0, PW, (len(lines)) * lh + 2 * pad, "F")
            self.set_x(LM + 4.5)
            self.cell(PW - 6, lh, line,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_y(y0 + box_h + 3)
        self._f("", 10)
        self.set_text_color(*DARK)

    def retenir(self, text):
        self.ln(3)
        lh = 5.0
        pad_v = 3.5
        avg_cw = 1.75  # mm/char approx at 9.5pt
        chars_pl = (PW - 10) / avg_cw
        paras = text.split("\n")
        n_lines = sum(max(1, len(p) / chars_pl) for p in paras) if paras else 1
        box_h = max(16, n_lines * lh + pad_v * 2 + 7)

        if self.get_y() + box_h > self.h - self.b_margin:
            self.add_page()

        y0 = self.get_y()
        self.set_fill_color(*RET_BG)
        self.rect(LM, y0, PW, box_h, "F")
        self.set_fill_color(*RET_BRD)
        self.rect(LM, y0, 2.5, box_h, "F")

        self.set_xy(LM + 5, y0 + pad_v)
        self._f("B", 9)
        self.set_text_color(*RET_BRD)
        self.cell(30, 5, "Retenir :")

        self.set_xy(LM + 5, y0 + pad_v + 6.5)
        self._f("", 9.5)
        self.set_text_color(15, 45, 75)
        self.multi_cell(PW - 10, lh, text, align="J",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        new_y = max(self.get_y() + pad_v, y0 + box_h) + 4
        self.set_y(new_y)
        self._f("", 10)
        self.set_text_color(*DARK)

    def sep(self):
        self.ln(3)
        self.set_draw_color(210, 210, 210)
        self.set_line_width(0.2)
        self.line(LM, self.get_y(), LM + PW, self.get_y())
        self.ln(4)


# ═════════════════════════════════════════════════════════════════════════════
# CONTENU
# ═════════════════════════════════════════════════════════════════════════════

def build(p: SahelPDF):

    # ── TITRE ──────────────────────────────────────────────────────────────
    p.title_page()

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1 — Pipeline de données
    # ══════════════════════════════════════════════════════════════════════
    p.phase_header("Phase 1 — Pipeline de données")

    # ── 1.1 Infrastructure ────────────────────────────────────────────────
    p.section("1.1  Infrastructure (étapes 1-2) : Docker Compose + TimescaleDB")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Docker Compose orchestre tous les services en réseau isolé. "
        "Chaque service est une image Docker ; la communication se fait par nom de service "
        "(ex. timescaledb:5432). TimescaleDB = PostgreSQL avec extension time-series, "
        "idéal pour des données mensuelles horodatées."
    )
    p.body(
        "Les services principaux : timescaledb, airflow-scheduler, airflow-webserver, "
        "airflow-init (bootstrap), dbt, fastapi, grafana, streamlit, jenkins."
    )
    p.code(
        "# Structure Docker Compose\n"
        "services:\n"
        "  timescaledb:\n"
        "    image: timescale/timescaledb:latest-pg15\n"
        "    environment:\n"
        "      POSTGRES_USER: ${POSTGRES_USER}\n"
        "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}\n"
        "      POSTGRES_DB: sahel_flow\n"
        "    volumes:\n"
        "      - timescale_data:/var/lib/postgresql/data\n"
        "      - ./infra/timescaledb/init.sql:/docker-entrypoint-initdb.d/init.sql\n"
        "    networks: [sahel_net]\n"
        "\n"
        "# init.sql cree les schemas + hypertables au premier démarrage\n"
        "CREATE SCHEMA IF NOT EXISTS raw;\n"
        "CREATE SCHEMA IF NOT EXISTS core;\n"
        "CREATE SCHEMA IF NOT EXISTS marts;\n"
        "SELECT create_hypertable('raw.food_prices', 'date', if_not_exists => TRUE);"
    )
    p.retenir(
        "Un service Docker = un nom DNS sur le réseau Compose. "
        "timescaledb = l'hôte accessible par tous les autres services. "
        "Les secrets viennent du .env (jamais committés). "
        "init.sql s'exécute exactement une fois : au premier démarrage du volume vide."
    )

    # ── 1.2 shared/ ───────────────────────────────────────────────────────
    p.section("1.2  shared/ (étape 3) : la configuration comme objet typé")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Au lieu de lire os.environ partout, on centralise dans un objet Pydantic "
        "Settings. Chaque composant (ingestion, API, tests) importe le même objet "
        "et bénéficie de la validation automatique au démarrage."
    )
    p.code(
        "# shared/config.py\n"
        "from pydantic_settings import BaseSettings\n"
        "\n"
        "class Settings(BaseSettings):\n"
        "    postgres_host: str\n"
        "    postgres_port: int = 5432\n"
        "    postgres_db: str\n"
        "    postgres_user: str\n"
        "    postgres_password: str\n"
        "\n"
        "    @property\n"
        "    def db_url(self) -> str:\n"
        "        return (f\"postgresql://{self.postgres_user}:{self.postgres_password}\"\n"
        "                f\"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}\")\n"
        "\n"
        "    model_config = SettingsConfigDict(env_file='.env', extra='ignore')\n"
        "\n"
        "settings = Settings()"
    )
    p.retenir(
        "Principe d'injection de dépendances : les modules ne lisent pas "
        "directement os.environ. Ils reçoivent la config depuis l'extérieur. "
        "Avantage : dans les tests, on peut passer une config différente sans "
        "modifier les variables d'environnement du processus."
    )

    # ── 1.3 Ingestion ─────────────────────────────────────────────────────
    p.section("1.3  Ingestion (étapes 4-5) : trois patterns à maîtriser")

    p.subsection("Pattern 1 — Extracteur avec pagination (World Bank)")
    p.body(
        "L'API World Bank pagine ses résultats. On itère jusqu'à ce que la page "
        "retournée soit vide. L'extracteur retourne une liste d'objets typés, "
        "pas des dicts bruts."
    )
    p.code(
        "# ingestion/world_bank.py\n"
        "class WBIngester:\n"
        "    def fetch(self, country: str, indicator: str) -> list[InflationRecord]:\n"
        "        records = []\n"
        "        page = 1\n"
        "        while True:\n"
        "            resp = self.client.get(\n"
        "                f\"/country/{country}/indicator/{indicator}\",\n"
        "                params={\"format\": \"json\", \"page\": page, \"per_page\": 100}\n"
        "            )\n"
        "            resp.raise_for_status()   # leve HTTPStatusError sur 4xx/5xx\n"
        "            data = resp.json()[1]      # [0]=meta, [1]=données\n"
        "            if not data:\n"
        "                break\n"
        "            records.extend(InflationRecord.from_wb(item) for item in data)\n"
        "            page += 1\n"
        "        return records"
    )

    p.subsection("Pattern 2 — Fail fast sur erreur HTTP")
    p.body(
        "httpx.RequestError couvre les erreurs réseau (timeout, DNS, etc.) mais "
        "PAS les erreurs HTTP (4xx, 5xx). Pour les attraper, il faut appeler "
        "raise_for_status() explicitement."
    )
    p.code(
        "try:\n"
        "    resp = client.get(url)\n"
        "    resp.raise_for_status()          # 400/404/500 -> HTTPStatusError\n"
        "except httpx.HTTPStatusError as e:\n"
        "    raise ValueError(f\"API error {e.response.status_code}\") from e\n"
        "except httpx.RequestError as e:\n"
        "    raise ValueError(f\"Network error: {e}\") from e"
    )

    p.subsection("Pattern 3 — Records typés (dataclasses)")
    p.body(
        "Les extracteurs retournent des objets Python typés, pas des dicts. "
        "Le loader reçoit ces objets et extrait les champs. "
        "Si le schéma de l'API change, l'erreur est visible dès la construction du record."
    )
    p.code(
        "from dataclasses import dataclass\n"
        "from datetime import date\n"
        "\n"
        "@dataclass\n"
        "class InflationRecord:\n"
        "    country_code: str\n"
        "    year: int\n"
        "    value: float | None\n"
        "\n"
        "    @classmethod\n"
        "    def from_wb(cls, item: dict) -> 'InflationRecord':\n"
        "        return cls(\n"
        "            country_code=item['country']['id'],\n"
        "            year=int(item['date']),\n"
        "            value=item['value'],   # peut être None\n"
        "        )"
    )
    p.retenir(
        "Ne jamais propager les dicts bruts de l'API jusqu'au loader. "
        "Les objets typés rendent les erreurs de schéma détectables à la construction, "
        "pas à l'insertion. Les valeurs None sont valides (indicateur non disponible "
        "pour une année donnée) -- le loader les gère avec NULL en base."
    )

    # ── 1.4 Loader ────────────────────────────────────────────────────────
    p.section("1.4  Loader (étape 6) : l'idempotence en pratique")
    p.label("Le problème :")
    p.body(
        "Si le pipeline tourne deux fois (relance Airflow, correction de bug...), "
        "on ne veut pas de doublons en base. La solution : ON CONFLICT DO UPDATE. "
        "L'INSERT écrase la ligne existante si la clé primaire existe déjà."
    )
    p.code(
        "# ingestion/loader.py\n"
        "def load_inflation(conn, records: list[InflationRecord]) -> int:\n"
        "    if not records:\n"
        "        return 0\n"
        "    with conn.cursor() as cur:\n"
        "        execute_values(\n"
        "            cur,\n"
        "            \"\"\"\n"
        "            INSERT INTO raw.inflation_indicators\n"
        "                (country_code, year, value, fetched_at)\n"
        "            VALUES %s\n"
        "            ON CONFLICT (country_code, year)\n"
        "            DO UPDATE SET\n"
        "                value      = EXCLUDED.value,\n"
        "                fetched_at = EXCLUDED.fetched_at\n"
        "            \"\"\",\n"
        "            [(r.country_code, r.year, r.value, datetime.utcnow())\n"
        "             for r in records]\n"
        "        )\n"
        "    conn.commit()\n"
        "    return len(records)"
    )
    p.retenir(
        "Idempotence = exécuter N fois donne le même résultat qu'une seule fois. "
        "ON CONFLICT DO UPDATE rend le loader idempotent : on peut relancer le "
        "pipeline autant de fois qu'on veut sans corrompre les données. "
        "execute_values() = un seul aller-retour réseau pour N lignes (batch insert)."
    )

    # ── 1.5 Airflow ───────────────────────────────────────────────────────
    p.section("1.5  Airflow (étapes 7 + 11) : penser en graphe de dépendances")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Un DAG (Directed Acyclic Graph) est un graphe de tâches sans cycle. "
        "Airflow execute les tâches dans l'ordre défini par les dépendances (>>). "
        "LocalExecutor = toutes les tâches s'exécutent sur la même machine."
    )
    p.bullets([
        "task_a >> task_b  : task_b démarre seulement si task_a réussit.",
        "[task_a, task_b] >> task_c  : task_c attend task_a ET task_b.",
        "schedule='@monthly' : déclenchement automatique chaque 1er du mois.",
        "start_date doit être dans le passé pour que le DAG soit actif.",
        "catchup=False : pas de backfill automatique des runs manqués.",
    ])
    p.code(
        "# dags/ingest_food_prices.py\n"
        "with DAG(\n"
        "    dag_id='ingest_food_prices',\n"
        "    schedule='@monthly',\n"
        "    start_date=datetime(2024, 1, 1),\n"
        "    catchup=False,\n"
        ") as dag:\n"
        "\n"
        "    extract = PythonOperator(\n"
        "        task_id='extract_wfp',\n"
        "        python_callable=run_extract,\n"
        "    )\n"
        "    load = PythonOperator(\n"
        "        task_id='load_timescaledb',\n"
        "        python_callable=run_load,\n"
        "    )\n"
        "    dbt_run = BashOperator(\n"
        "        task_id='dbt_run',\n"
        "        bash_command='dbt run --profiles-dir /dbt --project-dir /dbt',\n"
        "    )\n"
        "\n"
        "    extract >> load >> dbt_run"
    )
    p.retenir(
        "Ne jamais mettre de logique métier dans le DAG. Les callables (run_extract, "
        "run_load) sont de simples adaptateurs qui appellent les modules ingestion/. "
        "Le DAG orchestre; la logique vit dans les modules testables."
    )

    # ── 1.6 dbt ───────────────────────────────────────────────────────────
    p.section("1.6  dbt (étapes 8-10) : les 5 concepts fondamentaux")
    p.bullets([
        "sources : les tables brutes TimescaleDB (raw.*). dbt n'y écrit pas.",
        "models : fichiers SQL SELECT qui génèrent des tables/vues. "
        "raw -> core (nettoyage) -> marts (métier) -> monitoring (observabilité).",
        "ref() : dbt résout les dépendances entre modèles. "
        "{{ ref('core__food_prices') }} = dbt sait que ce modèle dépend du core.",
        "generate_schema_name : macro custom qui évite le préfixe username_ automatique. "
        "Sans elle, dbt crée 'johndoe_marts' au lieu de 'marts'.",
        "tests : unique + not_null sur les colonnes clés. "
        "dbt test les vérifie après chaque run.",
    ])
    p.code(
        "-- models/marts/mart__food__prices_monthly.sql\n"
        "{{ config(materialized='table') }}\n"
        "\n"
        "SELECT\n"
        "    date_trunc('month', date) AS month,\n"
        "    country_code,\n"
        "    commodity,\n"
        "    market,\n"
        "    AVG(price_usd) AS avg_price_usd,\n"
        "    COUNT(*)       AS n_observations\n"
        "FROM {{ ref('core__food_prices') }}\n"
        "GROUP BY 1, 2, 3, 4\n"
        "\n"
        "-- macros/generate_schema_name.sql\n"
        "{% macro generate_schema_name(custom_schema_name, node) %}\n"
        "    {{ custom_schema_name | trim }}\n"
        "{% endmacro %}"
    )
    p.retenir(
        "dbt transforme des données déjà en base (il ne fait pas d'ingestion). "
        "La chaine raw -> core -> marts est une convention, pas une obligation technique. "
        "La macro generate_schema_name est critique : sans elle, les noms de schemas "
        "en prod incluent le username dbt (comportement par défaut inattendu)."
    )

    # ── 1.7 Tests ─────────────────────────────────────────────────────────
    p.section("1.7  Tests (étape 12) : la pyramide appliquée")
    p.body(
        "La pyramide des tests : beaucoup d'unitaires (rapides, pas de DB), "
        "quelques d'intégration (DB réelle), peu d'E2E. "
        "Pour sahel-flow : 18 tests d'intégration qui tournent contre TimescaleDB."
    )
    p.code(
        "# ingestion/tests/conftest.py\n"
        "import pytest\n"
        "import psycopg2\n"
        "from shared.config import settings\n"
        "\n"
        "@pytest.fixture(scope='session')\n"
        "def db_conn():\n"
        "    \"\"\"Connexion vers test_raw (schema isolé des données de prod).\"\"\"\n"
        "    conn = psycopg2.connect(\n"
        "        host=settings.postgres_host,\n"
        "        port=settings.postgres_port,\n"
        "        dbname=settings.postgres_db,\n"
        "        user=settings.postgres_user,\n"
        "        password=settings.postgres_password,\n"
        "    )\n"
        "    yield conn\n"
        "    conn.close()\n"
        "\n"
        "# ingestion/tests/test_loader.py\n"
        "def test_load_inflation_records(db_conn):\n"
        "    records = [InflationRecord('SEN', 2023, 5.9)]\n"
        "    n = load_inflation(db_conn, records)\n"
        "    assert n == 1\n"
        "\n"
        "def test_load_empty_list(db_conn):\n"
        "    assert load_inflation(db_conn, []) == 0"
    )
    p.body(
        "schema='test_raw' dans les tests : défini dans pyproject.toml via "
        "POSTGRES_SCHEMA=test_raw. Les tables de test sont isolées des tables raw "
        "de production. Le schema injection vient du code interne, jamais de l'input "
        "utilisateur (pas de risque d'injection SQL)."
    )
    p.retenir(
        "scope='session' pour la connexion DB : une seule connexion pour tous les "
        "tests, pas de reconnexion à chaque test (plus rapide). "
        "pytest.mark.skipif(not db_available, ...) : les tests d'intégration "
        "se sautent proprement si TimescaleDB n'est pas lancé."
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2 — FastAPI
    # ══════════════════════════════════════════════════════════════════════
    p.phase_header("Phase 2 — API FastAPI")

    p.section("2.1  Infrastructure API (étapes 13-14) : lifespan + pool + Depends")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "FastAPI utilise le pattern lifespan pour initialiser les ressources au "
        "démarrage et les libérer à l'arrêt. Le pool de connexions psycopg2 "
        "(SimpleConnectionPool) évite d'ouvrir une connexion par requête."
    )
    p.code(
        "# api/app/database.py\n"
        "from psycopg2 import pool\n"
        "from contextlib import contextmanager\n"
        "\n"
        "connection_pool: pool.SimpleConnectionPool | None = None\n"
        "\n"
        "def init_pool(settings):\n"
        "    global connection_pool\n"
        "    connection_pool = pool.SimpleConnectionPool(\n"
        "        minconn=1, maxconn=10,\n"
        "        host=settings.postgres_host, ...\n"
        "    )\n"
        "\n"
        "@contextmanager\n"
        "def get_db():\n"
        "    conn = connection_pool.getconn()\n"
        "    try:\n"
        "        yield conn\n"
        "    finally:\n"
        "        connection_pool.putconn(conn)  # toujours remis dans le pool\n"
        "\n"
        "# api/app/main.py\n"
        "from contextlib import asynccontextmanager\n"
        "\n"
        "@asynccontextmanager\n"
        "async def lifespan(app: FastAPI):\n"
        "    init_pool(settings)    # démarrage\n"
        "    yield\n"
        "    connection_pool.closeall()  # arrêt propre\n"
        "\n"
        "app = FastAPI(lifespan=lifespan)"
    )
    p.retenir(
        "lifespan remplace @app.on_event (déprécié depuis FastAPI 0.93). "
        "Le pool de connexions = ressource partagée entre toutes les requêtes. "
        "get_db() comme context manager garantit que la connexion est toujours "
        "remise dans le pool, même en cas d'exception."
    )

    p.section("2.2  Pattern router -> service -> db (étapes 15-18)")
    p.label("Architecture en trois couches :")
    p.bullets([
        "Router : reçoit la requête HTTP, valide les paramètres, retourne la réponse JSON.",
        "Service : contient la logique SQL. Reçoit une connexion DB, retourne des objets Python.",
        "Database : le pool de connexions. Injecté via Depends().",
    ])
    p.code(
        "# api/app/routers/food_prices.py\n"
        "from fastapi import APIRouter, Depends, Query\n"
        "from ..database import get_db\n"
        "from ..services import food_prices_service\n"
        "from ..schemas import FoodPriceResponse\n"
        "\n"
        "router = APIRouter(prefix='/v1/food-prices')\n"
        "\n"
        "@router.get('/', response_model=list[FoodPriceResponse])\n"
        "def get_food_prices(\n"
        "    country: str = Query(..., min_length=3, max_length=3),\n"
        "    limit: int = Query(100, ge=1, le=1000),\n"
        "    db = Depends(get_db),\n"
        "):\n"
        "    return food_prices_service.get_prices(db, country, limit)\n"
        "\n"
        "# api/app/services/food_prices_service.py\n"
        "def get_prices(conn, country: str, limit: int) -> list[dict]:\n"
        "    with conn.cursor(cursor_factory=RealDictCursor) as cur:\n"
        "        cur.execute(\n"
        "            \"\"\"\n"
        "            SELECT month, commodity, market, avg_price_usd\n"
        "            FROM marts.mart__food__prices_monthly\n"
        "            WHERE country_code = %s\n"
        "            ORDER BY month DESC\n"
        "            LIMIT %s\n"
        "            \"\"\",\n"
        "            (country.upper(), limit)\n"
        "        )\n"
        "        return cur.fetchall()"
    )
    p.body(
        "Pydantic schemas : les classes BaseModel définissent le contrat JSON. "
        "FastAPI sérialise automatiquement les objets Python en JSON si le type "
        "de retour correspond au response_model."
    )
    p.retenir(
        "Depends(get_db) = injection de dépendances. FastAPI appelle get_db() "
        "pour chaque requête et injecte la connexion dans le paramètre db. "
        "Le service ne connaît pas FastAPI -- il reçoit juste une connexion psycopg2. "
        "Couplage minimal : le service est testable sans FastAPI."
    )

    p.section("2.3  Tests API (étape 19) : TestClient + dependency_overrides")
    p.body(
        "TestClient simule des requêtes HTTP sans lancer le serveur. "
        "dependency_overrides remplace get_db() par une connexion de test. "
        "On ne mocke pas la DB : on utilise la vraie TimescaleDB sur le schema test_raw."
    )
    p.code(
        "# api/tests/conftest.py\n"
        "import pytest\n"
        "from fastapi.testclient import TestClient\n"
        "from api.app.main import app\n"
        "from api.app.database import get_db\n"
        "\n"
        "@pytest.fixture(scope='module')\n"
        "def client(db_conn):\n"
        "    \"\"\"TestClient avec get_db() remplacé par la connexion de test.\"\"\"\n"
        "    def override_get_db():\n"
        "        yield db_conn\n"
        "\n"
        "    app.dependency_overrides[get_db] = override_get_db\n"
        "    with TestClient(app) as c:\n"
        "        yield c\n"
        "    app.dependency_overrides.clear()\n"
        "\n"
        "# api/tests/test_food_prices.py\n"
        "def test_food_prices_returns_200(client):\n"
        "    resp = client.get('/v1/food-prices/?country=SEN')\n"
        "    assert resp.status_code == 200\n"
        "    assert isinstance(resp.json(), list)\n"
        "\n"
        "def test_invalid_country_returns_422(client):\n"
        "    resp = client.get('/v1/food-prices/?country=TOOLONG')\n"
        "    assert resp.status_code == 422  # Pydantic validation"
    )
    p.retenir(
        "422 Unprocessable Entity = Pydantic a rejeté les paramètres de requête "
        "avant meme d'appeler le service. C'est FastAPI qui valide, pas le code SQL. "
        "scope='module' pour le client : une seule instance pour tous les tests "
        "du module, évite le re-démarrage de l'app à chaque test."
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3 — Observabilité
    # ══════════════════════════════════════════════════════════════════════
    p.phase_header("Phase 3 — Observabilité")

    p.section("3.1  Grafana (étapes 20-22) : config as code")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Grafana supporte le provisioning : des fichiers YAML/JSON placés dans "
        "des dossiers spécifiques sont lus au démarrage. Plus besoin de configurer "
        "manuellement la datasource ou d'importer les dashboards."
    )
    p.code(
        "# monitoring/grafana/provisioning/datasources/timescaledb.yaml\n"
        "apiVersion: 1\n"
        "datasources:\n"
        "  - name: TimescaleDB\n"
        "    type: postgres\n"
        "    url: timescaledb:5432\n"
        "    database: sahel_flow\n"
        "    user: ${POSTGRES_USER}\n"
        "    secureJsonData:\n"
        "      password: ${POSTGRES_PASSWORD}\n"
        "    jsonData:\n"
        "      sslmode: disable\n"
        "      timescaledb: true\n"
        "\n"
        "# monitoring/grafana/provisioning/dashboards/provider.yaml\n"
        "apiVersion: 1\n"
        "providers:\n"
        "  - name: sahel-flow\n"
        "    type: file\n"
        "    options:\n"
        "      path: /var/lib/grafana/dashboards"
    )
    p.body(
        "Les 4 dashboards JSON sont montés via volume Docker dans /var/lib/grafana/dashboards. "
        "Grafana les détecte automatiquement. Pour modifier un dashboard : "
        "exporter le JSON depuis l'UI Grafana, remplacer le fichier, redémarrer Grafana."
    )
    p.bullets([
        "food_prices.json : évolution des prix mensuels par commodité et marché.",
        "inflation.json : taux FP.CPI.TOTL.ZG SEN vs CIV, variation YoY.",
        "risk_score.json : score mensuel 0-100, jauge actuelle, décomposition 60/40.",
        "pipeline_freshness.json : fraîcheur (mon__pipeline_freshness), "
        "taux de NULL (mon__null_rates), comptages (mon__row_counts).",
    ])
    p.retenir(
        "Config as code = reproductible. Un docker compose up suffit pour avoir "
        "tous les dashboards sans configuration manuelle. "
        "Les modèles dbt monitoring/ (mon__*) alimentent le dashboard pipeline : "
        "on observe la qualité des données, pas seulement les métriques métier."
    )

    p.section("3.2  Streamlit (étape 23) : modèle d'exécution + cache + architecture")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Streamlit réexécute TOUT le script Python à chaque interaction utilisateur "
        "(clic, sélection, etc.). Sans cache, chaque clic déclencherait un appel "
        "API. @st.cache_data met le résultat en cache selon les arguments de la fonction."
    )
    p.code(
        "# apps/streamlit/api_client.py\n"
        "import httpx\n"
        "import streamlit as st\n"
        "\n"
        "@st.cache_data(ttl=300)  # cache 5 minutes\n"
        "def get_food_prices(country: str, limit: int = 100) -> list[dict]:\n"
        "    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:\n"
        "        resp = client.get('/v1/food-prices/', params={'country': country})\n"
        "        resp.raise_for_status()\n"
        "        return resp.json()\n"
        "\n"
        "# apps/streamlit/pages/1_Vue_d_ensemble.py\n"
        "import streamlit as st\n"
        "from api_client import get_food_prices\n"
        "\n"
        "st.title('Vue d ensemble -- Sahel Flow')\n"
        "country = st.selectbox('Pays', ['SEN', 'CIV'])\n"
        "data = get_food_prices(country)  # depuis le cache si < 5 min\n"
        "st.dataframe(data)"
    )
    p.body(
        "Règle d'architecture critique : Streamlit appelle l'API FastAPI uniquement. "
        "Jamais de connexion directe à TimescaleDB depuis Streamlit. "
        "FastAPI est le seul point d'accès aux données."
    )
    p.bullets([
        "page 1 : Vue d'ensemble (risk score global, dernière fraîcheur).",
        "page 2 : Comparaison SEN vs CIV (endpoint /v1/compare).",
        "page 3 : Prix alimentaires (filtres pays + commodité).",
        "page 4 : Inflation (évolution annuelle, graphique).",
        "page 5 : Méthodologie (formule risk score, sources de données).",
    ])
    p.retenir(
        "ttl=300 : le cache expire après 5 minutes. Raisonnable pour des données "
        "mensuelles. @st.cache_data sérialise les arguments en clé de cache : "
        "get_food_prices('SEN') et get_food_prices('CIV') ont des caches séparés. "
        "Ne jamais contourner l'API pour accéder directement à la DB depuis Streamlit."
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 4 — Jenkins CI/CD
    # ══════════════════════════════════════════════════════════════════════
    p.phase_header("Phase 4 — Jenkins CI/CD")

    p.section("4.1  Groupe 1 : Dockerfile Jenkins (image controller)")
    p.label("Ce qu'il faut construire :")
    p.body(
        "Jenkins LTS dans un conteneur. Le controller Jenkins doit pouvoir "
        "lancer des agents Docker et communiquer via le socket Docker. "
        "JCasC (Jenkins Configuration as Code) charge la config au démarrage."
    )
    p.code(
        "# jenkins/Dockerfile\n"
        "FROM jenkins/jenkins:lts-jdk17\n"
        "USER root\n"
        "\n"
        "# Docker CLI (socket /var/run/docker.sock monté en volume)\n"
        "RUN apt-get update && apt-get install -y \\\n"
        "    ca-certificates curl gnupg python3 python3-pip python3-venv \\\n"
        "    && install -m 0755 -d /etc/apt/keyrings \\\n"
        "    && curl -fsSL https://download.docker.com/linux/debian/gpg \\\n"
        "       | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \\\n"
        "    && echo \"deb [arch=$(dpkg --print-architecture) ...] \\\n"
        "       https://download.docker.com/linux/debian bookworm stable\" \\\n"
        "       | tee /etc/apt/sources.list.d/docker.list > /dev/null \\\n"
        "    && apt-get update && apt-get install -y docker-ce-cli \\\n"
        "    && rm -rf /var/lib/apt/lists/* \\\n"
        "    && groupadd -f docker && usermod -aG docker jenkins\n"
        "\n"
        "COPY plugins.txt /usr/share/jenkins/ref/plugins.txt\n"
        "RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt\n"
        "\n"
        "COPY casc.yaml /usr/share/jenkins/casc.yaml\n"
        "ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/casc.yaml\n"
        "USER jenkins"
    )
    p.code(
        "# jenkins/plugins.txt (8 plugins)\n"
        "git\n"
        "workflow-aggregator\n"
        "docker-workflow\n"
        "credentials-binding\n"
        "junit\n"
        "ansicolor\n"
        "configuration-as-code\n"
        "job-dsl"
    )
    p.retenir(
        "Le socket Docker /var/run/docker.sock est monté dans docker-compose.yml "
        "pour que Jenkins puisse lancer des conteneurs agents. "
        "usermod -aG docker jenkins : sans ça, Jenkins ne peut pas appeler docker. "
        "CASC_JENKINS_CONFIG : variable d'environnement qui dit à JCasC où lire sa config."
    )

    p.section("4.2  Groupe 2 : agent.Dockerfile + JCasC (casc.yaml)")
    p.label("Principe clé — deps baked dans l'image :")
    p.body(
        "L'agent Docker exécute les tests. Plutôt que d'installer les dépendances "
        "à chaque run du pipeline (lent, fragile), on les bake dans l'image "
        "au moment du build (make build-agent). Le pipeline n'installe rien."
    )
    p.code(
        "# jenkins/agent.Dockerfile\n"
        "FROM python:3.12-slim\n"
        "\n"
        "# git requis par Jenkins pour les opérations de workspace\n"
        "RUN apt-get update && apt-get install -y git \\\n"
        "    && rm -rf /var/lib/apt/lists/*\n"
        "\n"
        "# Dépendances baked -- pas de venv dans le pipeline\n"
        "COPY infra/airflow/requirements.txt /tmp/ingestion-requirements.txt\n"
        "COPY api/requirements.txt           /tmp/api-requirements.txt\n"
        "\n"
        "RUN pip install --no-cache-dir \\\n"
        "    -r /tmp/ingestion-requirements.txt \\\n"
        "    -r /tmp/api-requirements.txt \\\n"
        "    \"flake8==7.1.0\" \\\n"
        "    \"pre-commit\""
    )
    p.code(
        "# jenkins/casc.yaml\n"
        "jenkins:\n"
        "  securityRealm:\n"
        "    local:\n"
        "      allowsSignup: false\n"
        "      users:\n"
        "        - id: \"admin\"\n"
        "          password: \"${JENKINS_ADMIN_PASSWORD}\"\n"
        "  authorizationStrategy:\n"
        "    loggedInUsersCanDoAnything:\n"
        "      allowAnonymousRead: false\n"
        "\n"
        "credentials:\n"
        "  system:\n"
        "    domainCredentials:\n"
        "      - credentials:\n"
        "          - usernamePassword:\n"
        "              scope: GLOBAL\n"
        "              id: \"timescaledb-creds\"\n"
        "              username: \"${POSTGRES_USER}\"\n"
        "              password: \"${POSTGRES_PASSWORD}\""
    )
    p.retenir(
        "JCasC = Infrastructure as Code pour Jenkins. Les credentials ne sont jamais "
        "hardcodés dans casc.yaml -- ils viennent des variables d'env Docker Compose "
        "(${POSTGRES_USER}). withCredentials masque les secrets dans les logs Jenkins. "
        "Pas de Setup stage : les deps sont dans l'image, pas dans le pipeline."
    )

    p.section("4.3  Groupe 3 : Jenkinsfile (parallélisation, pollSCM, artefacts)")
    p.body(
        "Le Jenkinsfile définit le pipeline as code. agent none signifie que "
        "chaque stage déclare son propre agent. parallel {} exécute Lint et Test "
        "en même temps."
    )
    p.code(
        "// Jenkinsfile (structure principale)\n"
        "pipeline {\n"
        "    agent none     // pas d'agent global -- chaque stage le déclare\n"
        "\n"
        "    options {\n"
        "        ansiColor('xterm')        // couleurs dans les logs\n"
        "        timestamps()              // horodatage chaque ligne\n"
        "        timeout(time: 30, unit: 'MINUTES')  // kill si trop long\n"
        "    }\n"
        "\n"
        "    triggers { pollSCM('H/5 * * * *') }  // sondage toutes les 5 min\n"
        "\n"
        "    stages {\n"
        "        stage('Quality') {\n"
        "            parallel {\n"
        "                stage('Lint') {\n"
        "                    agent { docker { image 'sahel-agent:latest' } }\n"
        "                    // pas de network : Lint n'a pas besoin de la DB\n"
        "                }\n"
        "                stage('Test') {\n"
        "                    agent {\n"
        "                        docker {\n"
        "                            image   'sahel-agent:latest'\n"
        "                            network 'sahel-flow_sahel_net'  // nom Compose\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "        stage('Build') {\n"
        "            when { branch 'main' }  // uniquement sur main\n"
        "            agent any              // socket Docker sur le controller\n"
        "        }\n"
        "    }\n"
        "}"
    )
    p.bullets([
        "pollSCM('H/5 * * * *') : Jenkins sonde le repo toutes les 5 min. "
        "Le 'H' répartit la charge (hash du nom du job), pas pile à hh:00, hh:05...",
        "network 'sahel-flow_sahel_net' : Docker Compose préfixe les réseaux avec "
        "le nom du projet. Toujours vérifier avec docker network ls avant de coder.",
        "when { branch 'main' } : les branches feature ne buildent pas les images "
        "Docker (inutile, coûteux en stockage).",
        "post { always { junit } } : les résultats pytest sont publiés même si "
        "le test échoue.",
    ])
    p.retenir(
        "Trois commandes à connaître avant d'écrire du code Docker Compose : "
        "docker network ls, docker volume ls, docker ps --format '{{.Names}}'. "
        "Elles révèlent les vrais noms internes qui ne sont pas toujours évidents "
        "dans docker-compose.yml (préfixage automatique du nom de projet)."
    )

    p.section("4.4  Groupe 4 : Pre-commit hooks")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Pre-commit intercepte chaque git commit et exécute des vérifications "
        "automatiques. Si un hook échoue, le commit est bloqué. "
        "Les mêmes hooks tournent aussi dans le stage Lint du pipeline Jenkins."
    )
    p.code(
        "# .pre-commit-config.yaml\n"
        "repos:\n"
        "  - repo: https://github.com/pre-commit/pre-commit-hooks\n"
        "    rev: v4.6.0\n"
        "    hooks:\n"
        "      - id: trailing-whitespace    # espaces en fin de ligne\n"
        "      - id: end-of-file-fixer      # newline final manquant\n"
        "      - id: check-yaml             # YAML valide\n"
        "      - id: check-json             # JSON valide\n"
        "      - id: check-merge-conflict   # marqueurs <<< >>> ===\n"
        "      - id: no-commit-to-branch\n"
        "        args: [--branch, main]     # push direct sur main bloqué\n"
        "\n"
        "  - repo: https://github.com/PyCQA/flake8\n"
        "    rev: 7.1.0\n"
        "    hooks:\n"
        "      - id: flake8\n"
        "\n"
        "# black absent délibérément : formatter à activer dès le début\n"
        "# d'un nouveau projet, pas sur un projet existant (diff massif)."
    )
    p.body(
        "PRE_COMMIT_HOME=/tmp/pre-commit-cache dans le stage Jenkins Lint. "
        "Dans un conteneur Docker, le home par défaut peut ne pas être accessible "
        "en écriture. /tmp est toujours accessible."
    )
    p.retenir(
        "no-commit-to-branch(main) : protège la branche main des pushes accidentels "
        "en local. Le workflow normal : feature branch -> PR -> merge. "
        "En Jenkins, la syntaxe est PRE_COMMIT_HOME = '/tmp/pre-commit-cache' avec =, "
        "pas : (l'environnement Declarative Pipeline utilise = pas yaml)."
    )

    p.section("4.5  Groupe 5 : Shared Library + Multibranch Pipeline")
    p.label("Shared Library (vars/) :")
    p.body(
        "Une shared library Jenkins est un repo de code Groovy réutilisable. "
        "Le dossier vars/ contient des fonctions globales appelables dans n'importe "
        "quel Jenkinsfile. legacySCM(scm) charge la library depuis le checkout "
        "actuel -- zéro dépendance réseau externe."
    )
    p.code(
        "// vars/buildDockerImage.groovy\n"
        "def call(String imageName, String dockerfile, String context = '.') {\n"
        "    sh \"docker build -t ${imageName}:${env.BUILD_NUMBER} \\\\\"\n"
        "       + \"-f ${dockerfile} ${context}\"\n"
        "}\n"
        "\n"
        "// Jenkinsfile -- chargement de la library\n"
        "library identifier: 'sahel-flow@main',\n"
        "        retriever: legacySCM(scm)\n"
        "\n"
        "// usage dans le stage Build\n"
        "stage('Build') {\n"
        "    when { branch 'main' }\n"
        "    agent any\n"
        "    steps {\n"
        "        buildDockerImage('sahel-api',       'api/Dockerfile',            '.')\n"
        "        buildDockerImage('sahel-streamlit', 'apps/streamlit/Dockerfile', 'apps/streamlit/')\n"
        "    }\n"
        "}"
    )
    p.label("Multibranch Pipeline (casc.yaml) :")
    p.body(
        "Le job Multibranch scanne le repo et crée automatiquement un pipeline "
        "par branche. Chaque branche qui a un Jenkinsfile obtient son propre "
        "pipeline Jenkins. periodic(5) = scan toutes les 5 minutes."
    )
    p.code(
        "# jenkins/casc.yaml -- section jobs\n"
        "jobs:\n"
        "  - script: |\n"
        "      multibranchPipelineJob('sahel-flow') {\n"
        "        branchSources {\n"
        "          git {\n"
        "            id('sahel-flow-git')\n"
        "            remote('https://github.com/serignemodou85/sahel-flow.git')\n"
        "          }\n"
        "        }\n"
        "        factory {\n"
        "          workflowBranchProjectFactory {\n"
        "            scriptPath('Jenkinsfile')\n"
        "          }\n"
        "        }\n"
        "        orphanedItemStrategy {\n"
        "          discardOldItems { numToKeep(10) }\n"
        "        }\n"
        "        triggers { periodic(5) }\n"
        "      }"
    )
    p.retenir(
        "legacySCM(scm) vs GitHub remote : legacySCM charge vars/ depuis le "
        "workspace courant, sans appel réseau. Plus rapide et plus robuste "
        "(pas de token GitHub nécessaire, fonctionne offline). "
        "BUILD_NUMBER dans le tag Docker (sahel-api:42) : traçabilité immuable, "
        "chaque image est liée à un run Jenkins précis."
    )

    p.section("4.6  Synthèse : les décisions d'architecture Jenkins")
    p.bullets([
        "agent none global + agent docker par stage = moindre privilège réseau. "
        "Le stage Lint n'a pas accès à la DB (pas de network). "
        "Le stage Build a accès au socket Docker (agent any sur le controller).",
        "Deps baked dans l'image sahel-agent = pas de setup stage, "
        "pas d'installation réseau à chaque run. Plus rapide et reproductible.",
        "JCasC = Jenkins configuré comme code versionné. "
        "Reproductible : docker compose up donne toujours le même Jenkins.",
        "withCredentials masque les secrets dans les logs -- les variables "
        "POSTGRES_USER et POSTGRES_PASSWORD n'apparaissent jamais en clair.",
        "when { branch 'main' } = les branches feature ne buildent pas les images "
        "Docker, seule main le fait.",
        "parallel {} Quality = Lint et Test tournent en même temps. "
        "Le feedback est plus rapide.",
    ])
    p.code(
        "# Diagramme du pipeline\n"
        "#\n"
        "#  push / pollSCM(H/5)          Jenkins\n"
        "#         |\n"
        "#    +---------+\n"
        "#    | Quality |\n"
        "#    +----+----+\n"
        "#         |\n"
        "#  +------+------+\n"
        "#  |             |\n"
        "# Lint          Test\n"
        "# (agent        (agent\n"
        "# docker)       docker\n"
        "# flake8        + sahel_net)\n"
        "# pre-commit    pytest 28 tests\n"
        "#  |             |\n"
        "#  +------+------+\n"
        "#         |\n"
        "#      [ main ? ]\n"
        "#         |\n"
        "#       Build\n"
        "#    (agent any)\n"
        "#    docker build\n"
        "#    sahel-api:N\n"
        "#    sahel-streamlit:N"
    )
    p.retenir(
        "Le pipeline Jenkins traduit la boucle de feedback : chaque push est "
        "verifié automatiquement (qualité + tests) avant que le code atteigne main. "
        "La config (Dockerfile, plugins.txt, casc.yaml, Jenkinsfile) est dans le repo "
        "-- reproductible, versionné, reviewable comme tout autre code."
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 5 — Securite + Observabilite + Deploiement
    # ══════════════════════════════════════════════════════════════════════
    p.phase_header("Phase 5 — Securite + Observabilite + Deploiement (en cours)")

    # ── 5.1 Prometheus ────────────────────────────────────────────────────
    p.section("5.1  Prometheus (etape 33) : metriques RED sur l'API FastAPI")
    p.label("Ce qu'il faut comprendre :")
    p.body(
        "Prometheus collecte des metriques en 'scrappant' l'API toutes les 15s. "
        "prometheus-fastapi-instrumentator instrumente automatiquement FastAPI : "
        "il intercepte chaque requete et expose les compteurs au format OpenMetrics "
        "sur le endpoint /metrics (distinct du /v1/metrics JSON existant)."
    )
    p.code(
        "# api/app/main.py -- wiring Prometheus\n"
        "from prometheus_fastapi_instrumentator import Instrumentator\n"
        "\n"
        "Instrumentator(\n"
        "    should_group_status_codes=False,   # 200, 404, 500 -- pas 2xx, 4xx\n"
        "    excluded_handlers=[\"/metrics\"],   # evite auto-scrape\n"
        ").instrument(app).expose(app)           # ajoute GET /metrics\n"
        "\n"
        "# infra/prometheus/prometheus.yml\n"
        "scrape_configs:\n"
        "  - job_name: 'sahel-api'\n"
        "    static_configs:\n"
        "      - targets: ['api:8000']   # nom service Docker sur sahel_net\n"
        "    metrics_path: '/metrics'\n"
        "    scrape_interval: 15s"
    )
    p.label("Le pattern RED -- les 3 metriques suffisantes pour un service HTTP :")
    p.bullets([
        "Rate : sum(rate(http_requests_total[5m])) by (handler)  --> req/s par endpoint.",
        "Errors : sum(rate(http_requests_total{status_code=~'5..'}[5m])) by (handler).",
        "Duration P95 : histogram_quantile(0.95, sum(rate("
        "http_request_duration_seconds_bucket[5m])) by (handler, le)) * 1000  --> ms.",
    ])
    p.body(
        "Grafana dashboard api_performance.json (4 panels) : taux req/s, latence P95, "
        "erreurs 5xx, total par endpoint. La datasource Prometheus a un uid fixe "
        "'prometheus' -- reference dans le JSON du dashboard. "
        "Si l'uid change, tous les panels perdent leur source."
    )
    p.retenir(
        "should_group_status_codes=False : code exact dans la label (200, 404, 500). "
        "Avec True : groupes 2xx/4xx/5xx -- impossible de distinguer un 401 d'un 404. "
        "rate() = taux moyen sur la fenetre (stable pour les dashboards). "
        "irate() = taux instantane entre les 2 derniers points (pour les alertes). "
        "histogram_quantile() est une approximation -- sa precision depend des buckets."
    )

    p.sep()

    # ── 5.2 JWT Auth ──────────────────────────────────────────────────────
    p.section("5.2  JWT Auth (etape 34) : OAuth2 password grant + HS256")
    p.label("Le flow complet :")
    p.bullets([
        "Client : POST /v1/auth/token avec username + password (form-urlencoded).",
        "API : verifie credentials avec secrets.compare_digest, signe un JWT HS256 30 min.",
        "Client : stocke le token, envoie Authorization: Bearer <token> sur chaque requete.",
        "API : get_current_user() valide la signature, extrait le 'sub', autorise la route.",
    ])
    p.code(
        "# api/app/auth/service.py\n"
        "from jose import jwt, JWTError\n"
        "from fastapi.security import OAuth2PasswordBearer\n"
        "\n"
        "ALGORITHM = 'HS256'\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES = 30\n"
        "oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/v1/auth/token')\n"
        "\n"
        "def create_access_token(username: str) -> str:\n"
        "    expire = datetime.now(timezone.utc) + timedelta(minutes=30)\n"
        "    return jwt.encode(\n"
        "        {'sub': username, 'exp': expire},\n"
        "        get_settings().jwt_secret_key,\n"
        "        algorithm=ALGORITHM,\n"
        "    )\n"
        "\n"
        "def get_current_user(token: str = Depends(oauth2_scheme)) -> str:\n"
        "    try:\n"
        "        payload = jwt.decode(token, get_settings().jwt_secret_key,\n"
        "                             algorithms=[ALGORITHM])\n"
        "        username = payload.get('sub')\n"
        "        if username != get_settings().api_username:\n"
        "            raise HTTPException(401)\n"
        "    except JWTError:\n"
        "        raise HTTPException(401)\n"
        "    return username"
    )
    p.code(
        "# api/app/routers/auth.py -- endpoint qui delivre le token\n"
        "import secrets\n"
        "\n"
        "@router.post('/auth/token', response_model=Token)\n"
        "def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:\n"
        "    s = get_settings()\n"
        "    # compare_digest = temps constant (anti timing attack)\n"
        "    valid = (secrets.compare_digest(form_data.username, s.api_username)\n"
        "             and secrets.compare_digest(form_data.password, s.api_password))\n"
        "    if not valid:\n"
        "        raise HTTPException(401, detail='Identifiants incorrects')\n"
        "    return Token(\n"
        "        access_token=create_access_token(form_data.username),\n"
        "        token_type='bearer',\n"
        "    )\n"
        "\n"
        "# api/app/routers/food_prices.py -- protection au niveau router\n"
        "router = APIRouter(\n"
        "    tags=['food-prices'],\n"
        "    dependencies=[Depends(get_current_user)],  # toutes les routes protegees\n"
        ")"
    )
    p.label("Pourquoi router-level et non per-endpoint :")
    p.body(
        "Avec dependencies=[Depends(get_current_user)] sur l'APIRouter, chaque "
        "nouveau endpoint ajoute au router est automatiquement protege. "
        "Pas de risque d'oubli. La ligne de securite est declaree une seule fois."
    )
    p.label("Strategie de tests :")
    p.code(
        "# conftest.py -- fixture existante mise a jour\n"
        "app.dependency_overrides[get_current_user] = lambda: 'test-user'\n"
        "# -> les tests existants passent sans token (auth bypassee)\n"
        "\n"
        "# test_auth.py -- fixture sans override (teste vraiment l'auth)\n"
        "@pytest.fixture\n"
        "def raw_client():\n"
        "    with TestClient(app) as c:\n"
        "        yield c\n"
        "\n"
        "def test_protected_no_token(raw_client):\n"
        "    assert raw_client.get('/v1/food-prices?country=SEN').status_code == 401\n"
        "\n"
        "def test_login_returns_token(raw_client):\n"
        "    resp = raw_client.post('/v1/auth/token',\n"
        "        data={'username': 'admin', 'password': 'change_me_in_production'})\n"
        "    assert resp.status_code == 200\n"
        "    assert 'access_token' in resp.json()"
    )
    p.retenir(
        "secrets.compare_digest : compare en temps constant -- meme duree si "
        "le mot de passe est bon ou mauvais. Empeche les timing attacks "
        "(deviner le mot de passe en mesurant le temps de reponse). "
        "Pas de bcrypt ici : le password est deja en clair dans .env -- "
        "bcrypt ne protege que si la DB est compromise, pas le .env. "
        "sub (subject) = claim standard RFC 7519. Toujours mettre l'identifiant "
        "utilisateur dans 'sub', pas dans un champ custom."
    )

    # ── Page finale ───────────────────────────────────────────────────────
    p.add_page()
    p.set_y(90)
    p.set_fill_color(*NAVY)
    p.rect(0, 85, 210, 50, "F")
    p.set_fill_color(*PHASE_GOLD)
    p.rect(0, 85, 210, 1.5, "F")
    p.rect(0, 135, 210, 1.5, "F")

    p.set_y(100)
    p._f("B", 16)
    p.set_text_color(*WHITE)
    p.cell(0, 10, "33 tests en vert.", align="C",
           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p._f("I", 11)
    p.set_text_color(190, 215, 240)
    p.cell(0, 7, "Phase 5 en cours -- Render + Supabase (etape 35) a venir.",
           align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    p.set_y(150)
    p._f("", 9)
    p.set_text_color(*GRAY)
    p.cell(0, 6, "sahel-flow -- pipeline de sécurité alimentaire zone UEMOA (Sénégal, Côte d'Ivoire)",
           align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.cell(0, 6, "github.com/serignemodou85/sahel-flow",
           align="C")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pdf = SahelPDF()
    pdf.setup()
    build(pdf)
    out = os.path.join(os.path.dirname(__file__), "sahel-flow-notes.pdf")
    pdf.output(out)
    print(f"PDF genere : {out}")
