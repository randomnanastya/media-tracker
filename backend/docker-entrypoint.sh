#!/bin/bash
set -e

echo "=== Starting FastAPI backend initialization ==="

: "${POSTGRES_HOST:?}"
: "${POSTGRES_PORT:?}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_DB:?}"

echo "⏳ Waiting for PostgreSQL via asyncpg..."

python - <<'PY'
import asyncio
import asyncpg
import os
import sys

async def wait_db():
    dsn = (
        f"postgresql://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@"
        f"{os.environ['POSTGRES_HOST']}:"
        f"{os.environ['POSTGRES_PORT']}/"
        f"{os.environ['POSTGRES_DB']}"
    )

    for i in range(60):
        try:
            conn = await asyncpg.connect(dsn, timeout=5)
            await conn.close()
            print("✅ PostgreSQL is ready!")
            return
        except Exception as e:
            print(f"⏳ PostgreSQL not ready ({i+1}/60): {e}")
            await asyncio.sleep(3)

    print("❌ PostgreSQL is not available after timeout")
    sys.exit(1)

asyncio.run(wait_db())
PY

if [ "$APP_ENV" = "development" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running Alembic migrations..."
    alembic upgrade head || echo "⚠️ Migration failed, starting app anyway"
fi

echo "✅ Backend initialization complete!"
exec "$@"
