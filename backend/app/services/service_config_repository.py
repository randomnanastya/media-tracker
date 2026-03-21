"""Repository for ServiceConfig CRUD operations."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ServiceConfig, ServiceType
from app.utils.encryption import decrypt_api_key, encrypt_api_key


async def get_all_configs(session: AsyncSession) -> list[ServiceConfig]:
    """Get all service configs."""
    result = await session.execute(select(ServiceConfig))
    return list(result.scalars().all())


async def get_config_by_service(
    session: AsyncSession, service_type: ServiceType
) -> ServiceConfig | None:
    """Get config for a specific service."""
    result = await session.execute(
        select(ServiceConfig).where(ServiceConfig.service_type == service_type)
    )
    return result.scalar_one_or_none()


async def get_decrypted_config(
    session: AsyncSession, service_type: ServiceType
) -> tuple[str, str] | None:
    """Get url and decrypted api_key for a service. Returns None if not configured."""
    config = await get_config_by_service(session, service_type)
    if config is None:
        return None
    return config.url, decrypt_api_key(config.encrypted_api_key)


async def upsert_config(
    session: AsyncSession,
    service_type: ServiceType,
    url: str,
    api_key: str,
) -> ServiceConfig:
    """Create or update a service config. API key is encrypted before storing."""
    config = await get_config_by_service(session, service_type)
    encrypted = encrypt_api_key(api_key)

    if config is None:
        config = ServiceConfig(
            service_type=service_type,
            url=url.rstrip("/"),
            encrypted_api_key=encrypted,
        )
        session.add(config)
    else:
        config.url = url.rstrip("/")
        config.encrypted_api_key = encrypted

    await session.flush()
    return config


async def delete_config(session: AsyncSession, service_type: ServiceType) -> bool:
    """Delete a service config. Returns True if deleted, False if not found."""
    result = await session.execute(
        delete(ServiceConfig).where(ServiceConfig.service_type == service_type)
    )
    await session.flush()
    return bool(result.rowcount > 0)
