pipeline{
    agent any
    stages{
        stage('Pull'){
            steps{
                echo 'Pulling the code from the repository'
                cd '/data/motivetag'
                git 'pull'
            }
        }
        stage('Test'){
            steps{
                echo 'Testing the app'
            }
        }
        stage('Deploy'){
            steps{
                echo 'Deploying the app'
                cd '/data/motivetag'
                sh 'docker compose -f docker-compose.dev.yaml down'
                sh 'docker compose -f docker-compose.dev.yaml up -d --build'
            }
        }
    }
}
