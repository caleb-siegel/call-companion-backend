import asyncio
from sqlalchemy import text
from app.database import engine
from app.api.auth import get_password_hash

async def main():
    password = "password123"
    hashed = get_password_hash(password)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("UPDATE users SET hashed_password = :hashed"),
            {"hashed": hashed}
        )
        await conn.commit()
        print(f"Successfully reset {result.rowcount} users' passwords to 'password123'")

if __name__ == "__main__":
    asyncio.run(main())
