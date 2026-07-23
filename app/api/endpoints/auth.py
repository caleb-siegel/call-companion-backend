from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    Token,
    UserOut,
    UserCreate,
    OrganizationOut,
    OrganizationCreate,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.api.auth import (
    verify_password,
    create_access_token,
    get_password_hash,
    create_password_reset_token,
    verify_password_reset_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.api.deps import get_current_user
from app.services.email import send_password_reset_email

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()
    
    if user:
        token = create_password_reset_token(str(user.id))
        send_password_reset_email(user.email, token)
        
    return {"message": "If an account with that email exists, a password reset link has been sent."}

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = verify_password_reset_token(body.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )
        
    import uuid
    try:
        uuid_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload.",
        )
        
    result = await db.execute(select(User).where(User.id == uuid_user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    user.hashed_password = get_password_hash(body.new_password)
    await db.commit()
    
    return {"message": "Password reset successfully. You can now log in with your new password."}

