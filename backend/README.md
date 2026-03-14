# Media Tracker Backend

This is the backend part of the Media Tracker project.

Авторизация

Архитектура аутентификации

  Токены

  - Access JWT (15 мин, stateless) — для каждого запроса
  - Refresh Token (30 дней, opaque) — хранится как SHA-256 хэш в БД, ротируется при каждом обновлении

  Модели БД

  - AppUser — отдельная от существующего User (Jellyfin). Поля: username, hashed_password, recovery_code_hash, email (опц.)
  - RefreshToken — для per-session revocation

  First-time setup

  - GET /auth/status → {setup_required: bool}
  - Если пользователей нет → POST /auth/register открыт, иначе → 403

  Восстановление пароля (без SMTP)

  Основной путь — Recovery Code:
  1. При регистрации генерируется код формата XXXXX-XXXXX-XXXXX-XXXXX (bcrypt в БД)
  2. Показывается один раз в ответе — пользователь обязан сохранить
  3. POST /auth/reset-password { recovery_code, new_password } → сбрасывает пароль и возвращает новый recovery code
  4. GET /auth/recovery-code (с авторизацией) — сгенерировать новый код (инвалидирует старый)

  Резервный путь — CLI:
  docker exec media-tracker python -m app.cli reset-password --new-password newpass123
  Для случая, когда потеряны и пароль, и recovery code.

  Опциональный SMTP:
  Если все SMTP_* переменные заданы → дополнительно доступен email reset. Не обязателен.

  Добавление ключа для авторизации
  В env добавьте сгенерированный ключ HS256
  Сгенерировать ключ можно командой
  ```shell
   python -c "import secrets; print(secrets.token_hex(32))"
  ```
  В env добавляем:
  - JWT_SECRET=<random-256-bit-key-run: python -c "import secrets; print(secrets.token_hex(32))">
  - JWT_ALGORITHM=HS256
  - ACCESS_TOKEN_EXPIRE_MINUTES=15
  - REFRESH_TOKEN_EXPIRE_DAYS=30

👉 See the main [README.md](../README.md) for overall project info.
