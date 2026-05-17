from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserOut, UserCreate, UserUpdate
from app.api.deps import get_current_user, get_admin_user
from app.api.auth import get_password_hash

router = APIRouter()

@router.get("/", response_model=List[UserOut])
async def read_residents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View all residents in the organization."""
    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    return result.scalars().all()

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_resident(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Add a new resident (Admin only)."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    new_user = User(
        **user_in.dict(exclude={"password"}),
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.patch("/{user_id}", response_model=UserOut)
@router.put("/{user_id}", response_model=UserOut)
async def update_resident(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Update a resident's details (Admin only)."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == admin_user.organization_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user
