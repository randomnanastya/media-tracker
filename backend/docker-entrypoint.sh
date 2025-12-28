#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# Ждём базу бесконечно (или долго) — контейнер не упадёт
echo "⏳ Waiting for PostgreSQL to be ready..."
while ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1; do
    echo "⏳ PostgreSQL not ready yet... sleeping 5s"
    sleep 5
done
echo "✅ PostgreSQL is ready!"

# Всегда применяем миграции
echo "🔄 Running Alembic migrations..."
if alembic upgrade head; then
    echo "✅ All migrations applied successfully"
else
    echo "⚠️ Some migrations failed — starting app anyway"
fi

echo "✅ Backend initialization complete!"

# Запуск приложения
exec "$@"
