from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── Database ──────────────────────────────────────────────────────────────
    # "timescaledb" = nom du service Docker, résolu automatiquement sur sahel_net.
    # En dehors de Docker (tests locaux), passer POSTGRES_HOST=localhost.
    postgres_host:     str = "timescaledb"
    postgres_port:     int = 5432
    postgres_db:       str = "sahel_flow"
    postgres_user:     str = "sahel"
    postgres_password: str = "sahel_secret"

    # ── APIs sources ──────────────────────────────────────────────────────────
    wb_api_base_url:  str = "https://api.worldbank.org/v2"
    wfp_api_base_url: str = "https://api.wfpvam.org/v2"

    # WFP Data Bridges requiert un token Bearer.
    # Laisser vide en dev tant que le token n'est pas obtenu.
    # Inscription : https://api.wfpvam.org (voir .env.example)
    wfp_api_key: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    app_env:   str = "development"
    log_level: str = "INFO"

    # ── URL assemblée ─────────────────────────────────────────────────────────
    # Property plutôt que champ : calculée à la demande, jamais stockée en clair.
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # POSTGRES_HOST et postgres_host = même clé
    )


@lru_cache
def get_settings() -> Settings:
    # @lru_cache : l'objet Settings est créé une seule fois par processus.
    # Les appels suivants retournent l'instance en cache sans relire .env.
    return Settings()
