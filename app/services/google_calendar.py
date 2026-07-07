import os
import json
import urllib.request
import urllib.parse
import urllib.error
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, Shift

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Sync event prefix (base32hex compliant: only a-v and 0-9)
EVENT_ID_PREFIX = "callcompanionshift"

def _make_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, data: Any = None) -> Tuple[int, Any]:
    """Helper to perform synchronous HTTP requests using urllib."""
    headers = headers or {}
    req = urllib.request.Request(url, method=method, headers=headers)
    
    if data is not None:
        if isinstance(data, (dict, list)):
            req.data = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        elif isinstance(data, str):
            req.data = data.encode("utf-8")
        else:
            req.data = data

    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
        except Exception:
            err_json = {"detail": str(e)}
        return e.code, err_json
    except Exception as e:
        return 500, {"detail": str(e)}

async def make_request_async(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, data: Any = None) -> Tuple[int, Any]:
    """Async wrapper for the urllib request helper."""
    return await asyncio.to_thread(_make_request, url, method, headers, data)

async def refresh_google_tokens(user: User, db: AsyncSession) -> Optional[str]:
    """
    Refreshes the user's Google access token using their refresh token if expired.
    Wipes tokens from database if Google rejects the refresh token (e.g. access revoked).
    """
    if not user.google_refresh_token:
        return None

    # Check if token is expired or expiring within 5 minutes
    is_expired = True
    if user.google_token_expiry:
        # Buffer of 5 minutes
        is_expired = datetime.utcnow() + timedelta(minutes=5) >= user.google_token_expiry

    if not is_expired and user.google_access_token:
        return user.google_access_token

    # Token needs refresh
    payload = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": user.google_refresh_token,
        "grant_type": "refresh_token",
    }
    data = urllib.parse.urlencode(payload)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    status, response = await make_request_async(
        "https://oauth2.googleapis.com/token",
        method="POST",
        headers=headers,
        data=data
    )

    if status == 200:
        user.google_access_token = response.get("access_token")
        expires_in = response.get("expires_in", 3600)
        user.google_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        await db.commit()
        await db.refresh(user)
        return user.google_access_token
    else:
        # If the grant is invalid (revoked, password changed, etc.), disconnect integration
        error_desc = response.get("error_description", "")
        if "invalid_grant" in response.get("error", "") or "revoked" in error_desc:
            user.google_access_token = None
            user.google_refresh_token = None
            user.google_token_expiry = None
            user.google_calendar_id = None
            await db.commit()
            await db.refresh(user)
        return None

async def list_user_calendars(user: User, db: AsyncSession) -> List[Dict[str, Any]]:
    """Fetches list of Google Calendars for the authenticated user."""
    access_token = await refresh_google_tokens(user, db)
    if not access_token:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    status, response = await make_request_async(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        method="GET",
        headers=headers
    )

    if status == 200:
        return response.get("items", [])
    return []

async def sync_user_shifts_to_google(user: User, shifts: List[Shift], start_date: datetime, end_date: datetime, db: AsyncSession):
    """
    Performs a stateless, self-healing synchronization of a user's shifts within a date range.
    Inserts/updates assigned shifts, and deletes any events in Google Calendar that do not match current DB assignments.
    """
    calendar_id = user.google_calendar_id
    if not calendar_id:
        return

    access_token = await refresh_google_tokens(user, db)
    if not access_token:
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Format dates for Google API queries (RFC3339)
    # Convert dates to start of day and end of day respectively
    time_min = start_date.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (end_date + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Fetch current events in this range from the user's selected Google Calendar
    events_url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events"
    query_params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "maxResults": 250
    })
    
    status, response = await make_request_async(f"{events_url}?{query_params}", method="GET", headers=headers)
    if status != 200:
        # If calendar not found (deleted in Google), clear setting so they can select a new one
        if status == 404:
            user.google_calendar_id = None
            await db.commit()
        return

    google_events = response.get("items", [])
    
    # Filter google events to only those managed by Call Companion
    managed_google_events = {
        event["id"]: event for event in google_events 
        if event["id"].startswith(EVENT_ID_PREFIX)
    }

    # 2. Build expected list of events based on DB shifts
    expected_events: Dict[str, Dict[str, Any]] = {}
    
    for shift in shifts:
        # Build hex key (UUID is hex, stripping hyphens fits base32hex format perfectly)
        shift_hex = shift.id.hex
        user_hex = user.id.hex
        event_id = f"{EVENT_ID_PREFIX}{shift_hex}{user_hex}"
        
        # Build title summary
        summary = "Call Shift"
        if shift.note:
            summary += f" - {shift.note}"
        else:
            summary += f" ({shift.type.value.capitalize()})"
            
        start_str = shift.date.strftime("%Y-%m-%d")
        end_str = (shift.date + timedelta(days=1)).strftime("%Y-%m-%d")

        expected_events[event_id] = {
            "id": event_id,
            "summary": summary,
            "description": f"Call Companion Shift Assignment\nShift ID: {shift.id}",
            "start": {"date": start_str},
            "end": {"date": end_str},
        }

    # 3. Create or update expected events
    for event_id, event_data in expected_events.items():
        # Check if it exists and needs an update, or if we can do an idempotent PUT
        # Google's PUT is /events/{event_id} which updates an event. If 404, we import it.
        put_url = f"{events_url}/{event_id}"
        put_status, put_res = await make_request_async(put_url, method="PUT", headers=headers, data=event_data)
        
        if put_status == 404:
            # Event does not exist, use Import endpoint to create with our custom ID
            import_url = f"{events_url}/import"
            await make_request_async(import_url, method="POST", headers=headers, data=event_data)

    # 4. Clean up any managed Google events that are no longer expected
    for event_id in managed_google_events:
        if event_id not in expected_events:
            delete_url = f"{events_url}/{event_id}"
            await make_request_async(delete_url, method="DELETE", headers=headers)
