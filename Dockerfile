FROM python:3.10-slim-buster

# Instalación robusta de Chromium y sus dependencias
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    curl unzip gnupg ca-certificates \
    libnss3 libx11-6 fonts-liberation libatk-bridge2.0-0 libgtk-3-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN chmod +x start.sh

CMD sh -c 'echo "PORT is $PORT" && uvicorn app.main:app --host 0.0.0.0 --port $PORT'



