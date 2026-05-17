from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.models import User, Shift
from app.schemas.schemas import ShiftOut, ShiftCreate, ShiftUpdate
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()

@router.get("/", response_model=List[ShiftOut])
async def read_shifts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View all shifts for the organization."""
    result = await db.execute(
        select(Shift)
        .where(Shift.organization_id == current_user.organization_id)
        .options(selectinload(Shift.assigned_residents))
    )
    return result.scalars().all()

@router.post("/", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
async def create_shift(
    shift_in: ShiftCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Create a new shift (Admin only)."""
    new_shift = Shift(**shift_in.dict())
    db.add(new_shift)
    await db.commit()
    await db.refresh(new_shift)
    return new_shift

@router.patch("/{shift_id}", response_model=ShiftOut)
@router.put("/{shift_id}", response_model=ShiftOut)
async def update_shift(
    shift_id: UUID,
    shift_in: ShiftUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Update a shift (e.g., lock it or change date) (Admin only)."""
    result = await db.execute(
        select(Shift)
        .where(Shift.id == shift_id, Shift.organization_id == admin_user.organization_id)
    )
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    update_data = shift_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shift, field, value)
    
    await db.commit()
    await db.refresh(shift)
    return shift

@router.put("/{shift_id}/assign", response_model=ShiftOut)
async def assign_residents(
    shift_id: UUID,
    resident_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Manually assign/unassign residents to a shift (Admin only)."""
    result = await db.execute(
        select(Shift)
        .where(Shift.id == shift_id, Shift.organization_id == admin_user.organization_id)
        .options(selectinload(Shift.assigned_residents))
    )
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Fetch residents by IDs that belong to the same organization
    residents_result = await db.execute(
        select(User).where(
            User.id.in_(resident_ids), 
            User.organization_id == admin_user.organization_id
        )
    )
    residents = residents_result.scalars().all()
    
    shift.assigned_residents = residents
    await db.commit()
    await db.refresh(shift)
    return shift

