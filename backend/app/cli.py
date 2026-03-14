"""Emergency CLI password reset.

Usage:
    python -m app.cli reset-password --new-password <new_password>

Docker:
    docker exec media-tracker python -m app.cli reset-password --new-password newpass123
"""

import argparse
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import AppUser
from app.utils.security import generate_recovery_code, hash_password, hash_token


async def reset_password_cli(new_password: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AppUser).order_by(AppUser.id).limit(1))
        user = result.scalar_one_or_none()
        if user is None:
            print("Error: no AppUser found in database")
            return
        user.hashed_password = hash_password(new_password)
        new_code = generate_recovery_code()
        user.recovery_code_hash = hash_token(new_code)
        await session.commit()
        print(f"Password reset for user '{user.username}'")
        print(f"New recovery code: {new_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Media Tracker CLI")
    subparsers = parser.add_subparsers(dest="command")
    reset_cmd = subparsers.add_parser("reset-password")
    reset_cmd.add_argument("--new-password", required=True)
    args = parser.parse_args()
    if args.command == "reset-password":
        asyncio.run(reset_password_cli(args.new_password))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
