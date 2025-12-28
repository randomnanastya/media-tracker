#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
for i in {1..60}; do
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "⏳ PostgreSQL not ready yet ($i/60)..."
    sleep 3
done

# Run migrations in development or if explicitly enabled
if [ "$APP_ENV" = "development" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running Alembic migrations..."
    alembic upgrade head || {
        echo "⚠️ Migration failed, but starting app anyway..."
    }
fi

echo "✅ Backend initialization complete!"

# Запуск приложения — передаём управление CMD из Dockerfile
exec "$@"
