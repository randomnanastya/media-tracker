from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_users
from app.config import logger
from app.models import ServiceType, User
from app.schemas.jellyfin import JellyfinUsersResponse
from app.services.service_config_repository import get_decrypted_config


async def import_jellyfin_users(session: AsyncSession) -> JellyfinUsersResponse:
    """Imports users from Jellyfin into the database with logging."""
    config = await get_decrypted_config(session, ServiceType.JELLYFIN)
    if config is None:
        logger.info("Jellyfin is not configured, skipping import")
        return JellyfinUsersResponse(status="skipped", imported_count=0, updated_count=0)
    url, api_key = config
    users = await fetch_jellyfin_users(url, api_key)
    imported = 0
    updated = 0

    try:
        for u in users:
            user_id = u.get("Id")
            user_name = u.get("Name")

            if not user_id:
                logger.warning("Skipping user without Jellyfin user ID: %s", u.get("Name"))
                continue

            if not isinstance(user_name, str):
                logger.warning(
                    "Skipping user with invalid name type: %s (jellyfin_user_id: %s)",
                    type(user_name),
                    user_id,
                )
                continue

            query = select(User).where(User.jellyfin_user_id == user_id)
            result = await session.execute(query)
            user = result.scalars().first()

            if user is None:
                user_obj = User(
                    username=user_name,
                    jellyfin_user_id=user_id,
                )
                session.add(user_obj)
                await session.flush()
                logger.info("Added new user: %s (jellyfin_user_id: %s)", user_name, user_id)
                imported += 1

            else:
                if user.username != user_name:
                    user.username = user_name
                    session.add(user)
                    await session.flush()
                    logger.info(
                        "Updated username for jellyfin_user_id %s: %s -> %s",
                        user_id,
                        user.username,
                        user_name,
                    )
                    updated += 1
                else:
                    logger.debug(
                        "User %s (jellyfin_user_id: %s) already up-to-date", user_name, user_id
                    )

        await session.commit()
        logger.info(f"Imported {imported}, updated {updated} users from Jellyfin")
        return JellyfinUsersResponse(
            status="success", imported_count=imported, updated_count=updated
        )

    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise
