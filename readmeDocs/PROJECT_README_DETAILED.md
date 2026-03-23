# Meeting Bot Project - Complete Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Calendar Integration System](#calendar-integration-system)
4. [Webhook System](#webhook-system)
5. [Bot Creation with Playwright](#bot-creation-with-playwright)
6. [Audio Recording with FFmpeg & PulseAudio](#audio-recording-with-ffmpeg--pulseaudio)
7. [Docker Configuration](#docker-configuration)
8. [Database Schema](#database-schema)
9. [API Endpoints](#api-endpoints)
10. [Security & Authentication](#security--authentication)
11. [Deployment Guide](#deployment-guide)
12. [Troubleshooting](#troubleshooting)

## Project Overview

A comprehensive meeting automation system that integrates with multiple calendar platforms to automatically join virtual meetings, record audio sessions, and provide transcription services. The system uses browser automation, audio processing, and real-time webhook handling to deliver a seamless meeting recording experience.

### Key Features
- **Multi-Platform Support**: Google Calendar, Microsoft Teams, Zoom
- **Automated Meeting Joining**: Browser-based bot automation
- **Audio Recording**: High-quality audio capture with FFmpeg
- **Real-time Processing**: Webhook-driven event handling
- **Subscription Management**: Tiered access control
- **Scalable Architecture**: Docker-based deployment

## Architecture

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Calendar      │    │    Webhook      │    │   Browser       │
│   Platforms     │───▶│   Receiver      │───▶│   Automation    │
│                 │    │                 │    │   (Playwright)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask API     │    │   Celery Tasks   │    │   Audio         │
│   Server        │◀───│   Queue         │◀───│   Recording     │
│                 │    │   (Redis)       │    │   (FFmpeg)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   File Storage  │    │   PulseAudio    │
│   (SQLite/PG)   │    │   (Recordings)  │    │   (Audio Mgmt)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Backend**: Flask, SQLAlchemy, Celery
- **Browser Automation**: Playwright
- **Audio Processing**: FFmpeg, PulseAudio
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Task Queue**: Redis + Celery
- **Containerization**: Docker & Docker Compose

## Calendar Integration System

### Supported Platforms

#### Google Calendar Integration
```python
# OAuth Flow Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# API Endpoints
GET /calendar/google/events
POST /calendar/google/events/create-job
GET /calendar/google/auth
```

**Features:**
- OAuth 2.0 authentication with token refresh
- Real-time event synchronization via webhooks
- Automatic meeting URL extraction
- Recurring meeting support

#### Microsoft Teams/Outlook Integration
```python
# Microsoft Graph API
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID")

# API Endpoints
GET /calendar/microsoft/events
POST /calendar/microsoft/events/create-job
GET /calendar/microsoft/auth
```

**Features:**
- Microsoft Graph API integration
- Teams meeting link detection
- Calendar event parsing
- Webhook subscription management

#### Zoom Integration
```python
# Zoom REST API
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")

# API Endpoints
GET /calendar/zoom/events
POST /calendar/zoom/events/create-job
GET /calendar/zoom/auth
```

**Features:**
- Zoom REST API integration
- Meeting ID extraction
- Webhook event handling
- Recurring meeting support

### Calendar Service Architecture

#### Event Processing Pipeline
```python
# app/services/calendarService.py
class CalendarService:
    def fetch_events(self, user_id, platform):
        """Fetch events from calendar platform"""
        pass
    
    def extract_meeting_url(self, event):
        """Extract meeting URL from event data"""
        pass
    
    def create_bot_job(self, user_id, event):
        """Create bot recording job from event"""
        pass
```

#### Webhook Event Handlers
```python
# app/controller/webhook/
class GoogleWebhookController:
    def handle_event_created(self, payload):
        """Handle new calendar event creation"""
        pass
    
    def handle_event_updated(self, payload):
        """Handle calendar event updates"""
        pass
    
    def handle_event_deleted(self, payload):
        """Handle calendar event cancellation"""
        pass
```

## Webhook System

### Webhook Architecture

#### Receiver Endpoints
```python
# Webhook receiver routes
@app.route('/webhook/google', methods=['POST'])
def google_webhook():
    """Handle Google Calendar webhooks"""
    pass

@app.route('/webhook/microsoft', methods=['POST'])
def microsoft_webhook():
    """Handle Microsoft Graph webhooks"""
    pass

@app.route('/webhook/zoom', methods=['POST'])
def zoom_webhook():
    """Handle Zoom webhooks"""
    pass
```

#### Event Processing Flow
```
Webhook Received → Validate Signature → Parse Event → 
Check User Subscription → Create Bot Job → 
Schedule Celery Task → Update Database
```

#### Webhook Security
- **Signature Validation**: HMAC verification
- **IP Whitelisting**: Platform-specific IP ranges
- **Rate Limiting**: Prevent webhook abuse
- **Event Validation**: Schema verification

### Webhook Configuration

#### Google Calendar Webhooks
```python
# Webhook registration
webhook_data = {
    "id": "unique-webhook-id",
    "type": "web_hook",
    "address": "https://your-domain.com/webhook/google",
    "expiration": timestamp + 604800,  # 7 days
    "params": {
        "ttl": "604800"
    }
}
```

#### Microsoft Graph Webhooks
```python
# Subscription creation
subscription = {
    "changeType": "created,updated,deleted",
    "notificationUrl": "https://your-domain.com/webhook/microsoft",
    "resource": "me/events",
    "expirationDateTime": expiration_time,
    "clientState": "secret_client_state"
}
```

#### Zoom Webhooks
```python
# Event subscription
event_subscription = {
    "event_types": ["meeting.created", "meeting.updated"],
    "endpoint_url": "https://your-domain.com/webhook/zoom",
    "authorization": {
        "signature_ttl": 300
    }
}
```

## Bot Creation with Playwright

### Browser Automation Framework

#### BaseBot Class
```python
# app/logic/BaseBot.py
class BaseBot:
    def __init__(self, job_id, meeting_url, output_path):
        self.job_id = job_id
        self.meeting_url = meeting_url
        self.output_path = output_path
        self.browser = None
        self.page = None
        self.handler = None
        self.recorder = AudioRecorder(job_id, output_path)
```

#### Platform Handlers
```python
# Platform-specific handlers
handlers = {
    "zoom.us": Zoom(url=self.meeting_url, page=self.page),
    "meet.google.com": Meet(self.meeting_url, page=self.page),
    "teams.live.com": Teams(url=self.meeting_url, page=self.page),
}
```

### Browser Configuration

#### Chrome Launch Options
```python
browser_args = [
    "--autoplay-policy=no-user-gesture-required",
    "--use-fake-ui-for-media-stream",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--enable-features=WebRTCPulseAudio",
    "--alsa-output-device=pulse",
    "--use-fake-device-for-media-stream",
    "--disable-blink-features=AutomationControlled",
    "--disable-background-media-suspend",
    "--start-maximized",
    "--use-gl=swiftshader"
]
```

#### Audio Environment Setup
```python
job_env = {
    **os.environ,
    "LD_PRELOAD": "libpulse.so.0",
    "ALSA_CONFIG_PATH": "/etc/asound.conf",
    "PULSE_SINK": self.recorder.get_sink_name,
    "PULSE_SERVER": "unix:/var/run/user/1000/pulse/native",
    "PULSE_LATENCY_MSEC": "30",
}
```

### Meeting Platform Handlers

#### Google Meet Handler
```python
# app/logic/meet.py
class Meet:
    def join(self):
        """Join Google Meet meeting"""
        # Navigate to meeting URL
        self.page.goto(self.url)
        
        # Handle permissions
        self._handle_audio_video_permissions()
        
        # Enter name and join
        self._enter_name_and_join()
        
        # Handle waiting room
        return self._handle_waiting_room()
    
    def detect_end(self):
        """Detect meeting end"""
        # Check participant count
        # Check for meeting end messages
        # Handle waiting room timeout
        pass
```

#### Zoom Handler
```python
# app/logic/zoom.py
class Zoom:
    def join(self):
        """Join Zoom meeting"""
        # Navigate to meeting URL
        # Handle launch meeting page
        # Join from browser option
        # Handle audio permissions
        pass
    
    def detect_end(self):
        """Detect Zoom meeting end"""
        # Check for "Leave meeting" indicators
        # Monitor participant count
        # Handle host-ended meetings
        pass
```

#### Microsoft Teams Handler
```python
# app/logic/teams.py
class Teams:
    def join(self):
        """Join Teams meeting"""
        # Navigate to meeting URL
        # Handle browser vs app choice
        # Join on web option
        # Handle audio setup
        pass
    
    def detect_end(self):
        """Detect Teams meeting end"""
        # Check for meeting end screen
        # Monitor participant list
        # Handle call termination
        pass
```

### Bot Execution Flow

#### Job Creation Process
```python
@celery.task
def start_bot(job_id, meeting_url, output_path):
    """Start meeting bot task"""
    bot = BaseBot(job_id, meeting_url, output_path)
    
    try:
        # Setup browser and audio
        bot.setup_driver()
        bot.setup_handler()
        
        # Join meeting
        if bot.join_meeting():
            # Start recording
            bot.recorder.start()
            
            # Monitor meeting
            bot.detect_meeting_end()
            
        return True
    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
        return False
    finally:
        bot.stop()
```

## Audio Recording with FFmpeg & PulseAudio

### PulseAudio Integration

#### Audio Sink Management
```python
# app/helper/recording.py
class PulseAudio:
    def __init__(self, job_id):
        self.job_id = job_id
        self.sink_name = f"sink_{self.job_id}"
        self.module_id = None
    
    def create_sink(self):
        """Create null sink for audio capture"""
        cmd = [
            "pactl", "load-module", "module-null-sink",
            f"sink_name={self.sink_name}",
            f'sink_properties=device.description="Meeting_{self.job_id}"'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            self.module_id = int(result.stdout.strip())
            return True
        return False
```

#### Monitor Device Setup
```python
def get_monitor(self):
    """Get monitor device for audio capture"""
    result = subprocess.run(
        ["pactl", "list", "sources", "short"],
        capture_output=True, text=True
    )
    
    for line in result.stdout.split("\n"):
        if f"{self.sink_name}.monitor" in line:
            return line.split()[1]
    return None
```

### FFmpeg Recording

#### Audio Configuration
```python
class AudioRecorder:
    def start(self):
        """Start FFmpeg recording"""
        # Create PulseAudio sink
        self.monitor_device = self.pulse_audio.get_monitor()
        
        # Set default sink to our recording sink
        subprocess.run(
            ["pactl", "set-default-sink", self.get_sink_name],
            stdout=subprocess.DEVNULL
        )
        
        # FFmpeg command
        cmd = [
            "ffmpeg", "-y", "-nostdin",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-f", "pulse",
            "-i", self.monitor_device,
            "-c:a", "libmp3lame",
            "-q:a", "2",  # Quality setting
            "-ar", "44100",  # Sample rate
            "-ac", "2",  # Stereo
            "-flush_packets", "1",
            self.output_path
        ]
        
        # Start recording process
        self.ffmpeg_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.DEVNULL,
            stderr=self.record_log,
            env={"PULSE_LATENCY_MSEC": "30"}
        )
```

#### Audio Quality Settings
```python
# High-quality audio recording parameters
AUDIO_CONFIG = {
    "codec": "libmp3lame",
    "quality": "2",  # 0-9, 2 is high quality
    "sample_rate": "44100",  # CD quality
    "channels": "2",  # Stereo
    "bitrate": "192k",  # High bitrate
    "format": "mp3"
}
```

### Audio Processing Pipeline

#### Recording Flow
```
Browser Audio → PulseAudio Sink → Monitor Device → 
FFmpeg Capture → MP3 Encoding → File Storage
```

#### Audio Diagnostics
```python
def diagnose_pulse_audio():
    """Diagnose PulseAudio setup"""
    # List available sinks
    subprocess.run(["pactl", "list", "sinks", "short"])
    
    # List available sources
    subprocess.run(["pactl", "list", "sources", "short"])
    
    # Get default sink/source
    subprocess.run(["pactl", "get-default-sink"])
    subprocess.run(["pactl", "get-default-source"])
```

## Docker Configuration

### Dockerfile Analysis

#### Base Image & Dependencies
```dockerfile
FROM python:3.11-slim

# System dependencies for audio and browser
RUN apt update && apt install -y \
    ffmpeg \
    pulseaudio \
    redis-server \
    pulseaudio-utils \
    libpulse0 \
    libpulse-dev \
    alsa-utils \
    libasound2 \
    libasound2-plugins \
    # Browser dependencies
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation
```

#### Audio Configuration
```dockerfile
# ALSA configuration for PulseAudio
RUN echo "pcm.!default { \
    type pulse \
    fallback 'sysdefault' \
    hint { \
    show on \
    description 'Default Audio Device (PulseAudio)' \
    } \
    } \
    ctl.!default { \
    type pulse \
    }" >/etc/asound.conf
```

#### User Setup
```dockerfile
# Create non-root user for audio access
RUN useradd -m -u 1000 -s /bin/bash audiobot

# Set up PulseAudio directory
RUN mkdir -p /var/run/user/1000/pulse && \
    chown -R audiobot:audiobot /app /var/run/user/1000

# Install Playwright browsers
RUN playwright install chromium chromium-headless-shell
```

### Docker Compose Configuration

#### Service Definition
```yaml
version: '3.8'

services:
  meeting-bot:
    build:
      context: .
      dockerfile: DockerFile
    container_name: meeting-bot
    
    volumes:
      - .:/app  # Development volume mount
    
    group_add:
      - audio  # Audio device access
    
    environment:
      - PULSE_SERVER=unix:/tmp/pulse/native
      - XDG_RUNTIME_DIR=/tmp
      - LANG=en_US.UTF-8
      - LC_ALL=en_US.UTF-8
      - PYTHONUNBUFFERED=1
    
    ports:
      - "5000:5000"
    
    stdin_open: true
    tty: true
```

#### Production Services
```yaml
# Additional services for production
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: meeting_bot
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: bot_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  celery-worker:
    build: .
    command: celery -A app.celery worker --loglevel=info
    depends_on:
      - redis
      - postgres
  
  celery-beat:
    build: .
    command: celery -A app.celery beat --loglevel=info
    depends_on:
      - redis
      - postgres
```

### Container Audio Setup

#### PulseAudio in Container
```bash
# Host PulseAudio socket sharing
docker run -v /run/user/1000/pulse:/tmp/pulse \
           -e PULSE_SERVER=unix:/tmp/pulse/native \
           meeting-bot
```

#### Audio Device Permissions
```bash
# Add container user to audio group
sudo usermod -a -G audio $USER

# Check audio devices
docker run --device /dev/snd \
           --group-add audio \
           meeting-bot
```

## Database Schema

### Core Models

#### User Model
```python
class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan_model.id'))
    is_active = db.Column(db.Boolean, default=True)
    trial_end_date = db.Column(db.DateTime)
    
    # Relationships
    jobs = db.relationship('JobModel', backref='user', lazy=True)
    integrations = db.relationship('UserIntegrationModel', backref='user', lazy=True)
```

#### Plan Model
```python
class PlanModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, default=0.0)
    max_meetings_per_month = db.Column(db.Integer)
    max_recording_duration = db.Column(db.Integer)  # minutes
    features = db.Column(db.JSON)  # Feature flags
    
    # Relationships
    users = db.relationship('UserModel', backref='plan', lazy=True)
```

#### Job Model
```python
class JobModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    meeting_url = db.Column(db.String(500), nullable=False)
    meeting_platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Created')
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    recording_path = db.Column(db.String(500))
    transcription = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('UserModel', backref='jobs', lazy=True)
```

#### Integration Model
```python
class UserIntegrationModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # google, microsoft, zoom
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    webhook_id = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
```

## API Endpoints

### Authentication Endpoints
```python
# User Authentication
POST /auth/signup          # User registration
POST /auth/login           # User login
POST /auth/logout          # User logout
POST /auth/refresh         # Token refresh
GET  /auth/profile         # User profile
```

### Bot Management Endpoints
```python
# Bot Operations
POST /bot/meeting/start           # Create and start meeting bot
GET  /bot/status/{job_id}         # Get job status
GET  /bot/recording/{job_id}      # Download recording
GET  /bot/stream/{job_id}         # Stream recording
DELETE /bot/job/{job_id}           # Cancel/delete job
GET  /bot/jobs                    # List user jobs
```

### Calendar Integration Endpoints
```python
# Google Calendar
GET  /calendar/google/events           # Fetch calendar events
POST /calendar/google/events/create-job # Create bot from event
GET  /calendar/google/auth             # OAuth initiation
GET  /calendar/google/callback         # OAuth callback

# Microsoft Calendar
GET  /calendar/microsoft/events           # Fetch calendar events
POST /calendar/microsoft/events/create-job # Create bot from event
GET  /calendar/microsoft/auth             # OAuth initiation
GET  /calendar/microsoft/callback         # OAuth callback

# Zoom
GET  /calendar/zoom/events           # Fetch meetings
POST /calendar/zoom/events/create-job # Create bot from meeting
GET  /calendar/zoom/auth             # OAuth initiation
GET  /calendar/zoom/callback         # OAuth callback
```

### Webhook Endpoints
```python
# Webhook Receivers
POST /webhook/google          # Google Calendar webhooks
POST /webhook/microsoft       # Microsoft Graph webhooks
POST /webhook/zoom            # Zoom webhooks
GET  /webhook/status          # Webhook system status
POST /webhook/check-meetings  # Manual meeting check
```

### Admin Endpoints
```python
# Super Admin
POST /superadmin/plans                    # Create subscription plans
GET  /superadmin/plans                    # List all plans
PUT  /superadmin/plans/{id}               # Update plan
DELETE /superadmin/plans/{id}             # Delete plan
POST /superadmin/users/{user_id}/plan/assign # Assign user plan
GET  /superadmin/users                    # List all users
GET  /superadmin/stats                    # System statistics
```

## Security & Authentication

### JWT Authentication
```python
# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
JWT_TOKEN_LOCATION = "cookies"
JWT_COOKIE_SECURE = False  # Set to True in production
JWT_COOKIE_SAMESITE = "Lax"
```

### Subscription-Based Access Control
```python
# Plan access decorator
@require_plan_access(feature="recording")
def create_meeting_bot():
    """Only users with recording feature can create bots"""
    pass

# Feature checking
def check_feature_access(user_id, feature):
    user = UserModel.query.get(user_id)
    return feature in user.plan.features
```

### Security Features
- **Token-Based Authentication**: JWT with refresh tokens
- **Plan Enforcement**: Feature-based access control
- **Rate Limiting**: API endpoint throttling
- **Input Validation**: Request sanitization
- **SQL Injection Protection**: SQLAlchemy ORM
- **CORS Configuration**: Cross-origin request handling

## Deployment Guide

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd meeting-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration

# Database setup
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create superadmin user
python create_superadmin.py

# Start services
redis-server
celery -A app.celery worker --loglevel=info &
celery -A app.celery beat --loglevel=info &
flask run
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose up --scale celery-worker=3
```

### Production Configuration
```bash
# Environment variables for production
DATABASE_URL=postgresql://user:pass@localhost/meeting_bot
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# SSL/TLS configuration
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues & Solutions

#### Bot Creation Fails
**Symptoms**: Bot job creation returns 403 or fails to start
**Causes**: 
- User subscription expired
- Plan doesn't include recording feature
- Meeting limit reached
**Solutions**:
```python
# Check user subscription
user = UserModel.query.get(user_id)
if not user.is_active or not user.plan:
    return {"error": "No active subscription"}, 403

# Check meeting limits
monthly_jobs = JobModel.query.filter(
    JobModel.user_id == user_id,
    JobModel.created_at >= datetime.now().replace(day=1)
).count()

if monthly_jobs >= user.plan.max_meetings_per_month:
    return {"error": "Meeting limit reached"}, 403
```

#### Webhook Not Receiving Events
**Symptoms**: No webhook events being processed
**Causes**:
- Webhook URL not accessible
- SSL certificate issues
- Platform webhook registration expired
**Solutions**:
```bash
# Test webhook accessibility
curl -X POST https://your-domain.com/webhook/google \
     -H "Content-Type: application/json" \
     -d '{"test": "event"}'

# Check SSL certificate
openssl s_client -connect your-domain.com:443

# Verify webhook registration
python scripts/manage_ngrok_webhooks.py --check
```

#### Audio Recording Issues
**Symptoms**: Recording files are empty or corrupted
**Causes**:
- PulseAudio not configured properly
- FFmpeg not installed
- Browser audio permissions
**Solutions**:
```bash
# Diagnose PulseAudio
python -c "from app.helper.recording import diagnose_pulse_audio; diagnose_pulse_audio()"

# Check FFmpeg installation
ffmpeg -version

# Test audio capture
ffmpeg -f pulse -i default test_output.mp3
```

#### Docker Audio Problems
**Symptoms**: No audio in Docker container
**Causes**:
- Missing audio device access
- PulseAudio socket not shared
- User permissions
**Solutions**:
```bash
# Add audio group access
docker run --group-add audio meeting-bot

# Share PulseAudio socket
docker run -v /run/user/1000/pulse:/tmp/pulse/native \
           -e PULSE_SERVER=unix:/tmp/pulse/native \
           meeting-bot

# Check audio devices in container
docker exec meeting-bot pactl list sinks
```

### Debug Commands
```bash
# Check Celery workers
celery -A app.celery inspect active
celery -A app.celery inspect stats

# Check Redis connection
redis-cli ping

# Database queries
flask shell
>>> from app.models import JobModel
>>> JobModel.query.filter_by(status='Failed').count()

# Test webhook endpoints
curl -X POST http://localhost:5000/webhook/check-meetings

# Monitor logs
tail -f app.log
docker logs meeting-bot
```

### Performance Monitoring
```python
# Key metrics to monitor
- Meeting creation success rate
- Average recording duration
- Webhook processing latency
- Celery queue length
- Database query performance
- Memory usage per bot
- FFmpeg process health
```

---

## Support & Maintenance

### Regular Maintenance Tasks
- Update webhook subscriptions (weekly)
- Clean up old recordings (monthly)
- Monitor subscription expirations (daily)
- Update browser dependencies (monthly)
- SSL certificate renewal (annually)

### Monitoring & Alerting
- Set up monitoring for bot success rates
- Alert on webhook failures
- Monitor storage usage
- Track API response times
- Database performance metrics

### Backup Strategy
- Database backups daily
- Recording file backups weekly
- Configuration version control
- Disaster recovery plan

---

This comprehensive documentation covers all major aspects of the Meeting Bot project, from calendar integration and webhook handling to browser automation, audio recording, and Docker deployment. The system is designed to be scalable, secure, and maintainable with proper error handling and monitoring capabilities.
