# media-tracker

## How to Run

1. Pull the Docker image: `docker pull ghcr.io/randomnanastya/media-tracker:vX.Y.Z`
2. Use the provided `docker-compose.yml`:
   ```bash
   docker-compose up -d

3. Configure `.env` with your Jellyfin API key, PostgreSQL credentials, etc. (example in `.env.example`)

### Important: `APP_ENV` and cookie security

Set `APP_ENV=production` only if the app is served over **HTTPS**. With this value, auth cookies are set with the `Secure` flag — browsers will not store or send them over plain HTTP, so login will silently fail.

| Access | `APP_ENV` value |
|--------|----------------|
| HTTPS (recommended) | `production` |
| HTTP (local / internal network) | `development` |

Check the latest release on [GitHub Releases](https://github.com/randomnanastya/media-tracker/releases)
