FROM --platform=linux/amd64 python:3.9

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["gunicorn","-k","geventwebsocket.gunicorn.workers.GeventWebSocketWorker","-b", "0.0.0.0:3000", "-w", "1" ,"app:app" ]