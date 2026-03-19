"""
Zoom Calendar Service
Handles OAuth flow, event fetching, and webhook setup for Zoom.
"""

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from app.controller.calendar.base.baseCalendarService import BaseCalendarService
from app.utils.timezoneConverter import TimezoneConverter

ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API = "https://api.zoom.us/v2"
ZOOM_SCOPES = (
    "user:read:admin "
    "meeting:read:list_meetings:admin "
    "meeting:read:meeting:admin "
    "meeting:write:meeting:admin"
)


class ZoomCalendarService(BaseCalendarService):
    """Zoom Calendar service implementation"""

    def __init__(self):
        super().__init__()
        self.client_id = os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = os.getenv("ZOOM_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ZOOM_REDIRECT_URI")  # was missing before

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_authorization_url(self, state: str) -> str:
        """Generate Zoom OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": ZOOM_SCOPES,
        }
        return f"{ZOOM_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(ZOOM_TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()

        # Inject token_expires_at so callers can store it directly
        if tokens.get("expires_in"):
            tokens["token_expires_at"] = datetime.now(timezone.utc) + timedelta(
                seconds=tokens["expires_in"]
            )

        return tokens

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Zoom"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{ZOOM_API}/users/me", headers=headers)
        response.raise_for_status()
        info = response.json()
        return {
            "id": info.get("id"),
            "email": info.get("email"),
            "name": f"{info.get('first_name', '')} {info.get('last_name', '')}".strip(),
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
        """Get raw Zoom meetings"""
        now = datetime.now(timezone.utc)
        time_min = time_min or now
        time_max = time_max or (now + timedelta(days=7))

        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "type": "scheduled",
            "from": time_min.strftime("%Y-%m-%d"),
            "to": time_max.strftime("%Y-%m-%d"),
            "page_size": max_results,
        }
        response = requests.get(
            f"{ZOOM_API}/users/me/meetings", headers=headers, params=params
        )
        response.raise_for_status()
        return response.json().get("meetings", [])

    def get_upcoming_meetings(
        self,
        access_token: str,
        refresh_token: str = None,
        days_ahead: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get upcoming Zoom meetings with IST conversion"""
        raw_meetings = self.get_calendar_events(access_token, refresh_token)
        meetings = []

        for m in raw_meetings:
            start_raw = m.get("start_time", "")
            duration = m.get("duration", 0)  # minutes

            end_raw = ""
            if start_raw:
                try:
                    start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    end_raw = (start_dt + timedelta(minutes=duration)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                except ValueError:
                    pass

            meetings.append(
                {
                    "id": str(m.get("id")),
                    "title": m.get("topic", "No Title"),
                    "start_time": (
                        TimezoneConverter.convert_to_ist_or_keep(start_raw)
                        if start_raw
                        else ""
                    ),
                    "end_time": (
                        TimezoneConverter.convert_to_ist_or_keep(end_raw)
                        if end_raw
                        else ""
                    ),
                    "meeting_link": m.get("join_url", ""),
                    "platform": "zoom",
                    "timezone": "UTC",
                    "all_day": False,
                    "location": "",
                    "attendees": 0,
                }
            )

        return meetings

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def create_webhook_channel(
        self, access_token: str, webhook_url: str
    ) -> Dict[str, Any]:
        """Create Zoom webhook"""
        headers = {"Authorization": f"Bearer {access_token}"}
        # events must be a list, not a comma-separated string
        # authorization header goes in the request headers, NOT in the JSON body
        data = {
            "url": webhook_url,
            "events": [
                "meeting.created",
                "meeting.updated",
                "meeting.started",
                "meeting.ended",
            ],
        }
        response = requests.post(f"{ZOOM_API}/webhooks", headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def stop_webhook_channel(
        self, access_token: str, channel_id: str, resource_id: str = None
    ) -> bool:
        """Stop Zoom webhook"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            requests.delete(
                f"{ZOOM_API}/webhooks/{channel_id}", headers=headers
            ).raise_for_status()
            return True
        except Exception:
            return False
