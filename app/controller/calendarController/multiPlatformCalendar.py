from flask import request, jsonify
from typing import Dict, List, Optional
import logging
import secrets
from app.services.calendarServiceFactory import CalendarServiceFactory
from app.models.jobModel import JobModel

logger = logging.getLogger(__name__)


class MultiPlatformCalendarController:
    def __init__(self):
        self.calendar_services = {}
    
    def _get_calendar_service(self, platform: str):
        """Get or create calendar service for platform"""
        if platform not in self.calendar_services:
            self.calendar_services[platform] = CalendarServiceFactory.create_service(platform)
        return self.calendar_services[platform]
    
    def get_auth_url(self, platform: str, redirect_uri: str = None):
        """Get OAuth authorization URL for specified platform"""
        try:
            # Validate platform
            supported_platforms = CalendarServiceFactory.get_supported_platforms()
            if platform not in supported_platforms:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Configure redirect URI if provided
            if redirect_uri and hasattr(calendar_service, 'redirect_uri'):
                calendar_service.redirect_uri = redirect_uri
            
            # Get authorization URL
            auth_url = calendar_service.get_authorization_url(state)
            
            return {
                "platform": platform,
                "authorization_url": auth_url,
                "state": state,
                "redirect_uri": redirect_uri,
                "message": f"Use this URL to authorize {platform.title()} Calendar access"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate {platform} auth URL: {e}")
            raise Exception(f"Failed to generate authorization URL for {platform}")
    
    def handle_callback(self, platform: str, code: str, state: str, client_id: str = None, 
                      client_secret: str = None, redirect_uri: str = None):
        """Handle OAuth callback and exchange code for tokens"""
        try:
            if not code:
                raise ValueError("Authorization code not provided")
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Configure service with credentials if provided
            if client_id and hasattr(calendar_service, 'client_id'):
                calendar_service.client_id = client_id
            if client_secret and hasattr(calendar_service, 'client_secret'):
                calendar_service.client_secret = client_secret
            if redirect_uri and hasattr(calendar_service, 'redirect_uri'):
                calendar_service.redirect_uri = redirect_uri
            
            # Exchange authorization code for tokens
            tokens = calendar_service.exchange_code_for_tokens(code)
            
            # Get user information
            user_info = calendar_service.get_user_info(tokens['access_token'])
            
            return {
                "platform": platform,
                "access_token": tokens['access_token'],
                "refresh_token": tokens.get('refresh_token'),
                "expires_in": tokens.get('expires_in'),
                "token_type": tokens.get('token_type', 'Bearer'),
                "user_email": user_info.get('email'),
                "user_name": user_info.get('name'),
                "user_id": user_info.get('id'),
                "message": f"Successfully authorized {platform.title()} Calendar"
            }
            
        except Exception as e:
            logger.error(f"Failed to handle {platform} auth callback: {e}")
            raise Exception(f"Failed to authorize {platform.title()} Calendar")
    
    def get_events(self, platform: str, access_token: str, refresh_token: str, 
                  days_ahead: int = 7, client_id: str = None, client_secret: str = None):
        """Get upcoming calendar events with meeting links"""
        try:
            if not access_token or not refresh_token:
                raise ValueError("Access token and refresh token required")
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Configure service with credentials if provided
            if client_id and hasattr(calendar_service, 'client_id'):
                calendar_service.client_id = client_id
            if client_secret and hasattr(calendar_service, 'client_secret'):
                calendar_service.client_secret = client_secret
            
            # Get meetings
            meetings = calendar_service.get_upcoming_meetings(
                access_token=access_token,
                refresh_token=refresh_token,
                days_ahead=days_ahead
            )
            
            return {
                "platform": platform,
                "meetings": meetings,
                "count": len(meetings),
                "message": f"Found {len(meetings)} upcoming meetings from {platform.title()}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get {platform} calendar events: {e}")
            raise Exception(f"Failed to fetch calendar events from {platform.title()}")
    
    def create_job_from_event(self, platform: str, event_id: str, access_token: str, 
                             refresh_token: str, user_id: int, client_id: str = None, 
                             client_secret: str = None):
        """Create a meeting bot job from a calendar event"""
        try:
            if not all([event_id, access_token, refresh_token]):
                raise ValueError("event_id, access_token, and refresh_token required")
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Configure service with credentials if provided
            if client_id and hasattr(calendar_service, 'client_id'):
                calendar_service.client_id = client_id
            if client_secret and hasattr(calendar_service, 'client_secret'):
                calendar_service.client_secret = client_secret
            
            # Get specific event details
            meetings = calendar_service.get_upcoming_meetings(
                access_token=access_token,
                refresh_token=refresh_token,
                days_ahead=7
            )
            
            # Find the specific event
            target_event = None
            for event in meetings:
                if event['id'] == event_id:
                    target_event = event
                    break
            
            if not target_event:
                raise ValueError("Event not found")
            
            # Create job from event
            job = JobModel(
                job_url=target_event['meeting_link'],
                platform=target_event['platform'],
                status="Registered",
                user_id=user_id
            )
            
            job.save()
            
            return {
                "platform": platform,
                "job_id": job.id,
                "meeting_url": target_event['meeting_link'],
                "meeting_title": target_event['title'],
                "scheduled_time": target_event['start_time'],
                "message": f"Job created successfully from {platform.title()} calendar event"
            }
            
        except Exception as e:
            logger.error(f"Failed to create job from {platform} calendar event: {e}")
            raise Exception(f"Failed to create job from {platform.title()} calendar event")
    
    def refresh_token(self, platform: str, refresh_token: str, client_id: str = None, 
                     client_secret: str = None):
        """Refresh access token using refresh token"""
        try:
            if not refresh_token:
                raise ValueError("Refresh token required")
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Configure service with credentials if provided
            if client_id and hasattr(calendar_service, 'client_id'):
                calendar_service.client_id = client_id
            if client_secret and hasattr(calendar_service, 'client_secret'):
                calendar_service.client_secret = client_secret
            
            # Refresh token
            new_tokens = calendar_service.refresh_access_token(refresh_token)
            
            return {
                "platform": platform,
                "access_token": new_tokens['access_token'],
                "expires_in": new_tokens.get('expires_in'),
                "token_type": new_tokens.get('token_type', 'Bearer'),
                "message": f"{platform.title()} token refreshed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh {platform} token: {e}")
            raise Exception(f"Failed to refresh {platform.title()} token")
    
    def disconnect_calendar(self, platform: str, access_token: str, refresh_token: str = None):
        """Disconnect calendar integration (revoke tokens)"""
        try:
            if not access_token:
                raise ValueError("Access token required")
            
            # Get calendar service
            calendar_service = self._get_calendar_service(platform)
            
            # Revoke tokens
            success = calendar_service.revoke_tokens(access_token, refresh_token)
            
            if success:
                return {
                    "platform": platform,
                    "message": f"{platform.title()} calendar disconnected successfully"
                }
            else:
                raise Exception(f"Failed to revoke {platform.title()} tokens")
            
        except Exception as e:
            logger.error(f"Failed to disconnect {platform} calendar: {e}")
            raise Exception(f"Failed to disconnect {platform.title()} calendar")
    
    def get_supported_platforms(self):
        """Get list of supported calendar platforms"""
        try:
            platforms = CalendarServiceFactory.get_supported_platforms()
            return {
                "platforms": platforms,
                "message": "Supported platforms retrieved successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to get supported platforms: {e}")
            raise Exception("Failed to get supported platforms")
