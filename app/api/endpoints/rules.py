from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.models import User, SchedulingRule
from app.schemas.schemas import SchedulingRuleOut, SchedulingRuleCreate
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()

@router.get("/", response_model=List[SchedulingRuleOut])
async def read_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View all scheduling rules for the organization."""
    result = await db.execute(
        select(SchedulingRule).where(SchedulingRule.organization_id == current_user.organization_id)
    )
    return result.scalars().all()

@router.post("/", response_model=SchedulingRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_in: SchedulingRuleCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Add a new scheduling rule (Admin only)."""
    rule_dict = rule_in.dict()
    rule_dict["organization_id"] = admin_user.organization_id
    if rule_dict.get("id") is None:
        import uuid
        rule_dict["id"] = uuid.uuid4()
    
    new_rule = SchedulingRule(**rule_dict)
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Delete a scheduling rule (Admin only)."""
    result = await db.execute(
        select(SchedulingRule).where(
            SchedulingRule.id == rule_id, 
            SchedulingRule.organization_id == admin_user.organization_id
        )
    )
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()
    return None

@router.put("/{rule_id}", response_model=SchedulingRuleOut)
async def update_rule(
    rule_id: UUID,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Update a scheduling rule's priority or details (Admin only)."""
    result = await db.execute(
        select(SchedulingRule).where(
            SchedulingRule.id == rule_id, 
            SchedulingRule.organization_id == admin_user.organization_id
        )
    )
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    for field, value in updates.items():
        if hasattr(rule, field):
            if field == "type" and isinstance(value, str):
                from app.models.models import RuleType
                value = RuleType.MUST if value.lower() == "must" else RuleType.TRY
            setattr(rule, field, value)
            
    await db.commit()
    await db.refresh(rule)
    return rule

