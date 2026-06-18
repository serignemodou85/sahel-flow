// Charge vars/ depuis le même checkout que ce Jenkinsfile.
// legacySCM(scm) = même SCM que le job courant — zéro dépendance réseau externe.
// La version '@main' est ignorée quand legacySCM est utilisé : c'est le workspace
// courant qui est lu, quelle que soit la branche buildée.
library identifier: 'sahel-flow@main',
        retriever: legacySCM(scm)

pipeline {
    agent none

    options {
        ansiColor('xterm')
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        POSTGRES_HOST = "timescaledb"
        POSTGRES_DB   = "sahel_flow"
        POSTGRES_PORT = "5432"
    }

    stages {

        stage('Quality') {
            parallel {

                stage('Lint') {
                    agent { docker { image 'sahel-agent:latest' } }
                    environment {
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
                            junit 'reports/junit.xml'
                        }
                    }
                }

            }
        }

        // Build uniquement sur main — les images Docker des branches feature
        // ne seront jamais déployées, les builder serait du gaspillage.
        stage('Build') {
            when { branch 'main' }
            agent any
            steps {
                buildDockerImage('sahel-api',       'api/Dockerfile',            '.')
                buildDockerImage('sahel-streamlit', 'apps/streamlit/Dockerfile', 'apps/streamlit/')
            }
        }

    }

    post {
        always {
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
