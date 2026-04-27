#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL..."
until python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')" 2>/dev/null; do
  sleep 1
done
echo "==> PostgreSQL ready."

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting server..."
exec "$@"
