FROM eclipse-temurin:8-jre-jammy

WORKDIR /app

# Python
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install fastapi uvicorn

# DUK
COPY duk /app/duk

ENV DUK_PATH=/app/duk/dist/DUKIntegrator.jar

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]