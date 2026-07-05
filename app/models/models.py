import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Enum, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Association Tables for M2M relationships
shift_assignments = Table(
    "shift_assignments",
    Base.metadata,
    Column("shift_id", ForeignKey("shifts.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), # Changed resident_id to user_id
)

night_float_users = Table(
    "night_float_users",
    Base.metadata,
    Column("night_float_id", ForeignKey("night_floats.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), # Changed resident_id to user_id
)

class UserRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class ShiftType(enum.Enum):
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    HOLIDAY = "holiday"

class RuleType(enum.Enum):
    MUST = "must"
    TRY = "try"

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    shifts: Mapped[List["Shift"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    scheduling_rules: Mapped[List["SchedulingRule"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    night_floats: Mapped[List["NightFloat"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    
    name: Mapped[str] = mapped_column(String(255))
    pgy: Mapped[int] = mapped_column(Integer)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="users")
    day_off_requests: Mapped[List["DayOffRequest"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vacations: Mapped[List["Vacation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    shifts: Mapped[List["Shift"]] = relationship(
        secondary=shift_assignments, back_populates="assigned_residents"
    )
    night_floats: Mapped[List["NightFloat"]] = relationship(
        secondary=night_float_users, back_populates="users"
    )

class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime) # Changed from Date to DateTime for consistency and updated_at tracking
    type: Mapped[ShiftType] = mapped_column(Enum(ShiftType))
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="shifts")
    assigned_residents: Mapped[List["User"]] = relationship(
        secondary=shift_assignments, back_populates="shifts"
    )

class DayOffRequest(Base):
    __tablename__ = "day_off_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="day_off_requests")

class Vacation(Base):
    __tablename__ = "vacations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="vacations")

class NightFloat(Base):
    __tablename__ = "night_floats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    block_start: Mapped[datetime] = mapped_column(DateTime)
    block_end: Mapped[datetime] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="night_floats")
    users: Mapped[List["User"]] = relationship(
        secondary=night_float_users, back_populates="night_floats"
    )

class SchedulingRule(Base):
    __tablename__ = "scheduling_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String)
    type: Mapped[RuleType] = mapped_column(Enum(RuleType))
    priority: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="scheduling_rules")
