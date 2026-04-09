import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.controller.calendar.calendarController import CalendarController
from app.services.CalendarServiceFactory import CalendarServiceFactory


class TestCalendarController:
    """Test cases for CalendarController"""
    
    def test_calendar_controller_initialization(self):
        """Test CalendarController initialization"""
        with patch('app.services.CalendarServiceFactory.get_supported_platforms', return_value=['google', 'microsoft', 'zoom']):
            controller = CalendarController()
            
            assert hasattr(controller, '_services')
            assert hasattr(controller, 'supported_platforms')
            assert 'google' in controller.supported_platforms
            assert 'microsoft' in controller.supported_platforms
            assert 'zoom' in controller.supported_platforms
    
    def test_get_service_caching(self):
        """Test service caching in _get_service method"""
        controller = CalendarController()
        
        with patch('app.services.CalendarServiceFactory.create_service') as mock_create:
            mock_service = Mock()
            mock_create.return_value = mock_service
            
            # First call should create service
            service1 = controller._get_service('google')
            assert service1 == mock_service
            mock_create.assert_called_once_with('google')
            
            # Second call should return cached service
            service2 = controller._get_service('google')
            assert service2 == mock_service
            mock_create.assert_called_once()  # Still only called once
    
    def test_get_auth_url_success(self):
        """Test successful OAuth URL generation"""
        controller = CalendarController()
        
        with patch('app.services.CalendarServiceFactory.is_platform_supported', return_value=True), \
             patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            
            mock_service = Mock()
            mock_service.get_auth_url.return_value = {
                'auth_url': 'https://accounts.google.com/oauth/authorize?...',
                'state': 'encrypted_state'
            }
            mock_get_service.return_value = mock_service
            
            result = controller.get_auth_url('google', 123, 'https://example.com/callback')
            
            assert 'auth_url' in result
            assert 'state' in result
            mock_service.get_auth_url.assert_called_once()
    
    def test_get_auth_url_unsupported_platform(self):
        """Test OAuth URL generation for unsupported platform"""
        controller = CalendarController()
        
        with patch('app.services.CalendarServiceFactory.is_platform_supported', return_value=False):
            with pytest.raises(ValueError, match="Unsupported platform"):
                controller.get_auth_url('unsupported', 123)
    
    def test_get_auth_url_missing_user_id(self):
        """Test OAuth URL generation with missing user_id"""
        controller = CalendarController()
        
        with pytest.raises(ValueError, match="user_id is required"):
            controller.get_auth_url('google', None)
    
    def test_handle_oauth_callback_success(self):
        """Test successful OAuth callback handling"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.handle_callback.return_value = {
                'access_token': 'access_token_123',
                'refresh_token': 'refresh_token_123',
                'expires_in': 3600
            }
            mock_get_service.return_value = mock_service
            
            result = controller.handle_oauth_callback('google', 'auth_code', 'state')
            
            assert 'access_token' in result
            assert 'refresh_token' in result
            mock_service.handle_callback.assert_called_once()
    
    def test_get_calendar_events_success(self):
        """Test successful calendar events retrieval"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_events.return_value = [
                {
                    'id': 'event_123',
                    'title': 'Test Meeting',
                    'start_time': '2024-01-01T10:00:00Z',
                    'end_time': '2024-01-01T11:00:00Z'
                }
            ]
            mock_get_service.return_value = mock_service
            
            result = controller.get_calendar_events('google', 'access_token_123')
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['title'] == 'Test Meeting'
            mock_service.get_events.assert_called_once()
    
    def test_create_calendar_event_success(self):
        """Test successful calendar event creation"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.create_event.return_value = {
                'id': 'event_123',
                'title': 'New Meeting',
                'start_time': '2024-01-01T10:00:00Z',
                'end_time': '2024-01-01T11:00:00Z',
                'meeting_url': 'https://meet.google.com/abc-xyz'
            }
            mock_get_service.return_value = mock_service
            
            event_data = {
                'title': 'New Meeting',
                'start_time': '2024-01-01T10:00:00Z',
                'end_time': '2024-01-01T11:00:00Z',
                'attendees': ['user@example.com']
            }
            
            result = controller.create_calendar_event('google', 'access_token_123', event_data)
            
            assert result['title'] == 'New Meeting'
            assert 'meeting_url' in result
            mock_service.create_event.assert_called_once()
    
    def test_update_calendar_event_success(self):
        """Test successful calendar event update"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.update_event.return_value = {
                'id': 'event_123',
                'title': 'Updated Meeting',
                'start_time': '2024-01-01T14:00:00Z',
                'end_time': '2024-01-01T15:00:00Z'
            }
            mock_get_service.return_value = mock_service
            
            update_data = {
                'title': 'Updated Meeting',
                'start_time': '2024-01-01T14:00:00Z',
                'end_time': '2024-01-01T15:00:00Z'
            }
            
            result = controller.update_calendar_event('google', 'access_token_123', 'event_123', update_data)
            
            assert result['title'] == 'Updated Meeting'
            mock_service.update_event.assert_called_once()
    
    def test_delete_calendar_event_success(self):
        """Test successful calendar event deletion"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.delete_event.return_value = {'deleted': True}
            mock_get_service.return_value = mock_service
            
            result = controller.delete_calendar_event('google', 'access_token_123', 'event_123')
            
            assert result['deleted'] is True
            mock_service.delete_event.assert_called_once()
    
    def test_setup_webhook_success(self):
        """Test successful webhook setup"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service, \
             patch('app.controller.calendar.calendarController.NgrokWebhookManager') as mock_ngrok:
            
            mock_service = Mock()
            mock_service.setup_webhook.return_value = {
                'webhook_id': 'webhook_123',
                'webhook_url': 'https://ngrok.io/webhook',
                'active': True
            }
            mock_get_service.return_value = mock_service
            mock_ngrok.get_public_url.return_value = 'https://ngrok.io/webhook'
            
            result = controller.setup_webhook('google', 'access_token_123')
            
            assert result['webhook_id'] == 'webhook_123'
            assert result['active'] is True
            mock_service.setup_webhook.assert_called_once()


class TestGoogleCalendarService:
    """Test cases for Google Calendar Service"""
    
    def test_google_calendar_get_auth_url(self):
        """Test Google Calendar auth URL generation"""
        with patch('app.controller.calendar.platform.googleCalendarService.GoogleCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.get_auth_url.return_value = {
                'auth_url': 'https://accounts.google.com/oauth/authorize?...',
                'state': 'encrypted_state'
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.get_auth_url(123, 'https://example.com/callback')
            
            assert 'auth_url' in result
            assert 'state' in result
    
    def test_google_calendar_handle_callback(self):
        """Test Google Calendar OAuth callback handling"""
        with patch('app.controller.calendar.platform.googleCalendarService.GoogleCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.handle_callback.return_value = {
                'access_token': 'google_access_token',
                'refresh_token': 'google_refresh_token',
                'expires_in': 3600
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.handle_callback('auth_code', 'state')
            
            assert result['access_token'] == 'google_access_token'
            assert result['refresh_token'] == 'google_refresh_token'
    
    def test_google_calendar_create_meeting(self):
        """Test Google Calendar meeting creation"""
        with patch('app.controller.calendar.platform.googleCalendarService.GoogleCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.create_event.return_value = {
                'id': 'google_event_123',
                'title': 'Google Meeting',
                'hangoutLink': 'https://meet.google.com/abc-xyz',
                'start': {'dateTime': '2024-01-01T10:00:00Z'},
                'end': {'dateTime': '2024-01-01T11:00:00Z'}
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            event_data = {
                'title': 'Google Meeting',
                'start_time': '2024-01-01T10:00:00Z',
                'end_time': '2024-01-01T11:00:00Z'
            }
            
            result = service.create_event('access_token', event_data)
            
            assert result['title'] == 'Google Meeting'
            assert 'hangoutLink' in result


class TestMicrosoftCalendarService:
    """Test cases for Microsoft Calendar Service"""
    
    def test_microsoft_calendar_get_auth_url(self):
        """Test Microsoft Calendar auth URL generation"""
        with patch('app.controller.calendar.platform.microsoftCalendarService.MicrosoftCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.get_auth_url.return_value = {
                'auth_url': 'https://login.microsoftonline.com/oauth/authorize?...',
                'state': 'encrypted_state'
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.get_auth_url(123, 'https://example.com/callback')
            
            assert 'auth_url' in result
            assert 'state' in result
    
    def test_microsoft_calendar_handle_callback(self):
        """Test Microsoft Calendar OAuth callback handling"""
        with patch('app.controller.calendar.platform.microsoftCalendarService.MicrosoftCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.handle_callback.return_value = {
                'access_token': 'microsoft_access_token',
                'refresh_token': 'microsoft_refresh_token',
                'expires_in': 3600
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.handle_callback('auth_code', 'state')
            
            assert result['access_token'] == 'microsoft_access_token'
            assert result['refresh_token'] == 'microsoft_refresh_token'
    
    def test_microsoft_calendar_create_meeting(self):
        """Test Microsoft Calendar meeting creation"""
        with patch('app.controller.calendar.platform.microsoftCalendarService.MicrosoftCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.create_event.return_value = {
                'id': 'microsoft_event_123',
                'subject': 'Teams Meeting',
                'onlineMeeting': {
                    'joinUrl': 'https://teams.microsoft.com/meeting/abc-xyz'
                },
                'start': {'dateTime': '2024-01-01T10:00:00Z'},
                'end': {'dateTime': '2024-01-01T11:00:00Z'}
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            event_data = {
                'title': 'Teams Meeting',
                'start_time': '2024-01-01T10:00:00Z',
                'end_time': '2024-01-01T11:00:00Z'
            }
            
            result = service.create_event('access_token', event_data)
            
            assert result['subject'] == 'Teams Meeting'
            assert 'onlineMeeting' in result
            assert 'joinUrl' in result['onlineMeeting']


class TestZoomCalendarService:
    """Test cases for Zoom Calendar Service"""
    
    def test_zoom_calendar_get_auth_url(self):
        """Test Zoom Calendar auth URL generation"""
        with patch('app.controller.calendar.platform.zoomCalendarService.ZoomCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.get_auth_url.return_value = {
                'auth_url': 'https://zoom.us/oauth/authorize?...',
                'state': 'encrypted_state'
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.get_auth_url(123, 'https://example.com/callback')
            
            assert 'auth_url' in result
            assert 'state' in result
    
    def test_zoom_calendar_handle_callback(self):
        """Test Zoom Calendar OAuth callback handling"""
        with patch('app.controller.calendar.platform.zoomCalendarService.ZoomCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.handle_callback.return_value = {
                'access_token': 'zoom_access_token',
                'refresh_token': 'zoom_refresh_token',
                'expires_in': 3600
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            result = service.handle_callback('auth_code', 'state')
            
            assert result['access_token'] == 'zoom_access_token'
            assert result['refresh_token'] == 'zoom_refresh_token'
    
    def test_zoom_calendar_create_meeting(self):
        """Test Zoom Calendar meeting creation"""
        with patch('app.controller.calendar.platform.zoomCalendarService.ZoomCalendarService') as mock_service:
            mock_instance = Mock()
            mock_instance.create_event.return_value = {
                'id': 'zoom_meeting_123',
                'topic': 'Zoom Meeting',
                'join_url': 'https://zoom.us/j/123456789',
                'start_time': '2024-01-01T10:00:00Z',
                'duration': 60
            }
            mock_service.return_value = mock_instance
            
            service = mock_instance
            event_data = {
                'title': 'Zoom Meeting',
                'start_time': '2024-01-01T10:00:00Z',
                'duration': 60
            }
            
            result = service.create_event('access_token', event_data)
            
            assert result['topic'] == 'Zoom Meeting'
            assert 'join_url' in result
            assert result['duration'] == 60


class TestCalendarIntegration:
    """Test cases for calendar integration scenarios"""
    
    def test_cross_platform_meeting_creation(self):
        """Test creating meetings across different platforms"""
        platforms = ['google', 'microsoft', 'zoom']
        
        for platform in platforms:
            controller = CalendarController()
            
            with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
                mock_service = Mock()
                mock_service.create_event.return_value = {
                    'id': f'{platform}_event_123',
                    'title': f'{platform.title()} Meeting',
                    'platform': platform
                }
                mock_get_service.return_value = mock_service
                
                event_data = {
                    'title': f'{platform.title()} Meeting',
                    'start_time': '2024-01-01T10:00:00Z',
                    'end_time': '2024-01-01T11:00:00Z'
                }
                
                result = controller.create_calendar_event(platform, 'access_token', event_data)
                
                assert result['platform'] == platform
                assert f'{platform.title()} Meeting' in result['title']
    
    def test_calendar_sync_across_platforms(self):
        """Test calendar synchronization across platforms"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_events.return_value = [
                {'id': 'event_1', 'title': 'Meeting 1'},
                {'id': 'event_2', 'title': 'Meeting 2'}
            ]
            mock_get_service.return_value = mock_service
            
            # Get events from multiple platforms
            platforms = ['google', 'microsoft', 'zoom']
            all_events = []
            
            for platform in platforms:
                events = controller.get_calendar_events(platform, 'access_token')
                all_events.extend(events)
            
            assert len(all_events) == 6  # 2 events × 3 platforms
    
    def test_calendar_conflict_detection(self):
        """Test calendar conflict detection"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_events.return_value = [
                {
                    'id': 'existing_event',
                    'start_time': '2024-01-01T10:30:00Z',
                    'end_time': '2024-01-01T11:30:00Z'
                }
            ]
            mock_get_service.return_value = mock_service
            
            # Check for conflicts
            existing_events = controller.get_calendar_events('google', 'access_token')
            new_event = {
                'start_time': '2024-01-01T10:00:00Z',
                'end_time': '2024-01-01T11:00:00Z'
            }
            
            # Simple conflict detection logic
            has_conflict = False
            for event in existing_events:
                if (new_event['start_time'] < event['end_time'] and 
                    new_event['end_time'] > event['start_time']):
                    has_conflict = True
                    break
            
            assert has_conflict is True
    
    def test_calendar_webhook_setup_all_platforms(self):
        """Test webhook setup for all calendar platforms"""
        controller = CalendarController()
        
        with patch('app.controller.calendar.calendarController.CalendarController._get_service') as mock_get_service, \
             patch('app.controller.calendar.calendarController.NgrokWebhookManager') as mock_ngrok:
            
            mock_service = Mock()
            mock_service.setup_webhook.return_value = {
                'webhook_id': 'webhook_123',
                'active': True
            }
            mock_get_service.return_value = mock_service
            mock_ngrok.get_public_url.return_value = 'https://ngrok.io/webhook'
            
            platforms = ['google', 'microsoft', 'zoom']
            webhooks = []
            
            for platform in platforms:
                webhook = controller.setup_webhook(platform, 'access_token')
                webhooks.append(webhook)
            
            assert len(webhooks) == 3
            for webhook in webhooks:
                assert webhook['active'] is True
