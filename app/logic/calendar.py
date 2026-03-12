import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import json
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar integration service using OAuth 2.0"""
    
    def __init__(self):
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
        self.scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        
        if not all([self.client_id, self.client_secret]):
            logger.error("Google OAuth credentials not found in environment variables")
            raise ValueError("Missing Google OAuth credentials")
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'access_type': 'offline',  # For refresh token
            'prompt': 'consent'
        }
        
        if state:
            params['state'] = state
            
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.info(f"Generated Google OAuth URL: {auth_url}")
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            logger.info("Successfully exchanged code for tokens")
            return tokens
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            logger.info("Successfully refreshed access token")
            return tokens
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise
    
    def get_calendar_events(self, access_token: str, time_min: datetime = None, 
                          time_max: datetime = None, max_results: int = 10) -> List[Dict]:
        """Fetch calendar events within specified time range"""
        if not time_min:
            time_min = datetime.now(timezone.utc)
        if not time_max:
            time_max = time_min + timedelta(days=7)
            
        calendar_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        
        params = {
            'timeMin': time_min.isoformat() + 'Z',
            'timeMax': time_max.isoformat() + 'Z',
            'maxResults': max_results,
            'singleEvents': 'true',
            'orderBy': 'startTime'
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(calendar_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('items', [])
            
            logger.info(f"Successfully fetched {len(events)} calendar events")
            return self._format_events(events)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            raise
    
    def _format_events(self, events: List[Dict]) -> List[Dict]:
        """Format calendar events for the application"""
        formatted_events = []
        
        for event in events:
            # Extract meeting link if present
            meeting_link = None
            if 'hangoutLink' in event:
                meeting_link = event['hangoutLink']
            elif 'description' in event:
                # Look for Google Meet links in description
                import re
                meet_links = re.findall(r'https://meet\.google\.com/[a-zA-Z0-9-]+', event['description'])
                if meet_links:
                    meeting_link = meet_links[0]
            
            # Parse start and end times
            start_time = event.get('start', {}).get('dateTime', event.get('start', {}).get('dateTime'))
            end_time = event.get('end', {}).get('dateTime', event.get('end', {}).get('dateTime'))
            
            formatted_event = {
                'id': event['id'],
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': start_time,
                'end_time': end_time,
                'meeting_link': meeting_link,
                'platform': 'google_meet' if meeting_link and 'meet.google.com' in meeting_link else 'other',
                'all_day': 'date' in event.get('start', {}),
                'location': event.get('location', ''),
                'attendees': len(event.get('attendees', []))
            }
            
            formatted_events.append(formatted_event)
        
        return formatted_events
    
    def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Google"""
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(userinfo_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"Successfully fetched user info for: {user_info.get('email')}")
            return user_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise


class CalendarManager:
    """Main calendar management class"""
    
    def __init__(self):
        self.google_service = GoogleCalendarService()
    
    def get_upcoming_meetings(self, access_token: str, refresh_token: str, 
                            days_ahead: int = 7) -> List[Dict]:
        """Get upcoming meetings from all connected calendars"""
        try:
            # Try to get events with current access token
            time_min = datetime.now(timezone.utc)
            time_max = time_min + timedelta(days=days_ahead)
            
            events = self.google_service.get_calendar_events(
                access_token=access_token,
                time_min=time_min,
                time_max=time_max,
                max_results=50
            )
            
            # Filter only events with meeting links
            meetings = [event for event in events if event['meeting_link']]
            
            logger.info(f"Found {len(meetings)} upcoming meetings")
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get upcoming meetings: {e}")
            # Try to refresh token and retry once
            try:
                new_tokens = self.google_service.refresh_access_token(refresh_token)
                new_access_token = new_tokens['access_token']
                
                events = self.google_service.get_calendar_events(
                    access_token=new_access_token,
                    time_min=time_min,
                    time_max=time_max,
                    max_results=50
                )
                
                meetings = [event for event in events if event['meeting_link']]
                logger.info(f"Found {len(meetings)} upcoming meetings after token refresh")
                return meetings
                
            except Exception as refresh_error:
                logger.error(f"Failed to refresh token and get meetings: {refresh_error}")
                raise
