pipeline {
    agent none

    options {
        ansiColor('xterm')
        timestamps()
        timeout(time: 30, unit: 'MINUTES')   // protège contre les builds bloqués
    }

    // Polling SCM toutes les ~5 min — se déclenche automatiquement sur commit détecté
    triggers {
        pollSCM('H/5 * * * *')
    }

    // Constantes sans dépendance au workspace — sûres à pipeline-level avec agent none.
    // POSTGRES_USER + POSTGRES_PASSWORD viennent de withCredentials (stage Test).
    environment {
        POSTGRES_HOST = "timescaledb"
        POSTGRES_DB   = "sahel_flow"
        POSTGRES_PORT = "5432"
    }

    stages {

        // Lint et Test sont indépendants — ils tournent simultanément après checkout.
        // Les deps sont dans l'image sahel-agent:latest (baked via make build-agent).
        // Pas de stage Setup : pas de venv, pas d'install à la volée.
        stage('Quality') {
            parallel {

                stage('Lint') {
                    // Pas de socket, pas de réseau — isolation maximale
                    agent { docker { image 'sahel-agent:latest' } }
                    environment {
                        // Dirige le cache pre-commit vers /tmp — writable sans problème de permissions.
                        // Ne persiste pas entre builds (container éphémère) — acceptable en portfolio.
                        // En prod : monter un volume cache dédié pour éviter les téléchargements répétés.
                        PRE_COMMIT_HOME = '/tmp/pre-commit-cache'
                    }
                    steps {
                        sh 'pre-commit run --all-files'
                    }
                }

                stage('Test') {
                    agent {
                        docker {
                            image   'sahel-agent:latest'
                            // Nom réel du réseau Docker Compose : {projet}_{réseau}
                            // "sahel-flow" = nom du répertoire racine (COMPOSE_PROJECT_NAME)
                            // Pas de socket — uniquement l'accès réseau à timescaledb:5432
                            network 'sahel-flow_sahel_net'
                        }
                    }
                    steps {
                        withCredentials([usernamePassword(
                            credentialsId: 'timescaledb-creds',
                            usernameVariable: 'POSTGRES_USER',
                            passwordVariable: 'POSTGRES_PASSWORD'
                        )]) {
                            sh '''
                                mkdir -p reports
                                PYTHONPATH="${WORKSPACE}:${WORKSPACE}/api" \
                                pytest ingestion/tests/ api/tests/ \
                                    -v --tb=short \
                                    --junitxml=reports/junit.xml
                            '''
                        }
                    }
                    post {
                        always {
                            // Publie les résultats dans l'UI Jenkins (courbes de tendance par build)
                            junit 'reports/junit.xml'
                        }
                    }
                }

            }
        }

        stage('Build') {
            // agent any = controller Jenkins — socket Docker disponible via volume mount
            agent any
            steps {
                sh 'docker build -t sahel-api:${BUILD_NUMBER} -f api/Dockerfile .'
                sh 'docker build -t sahel-streamlit:${BUILD_NUMBER} -f apps/streamlit/Dockerfile apps/streamlit/'
            }
        }
    }

    post {
        always {
            // Le workspace est physiquement sur le controller — accessible depuis le post pipeline-level
            archiveArtifacts artifacts: 'reports/junit.xml', allowEmptyArchive: true
        }
        success {
            echo "Pipeline réussi — build #${BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline échoué — consultez les logs ci-dessus"
        }
    }
}
