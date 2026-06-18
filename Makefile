.PHONY: up down logs ps build db-only fernet-key build-agent build-jenkins pre-commit-install

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

## Construit l'image agent Docker Jenkins — prérequis au premier lancement CI
## À exécuter une fois après clone, ou quand jenkins/agent.Dockerfile change
build-agent:
	docker build -t sahel-agent:latest -f jenkins/agent.Dockerfile .

## Rebuild l'image Jenkins controller — nécessaire si plugins.txt ou casc.yaml change
build-jenkins:
	docker compose build jenkins

## Installe le hook pre-commit dans .git/hooks/pre-commit (à faire une fois après clone)
pre-commit-install:
	pre-commit install
