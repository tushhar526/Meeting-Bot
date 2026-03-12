from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CalendarServiceInterface(ABC):
    """Abstract interface for calendar services"""
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Get authorization URL for OAuth flow"""
        pass
    
    @abstractmethod
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        pass
    
    @abstractmethod
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from access token"""
        pass
    
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        pass
    
    @abstractmethod
    def get_upcoming_meetings(self, access_token: str, refresh_token: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming meetings from calendar"""
        pass
    
    @abstractmethod
    def revoke_tokens(self, access_token: str, refresh_token: str = None) -> bool:
        """Revoke access tokens"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the platform name"""
        pass


class GoogleCalendarService(CalendarServiceInterface):
    """Google Calendar service implementation"""
    
    def __init__(self):
        from app.logic.calendar import CalendarManager
        self.calendar_manager = CalendarManager()
    
    def get_authorization_url(self, state: str) -> str:
        return self.calendar_manager.google_service.get_authorization_url(state)
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        return self.calendar_manager.google_service.exchange_code_for_tokens(code)
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        return self.calendar_manager.google_service.get_user_info(access_token)
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        return self.calendar_manager.google_service.refresh_access_token(refresh_token)
    
    def get_upcoming_meetings(self, access_token: str, refresh_token: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        return self.calendar_manager.get_upcoming_meetings(access_token, refresh_token, days_ahead)
    
    def revoke_tokens(self, access_token: str, refresh_token: str = None) -> bool:
        # Implement token revocation for Google
        try:
            import requests
            response = requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': access_token}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke Google tokens: {e}")
            return False
    
    def get_platform_name(self) -> str:
        return "google"


class MicrosoftCalendarService(CalendarServiceInterface):
    """Microsoft Graph Calendar service implementation"""
    
    def __init__(self):
        self.client_id = None  # Will be loaded from config
        self.client_secret = None  # Will be loaded from config
        self.redirect_uri = None  # Will be loaded from config
        self.scope = "https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/User.Read"
    
    def get_authorization_url(self, state: str) -> str:
        # Microsoft OAuth URL
        auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': state
        }
        
        from urllib.parse import urlencode
        return f"{auth_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        try:
            import requests
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code',
                'scope': self.scope
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to exchange Microsoft code for tokens: {e}")
            raise
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers
            )
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                'name': user_data.get('displayName'),
                'id': user_data.get('id')
            }
            
        except Exception as e:
            logger.error(f"Failed to get Microsoft user info: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            import requests
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'scope': self.scope
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to refresh Microsoft token: {e}")
            raise
    
    def get_upcoming_meetings(self, access_token: str, refresh_token: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        try:
            import requests
            from datetime import datetime, timedelta
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Calculate time range
            now = datetime.utcnow()
            end_time = now + timedelta(days=days_ahead)
            
            # Get calendar events
            url = f"https://graph.microsoft.com/v1.0/me/calendar/calendarView"
            params = {
                'startDateTime': now.isoformat() + 'Z',
                'endDateTime': end_time.isoformat() + 'Z',
                '$select': 'id,subject,start,end,onlineMeeting,location',
                '$orderby': 'start/dateTime'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            events = response.json().get('value', [])
            meetings = []
            
            for event in events:
                if self._is_meeting_event(event):
                    meeting = self._parse_meeting_event(event)
                    meetings.append(meeting)
            
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get Microsoft meetings: {e}")
            raise
    
    def _is_meeting_event(self, event: Dict[str, Any]) -> bool:
        """Check if event is a meeting"""
        return (
            event.get('onlineMeeting') or
            (event.get('location', {}).get('displayName') and 'meet' in event['location']['displayName'].lower())
        )
    
    def _parse_meeting_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Microsoft event to standard meeting format"""
        online_meeting = event.get('onlineMeeting', {})
        
        return {
            'id': event['id'],
            'title': event.get('subject', 'No Title'),
            'start_time': event['start']['dateTime'],
            'end_time': event['end']['dateTime'],
            'meeting_link': online_meeting.get('joinUrl') or self._extract_meeting_link(event),
            'platform': self._detect_platform(online_meeting.get('joinUrl', '')),
            'platform_name': 'Microsoft Teams'
        }
    
    def _extract_meeting_link(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract meeting link from event body or location"""
        # Try to extract from location
        location = event.get('location', {}).get('displayName', '')
        if 'teams.microsoft.com' in location or 'meet' in location.lower():
            return location
        
        # Could also parse body content here for links
        return None
    
    def _detect_platform(self, meeting_url: str) -> str:
        """Detect meeting platform from URL"""
        if 'teams.microsoft.com' in meeting_url:
            return 'Microsoft Teams'
        elif 'zoom.us' in meeting_url:
            return 'Zoom'
        else:
            return 'Microsoft Teams'
    
    def revoke_tokens(self, access_token: str, refresh_token: str = None) -> bool:
        # Implement token revocation for Microsoft
        try:
            import requests
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/logout',
                params={'post_logout_redirect_uri': self.redirect_uri}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke Microsoft tokens: {e}")
            return False
    
    def get_platform_name(self) -> str:
        return "microsoft"


class ZoomCalendarService(CalendarServiceInterface):
    """Zoom Calendar service implementation"""
    
    def __init__(self):
        self.client_id = None  # Will be loaded from config
        self.client_secret = None  # Will be loaded from config
        self.redirect_uri = None  # Will be loaded from config
    
    def get_authorization_url(self, state: str) -> str:
        auth_url = "https://zoom.us/oauth/authorize"
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state
        }
        
        from urllib.parse import urlencode
        return f"{auth_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        try:
            import requests
            import base64
            
            token_url = "https://zoom.us/oauth/token"
            
            # Basic auth header
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_header = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to exchange Zoom code for tokens: {e}")
            raise
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(
                'https://api.zoom.us/v2/users/me',
                headers=headers
            )
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'email': user_data.get('email'),
                'name': user_data.get('display_name') or user_data.get('first_name') + ' ' + user_data.get('last_name', ''),
                'id': user_data.get('id')
            }
            
        except Exception as e:
            logger.error(f"Failed to get Zoom user info: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            import requests
            import base64
            
            token_url = "https://zoom.us/oauth/token"
            
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_header = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to refresh Zoom token: {e}")
            raise
    
    def get_upcoming_meetings(self, access_token: str, refresh_token: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        try:
            import requests
            from datetime import datetime, timedelta
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get user's meetings
            url = "https://api.zoom.us/v2/users/me/meetings"
            params = {
                'type': 'scheduled',  # Get scheduled meetings
                'page_size': 100
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            meetings_data = response.json().get('meetings', [])
            meetings = []
            
            now = datetime.utcnow()
            end_time = now + timedelta(days=days_ahead)
            
            for meeting in meetings_data:
                start_time = datetime.fromisoformat(meeting['start_time'].replace('Z', '+00:00'))
                
                if now <= start_time <= end_time:
                    parsed_meeting = self._parse_zoom_meeting(meeting)
                    meetings.append(parsed_meeting)
            
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get Zoom meetings: {e}")
            raise
    
    def _parse_zoom_meeting(self, meeting: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Zoom meeting to standard format"""
        return {
            'id': meeting['id'],
            'title': meeting.get('topic', 'No Title'),
            'start_time': meeting['start_time'],
            'end_time': meeting.get('end_time', ''),
            'meeting_link': meeting.get('join_url'),
            'platform': 'Zoom',
            'platform_name': 'Zoom'
        }
    
    def revoke_tokens(self, access_token: str, refresh_token: str = None) -> bool:
        # Implement token revocation for Zoom
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.post(
                'https://api.zoom.us/v2/users/me/token/revoke',
                headers=headers
            )
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Failed to revoke Zoom tokens: {e}")
            return False
    
    def get_platform_name(self) -> str:
        return "zoom"


class CalendarServiceFactory:
    """Factory class for creating calendar service instances"""
    
    _services = {
        'google': GoogleCalendarService,
        'microsoft': MicrosoftCalendarService,
        'zoom': ZoomCalendarService
    }
    
    @classmethod
    def create_service(cls, platform: str) -> CalendarServiceInterface:
        """Create a calendar service instance for the specified platform"""
        if platform not in cls._services:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return cls._services[platform]()
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Get list of supported platforms"""
        return list(cls._services.keys())
    
    @classmethod
    def register_service(cls, platform: str, service_class):
        """Register a new calendar service"""
        cls._services[platform] = service_class
