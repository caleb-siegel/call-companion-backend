import asyncio
import uuid
from sqlalchemy.future import select
from app.database import SessionLocal
from app.models.models import User, UserRole
from app.api.auth import get_password_hash

async def main():
    org_id = uuid.UUID("e84b4a57-e802-4042-a088-e1736753daaa")
    password = "password123"
    hashed = get_password_hash(password)
    
    residents_data = [
        # PGY 1
        {"name": "Lamine Yamal", "email": "lamine.yamal@stjude.org", "pgy": 1},
        {"name": "Jude Bellingham", "email": "jude.bellingham@stjude.org", "pgy": 1},
        {"name": "Folarin Balogun", "email": "folarin.balogun@stjude.org", "pgy": 1},
        {"name": "Michael Olise", "email": "michael.olise@stjude.org", "pgy": 1},
        # PGY 2
        {"name": "Erling Haaland", "email": "erling.haaland@stjude.org", "pgy": 2},
        {"name": "Vinicius Jr", "email": "vinicius.jr@stjude.org", "pgy": 2},
        {"name": "Kylian Mbappe", "email": "kylian.mbappe@stjude.org", "pgy": 2},
        {"name": "Ousmane Dembele", "email": "ousmane.dembele@stjude.org", "pgy": 2},
        # PGY 3
        {"name": "Harry Kane", "email": "harry.kane@stjude.org", "pgy": 3},
        {"name": "Bukayo Saka", "email": "bukayo.saka@stjude.org", "pgy": 3},
        {"name": "Antoine Griezmann", "email": "antoine.griezmann@stjude.org", "pgy": 3},
        {"name": "Kevin De Bruyne", "email": "kevin.debruyne@stjude.org", "pgy": 3},
        # PGY 4
        {"name": "Lionel Messi", "email": "lionel.messi@stjude.org", "pgy": 4},
        {"name": "Cristiano Ronaldo", "email": "cristiano.ronaldo@stjude.org", "pgy": 4},
        {"name": "Luka Modric", "email": "luka.modric@stjude.org", "pgy": 4},
        {"name": "Karim Benzema", "email": "karim.benzema@stjude.org", "pgy": 4},
    ]

    async with SessionLocal() as db:
        # First, delete existing seeded users with the stjude.org domain to ensure idempotency
        delete_emails = [r["email"] for r in residents_data]
        
        # We find these users first
        result = await db.execute(
            select(User).where(User.organization_id == org_id, User.email.in_(delete_emails))
        )
        existing_users = result.scalars().all()
        for u in existing_users:
            await db.delete(u)
        
        if existing_users:
            print(f"Deleted {len(existing_users)} existing seeded users.")
            await db.commit()
            
        # Add new users
        new_users = []
        for r in residents_data:
            user = User(
                id=uuid.uuid4(),
                email=r["email"],
                hashed_password=hashed,
                name=r["name"],
                pgy=r["pgy"],
                role=UserRole.MEMBER,
                organization_id=org_id
            )
            db.add(user)
            new_users.append(user)
            
        await db.commit()
        print(f"Successfully seeded {len(new_users)} residents in organization {org_id}.")
        for u in new_users:
            print(f"  Added PGY-{u.pgy}: {u.name} ({u.email})")

if __name__ == "__main__":
    asyncio.run(main())
