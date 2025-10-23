import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_users
from app.config import logger
from app.models import User
from app.schemas.error_codes import JellyfinErrorCode
from app.schemas.jellyfin import JellyfinUsersResponse
from app.schemas.responses import ErrorDetail


async def import_jellyfin_users(session: AsyncSession) -> JellyfinUsersResponse:
    """Imports users from Radarr into the database with logging."""
    try:
        users = await fetch_jellyfin_users()
    except httpx.RequestError as e:
        logger.error("Network error fetching Jellyfin users: %s", str(e))
        raise HTTPException(
            status_code=502,
            detail=ErrorDetail(
                code=JellyfinErrorCode.NETWORK_ERROR,
                message=f"Network error: {e!s}",
            ).model_dump(),
        ) from e
    except Exception as e:
        logger.error("Failed to fetch users from Jellyfin: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=ErrorDetail(
                code=JellyfinErrorCode.JELLYFIN_FETCH_FAILED,
                message=f"Failed to fetch users: {e!s}",
            ).model_dump(),
        ) from e

    imported = 0
    updated = 0

    for u in users:
        user_id = u.get("Id")
        user_name = u.get("Name")

        if not user_id:
            logger.warning("Skipping user without Jellyfin user ID: %s", u.get("Name"))
            continue

        query = select(User).where(User.jellyfin_user_id == user_id)
        result = await session.execute(query)
        user = result.scalars().first()

        try:
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
                    continue

            await session.commit()

        except Exception as e:
            logger.error(
                "Failed to insert user from jellyfin '%s' into the database: %s", user_name, e
            )
            await session.rollback()
            continue

    logger.info(f"Imported {imported}, updated {updated} users from Jellyfin")
    return JellyfinUsersResponse(status="success", imported_count=imported, updated_count=updated)
