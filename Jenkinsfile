pipeline {
    agent any

    options {
        ansiColor('xterm')
        timestamps()
    }

    // POSTGRES_USER et POSTGRES_PASSWORD viennent de l'environment du container Jenkins
    // (docker-compose jenkins.environment) — injectés automatiquement dans les sh steps.
    environment {
        PYTHONPATH = "${WORKSPACE}:${WORKSPACE}/api"
        POSTGRES_HOST = "timescaledb"
        POSTGRES_DB   = "sahel_flow"
        POSTGRES_PORT = "5432"
    }

    stages {

        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/pip install --quiet --upgrade pip
                    .venv/bin/pip install --quiet -r infra/airflow/requirements.txt
                    .venv/bin/pip install --quiet -r api/requirements.txt
                    .venv/bin/pip install --quiet "flake8==7.1.0"
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    .venv/bin/flake8 ingestion/ api/ shared/ dags/ apps/
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    mkdir -p reports
                    .venv/bin/pytest ingestion/tests/ api/tests/ \
                        -v --tb=short \
                        --junitxml=reports/junit.xml
                '''
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Build') {
            steps {
                // Contexte racine pour l'API (accès à shared/)
                sh 'docker build -t sahel-api:${BUILD_NUMBER} -f api/Dockerfile .'
                // Contexte apps/streamlit/ (Dockerfile relatif)
                sh 'docker build -t sahel-streamlit:${BUILD_NUMBER} -f apps/streamlit/Dockerfile apps/streamlit/'
            }
        }
    }

    post {
        success {
            echo "Pipeline réussi — build #${BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline échoué — consultez les logs ci-dessus"
        }
    }
}
