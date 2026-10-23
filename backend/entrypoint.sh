#!/usr/bin/env bash
set -e

echo "Running database migrations..."
for i in {1..10}; do
    if alembic upgrade head; then
        echo "Migrations applied successfully."
        break
    else
        echo "Migration attempt $i failed. Retrying in 2 seconds..."
        sleep 2
    fi
    if [ "$i" -eq 10 ]; then
        echo "Failed to apply migrations after 10 attempts."
        exit 1
    fi
done

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
