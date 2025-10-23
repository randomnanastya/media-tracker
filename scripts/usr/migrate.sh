#!/bin/bash
sudo docker compose -f docker-compose.dev.yaml exec backend poetry run alembic revision --autogenerate -m "$1"
sudo docker compose -f docker-compose.dev.yaml exec backend poetry run alembic upgrade head
# Исправить права после миграции
sudo find backend/migrations/ -name "*.py" -exec chown $USER:$USER {} \;
sudo find backend/migrations/ -name "*.py" -exec chmod 664 {} \;
sudo find backend/migrations/ -type d -exec chmod 775 {} \;
