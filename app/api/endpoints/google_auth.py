import os
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.database import get_db
from app.models.models import User
from app.api.auth import SECRET_KEY, ALGORITHM
from app.api.deps import get_current_user
from app.services.google_calendar import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    make_request_async,
    list_user_calendars
)

router = APIRouter()

class SelectCalendarSchema(BaseModel):
    calendar_id: str

@router.get("/login")
async def google_login(token: str, request: Request):
    """
    Initiates Google OAuth flow by validating the user's JWT token
    and redirecting them to Google's authorization consent screen.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Dynamically build the redirect URI based on the request host
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    redirect_uri = f"{scheme}://{host}/api/google/callback"

    # Google Authorization params
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        # Request access to calendar events (read/write)
        "scope": "https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",  # Crucial to get a refresh token
        "prompt": "consent",       # Force consent screen to guarantee refresh token is returned
        "state": user_id           # Securely pass the user ID as state to link them on callback
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles Google's redirect callback, exchanges code for access/refresh tokens,
    saves them to the corresponding User record, and redirects back to the frontend.
    """
    user_id = state
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Reconstruct the exact redirect URI used during login initiation
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    redirect_uri = f"{scheme}://{host}/api/google/callback"

    # Token exchange payload
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    data = urllib.parse.urlencode(payload)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    status_code, response = await make_request_async(
        "https://oauth2.googleapis.com/token",
        method="POST",
        headers=headers,
        data=data
    )

    if status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Google token exchange failed: {response}"
        )

    # Save credentials
    user.google_access_token = response.get("access_token")
    # Google only returns refresh_token when prompt=consent is requested
    if response.get("refresh_token"):
        user.google_refresh_token = response.get("refresh_token")
        
    expires_in = response.get("expires_in", 3600)
    user.google_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

    await db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    if frontend_url.endswith("/"):
        frontend_url = frontend_url[:-1]

    # Redirect back to the frontend home page with success status
    return RedirectResponse(url=f"{frontend_url}/?google_connected=true")

@router.get("/calendars")
async def get_calendars(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves list of user's Google Calendars (Authenticated)."""
    if not current_user.google_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Google Calendar is not connected"
        )
    return await list_user_calendars(current_user, db)

@router.post("/select-calendar")
async def select_calendar(
    body: SelectCalendarSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves the user's selected sync calendar target ID (Authenticated)."""
    if not current_user.google_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Google Calendar is not connected"
        )
    current_user.google_calendar_id = body.calendar_id
    await db.commit()
    return {"message": "Sync calendar selected successfully", "google_calendar_id": body.calendar_id}

@router.post("/disconnect")
async def disconnect_calendar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnects Google Calendar by wiping all credentials (Authenticated)."""
    current_user.google_access_token = None
    current_user.google_refresh_token = None
    current_user.google_token_expiry = None
    current_user.google_calendar_id = None
    await db.commit()
    return {"message": "Google Calendar disconnected successfully"}
