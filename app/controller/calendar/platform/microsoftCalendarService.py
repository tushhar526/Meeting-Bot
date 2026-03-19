"""
Microsoft Calendar Service
Handles OAuth flow, event fetching, and webhook setup for Microsoft Calendar.
"""

import os
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from app.controller.calendar.base.baseCalendarService import BaseCalendarService
from app.utils.timezoneConverter import TimezoneConverter

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

# offline_access is required — without it Microsoft will not issue a refresh_token
MS_SCOPES = (
    "https://graph.microsoft.com/Calendars.Read "
    "https://graph.microsoft.com/Calendars.ReadWrite "
    "https://graph.microsoft.com/User.Read "
    "offline_access"
)


class MicrosoftCalendarService(BaseCalendarService):

    def __init__(self):
        super().__init__()
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI")

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": MS_SCOPES,
            "response_type": "code",
            "state": state,
            "response_mode": "query",
        }
        return f"{MS_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "scope": MS_SCOPES,
        }
        response = requests.post(MS_TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()
        if tokens.get("expires_in"):
            tokens["token_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
        return tokens

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{GRAPH_BASE}/me", headers=headers)
        response.raise_for_status()
        info = response.json()
        return {
            "id": info.get("id"),
            "email": info.get("mail") or info.get("userPrincipalName"),
            "name": info.get("displayName"),
        }

    def get_calendar_events(self, access_token, refresh_token=None, time_min=None, time_max=None, max_results=50):
        now = datetime.now(timezone.utc)
        time_min = time_min or now
        time_max = time_max or (now + timedelta(days=7))
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "startDateTime": time_min.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": time_max.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "$select": "id,subject,start,end,onlineMeeting,onlineMeetingUrl,location,body,attendees",
            "$top": max_results,
            "$orderby": "start/dateTime",
        }
        # calendarView supports startDateTime/endDateTime directly
        # /me/events requires $filter with stricter formatting
        response = requests.get(f"{GRAPH_BASE}/me/calendarView", headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("value", [])

    def get_upcoming_meetings(self, access_token, refresh_token=None, days_ahead=7):
        events = self.get_calendar_events(access_token, refresh_token)
        meetings = []
        for event in events:
            start_raw = event.get("start", {}).get("dateTime", "")
            end_raw = event.get("end", {}).get("dateTime", "")
            meetings.append({
                "id": event.get("id"),
                "title": event.get("subject", "No Title"),
                "start_time": TimezoneConverter.convert_to_ist_or_keep(start_raw) if start_raw else "",
                "end_time": TimezoneConverter.convert_to_ist_or_keep(end_raw) if end_raw else "",
                "meeting_link": self._extract_meeting_link(event),
                "platform": "microsoft",
                "timezone": event.get("start", {}).get("timeZone"),
                "all_day": False,
                "location": event.get("location", {}).get("displayName", ""),
                "attendees": len(event.get("attendees", [])),
            })
        return meetings

    def create_webhook_channel(self, access_token: str, webhook_url: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
        data = {
            "changeType": "created,updated",
            "notificationUrl": webhook_url,
            "resource": "me/events",   # correct — NOT "me/calendar/events"
            "expirationDateTime": expiry,
            "clientState": os.getenv("MICROSOFT_CLIENT_STATE", "meetingbot-secret"),  # must be static
        }
        response = requests.post(f"{GRAPH_BASE}/subscriptions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def stop_webhook_channel(self, access_token: str, channel_id: str, resource_id: str = None) -> bool:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            requests.delete(f"{GRAPH_BASE}/subscriptions/{channel_id}", headers=headers).raise_for_status()
            return True
        except Exception:
            return False

    def renew_webhook_channel(self, access_token: str, subscription_id: str) -> bool:
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
        try:
            requests.patch(
                f"{GRAPH_BASE}/subscriptions/{subscription_id}",
                headers=headers,
                json={"expirationDateTime": expiry},
            ).raise_for_status()
            return True
        except Exception:
            return False

    def _extract_meeting_link(self, event: Dict[str, Any]) -> Optional[str]:
        online = event.get("onlineMeeting") or {}
        if online.get("joinUrl"):
            return online["joinUrl"]
        if event.get("onlineMeetingUrl"):
            return event["onlineMeetingUrl"]
        location = event.get("location", {}).get("displayName", "")
        if any(d in location for d in ["teams.microsoft.com", "meet.google.com", "zoom.us"]):
            return location
        body = event.get("body", {}).get("content", "")
        match = re.search(r"https://teams\.microsoft\.com/l/meetup-join/[^\s\)\"]+", body)
        return match.group(0) if match else None