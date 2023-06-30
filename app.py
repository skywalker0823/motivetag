from api import create_app, socketio

app = create_app("dev")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)

# The AWS_motivetag_DB in .env should be changed to current database

# local test docker for mysql
# docker run -dp 3306:3306 --name a_mysql -e MYSQL_ROOT_PASSWORD=123123 mysql:8
# python3 database/build.py

# local development
# python3 app.py

# Start server
# docker build -t motivetag .  
# docker run -dp 3000:3000 --name motivetag motivetag  

# Start server with docker-compose
# docker-compose up --build -d
# Open 127.0.0.1
# docker-compose down