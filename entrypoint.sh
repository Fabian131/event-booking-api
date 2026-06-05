#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Running database seeders..."
python -m app.seeds.seed_admin
echo "Seeders complete."

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
