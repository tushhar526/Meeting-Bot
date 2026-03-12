import logging
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.webhookModel import WebhookModel
from app.models.jobModel import JobModel
from app.services.calendarServiceFactory import CalendarServiceFactory
from app.extension import db

logger = logging.getLogger(__name__)


class WebhookScheduler:
    def __init__(self):
        self.calendar_services = {}
    
    def _get_calendar_service(self, platform: str):
        """Get or create calendar service for platform"""
        if platform not in self.calendar_services:
            self.calendar_services[platform] = CalendarServiceFactory.create_service(platform)
        return self.calendar_services[platform]
    
    def check_calendar_webhooks(self):
        """Check all active calendar webhooks and create jobs for upcoming meetings"""
        try:
            webhooks = WebhookModel.query.filter_by(
                is_active=True, 
                auto_create_jobs=True
            ).all()
            
            for webhook in webhooks:
                if webhook.access_token and webhook.refresh_token:
                    self._process_webhook(webhook)
                    
        except Exception as e:
            logger.error(f"Error in webhook scheduler: {e}")
    
    def _process_webhook(self, webhook: WebhookModel):
        """Process a single webhook and create jobs for upcoming meetings"""
        try:
            # Get calendar service for this platform
            calendar_service = self._get_calendar_service(webhook.platform)
            
            # Configure service with credentials if needed
            if webhook.platform in ['microsoft', 'zoom']:
                self._configure_service(calendar_service, webhook)
            
            # Get upcoming meetings
            meetings = calendar_service.get_upcoming_meetings(
                access_token=webhook.access_token,
                refresh_token=webhook.refresh_token,
                days_ahead=1  # Check next 24 hours
            )
            
            for meeting in meetings:
                if self._should_create_job(meeting, webhook):
                    job = self._create_job_from_meeting(meeting, webhook.user_id)
                    
                    if job:
                        # Send webhook notification
                        self._send_webhook_notification(webhook, job, meeting)
                        
                        # Update last triggered
                        webhook.last_triggered = datetime.now()
                        webhook.save()
                        
                        logger.info(f"Created job {job.job_id} for meeting: {meeting['title']}")
                        
        except Exception as e:
            logger.error(f"Error processing webhook {webhook.webhook_id}: {e}")
    
    def _configure_service(self, service, webhook: WebhookModel):
        """Configure calendar service with platform-specific credentials"""
        if hasattr(service, 'client_id'):
            service.client_id = webhook.client_id
        if hasattr(service, 'client_secret'):
            service.client_secret = webhook.client_secret
        if hasattr(service, 'redirect_uri'):
            service.redirect_uri = webhook.redirect_uri
    
    def _should_create_job(self, meeting: Dict, webhook: WebhookModel) -> bool:
        """Check if a job should be created for this meeting"""
        try:
            # Parse meeting start time
            start_time = datetime.fromisoformat(meeting['start_time'].replace('Z', '+00:00'))
            now = datetime.now()
            
            # Check if meeting is within the buffer time
            time_until_meeting = (start_time - now).total_seconds() / 60
            
            if time_until_meeting <= webhook.meeting_start_buffer_minutes and time_until_meeting > 0:
                # Check if job already exists
                existing_job = JobModel.query.filter_by(
                    job_url=meeting['meeting_link'],
                    status="Registered"
                ).first()
                
                return existing_job is None
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking if job should be created: {e}")
            return False
    
    def _create_job_from_meeting(self, meeting: Dict, user_id: int) -> JobModel:
        """Create a job from a meeting"""
        try:
            job = JobModel(
                job_url=meeting['meeting_link'],
                platform=meeting['platform'],
                status="Registered",
                user_id=user_id
            )
            
            job.save()
            return job
            
        except Exception as e:
            logger.error(f"Error creating job from meeting: {e}")
            return None
    
    def _send_webhook_notification(self, webhook: WebhookModel, job: JobModel, meeting: Dict):
        """Send webhook notification about job creation"""
        try:
            if not webhook.webhook_url:
                return
                
            payload = {
                "event": "job_created",
                "job": {
                    "id": job.job_id,
                    "meeting_url": job.job_url,
                    "platform": job.platform,
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None
                },
                "meeting": {
                    "id": meeting.get('id'),
                    "title": meeting.get('title'),
                    "start_time": meeting.get('start_time'),
                    "end_time": meeting.get('end_time'),
                    "meeting_link": meeting.get('meeting_link'),
                    "platform": meeting.get('platform')
                },
                "webhook_id": webhook.webhook_id,
                "timestamp": datetime.now().isoformat()
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            if webhook.webhook_secret:
                headers['X-Webhook-Secret'] = webhook.webhook_secret
            
            response = requests.post(
                webhook.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook notification sent successfully to {webhook.webhook_url}")
            else:
                logger.warning(f"Webhook notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    def register_webhook(self, user_id: int, webhook_url: str, platform: str, event_types: List[str], 
                        calendar_email: str = None, access_token: str = None, 
                        refresh_token: str = None, webhook_secret: str = None,
                        client_id: str = None, client_secret: str = None, redirect_uri: str = None,
                        auto_create_jobs: bool = True, check_interval_minutes: int = 30,
                        meeting_start_buffer_minutes: int = 5) -> WebhookModel:
        """Register a new webhook"""
        try:
            # Validate platform
            supported_platforms = CalendarServiceFactory.get_supported_platforms()
            if platform not in supported_platforms:
                raise ValueError(f"Unsupported platform: {platform}. Supported platforms: {supported_platforms}")
            
            webhook = WebhookModel(
                user_id=user_id,
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                event_types=json.dumps(event_types),
                platform=platform,
                calendar_email=calendar_email,
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                auto_create_jobs=auto_create_jobs,
                check_interval_minutes=check_interval_minutes,
                meeting_start_buffer_minutes=meeting_start_buffer_minutes
            )
            
            webhook.save()
            logger.info(f"Webhook registered: {webhook.webhook_id} for platform: {platform}")
            return webhook
            
        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            raise
    
    def update_webhook(self, webhook_id: int, **kwargs) -> bool:
        """Update an existing webhook"""
        try:
            webhook = WebhookModel.query.get(webhook_id)
            if not webhook:
                return False
                
            for key, value in kwargs.items():
                if hasattr(webhook, key):
                    setattr(webhook, key, value)
            
            webhook.save()
            logger.info(f"Webhook updated: {webhook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating webhook: {e}")
            return False
    
    def delete_webhook(self, webhook_id: int) -> bool:
        """Delete a webhook"""
        try:
            webhook = WebhookModel.query.get(webhook_id)
            if not webhook:
                return False
                
            db.session.delete(webhook)
            db.session.commit()
            logger.info(f"Webhook deleted: {webhook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
