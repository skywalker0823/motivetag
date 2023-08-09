pipeline{
    agent any
    stages{
        stage('check'){
            steps{
                echo 'Checking...'
                sh 'pwd'
                sh 'ls -la'
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
                sh 'docker-compose -f docker-compose.dev.yaml down'
                sh 'docker-compose -f docker-compose.dev.yaml up -d --build'
            }
        }
    }
}
