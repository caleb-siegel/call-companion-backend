import enum
import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import String, Integer, Date, Boolean, ForeignKey, Enum, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

# Association Tables for M2M relationships
shift_assignments = Table(
    "shift_assignments",
    Base.metadata,
    Column("shift_id", ForeignKey("shifts.id", ondelete="CASCADE"), primary_key=True),
    Column("resident_id", ForeignKey("residents.id", ondelete="CASCADE"), primary_key=True),
)

night_float_residents = Table(
    "night_float_residents",
    Base.metadata,
    Column("night_float_id", ForeignKey("night_floats.id", ondelete="CASCADE"), primary_key=True),
    Column("resident_id", ForeignKey("residents.id", ondelete="CASCADE"), primary_key=True),
)

class ShiftType(enum.Enum):
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class RuleType(enum.Enum):
    MUST = "must"
    TRY = "try"

class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    pgy: Mapped[int] = mapped_column(Integer)

    # Relationships
    day_off_requests: Mapped[List["DayOffRequest"]] = relationship(back_populates="resident", cascade="all, delete-orphan")
    vacations: Mapped[List["Vacation"]] = relationship(back_populates="resident", cascade="all, delete-orphan")
    shifts: Mapped[List["Shift"]] = relationship(
        secondary=shift_assignments, back_populates="assigned_residents"
    )
    night_floats: Mapped[List["NightFloat"]] = relationship(
        secondary=night_float_residents, back_populates="residents"
    )

class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[ShiftType] = mapped_column(Enum(ShiftType))
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    assigned_residents: Mapped[List["Resident"]] = relationship(
        secondary=shift_assignments, back_populates="shifts"
    )

class DayOffRequest(Base):
    __tablename__ = "day_off_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("residents.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)

    # Relationships
    resident: Mapped["Resident"] = relationship(back_populates="day_off_requests")

class Vacation(Base):
    __tablename__ = "vacations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("residents.id", ondelete="CASCADE"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    # Relationships
    resident: Mapped["Resident"] = relationship(back_populates="vacations")

class NightFloat(Base):
    __tablename__ = "night_floats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    block_start: Mapped[date] = mapped_column(Date)
    block_end: Mapped[date] = mapped_column(Date)

    # Relationships
    residents: Mapped[List["Resident"]] = relationship(
        secondary=night_float_residents, back_populates="night_floats"
    )

class SchedulingRule(Base):
    __tablename__ = "scheduling_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(String)
    type: Mapped[RuleType] = mapped_column(Enum(RuleType))
    priority: Mapped[int] = mapped_column(Integer, default=0)
