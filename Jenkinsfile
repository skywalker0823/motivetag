pipeline{
    agent any
    stages{
        stage('check'){
            steps{
                sh '''
                    echo 'Checking the app'
                    docker info
                    docker compose version
                    git status
                '''
            }
        }
        stage('Test'){
            steps{
                echo 'Testing the app'
                sh 'docker exec -it a_flask bash -c "pytest"'
            }
        }
        stage('Deploy'){
            steps{
                echo 'Deploying the app'
                sh 'docker compose -f docker-compose.dev.yaml down'
                sh 'docker compose -f docker-compose.dev.yaml up -d --build'
            }
        }
    }
}
