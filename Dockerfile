FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8000

# Healthcheck so container orchestrators can detect a broken startup.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:8000/healthz/ || exit 1

# Worker count defaults to 3 (2 × 1 CPU + 1). Override via GUNICORN_WORKERS env var.
# Uses gthread worker class (I/O-friendly) with 2 threads per worker.
# --max-requests recycles workers to prevent memory leaks; jitter spreads restarts.
# Run collectstatic and migrate before starting so the app is always up-to-date.
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn Hello.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --worker-class gthread --threads 2 --timeout 60 --max-requests 1000 --max-requests-jitter 100 --preload --access-logfile -"]