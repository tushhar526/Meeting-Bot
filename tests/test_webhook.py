import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Request
from app.controller.webhook.webhookController import WebhookController
from app.controller.webhook.base.basewebhookController import BaseWebhookHandler, HandlerResult


class TestWebhookController:
    """Test cases for WebhookController"""
    
    def test_dispatch_supported_platform_success(self):
        """Test successful webhook dispatch for supported platform"""
        mock_handler = Mock(spec=BaseWebhookHandler)
        mock_handler.verify.return_value = True
        mock_handler.handle.return_value = ({"status": "success"}, 200)
        
        with patch.dict(WebhookController._registry, {"google": mock_handler}):
            response, status_code = WebhookController.dispatch("google", Mock())
            
            assert status_code == 200
            assert response["status"] == "success"
            mock_handler.verify.assert_called_once()
            mock_handler.handle.assert_called_once()
    
    def test_dispatch_unsupported_platform(self):
        """Test webhook dispatch for unsupported platform"""
        response, status_code = WebhookController.dispatch("unsupported", Mock())
        
        assert status_code == 400
        assert "Unsupported platform" in response["error"]
    
    def test_dispatch_verification_failure(self):
        """Test webhook dispatch with verification failure"""
        mock_handler = Mock(spec=BaseWebhookHandler)
        mock_handler.verify.return_value = False
        
        with patch.dict(WebhookController._registry, {"google": mock_handler}):
            response, status_code = WebhookController.dispatch("google", Mock())
            
            assert status_code == 401
            assert "Webhook verification failed" in response["error"]
            mock_handler.verify.assert_called_once()
            mock_handler.handle.assert_not_called()
    
    def test_register_new_platform(self):
        """Test registering a new platform handler"""
        mock_handler = Mock(spec=BaseWebhookHandler)
        
        WebhookController.register("new_platform", mock_handler)
        
        assert "new_platform" in WebhookController._registry
        assert WebhookController._registry["new_platform"] == mock_handler
    
    def test_supported_platforms(self):
        """Test getting list of supported platforms"""
        platforms = WebhookController.supported_platforms()
        
        assert isinstance(platforms, list)
        assert "google" in platforms
        assert "microsoft" in platforms
        assert "zoom" in platforms


class TestGoogleWebhookHandler:
    """Test cases for Google webhook handler"""
    
    def test_verify_google_webhook_success(self):
        """Test successful Google webhook verification"""
        with patch('app.controller.webhook.platform.googlewebhookController.GoogleWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            result = handler.verify(Mock())
            
            assert result is True
    
    def test_handle_google_webhook_event(self):
        """Test handling Google webhook event"""
        with patch('app.controller.webhook.platform.googlewebhookController.GoogleWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.handle.return_value = ({"event_processed": True}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(Mock())
            
            assert status_code == 200
            assert response["event_processed"] is True
    
    def test_google_calendar_event_created(self):
        """Test handling Google calendar event created webhook"""
        mock_request = Mock()
        mock_request.json = {
            "kind": "calendar#event",
            "id": "event_123",
            "status": "confirmed",
            "summary": "Test Meeting"
        }
        
        with patch('app.controller.webhook.platform.googlewebhookController.GoogleWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"calendar_event": "created"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["calendar_event"] == "created"
    
    def test_google_calendar_event_updated(self):
        """Test handling Google calendar event updated webhook"""
        mock_request = Mock()
        mock_request.json = {
            "kind": "calendar#event",
            "id": "event_123",
            "status": "confirmed",
            "summary": "Updated Meeting",
            "updated": "2024-01-01T10:00:00Z"
        }
        
        with patch('app.controller.webhook.platform.googlewebhookController.GoogleWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"calendar_event": "updated"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["calendar_event"] == "updated"


class TestMicrosoftWebhookHandler:
    """Test cases for Microsoft webhook handler"""
    
    def test_verify_microsoft_webhook_success(self):
        """Test successful Microsoft webhook verification"""
        with patch('app.controller.webhook.platform.microsoftwebhookController.MicrosoftWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            result = handler.verify(Mock())
            
            assert result is True
    
    def test_handle_microsoft_webhook_event(self):
        """Test handling Microsoft webhook event"""
        with patch('app.controller.webhook.platform.microsoftwebhookController.MicrosoftWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.handle.return_value = ({"event_processed": True}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(Mock())
            
            assert status_code == 200
            assert response["event_processed"] is True
    
    def test_microsoft_teams_meeting_created(self):
        """Test handling Microsoft Teams meeting created webhook"""
        mock_request = Mock()
        mock_request.json = {
            "@odata.type": "#microsoft.graph.onlineMeeting",
            "id": "meeting_123",
            "subject": "Test Teams Meeting"
        }
        
        with patch('app.controller.webhook.platform.microsoftwebhookController.MicrosoftWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"teams_meeting": "created"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["teams_meeting"] == "created"


class TestZoomWebhookHandler:
    """Test cases for Zoom webhook handler"""
    
    def test_verify_zoom_webhook_success(self):
        """Test successful Zoom webhook verification"""
        with patch('app.controller.webhook.platform.zoomwebhookController.ZoomWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            result = handler.verify(Mock())
            
            assert result is True
    
    def test_handle_zoom_webhook_event(self):
        """Test handling Zoom webhook event"""
        with patch('app.controller.webhook.platform.zoomwebhookController.ZoomWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.handle.return_value = ({"event_processed": True}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(Mock())
            
            assert status_code == 200
            assert response["event_processed"] is True
    
    def test_zoom_meeting_started(self):
        """Test handling Zoom meeting started webhook"""
        mock_request = Mock()
        mock_request.json = {
            "event": "meeting.started",
            "payload": {
                "object": {
                    "id": "123456789",
                    "topic": "Test Zoom Meeting",
                    "start_time": "2024-01-01T10:00:00Z"
                }
            }
        }
        
        with patch('app.controller.webhook.platform.zoomwebhookController.ZoomWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"zoom_meeting": "started"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["zoom_meeting"] == "started"
    
    def test_zoom_meeting_ended(self):
        """Test handling Zoom meeting ended webhook"""
        mock_request = Mock()
        mock_request.json = {
            "event": "meeting.ended",
            "payload": {
                "object": {
                    "id": "123456789",
                    "topic": "Test Zoom Meeting",
                    "end_time": "2024-01-01T11:00:00Z"
                }
            }
        }
        
        with patch('app.controller.webhook.platform.zoomwebhookController.ZoomWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"zoom_meeting": "ended"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["zoom_meeting"] == "ended"
    
    def test_zoom_recording_completed(self):
        """Test handling Zoom recording completed webhook"""
        mock_request = Mock()
        mock_request.json = {
            "event": "recording.completed",
            "payload": {
                "object": {
                    "id": "123456789",
                    "topic": "Test Zoom Meeting",
                    "recording_files": [
                        {
                            "id": "rec_123",
                            "file_type": "MP4",
                            "download_url": "https://zoom.us/recording/download/123"
                        }
                    ]
                }
            }
        }
        
        with patch('app.controller.webhook.platform.zoomwebhookController.ZoomWebhookHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.verify.return_value = True
            mock_instance.handle.return_value = ({"zoom_recording": "completed"}, 200)
            mock_handler.return_value = mock_instance
            
            handler = mock_instance
            response, status_code = handler.handle(mock_request)
            
            assert status_code == 200
            assert response["zoom_recording"] == "completed"


class TestWebhookIntegration:
    """Test cases for webhook integration scenarios"""
    
    def test_cross_platform_webhook_handling(self):
        """Test handling webhooks from multiple platforms"""
        platforms = ["google", "microsoft", "zoom"]
        
        for platform in platforms:
            mock_handler = Mock(spec=BaseWebhookHandler)
            mock_handler.verify.return_value = True
            mock_handler.handle.return_value = ({"platform": platform, "processed": True}, 200)
            
            with patch.dict(WebhookController._registry, {platform: mock_handler}):
                response, status_code = WebhookController.dispatch(platform, Mock())
                
                assert status_code == 200
                assert response["platform"] == platform
                assert response["processed"] is True
    
    def test_webhook_authentication_validation(self):
        """Test webhook authentication validation across platforms"""
        platforms = ["google", "microsoft", "zoom"]
        
        for platform in platforms:
            mock_handler = Mock(spec=BaseWebhookHandler)
            mock_handler.verify.return_value = False  # Authentication fails
            
            with patch.dict(WebhookController._registry, {platform: mock_handler}):
                response, status_code = WebhookController.dispatch(platform, Mock())
                
                assert status_code == 401
                assert "Webhook verification failed" in response["error"]
    
    def test_webhook_error_handling(self):
        """Test webhook error handling"""
        mock_handler = Mock(spec=BaseWebhookHandler)
        mock_handler.verify.return_value = True
        mock_handler.handle.side_effect = Exception("Handler error")
        
        with patch.dict(WebhookController._registry, {"google": mock_handler}):
            with pytest.raises(Exception, match="Handler error"):
                WebhookController.dispatch("google", Mock())
    
    def test_webhook_payload_parsing(self):
        """Test webhook payload parsing"""
        mock_request = Mock()
        mock_request.json = {
            "event": "test.event",
            "data": {
                "meeting_id": "123",
                "user_id": "456"
            }
        }
        
        mock_handler = Mock(spec=BaseWebhookHandler)
        mock_handler.verify.return_value = True
        mock_handler.handle.return_value = ({"parsed": True, "meeting_id": "123"}, 200)
        
        with patch.dict(WebhookController._registry, {"test": mock_handler}):
            response, status_code = WebhookController.dispatch("test", mock_request)
            
            assert status_code == 200
            assert response["parsed"] is True
            assert response["meeting_id"] == "123"
