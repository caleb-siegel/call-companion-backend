from typing import List
from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.models import User, Shift
from app.schemas.schemas import ShiftOut, ShiftCreate, ShiftUpdate, ShiftBulkItem
from app.api.deps import get_current_user, get_admin_user
from app.services.google_calendar import sync_user_shifts_to_google

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
    
    # Eagerly load the relationship before serializing to avoid MissingGreenlet error
    result = await db.execute(
        select(Shift)
        .where(Shift.id == new_shift.id)
        .options(selectinload(Shift.assigned_residents))
    )
    return result.scalars().first()

@router.put("/bulk", response_model=List[ShiftOut])
async def bulk_save_shifts(
    shifts_in: List[ShiftBulkItem],
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Bulk save (create or update) shifts and their resident assignments (Admin only)."""
    # Fetch all existing shifts for this organization
    result = await db.execute(
        select(Shift)
        .where(Shift.organization_id == admin_user.organization_id)
        .options(selectinload(Shift.assigned_residents))
    )
    existing_shifts = result.scalars().all()
    
    # Map existing shifts by (date.date(), type) to match
    existing_map = {}
    for s in existing_shifts:
        existing_map[(s.date.date(), s.type)] = s

    # Gather all resident IDs mentioned in the request
    all_resident_ids = set()
    for s_in in shifts_in:
        all_resident_ids.update(s_in.assignedResidentIds)
    
    residents = {}
    if all_resident_ids:
        residents_result = await db.execute(
            select(User).where(
                User.id.in_(list(all_resident_ids)),
                User.organization_id == admin_user.organization_id
            )
        )
        residents = {r.id: r for r in residents_result.scalars().all()}

    saved_shifts = []
    for s_in in shifts_in:
        normalized_date = s_in.date.date()
        shift_key = (normalized_date, s_in.type)
        assigned = [residents[rid] for rid in s_in.assignedResidentIds if rid in residents]
        
        if shift_key in existing_map:
            shift = existing_map[shift_key]
            shift.locked = s_in.locked
            shift.assigned_residents = assigned
            shift.note = s_in.note
        else:
            shift = Shift(
                organization_id=admin_user.organization_id,
                date=s_in.date,
                type=s_in.type,
                locked=s_in.locked,
                assigned_residents=assigned,
                note=s_in.note
            )
            db.add(shift)
            
        saved_shifts.append(shift)
        
    # Delete any existing shifts within the published date range that are not in the payload (deleted custom shifts)
    if shifts_in:
        min_date = min(s.date for s in shifts_in)
        max_date = max(s.date for s in shifts_in)
        incoming_keys = {(s.date.date(), s.type) for s in shifts_in}
        
        for s in existing_shifts:
            if min_date <= s.date <= max_date:
                if (s.date.date(), s.type) not in incoming_keys:
                    await db.delete(s)

    await db.commit()
    
    # Sync Google Calendars for affected users
    if shifts_in:
        min_date = min(s.date for s in shifts_in)
        max_date = max(s.date for s in shifts_in)
        
        affected_user_ids = set()
        for s_in in shifts_in:
            affected_user_ids.update(s_in.assignedResidentIds)
        for s in existing_shifts:
            if min_date <= s.date <= max_date:
                for r in s.assigned_residents:
                    affected_user_ids.add(r.id)

        if affected_user_ids:
            users_res = await db.execute(
                select(User).where(User.id.in_(list(affected_user_ids)))
            )
            users_to_sync = users_res.scalars().all()
            for user in users_to_sync:
                if user.google_calendar_id:
                    user_shifts_res = await db.execute(
                        select(Shift)
                        .join(Shift.assigned_residents)
                        .where(
                            User.id == user.id,
                            Shift.date >= min_date,
                            Shift.date <= max_date
                        )
                    )
                    user_shifts = user_shifts_res.scalars().all()
                    try:
                        await sync_user_shifts_to_google(user, user_shifts, min_date, max_date, db)
                    except Exception as e:
                        print(f"Error syncing Google Calendar for user {user.id}: {e}")
    
    # Query all the saved shifts back with relationship eagerly loaded to prevent MissingGreenlet errors during serialization
    saved_ids = [s.id for s in saved_shifts]
    final_result = await db.execute(
        select(Shift)
        .where(Shift.id.in_(saved_ids))
        .options(selectinload(Shift.assigned_residents))
    )
    return final_result.scalars().all()

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
        .options(selectinload(Shift.assigned_residents))
    )
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    update_data = shift_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shift, field, value)
    
    await db.commit()
    
    # Eagerly load the relationship before serializing to avoid MissingGreenlet error
    final_result = await db.execute(
        select(Shift)
        .where(Shift.id == shift.id)
        .options(selectinload(Shift.assigned_residents))
    )
    return final_result.scalars().first()

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
    
    previous_residents = list(shift.assigned_residents)
    
    shift.assigned_residents = residents
    await db.commit()
    await db.refresh(shift)
    
    # Sync both previous and new residents
    affected_users = set(previous_residents + residents)
    for user in affected_users:
        if user.google_calendar_id:
            start_of_month = shift.date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_of_month.month == 12:
                end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1) - timedelta(days=1)
            else:
                end_of_month = start_of_month.replace(month=start_of_month.month + 1) - timedelta(days=1)
                
            user_shifts_res = await db.execute(
                select(Shift)
                .join(Shift.assigned_residents)
                .where(
                    User.id == user.id,
                    Shift.date >= start_of_month,
                    Shift.date <= end_of_month
                )
            )
            user_shifts = user_shifts_res.scalars().all()
            try:
                await sync_user_shifts_to_google(user, user_shifts, start_of_month, end_of_month, db)
            except Exception as e:
                print(f"Error syncing Google Calendar for user {user.id}: {e}")
                
    return shift

@router.delete("", response_model=dict)
async def delete_all_shifts(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Delete all shifts for the current organization (Admin only)."""
    await db.execute(
        delete(Shift).where(Shift.organization_id == admin_user.organization_id)
    )
    await db.commit()
    return {"message": "All shifts successfully deleted"}

@router.delete("/{shift_id}", response_model=dict)
async def delete_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Delete a single shift (Admin only)."""
    result = await db.execute(
        select(Shift)
        .where(Shift.id == shift_id, Shift.organization_id == admin_user.organization_id)
        .options(selectinload(Shift.assigned_residents))
    )
    shift = result.scalars().first()
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    
    assigned_residents = list(shift.assigned_residents)
    shift_date = shift.date
    
    await db.delete(shift)
    await db.commit()
    
    # Sync Google Calendars for the affected residents
    for user in assigned_residents:
        if user.google_calendar_id:
            start_of_month = shift_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_of_month.month == 12:
                end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1) - timedelta(days=1)
            else:
                end_of_month = start_of_month.replace(month=start_of_month.month + 1) - timedelta(days=1)
                
            user_shifts_res = await db.execute(
                select(Shift)
                .join(Shift.assigned_residents)
                .where(
                    User.id == user.id,
                    Shift.date >= start_of_month,
                    Shift.date <= end_of_month
                )
            )
            user_shifts = user_shifts_res.scalars().all()
            try:
                await sync_user_shifts_to_google(user, user_shifts, start_of_month, end_of_month, db)
            except Exception as e:
                print(f"Error syncing Google Calendar for user {user.id}: {e}")
                
    return {"message": "Shift successfully deleted"}



