FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8000

# Worker count defaults to 3 (2 x 1 CPU + 1). Override via GUNICORN_WORKERS env var.
CMD ["sh", "-c", "gunicorn Hello.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3}"]