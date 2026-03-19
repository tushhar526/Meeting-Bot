"""
Integrated Meeting Bot Cron for Flask App
Automatically starts when Flask server starts
"""

import os
import sys
import threading
import time
import logging
import traceback
from datetime import datetime, timezone, timedelta

# Try to import apscheduler, handle gracefully if not available
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    print("Warning: APScheduler not available. Cron functionality will be disabled.")
    print("Install with: pip install apscheduler")

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.extension import db
from app.models.userIntegrationModel import UserIntegration
from app.models.userModel import userModel
from app.services.CalendarServiceFactory import CalendarServiceFactory
from app.logic.BaseBot import BaseBot
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MeetingBotCron:
    """Integrated cron scheduler for Flask app"""
    
    def __init__(self, app=None):
        self.scheduler = None
        self.factory = CalendarServiceFactory()
        self.app = app
        self.active_bots = {}
        self.scheduled_jobs = {}
        self.scheduled_meeting_links = set()  # Track scheduled meeting links to prevent duplicates
        self.joined_meetings = set()
        self.user = None
        self.user_integrations = []
        
        # Only initialize scheduler if apscheduler is available
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            logger.info("MeetingBotCron initialized with APScheduler")
        else:
            logger.warning("MeetingBotCron initialized without APScheduler - cron functionality disabled")
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize cron with Flask app"""
        self.app = app
        
        if not APSCHEDULER_AVAILABLE:
            logger.warning("Cannot start cron - APScheduler not available")
            return False
        
        try:
            with app.app_context():
                # Enable SQLite WAL mode for concurrent access
                if db.engine.url.drivername == 'sqlite':
                    db.engine.execute("PRAGMA journal_mode=WAL")
                    logger.info("SQLite WAL mode enabled for concurrent access")
                
                # Start scheduler
                self.scheduler.start()
                logger.info("Meeting Bot Cron started successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start Meeting Bot Cron: {e}")
            return False
    
    def initialize(self):
        """Initialize the scheduler"""
        # Get user and integrations
        username = "gachaGOAT"
        user = userModel.query.filter_by(username=username, is_deleted=False).first()
        
        if not user:
            logger.error(f"User '{username}' not found!")
            return False
        
        self.user = user
        
        # Get integrations
        integrations = UserIntegration.query.filter_by(
            user_id=user.user_id,
            is_active=True
        ).all()
        
        if not integrations:
            logger.error("No active integrations found!")
            return False
        
        self.user_integrations = integrations
        
        return True
    
    def refresh_integration_token(self, integration):
        """Refresh expired token for an integration"""
        try:
            # Import controller to use its refresh method
            from app.controller.MultiPlatformCalendarController import MultiPlatformCalendarController
            
            controller = MultiPlatformCalendarController()
            
            if not integration.refresh_token:
                logger.error(f"   ❌ No refresh token for {integration.platform}")
                return None
            
            # Get client credentials for token refresh
            client_credentials = {}
            if integration.platform == 'google':
                client_credentials = {
                    'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
                    'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET')
                }
            elif integration.platform == 'microsoft':
                client_credentials = {
                    'MICROSOFT_CLIENT_ID': os.getenv('MICROSOFT_CLIENT_ID'),
                    'MICROSOFT_CLIENT_SECRET': os.getenv('MICROSOFT_CLIENT_SECRET')
                }
            elif integration.platform == 'zoom':
                client_credentials = {
                    'ZOOM_CLIENT_ID': os.getenv('ZOOM_CLIENT_ID'),
                    'ZOOM_CLIENT_SECRET': os.getenv('ZOOM_CLIENT_SECRET')
                }
            
            # Refresh the token using controller
            new_tokens = controller.refresh_token(
                integration.platform, 
                integration.refresh_token, 
                **client_credentials
            )
            
            # Update integration in database
            integration.update_tokens(
                access_token=new_tokens['access_token'],
                refresh_token=new_tokens.get('refresh_token', integration.refresh_token),
                expires_in=new_tokens.get('expires_in', 3600)
            )
            db.session.commit()
            
            logger.info(f"   ✅ Refreshed expired token for {integration.platform}")
            return integration.access_token
            
        except Exception as e:
            logger.error(f"   ❌ Failed to refresh {integration.platform} token: {e}")
            return None
    
    def get_upcoming_meetings(self):
        """Get all upcoming meetings from all platforms using new architecture"""
        all_meetings = []
        
        # Get all active integrations
        self.user_integrations = UserIntegration.query.filter_by(is_active=True).all()
        
        for integration in self.user_integrations:
            try:
                # Check if token is expired and refresh if needed
                access_token = integration.access_token
                if integration.is_expired():
                    access_token = self.refresh_integration_token(integration)
                    if not access_token:
                        continue
                
                # Get calendar service
                calendar_service = self.factory.create_service(integration.platform)
                
                # Configure platform-specific credentials (like the controller does)
                if integration.platform == 'google':
                    if hasattr(calendar_service, 'GOOGLE_CLIENT_ID'):
                        calendar_service.GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
                    if hasattr(calendar_service, 'GOOGLE_CLIENT_SECRET'):
                        calendar_service.GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
                elif integration.platform == 'microsoft':
                    if hasattr(calendar_service, 'MICROSOFT_CLIENT_ID'):
                        calendar_service.MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID')
                    if hasattr(calendar_service, 'MICROSOFT_CLIENT_SECRET'):
                        calendar_service.MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET')
                elif integration.platform == 'zoom':
                    if hasattr(calendar_service, 'ZOOM_CLIENT_ID'):
                        calendar_service.ZOOM_CLIENT_ID = os.getenv('ZOOM_CLIENT_ID')
                    if hasattr(calendar_service, 'ZOOM_CLIENT_SECRET'):
                        calendar_service.ZOOM_CLIENT_SECRET = os.getenv('ZOOM_CLIENT_SECRET')
                
                try:
                    # Use new architecture's get_upcoming_meetings which handles IST conversion
                    meetings = calendar_service.get_upcoming_meetings(
                        access_token,
                        integration.refresh_token,
                        days_ahead=1  # Next 24 hours
                    )
                    
                    # Process meetings directly
                    for meeting in meetings:
                        try:
                            # Calculate time until meeting using IST times
                            from datetime import datetime, timezone
                            import pytz
                            
                            ist = pytz.timezone('Asia/Kolkata')
                            now_ist = datetime.now(ist)
                            
                            # Parse meeting start time (should be in IST already with timezone)
                            meeting_start_str = meeting.get('start_time', '')
                            if meeting_start_str:
                                # Handle both timezone-aware and naive strings
                                if '+' in meeting_start_str or meeting_start_str.endswith('Z'):
                                    meeting_start = datetime.fromisoformat(meeting_start_str.replace('Z', '+00:00'))
                                else:
                                    # Naive string - assume IST
                                    meeting_start = ist.localize(datetime.fromisoformat(meeting_start_str))
                                
                                time_until = (meeting_start - now_ist).total_seconds() / 60  # minutes
                                
                                if 0 <= time_until <= 1440:  # Within next 24 hours
                                    # Create unique meeting ID
                                    meeting_id = f"{integration.platform}_{meeting.get('id')}_{meeting_start.strftime('%Y%m%d_%H%M')}"
                                    
                                    all_meetings.append({
                                        'meeting_id': meeting_id,
                                        'id': meeting.get('id'),
                                        'title': meeting.get('title', 'No Title'),
                                        'start_time': meeting_start,
                                        'end_time': meeting.get('end_time', ''),
                                        'meeting_link': meeting.get('meeting_link', ''),
                                        'platform': integration.platform,
                                        'time_until_minutes': time_until,
                                        'integration': integration
                                    })
                        except Exception as meeting_error:
                            continue
                    
                except Exception as api_error:
                    continue
                        
            except Exception as e:
                continue
        
        return all_meetings
    
    def parse_event(self, event, platform, integration):
        """Parse calendar event and extract meeting info"""
        try:
            # Get event time - handle different field names
            event_time = None
            if 'start_time' in event:
                event_time = event['start_time']
            elif 'start' in event and isinstance(event['start'], dict):
                event_time = event['start'].get('datetime') or event['start'].get('date')
            elif 'start' in event:
                event_time = event['start']
            
            if not event_time:
                logger.warning(f"   ⚠️  No start time found in event: {event.get('title', 'unknown')}")
                return None
            
            # Parse event time to UTC datetime
            event_dt = None
            if isinstance(event_time, str):
                try:
                    # Handle different datetime formats
                    if event_time.endswith('Z'):
                        event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    elif '+' in event_time or '-' in event_time[-6:]:
                        # Already has timezone info
                        event_dt = datetime.fromisoformat(event_time)
                    else:
                        # Naive datetime - assume UTC
                        event_dt = datetime.fromisoformat(event_time)
                        event_dt = event_dt.replace(tzinfo=timezone.utc)
                    
                    # Convert to UTC for consistent comparison
                    if event_dt.tzinfo is None:
                        event_dt = event_dt.replace(tzinfo=timezone.utc)
                    else:
                        event_dt = event_dt.astimezone(timezone.utc)
                        
                except Exception as parse_error:
                    logger.warning(f"   ⚠️  Could not parse time '{event_time}': {parse_error}")
                    return None
            elif isinstance(event_time, datetime):
                event_dt = event_time
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                else:
                    event_dt = event_dt.astimezone(timezone.utc)
            else:
                logger.warning(f"   ⚠️  Unsupported time format: {type(event_time)}")
                return None
            
            # Calculate time until meeting (both in UTC)
            now_utc = datetime.now(timezone.utc)
            try:
                time_until = event_dt - now_utc
            except Exception as time_error:
                logger.error(f"   ❌ Error calculating time difference: {time_error}")
                logger.error(f"   event_dt: {event_dt}, timezone: {event_dt.tzinfo}")
                logger.error(f"   now_utc: {now_utc}, timezone: {now_utc.tzinfo}")
                return None
            
            if time_until.total_seconds() < 0:
                logger.info(f"   ✅ Meeting already passed: {event.get('title', 'unknown')} (was {int(abs(time_until.total_seconds()) / 60)} minutes ago)")
                return None  # Meeting already passed
            
            # Create unique meeting ID
            meeting_id = f"{platform}_{event_dt.strftime('%Y%m%d_%H%M')}_{event.get('title', 'unknown')[:20]}"
            
            # Get meeting link from various possible fields
            meeting_link = None
            if 'meeting_link' in event:
                meeting_link = event['meeting_link']
            elif 'hangoutLink' in event:
                meeting_link = event['hangoutLink']
            elif 'join_url' in event:
                meeting_link = event['join_url']
            
            return {
                'meeting_id': meeting_id,
                'platform': platform,
                'integration': integration,
                'title': event.get('title', event.get('subject', 'No title')),
                'start_time': event_dt,  # Always UTC
                'time_until_minutes': time_until.total_seconds() / 60,
                'meeting_link': meeting_link,
                'event': event
            }
            
        except Exception as e:
            logger.warning(f"   ⚠️  Error parsing event: {e}")
            logger.warning(f"   Event data: {event}")
            return None
    
    def schedule_meeting_bot(self, meeting):
        """Schedule a bot to join a meeting 5 minutes before it starts, or join immediately if already past"""
        meeting_time = meeting['start_time']
        bot_start_time = meeting_time - timedelta(minutes=5)
        
        # Ensure bot_start_time is timezone-aware
        if bot_start_time.tzinfo is None:
            bot_start_time = bot_start_time.replace(tzinfo=timezone.utc)
        
        # Check if already scheduled (by meeting link - handles same meeting across platforms)
        meeting_link = meeting.get('meeting_link', '')
        
        # Check in-memory by meeting link
        if meeting_link and meeting_link in self.scheduled_meeting_links:
            return
        
        # Check database for existing scheduled job (persists across restarts)
        from app.models.jobModel import JobModel
        existing_job = JobModel.query.filter_by(
            meeting_link=meeting_link
        ).first()
        
        if existing_job:
            # Already has a job record, skip
            self.scheduled_meeting_links.add(meeting_link)
            return
        
        # Use same timezone as meeting_time for comparison
        now = datetime.now(meeting_time.tzinfo) if meeting_time.tzinfo else datetime.now(timezone.utc)
        
        # If bot start time has passed but meeting hasn't started yet, join immediately
        if bot_start_time <= now:
            # Check if meeting is still ongoing (within 30 min of start)
            meeting_end_buffer = meeting_time + timedelta(minutes=30)
            if now <= meeting_end_buffer:
                logger.info(f"⚡ Bot joining '{meeting['title']}' immediately (missed 5-min early window)")
                self.scheduled_meeting_links.add(meeting_link)
                self.create_and_start_bot(meeting)
            return
        
        # Schedule the bot job
        job_id = f"bot-{meeting['meeting_id']}"
        
        try:
            self.scheduler.add_job(
                func=self.create_and_start_bot,
                trigger='date',
                run_date=bot_start_time,
                args=[meeting],
                id=job_id,
                name=f"Bot for {meeting['title']}",
                misfire_grace_time=300  # 5 minutes grace period
            )
            
            self.scheduled_jobs[meeting['meeting_id']] = job_id
            self.scheduled_meeting_links.add(meeting_link)  # Track this meeting link
            
            logger.info(f"📅 Bot scheduled for '{meeting['title']}' at {meeting_time.strftime('%H:%M')} (joining 5 min early)")
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule bot for {meeting['title']}: {e}")
    
    def create_and_start_bot(self, meeting):
        """Create and start a bot for a meeting"""
        logger.info(f"🤖 Bot joining '{meeting['title']}'...")
        
        if not meeting['meeting_link']:
            logger.error(f"❌ No meeting link for {meeting['title']}")
            return
        
        try:
            # Detect platform from meeting link
            meeting_link = meeting['meeting_link']
            if 'zoom.us' in meeting_link:
                platform = 'zoom'
            elif 'meet.google.com' in meeting_link:
                platform = 'google_meet'
            elif 'teams.microsoft.com' in meeting_link or 'teams.live.com' in meeting_link:
                platform = 'teams'
            else:
                platform = meeting.get('platform', 'unknown')
            
            # Create Flask app context for database operations
            with self.app.app_context():
                from app.models.jobModel import JobModel
                
                # Create job record in database first
                job = JobModel(
                    job_url=meeting_link,
                    status="Bot Created",
                    platform=platform,
                    meeting_title=meeting['title'],
                    meeting_link=meeting_link,
                    scheduled_time=meeting['start_time'],
                    user_id=self.user.user_id
                )
                job.save()
                
                job_id = job.job_id
                output_path = f"/tmp/meeting_bot_{job_id}"
                
                # Update job with audio path
                job.audio_path = output_path
                db.session.commit()
                
                # Initialize BaseBot with meeting details
                bot = BaseBot(
                    job_id=job_id,
                    meeting_url=meeting_link,
                    output_path=output_path
                )
                
                # Run bot in a separate thread with proper context
                def run_bot_with_context():
                    with self.app.app_context():
                        try:
                            bot.run()
                        except Exception as e:
                            logger.error(f"❌ Bot error for {meeting['title']}: {e}")
                        finally:
                            # Clean up from active bots
                            if meeting['meeting_id'] in self.active_bots:
                                del self.active_bots[meeting['meeting_id']]
                
                bot_thread = threading.Thread(
                    target=run_bot_with_context,
                    daemon=True,
                    name=f"Bot-{job_id}"
                )
                
                bot_thread.start()
                
                # Store bot thread for management
                self.active_bots[meeting['meeting_id']] = {
                    'bot': bot,
                    'thread': bot_thread,
                    'job_id': job_id,
                    'meeting': meeting,
                    'started_at': datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to start bot for {meeting['title']}: {e}")
    
    def monitor_and_schedule(self):
        """Main monitoring function - check meetings and schedule bots"""
        logger.info("🔍 Checking for upcoming meetings...")
        try:
            # Need Flask app context for database operations
            with self.app.app_context():
                meetings = self.get_upcoming_meetings()
                
                if not meetings:
                    return
                
                for meeting in meetings:
                    # Schedule bot if meeting is in the future
                    if meeting['time_until_minutes'] > 0:
                        self.schedule_meeting_bot(meeting)
            
        except Exception as e:
            logger.error(f"❌ Error in monitor_and_schedule: {e}")
    
    def start_scheduler(self):
        """Start the cron scheduler"""
        logger.info("🤖 Meeting Bot Cron started - monitoring every 2 minutes")
        
        # Add monitoring job - run every 2 minutes
        self.scheduler.add_job(
            func=self.monitor_and_schedule,
            trigger=IntervalTrigger(minutes=2),
            id='monitor-meetings',
            name='Monitor meetings and schedule bots'
        )
        
        # Start the scheduler
        self.scheduler.start()
        
        # Run initial check
        self.monitor_and_schedule()
    
    def shutdown(self):
        """Shutdown the scheduler and clean up"""
        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        # Stop all active bots
        for meeting_id, bot_info in self.active_bots.items():
            try:
                bot_info['bot'].stop()
            except Exception as e:
                pass
        
        logger.info("🛑 Meeting Bot Cron stopped")


# Initialize the cron instance
meeting_bot_cron = MeetingBotCron()
