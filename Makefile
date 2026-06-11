.PHONY: up down logs ps build db-only fernet-key

## Démarre tous les services (build si l'image n'existe pas)
up:
	docker compose up -d

## Démarre uniquement TimescaleDB — pour l'étape 1 du développement
db-only:
	docker compose up -d timescaledb

## Arrête et supprime les containers (volumes conservés)
down:
	docker compose down

## Arrête et supprime containers + volumes (reset complet — DESTRUCTIF)
down-v:
	docker compose down -v

## Rebuild les images Airflow après modification de infra/airflow/
build:
	docker compose build airflow-init airflow-webserver airflow-scheduler

## Logs en temps réel de tous les services (Ctrl+C pour quitter)
logs:
	docker compose logs -f

## Logs d'un service spécifique : make logs-s SERVICE=timescaledb
logs-s:
	docker compose logs -f $(SERVICE)

## État des containers
ps:
	docker compose ps

## Génère une clé Fernet pour Airflow (à copier dans .env)
fernet-key:
	python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
