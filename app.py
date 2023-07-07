from api import create_app, socketio

app = create_app("dev")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000, debug=False)

# The AWS_motivetag_DB in .env should be changed to current database

# local test docker for mysql
# docker run -dp 3306:3306 --name a_mysql_local -e MYSQL_ROOT_PASSWORD=yourDBpassword mysql:8
# python3 database/build.py

# local development
# gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -b 0.0.0.0:3000 -w 1 app:app

# Start server
# docker build -t motivetag .  
# docker run -dp 3000:3000 --name motivetag motivetag  

# Start server with docker-compose
# docker-compose up --build -d(Production)
# docker-compose -f docker-compose.dev.yaml up -d --build(Development)
# Open localhost on browser(sometimes need to wait for mysql and flask to start completely)
# docker-compose down
