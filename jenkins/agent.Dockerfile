FROM python:3.12-slim

# git requis par Jenkins pour les opérations de workspace dans l'agent
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python — baked dans l'image, pas de venv dans le pipeline
# Contexte de build = racine du projet (make build-agent)
COPY infra/airflow/requirements.txt /tmp/ingestion-requirements.txt
COPY api/requirements.txt           /tmp/api-requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/ingestion-requirements.txt \
    -r /tmp/api-requirements.txt \
    "flake8==7.1.0" \
    "pre-commit"
