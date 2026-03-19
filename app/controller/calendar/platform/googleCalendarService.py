"""
Google Calendar Service
Handles OAuth flow, event fetching, and webhook setup for Google Calendar.
"""

import os
import re
import uuid
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from app.controller.calendar.base.baseCalendarService import BaseCalendarService
from app.utils.timezoneConverter import TimezoneConverter

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/calendar.readonly "
    "https://www.googleapis.com/auth/userinfo.email"
)


class GoogleCalendarService(BaseCalendarService):
    """Google Calendar service implementation"""

    def __init__(self):
        super().__init__()
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_authorization_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": GOOGLE_SCOPES,
            "response_type": "code",
            "state": state,
            "access_type": "offline",   # required for refresh token
            "prompt": "consent",        # force consent screen to always get refresh token
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()

        # Inject token_expires_at so callers can store it directly
        if tokens.get("expires_in"):
            tokens["token_expires_at"] = datetime.now(timezone.utc) + timedelta(
                seconds=tokens["expires_in"]
            )

        return tokens

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        response.raise_for_status()
        info = response.json()
        return {
            "id": info.get("id"),
            "email": info.get("email"),
            "name": info.get("name"),
        }

    # ------------------------------------------------------------------
    # Calendar data
    # ------------------------------------------------------------------

    def get_calendar_events(
        self,
        access_token: str,
        refresh_token: str = None,
        time_min: datetime = None,
        time_max: datetime = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get raw Google calendar events"""
        now = datetime.now(timezone.utc)
        time_min = time_min or now
        time_max = time_max or (now + timedelta(days=7))

        if time_min.tzinfo is None:
            time_min = time_min.replace(tzinfo=timezone.utc)
        if time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=timezone.utc)

        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "timeMin": time_min.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timeMax": time_max.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        response = requests.get(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return response.json().get("items", [])

    def get_upcoming_meetings(
        self,
        access_token: str,
        refresh_token: str = None,
        days_ahead: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get upcoming meetings from Google Calendar with IST conversion"""
        events = self.get_calendar_events(access_token, refresh_token)
        meetings = []

        for event in events:
            start_data = event.get("start", {})
            end_data = event.get("end", {})
            tz = start_data.get("timeZone") or end_data.get("timeZone")
            start_raw = start_data.get("dateTime", start_data.get("date", ""))
            end_raw = end_data.get("dateTime", end_data.get("date", ""))

            meetings.append({
                "id": event.get("id"),
                "title": event.get("summary", "No Title"),
                "start_time": TimezoneConverter.convert_to_ist_or_keep(start_raw, tz) if start_raw else "",
                "end_time": TimezoneConverter.convert_to_ist_or_keep(end_raw, tz) if end_raw else "",
                "meeting_link": self._extract_meeting_link(event),
                "platform": "google",
                "timezone": tz,
                "all_day": "date" in start_data,
                "location": event.get("location", ""),
                "attendees": len(event.get("attendees", [])),
            })

        return meetings

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def create_webhook_channel(
        self, access_token: str, webhook_url: str
    ) -> Dict[str, Any]:
        """Create Google Calendar webhook channel"""
        headers = {"Authorization": f"Bearer {access_token}"}
        expiration_ms = int(
            (datetime.now(timezone.utc) + timedelta(days=7)).timestamp() * 1000
        )
        channel_data = {
            "id": str(uuid.uuid4()),   # uuid4 — stable and unique across restarts
            "type": "web_hook",
            "address": webhook_url,
            "expiration": str(expiration_ms),
        }
        response = requests.post(
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events/watch",
            headers=headers,
            json=channel_data,
        )
        response.raise_for_status()
        return response.json()

    def stop_webhook_channel(
        self, access_token: str, channel_id: str, resource_id: str = None
    ) -> bool:
        """Stop Google Calendar webhook channel"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post(
                f"{GOOGLE_CALENDAR_API}/channels/stop",
                headers=headers,
                json={"id": channel_id, "resourceId": resource_id},
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Meeting link extraction
    # ------------------------------------------------------------------

    def _extract_meeting_link(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract meeting link from Google event"""
        # hangoutLink is the most direct source
        if event.get("hangoutLink"):
            return event["hangoutLink"]

        # conferenceData entryPoints
        for ep in event.get("conferenceData", {}).get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep.get("uri")

        # description and location fallback
        for text in [event.get("description", ""), event.get("location", "")]:
            for pattern in [
                r"https://meet\.google\.com/[a-zA-Z0-9?=-]+",
                r"https://zoom\.us/[^\s\)\"]+",
                r"https://teams\.microsoft\.com/[^\s\)\"]+",
            ]:
                match = re.search(pattern, text)
                if match:
                    return match.group(0)

        return None