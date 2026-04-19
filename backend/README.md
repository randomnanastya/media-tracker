# Media Tracker — Backend

FastAPI backend for the Media Tracker project. Collects data from Jellyfin, Radarr, and Sonarr, stores it in PostgreSQL, and exposes a REST API consumed by the frontend.

See the main [README.md](../README.md) for deployment instructions.

## API Reference

Interactive docs (Swagger UI) are available at:

```
http://<your-host>:<APP_PORT>/docs
```

ReDoc alternative:

```
http://<your-host>:<APP_PORT>/redoc
```

## Authentication

- **Access token** — JWT, 15 min lifetime, stateless, sent with every request
- **Refresh token** — opaque, 30-day lifetime, stored as SHA-256 hash in DB, rotated on each use

### First-time setup

```
GET /api/v1/auth/status  →  { "setup_required": true/false }
```

If no users exist, `POST /api/v1/auth/register` is open. Once an account is created it returns 403.

### Password recovery

Primary path — recovery code (no email required):

1. A code in the format `XXXXX-XXXXX-XXXXX-XXXXX` is generated at registration
2. It is shown once in the response — save it
3. `POST /api/v1/auth/reset-password { "recovery_code": "...", "new_password": "..." }` resets the password and returns a new recovery code
4. `GET /api/v1/auth/recovery-code` (authenticated) — generate a new code, invalidates the old one

Fallback — CLI (when both password and recovery code are lost):

```bash
docker exec media-backend python -m app.cli reset-password --new-password newpass123
```

### JWT secret

Generate a secret key for signing tokens:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Required env variables:

```
JWT_SECRET=<generated-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```
