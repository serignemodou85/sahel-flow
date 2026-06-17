pipeline {
    agent none   // chaque stage déclare son propre agent

    options {
        ansiColor('xterm')
        timestamps()
    }

    // Constantes sans dépendance au workspace — sûres à pipeline-level avec agent none.
    // POSTGRES_USER + POSTGRES_PASSWORD viennent de withCredentials dans le stage Test.
    environment {
        POSTGRES_HOST = "timescaledb"
        POSTGRES_DB   = "sahel_flow"
        POSTGRES_PORT = "5432"
    }

    stages {

        stage('Setup') {
            agent { docker { image 'sahel-agent:latest' } }
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
            // Pas de socket — l'isolation est totale, flake8 n'a besoin d'aucun daemon
            agent { docker { image 'sahel-agent:latest' } }
            steps {
                sh '.venv/bin/flake8 ingestion/ api/ shared/ dags/ apps/'
            }
        }

        stage('Test') {
            agent {
                docker {
                    image 'sahel-agent:latest'
                    // sahel_net : accès à timescaledb. Pas de socket — pas de docker build ici.
                    args  '--network sahel_net'
                }
            }
            steps {
                // Credentials injectés depuis Jenkins (JCasC) — masqués dans les logs
                withCredentials([usernamePassword(
                    credentialsId: 'timescaledb-creds',
                    usernameVariable: 'POSTGRES_USER',
                    passwordVariable: 'POSTGRES_PASSWORD'
                )]) {
                    sh '''
                        mkdir -p reports
                        PYTHONPATH="${WORKSPACE}:${WORKSPACE}/api" \
                        .venv/bin/pytest ingestion/tests/ api/tests/ \
                            -v --tb=short \
                            --junitxml=reports/junit.xml
                    '''
                }
            }
            post {
                always {
                    // Publie les résultats dans l'UI Jenkins même si des tests échouent
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Build') {
            // agent any = controller Jenkins — accès au socket Docker via volume mount
            agent any
            steps {
                sh 'docker build -t sahel-api:${BUILD_NUMBER} -f api/Dockerfile .'
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
