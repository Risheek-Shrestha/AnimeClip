#!/usr/bin/env bash
# scripts/backup_db.sh — daily PostgreSQL backup to a local directory.
#
# Usage (manual):
#   DB_NAME=animeclip DB_USER=animeclip DB_PASSWORD=secret ./scripts/backup_db.sh
#
# Usage (cron — runs at 02:00 every day):
#   0 2 * * * /app/scripts/backup_db.sh >> /var/log/animeclip-backup.log 2>&1
#
# Usage (Docker Compose — add to docker-compose.yml):
#   backup:
#     image: postgres:16-alpine
#     restart: unless-stopped
#     env_file: .env
#     volumes:
#       - ./backups:/backups
#       - ./scripts:/scripts:ro
#     depends_on:
#       db:
#         condition: service_healthy
#     entrypoint: ["sh", "-c", "crond -f -d 8 & sh /scripts/backup_db.sh"]
#
# The script keeps the last KEEP_DAYS worth of dumps and deletes older files.
# For off-site storage, pipe BACKUP_DIR to an S3 bucket via aws-cli or rclone.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_NAME="${DB_NAME:?DB_NAME must be set}"
DB_USER="${DB_USER:?DB_USER must be set}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
KEEP_DAYS="${KEEP_DAYS:-7}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup of ${DB_NAME} → ${FILENAME}"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --no-password \
    --format=plain \
    "${DB_NAME}" \
  | gzip > "${FILENAME}"

echo "[$(date)] Backup complete: ${FILENAME} ($(du -sh "${FILENAME}" | cut -f1))"

# Remove backups older than KEEP_DAYS days
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime "+${KEEP_DAYS}" -print -delete
echo "[$(date)] Pruned backups older than ${KEEP_DAYS} days"
