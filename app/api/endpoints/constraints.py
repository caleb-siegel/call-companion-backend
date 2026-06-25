from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import User, DayOffRequest, Vacation, NightFloat, UserRole
from app.schemas.schemas import DayOffRequestOut, DayOffRequestCreate, VacationOut, VacationCreate, NightFloatOut, NightFloatCreate
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()

# --- Day Off Requests ---

@router.get("/day-off-requests", response_model=List[DayOffRequestOut])
async def read_day_off_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View day off requests (members only see their own, admins see all)."""
    if current_user.role != UserRole.ADMIN:
        result = await db.execute(
            select(DayOffRequest)
            .where(DayOffRequest.user_id == current_user.id)
        )
    else:
        result = await db.execute(
            select(DayOffRequest)
            .join(User)
            .where(User.organization_id == current_user.organization_id)
        )
    return result.scalars().all()

@router.post("/day-off-requests", response_model=DayOffRequestOut, status_code=status.HTTP_201_CREATED)
async def create_day_off_request(
    request_in: DayOffRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_user_id = current_user.id
    if request_in.user_id and current_user.role == UserRole.ADMIN:
        target_user_id = request_in.user_id
    elif request_in.user_id and request_in.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Regular members can only create day-off requests for themselves."
        )
        
    # Enforce limit of 1 request per month
    from datetime import datetime
    import calendar
    
    req_year = request_in.date.year
    req_month = request_in.date.month
    start_date = datetime(req_year, req_month, 1)
    last_day = calendar.monthrange(req_year, req_month)[1]
    end_date = datetime(req_year, req_month, last_day, 23, 59, 59)
    
    existing_result = await db.execute(
        select(DayOffRequest).where(
            DayOffRequest.user_id == target_user_id,
            DayOffRequest.date >= start_date,
            DayOffRequest.date <= end_date
        )
    )
    existing_req = existing_result.scalars().first()
    if existing_req:
        existing_date_str = existing_req.date.strftime("%B %d, %Y")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has a day-off request for {existing_date_str}. Only 1 request is allowed per month."
        )
        
    new_req = DayOffRequest(
        date=request_in.date,
        description=request_in.description,
        user_id=target_user_id
    )
    db.add(new_req)
    await db.commit()
    await db.refresh(new_req)
    return new_req

@router.delete("/day-off-requests/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_day_off_request(
    req_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a day off request (must be owner or admin)."""
    result = await db.execute(select(DayOffRequest).where(DayOffRequest.id == req_id))
    req = result.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough privileges")
        
    await db.delete(req)
    await db.commit()
    return None

# --- Vacations ---

@router.get("/vacations", response_model=List[VacationOut])
async def read_vacations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Vacation)
        .join(User)
        .where(User.organization_id == current_user.organization_id)
    )
    return result.scalars().all()

@router.post("/vacations", response_model=VacationOut, status_code=status.HTTP_201_CREATED)
async def create_vacation(
    vacation_in: VacationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_user_id = current_user.id
    if vacation_in.user_id and current_user.role == UserRole.ADMIN:
        target_user_id = vacation_in.user_id
        
    new_vac = Vacation(
        start_date=vacation_in.start_date,
        end_date=vacation_in.end_date,
        user_id=target_user_id
    )
    db.add(new_vac)
    await db.commit()
    await db.refresh(new_vac)
    return new_vac

@router.delete("/vacations/{vac_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacation(
    vac_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Vacation).where(Vacation.id == vac_id))
    vac = result.scalars().first()
    if not vac:
        raise HTTPException(status_code=404, detail="Vacation not found")
    if vac.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    await db.delete(vac)
    await db.commit()
    return None

# --- Night Floats ---

@router.get("/night-floats", response_model=List[NightFloatOut])
async def read_night_floats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(NightFloat)
        .where(NightFloat.organization_id == current_user.organization_id)
        .options(selectinload(NightFloat.users))
    )
    return result.scalars().all()

@router.post("/night-floats", response_model=NightFloatOut, status_code=status.HTTP_201_CREATED)
async def create_night_float(
    nf_in: NightFloatCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    users_result = await db.execute(select(User).where(User.id.in_(nf_in.resident_ids)))
    users = users_result.scalars().all()
    
    new_nf = NightFloat(
        organization_id=admin_user.organization_id,
        block_start=nf_in.block_start,
        block_end=nf_in.block_end,
        users=users
    )
    db.add(new_nf)
    await db.commit()
    await db.refresh(new_nf)
    
    # Must explicitly load users to return NightFloatOut correctly if not eager loaded by default
    result = await db.execute(
        select(NightFloat)
        .where(NightFloat.id == new_nf.id)
        .options(selectinload(NightFloat.users))
    )
    return result.scalars().first()

@router.delete("/night-floats/{nf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_night_float(
    nf_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(NightFloat)
        .where(NightFloat.id == nf_id, NightFloat.organization_id == admin_user.organization_id)
    )
    nf = result.scalars().first()
    if not nf:
        raise HTTPException(status_code=404, detail="Night float not found")
    await db.delete(nf)
    await db.commit()
    return None
