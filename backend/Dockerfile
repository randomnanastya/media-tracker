# Используем официальный образ Python
FROM python:3.12-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем только файлы с зависимостями
COPY pyproject.toml poetry.lock* ./

# Обновляем pip и устанавливаем Poetry
RUN pip install --upgrade pip \
    && pip install poetry

# Устанавливаем только prod-зависимости
RUN poetry install --no-root --no-dev

# Копируем код приложения
COPY . /app

# Устанавливаем Gunicorn для продакшена
RUN pip install gunicorn uvicorn

# Указываем команду запуска
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "4"]
