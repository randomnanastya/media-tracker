#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# База уже должна быть готова благодаря depends_on: service_healthy
# Но на всякий случай делаем одну проверку (если что-то пошло не так)
echo "🔍 Checking PostgreSQL connection..."
if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1; then
    echo "❌ PostgreSQL is not available! Check db container logs."
    exit 1
fi
echo "✅ PostgreSQL is ready!"

# Всегда применяем миграции
echo "🔄 Running Alembic migrations..."
if alembic upgrade head; then
    echo "✅ All migrations applied successfully"
else
    echo "⚠️ Some migrations failed — starting app anyway (check logs!)"
fi

echo "✅ Backend initialization complete!"

# Запуск приложения
exec "$@"
