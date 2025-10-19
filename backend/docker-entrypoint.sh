#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# Устанавливаем PostgreSQL клиент
if ! command -v psql &> /dev/null; then
    apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
fi

# Ждем PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
for i in {1..60}; do
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "⏳ PostgreSQL not ready yet ($i/60)..."
    sleep 3
done

# Для runtime миграций - временно устанавливаем alembic
if [ "$APP_ENV" = "development" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Installing dev dependencies for migrations..."
    poetry install --only=dev --no-interaction

    echo "🔄 Running Alembic migrations..."
    poetry run alembic upgrade head || {
        echo "⚠️  Migration failed, but starting app anyway..."
    }
fi

echo "✅ Backend initialization complete!"
exec "$@"
