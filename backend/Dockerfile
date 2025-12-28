FROM python:3.12-slim as builder

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

# Устанавливаем только прод-зависимости (без dev)
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Генерируем requirements.txt из установленного окружения (надёжнее export)
RUN poetry run pip freeze > requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
