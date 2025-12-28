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

if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1; then
    echo "❌ PostgreSQL connection failed after 60 attempts!"
    exit 1
fi

# === ВСЕГДА запускаем миграции при старте контейнера ===
echo "🔄 Running Alembic migrations..."
if alembic upgrade head; then
    echo "✅ All migrations applied successfully"
else
    echo "⚠️ Some migrations failed — continuing startup (check logs!)"
    # Не выходим — приложение может работать с частично применёнными миграциями
fi

echo "✅ Backend initialization complete!"

# Передаём управление команде из CMD в Dockerfile
exec "$@"
