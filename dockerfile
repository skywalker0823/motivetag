FROM --platform=linux/amd64 python:3.9

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["gunicorn","-k","geventwebsocket.gunicorn.workers.GeventWebSocketWorker","-b", "0.0.0.0:3000", "-w", "1" ,"app:app" ]

# Multi-Stage Build
# FROM --platform=arm64 python:3.9 as builder

# RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels gunicorn

# FROM --platform=arm64 python:3.9-slim

# COPY --from=builder /wheels /wheels

# RUN pip install --no-cache /wheels/*

# COPY ./requirements.txt /app/requirements.txt

# WORKDIR /app

# ENTRYPOINT ["gunicorn","-k","geventwebsocket.gunicorn.workers.GeventWebSocketWorker","-b", "0.0.0.0:3000", "-w", "1" ,"app:app" ]