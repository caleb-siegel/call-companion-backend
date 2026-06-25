import asyncio
from sqlalchemy import text
from app.database import engine
from app.api.auth import get_password_hash

async def main():
    password = "password123"
    hashed = get_password_hash(password)
    async with engine.connect() as conn:
        # Update caleb.siegel@gmail.com
        await conn.execute(
            text("UPDATE users SET hashed_password = :hashed WHERE email = :email"),
            {"hashed": hashed, "email": "caleb.siegel@gmail.com"}
        )
        # Update tova.niderberg@hmhn.org
        await conn.execute(
            text("UPDATE users SET hashed_password = :hashed WHERE email = :email"),
            {"hashed": hashed, "email": "tova.niderberg@hmhn.org"}
        )
        await conn.commit()
    print("Passwords successfully reset to 'password123'")

if __name__ == "__main__":
    asyncio.run(main())
