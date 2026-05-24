from pydantic import BaseModel


class JellyfinUserResponse(BaseModel):
    id: int
    username: str
    jellyfin_user_id: str | None
