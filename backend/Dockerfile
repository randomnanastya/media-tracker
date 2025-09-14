FROM python:3.12-slim

# Устанавливаем poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Копируем зависимости
COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-root --no-interaction --no-ansi

# Копируем приложение
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]