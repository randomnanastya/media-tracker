#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# Install postgresql-client if not present
if ! command -v psql &> /dev/null; then
    apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
fi

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

# Run migrations in prod or if explicitly enabled
if [ "$APP_ENV" = "development" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running Alembic migrations..."
    poetry run alembic upgrade head || {
        echo "⚠️ Migration failed, but starting app anyway..."
    }
fi

echo "✅ Backend initialization complete!"
exec "$@"
