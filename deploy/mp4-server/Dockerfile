FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -e ".[web]"

EXPOSE 8080

CMD ["uvicorn", "video2ascii.services.mp4_api:app", "--host", "0.0.0.0", "--port", "8080"]
