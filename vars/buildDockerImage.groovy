/**
 * Construit une image Docker et la tague avec BUILD_NUMBER.
 *
 * @param imageName  Nom de l'image (ex: 'sahel-api')
 * @param dockerfile Chemin vers le Dockerfile (ex: 'api/Dockerfile')
 * @param context    Contexte de build Docker (défaut: '.')
 */
def call(String imageName, String dockerfile, String context = '.') {
    sh "docker build -t ${imageName}:${env.BUILD_NUMBER} -f ${dockerfile} ${context}"
}
