from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import Organization, User, UserRole
from app.schemas.schemas import OrganizationOut, OrganizationCreate, UserOut, UserCreate
from app.api.auth import get_password_hash
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()

@router.get("/", response_model=List[OrganizationOut])
async def read_organizations(db: AsyncSession = Depends(get_db)):
    """Get all organizations (useful for signup)."""
    result = await db.execute(select(Organization))
    return result.scalars().all()

@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(org_in: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    """Create a new organization."""
    new_org = Organization(**org_in.dict())
    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)
    return new_org

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Signup a new user to an organization."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")
        
    org_result = await db.execute(select(Organization).where(Organization.id == user_in.organization_id))
    if not org_result.scalars().first():
        raise HTTPException(status_code=404, detail="Organization not found")
        
    new_user = User(
        **user_in.dict(exclude={"password"}),
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
