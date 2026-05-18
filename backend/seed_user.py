import asyncio
import uuid
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Must import app.db.base first so ALL models are registered with SQLAlchemy mapper
import app.db.base  # noqa: F401
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed():
    async with SessionLocal() as db:
        # Check if exists
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        existing = result.scalars().first()
        if existing:
            print("User admin@example.com already exists.")
            return

        user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)
        await db.commit()
        print("Test user admin@example.com created with password 'password123'!")

if __name__ == "__main__":
    asyncio.run(seed())
