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
        stage('Pull'){
            steps{
                echo 'Pulling the code from the repository'
                dir ('/data/motivetag'){
                    git 'pull'
                }
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
                dir('/data/motivetag'){
                    sh 'docker-compose -f docker-compose.dev.yaml down'
                    sh 'docker-compose -f docker-compose.dev.yaml up -d --build'
                }
            }
        }
    }
}
