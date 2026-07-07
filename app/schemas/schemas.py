from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.models import UserRole, ShiftType, RuleType

# Shared Base
class TimestampModel(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User / Resident
class UserBase(BaseModel):
    email: EmailStr
    name: str
    pgy: int
    role: UserRole = UserRole.MEMBER

class UserCreate(UserBase):
    password: str
    organization_id: UUID

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    pgy: Optional[int] = None
    role: Optional[UserRole] = None

class UserOut(UserBase, TimestampModel):
    id: UUID
    organization_id: UUID
    google_connected: bool
    google_calendar_id: Optional[str] = None

# Organization
class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase, TimestampModel):
    id: UUID

# Shift
class ShiftBase(BaseModel):
    date: datetime
    type: ShiftType
    locked: bool = False
    note: Optional[str] = None

class ShiftCreate(ShiftBase):
    organization_id: UUID

class ShiftUpdate(BaseModel):
    date: Optional[datetime] = None
    type: Optional[ShiftType] = None
    locked: Optional[bool] = None
    note: Optional[str] = None

class ShiftOut(ShiftBase, TimestampModel):
    id: UUID
    organization_id: UUID
    assigned_residents: List[UserOut]

class ShiftBulkItem(BaseModel):
    id: Optional[str] = None
    date: datetime
    type: ShiftType
    locked: bool = False
    assignedResidentIds: List[UUID]
    note: Optional[str] = None

# Scheduling Rule
class SchedulingRuleBase(BaseModel):
    text: str
    type: RuleType
    priority: int = 0

class SchedulingRuleCreate(SchedulingRuleBase):
    id: Optional[UUID] = None
    organization_id: Optional[UUID] = None

class SchedulingRuleOut(SchedulingRuleBase, TimestampModel):
    id: UUID
    organization_id: UUID

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    email: Optional[str] = None

# Constraints
class DayOffRequestBase(BaseModel):
    date: datetime
    description: Optional[str] = None

class DayOffRequestCreate(DayOffRequestBase):
    user_id: Optional[UUID] = None

class DayOffRequestOut(DayOffRequestBase, TimestampModel):
    id: UUID
    user_id: UUID

class VacationBase(BaseModel):
    start_date: datetime
    end_date: datetime

class VacationCreate(VacationBase):
    user_id: Optional[UUID] = None

class VacationOut(VacationBase, TimestampModel):
    id: UUID
    user_id: UUID

class NightFloatBase(BaseModel):
    block_start: datetime
    block_end: datetime

class NightFloatCreate(NightFloatBase):
    organization_id: Optional[UUID] = None
    resident_ids: List[UUID]

class NightFloatOut(NightFloatBase, TimestampModel):
    id: UUID
    organization_id: UUID
    users: List[UserOut]
