FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    curl unzip gnupg ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN chmod +x start.sh

# ESTA LÍNEA FINAL ES LA CLAVE:
CMD sh -c 'echo "PORT is $PORT" && uvicorn app.main:app --host 0.0.0.0 --port $PORT'


