#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

# Проверка обязательных переменных
: "${POSTGRES_HOST:?Error: POSTGRES_HOST is not set}"
: "${POSTGRES_USER:?Error: POSTGRES_USER is not set}"
: "${POSTGRES_PASSWORD:?Error: POSTGRES_PASSWORD is not set}"
: "${POSTGRES_DB:?Error: POSTGRES_DB is not set}"

POSTGRES_PORT=${POSTGRES_PORT:-5432}

# Ждём базу
echo "⏳ Waiting for PostgreSQL ($POSTGRES_HOST:$POSTGRES_PORT)..."
while ! PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1; do
    echo "⏳ PostgreSQL not ready yet... sleeping 5s"
    sleep 5
done
echo "✅ PostgreSQL is ready!"

# Миграции
echo "🔄 Running Alembic migrations..."
if alembic upgrade head; then
    echo "✅ All migrations applied successfully"
else
    echo "⚠️ Some migrations failed — starting app anyway"
fi

echo "✅ Backend initialization complete!"
exec "$@"
