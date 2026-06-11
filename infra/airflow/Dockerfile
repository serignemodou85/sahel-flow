FROM apache/airflow:2.9.2-python3.11

# On installe en tant qu'utilisateur "airflow" (non-root) — bonne pratique de sécurité
USER airflow

# Copie le fichier requirements dans un répertoire temporaire
COPY infra/airflow/requirements.txt /tmp/requirements.txt

# Installation sans cache pour garder l'image légère
RUN pip install --no-cache-dir -r /tmp/requirements.txt
