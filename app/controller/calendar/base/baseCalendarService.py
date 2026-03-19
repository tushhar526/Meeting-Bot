"""
Base Calendar Service
Abstract base class defining the interface all platform services must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseCalendarService(ABC):
    """Abstract base class for calendar services"""
    
    def __init__(self):
        self.redirect_uri = None
        self.client_id = None
        self.client_secret = None
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL for the platform
        
        Args:
            state: OAuth state parameter for security
            
        Returns:
            str: Authorization URL
        """
        pass
    
    @abstractmethod
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dict containing tokens and metadata:
            - access_token: str
            - refresh_token: str (optional)
            - expires_in: int (optional)
            - token_type: str (optional)
        """
        pass
    
    @abstractmethod
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from the platform
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dict containing user info:
            - id: str
            - email: str
            - name: str (optional)
        """
        pass
    
    @abstractmethod
    def get_upcoming_meetings(
        self, 
        access_token: str, 
        refresh_token: str = None,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming meetings/events from the calendar
        
        Args:
            access_token: Valid access token
            refresh_token: Refresh token for token renewal (optional)
            days_ahead: Number of days ahead to fetch events
            
        Returns:
            List of meeting events with:
            - id: str
            - title: str
            - start_time: str (ISO format)
            - end_time: str (ISO format)
            - meeting_link: str (optional)
            - description: str (optional)
        """
        pass
    
    @abstractmethod
    def create_webhook_channel(
        self, 
        access_token: str, 
        webhook_url: str
    ) -> Dict[str, Any]:
        """
        Create webhook channel for receiving event notifications
        
        Args:
            access_token: Valid access token
            webhook_url: URL to receive webhook notifications
            
        Returns:
            Dict containing webhook information:
            - channel_id: str
            - resource_id: str (optional)
            - expiration: str (optional)
            - Other platform-specific fields
        """
        pass
    
    def stop_webhook_channel(
        self, 
        access_token: str, 
        channel_id: str, 
        resource_id: str = None
    ) -> bool:
        """
        Stop webhook channel (optional implementation)
        
        Args:
            access_token: Valid access token
            channel_id: Webhook channel ID
            resource_id: Webhook resource ID (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Default implementation - platforms can override
        return True
    
    def refresh_access_token(
        self, 
        refresh_token: str, 
        client_id: str = None, 
        client_secret: str = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token (optional implementation)
        
        Args:
            refresh_token: Valid refresh token
            client_id: OAuth client ID (optional)
            client_secret: OAuth client secret (optional)
            
        Returns:
            Dict containing new tokens:
            - access_token: str
            - refresh_token: str (optional)
            - expires_in: int (optional)
        """
        # Default implementation - platforms can override
        raise NotImplementedError("Token refresh not implemented for this platform")
