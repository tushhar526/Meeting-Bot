import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.tokenService import TokenService
from app.services.CalendarServiceFactory import CalendarServiceFactory
from app.models.userIntegrationModel import UserIntegration
from app.models.webhookModel import WebhookModel


class TestTokenService:
    """Test cases for TokenService"""
    
    def test_get_valid_access_token_not_expired(self, db_session, sample_user):
        """Test getting valid access token when not expired"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(TokenService, '_is_token_expired', return_value=False):
            token = TokenService.get_valid_access_token(integration)
            assert token == "valid_token"
    
    def test_get_valid_access_token_expired_refresh_success(self, db_session, sample_user):
        """Test getting valid access token when expired and refresh succeeds"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(TokenService, '_is_token_expired', return_value=True), \
             patch.object(TokenService, '_refresh_token', return_value={
                 'access_token': 'new_token',
                 'refresh_token': 'new_refresh_token',
                 'expires_in': 3600
             }):
            token = TokenService.get_valid_access_token(integration)
            assert token == "new_token"
    
    def test_get_valid_access_token_expired_refresh_failure(self, db_session, sample_user):
        """Test getting valid access token when expired and refresh fails"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(TokenService, '_is_token_expired', return_value=True), \
             patch.object(TokenService, '_refresh_token', side_effect=Exception("Refresh failed")):
            token = TokenService.get_valid_access_token(integration)
            assert token == "expired_token"  # Fallback to stored token
    
    def test_refresh_access_token_if_needed_not_expired(self, db_session, sample_user):
        """Test refresh token if not needed"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(TokenService, '_is_token_expired', return_value=False):
            token = TokenService.refresh_access_token_if_needed(integration)
            assert token == "valid_token"
    
    def test_refresh_access_token_if_needed_no_refresh_token(self, db_session, sample_user):
        """Test refresh when no refresh token available"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="expired_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(TokenService, '_is_token_expired', return_value=True):
            token = TokenService.refresh_access_token_if_needed(integration)
            assert token is None
    
    @patch('requests.post')
    def test_refresh_token_success(self, mock_post):
        """Test successful token refresh"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            result = TokenService._refresh_token('google', 'refresh_token')
            
            assert result['access_token'] == 'new_access_token'
            assert result['refresh_token'] == 'new_refresh_token'
            assert result['expires_in'] == 3600
    
    @patch('requests.post')
    def test_refresh_token_failure(self, mock_post):
        """Test token refresh failure"""
        mock_post.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            TokenService._refresh_token('google', 'refresh_token')
    
    def test_revoke_tokens_user_integration(self, db_session, sample_user):
        """Test revoking tokens for UserIntegration"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="access_token",
            refresh_token="refresh_token"
        )
        db_session.add(integration)
        db_session.commit()
        
        result = TokenService.revoke_tokens(integration)
        
        assert result is True
        assert integration.is_active is False
    
    def test_revoke_tokens_webhook_model(self, db_session, sample_user):
        """Test revoking tokens for WebhookModel"""
        webhook = WebhookModel(
            user_id=sample_user.user_id,
            webhook_url="https://example.com/webhook",
            platform="google",
            access_token="access_token",
            refresh_token="refresh_token"
        )
        db_session.add(webhook)
        db_session.commit()
        
        result = TokenService.revoke_tokens(webhook)
        
        assert result is True
        assert webhook.is_active is False
        assert webhook.access_token is None
        assert webhook.refresh_token is None
    
    def test_is_token_expired_user_integration(self, db_session, sample_user):
        """Test token expiration check for UserIntegration"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(integration)
        db_session.commit()
        
        with patch.object(integration, 'is_expired', return_value=True):
            result = TokenService._is_token_expired(integration)
            assert result is True
    
    def test_is_token_expired_webhook_model(self, db_session, sample_user):
        """Test token expiration check for WebhookModel"""
        # Expired webhook
        expired_webhook = WebhookModel(
            user_id=sample_user.user_id,
            webhook_url="https://example.com/webhook",
            platform="google",
            token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(expired_webhook)
        
        # Valid webhook
        valid_webhook = WebhookModel(
            user_id=sample_user.user_id,
            webhook_url="https://example.com/webhook2",
            platform="google",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(valid_webhook)
        db_session.commit()
        
        assert TokenService._is_token_expired(expired_webhook) is True
        assert TokenService._is_token_expired(valid_webhook) is False


class TestCalendarServiceFactory:
    """Test cases for CalendarServiceFactory"""
    
    def test_create_service_google(self):
        """Test creating Google calendar service"""
        with patch('app.controller.calendar.platform.googleCalendarService.GoogleCalendarService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            service = CalendarServiceFactory.create_service('google')
            
            assert service == mock_instance
            mock_service.assert_called_once()
    
    def test_create_service_microsoft(self):
        """Test creating Microsoft calendar service"""
        with patch('app.controller.calendar.platform.microsoftCalendarService.MicrosoftCalendarService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            service = CalendarServiceFactory.create_service('microsoft')
            
            assert service == mock_instance
            mock_service.assert_called_once()
    
    def test_create_service_zoom(self):
        """Test creating Zoom calendar service"""
        with patch('app.controller.calendar.platform.zoomCalendarService.ZoomCalendarService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            service = CalendarServiceFactory.create_service('zoom')
            
            assert service == mock_instance
            mock_service.assert_called_once()
    
    def test_create_service_unsupported_platform(self):
        """Test creating service for unsupported platform"""
        with pytest.raises(ValueError, match="Unsupported platform: unsupported"):
            CalendarServiceFactory.create_service('unsupported')
    
    def test_get_supported_platforms(self):
        """Test getting list of supported platforms"""
        platforms = CalendarServiceFactory.get_supported_platforms()
        expected_platforms = ['microsoft', 'google', 'zoom']
        
        for platform in expected_platforms:
            assert platform in platforms
    
    def test_is_platform_supported(self):
        """Test checking if platform is supported"""
        assert CalendarServiceFactory.is_platform_supported('google') is True
        assert CalendarServiceFactory.is_platform_supported('microsoft') is True
        assert CalendarServiceFactory.is_platform_supported('zoom') is True
        assert CalendarServiceFactory.is_platform_supported('unsupported') is False
    
    def test_register_service(self):
        """Test registering a new service"""
        mock_service_class = Mock()
        
        CalendarServiceFactory.register_service('new_platform', mock_service_class)
        
        assert CalendarServiceFactory.is_platform_supported('new_platform') is True
        assert 'new_platform' in CalendarServiceFactory.get_supported_platforms()
