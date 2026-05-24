from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_jellyfin_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.username))
    return list(result.scalars().all())
