"""
Admin user seeder.

Reads credentials from environment variables (set in .env) and inserts a
default admin user into the database if one does not already exist.
This script is designed to run inside Docker after migrations complete.

Usage:
    python -m app.seeds.seed_admin
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked with `python -m`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.domain.models.user import User


async def seed_admin() -> None:
    """Create the default admin user if it doesn't already exist."""

    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        print("[seed] ADMIN_EMAIL / ADMIN_PASSWORD not set – skipping admin seed.")
        return

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # Check if this email already exists
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[seed] Admin user '{settings.ADMIN_EMAIL}' already exists – skipping.")
            return

        admin = User(
            first_name=settings.ADMIN_FIRST_NAME,
            last_name=settings.ADMIN_LAST_NAME,
            email=settings.ADMIN_EMAIL,
            phone=settings.ADMIN_PHONE,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            role="business",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"[seed] Admin user '{settings.ADMIN_EMAIL}' created successfully (role=business).")


if __name__ == "__main__":
    asyncio.run(seed_admin())
