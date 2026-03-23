# Webhook System Documentation

## Overview

The Meeting Bot webhook system provides real-time calendar event monitoring and automatic bot creation for upcoming meetings. It integrates with Google Calendar (and supports Microsoft/Zoom) to detect meeting events and automatically create bot jobs to join those meetings.

## Architecture

### Components

1. **WebhookModel** (`app/models/webhookModel.py`)
   - Stores webhook configurations and credentials
   - Manages Google Calendar webhook channels
   - Tracks webhook status and expiration

2. **WebhookScheduler** (`app/services/webhookScheduler.py`)
   - Registers and manages webhooks
   - Processes calendar events and creates jobs
   - Handles webhook renewal and cleanup

3. **Webhook Routes** (`app/routes/webhookRoutes.py`)
   - REST API for webhook management
   - Registration, activation, and configuration

4. **Webhook Receiver** (`app/routes/webhookReceiverRoutes.py`)
   - Handles incoming webhook notifications
   - Processes Google Calendar push notifications
   - Validates and routes events to scheduler

5. **Calendar Integration** (`app/logic/calendar.py`)
   - Google Calendar API integration
   - Webhook channel creation and management
   - Event parsing and formatting

## Features

### ✅ Implemented Features

- **OAuth Integration**: Automatic webhook creation after Google Calendar connection
- **Real-time Monitoring**: Google Calendar push notifications
- **Meeting Detection**: Identifies meetings with video links (Google Meet, Zoom, etc.)
- **Automatic Bot Creation**: Creates jobs 5 minutes before meeting start
- **Token Management**: Handles access/refresh token rotation
- **Webhook Renewal**: Automatic renewal of expired webhook channels
- **Multi-platform Support**: Extensible architecture for Microsoft/Zoom
- **Error Handling**: Comprehensive logging and error recovery
- **Database Integration**: Full webhook lifecycle management

### 🔧 Configuration Options

```python
# Webhook Settings
auto_create_jobs: bool = True              # Automatically create bot jobs
check_interval_minutes: int = 30           # Polling interval (fallback)
meeting_start_buffer_minutes: int = 5      # Minutes before meeting to create bot
webhook_expiration_days: int = 7           # Google webhook expiration
```

## API Endpoints

### Webhook Management

#### Register Webhook
```http
POST /webhooks/register
Content-Type: application/json

{
    "user_id": 1,
    "platform": "google",
    "webhook_url": "https://your-domain.com/webhooks/receive/google",
    "calendar_email": "user@gmail.com",
    "access_token": "oauth_access_token",
    "refresh_token": "oauth_refresh_token",
    "auto_create_jobs": true,
    "meeting_start_buffer_minutes": 5,
    "check_interval_minutes": 30
}
```

#### Get User Webhooks
```http
GET /webhooks/user/{user_id}
Authorization: Bearer {jwt_token}
```

#### Update Webhook
```http
PUT /webhooks/{webhook_id}
Content-Type: application/json

{
    "auto_create_jobs": false,
    "meeting_start_buffer_minutes": 10
}
```

#### Delete Webhook
```http
DELETE /webhooks/{webhook_id}
Authorization: Bearer {jwt_token}
```

### Webhook Receiver

#### Google Calendar Webhook
```http
POST /webhooks/receive/google
Headers:
    X-Goog-Channel-ID: {channel_id}
    X-Goog-Resource-ID: {resource_id}
    X-Goog-Resource-State: {sync|exists}
    X-Goog-Resource-URI: {resource_uri}
```

## Database Schema

### Webhooks Table
```sql
CREATE TABLE webhooks (
    webhook_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    webhook_url VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255),
    event_types TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    last_triggered DATETIME,
    
    -- Calendar specific fields
    platform VARCHAR(50) DEFAULT 'google',
    calendar_email VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    GOOGLE_CLIENT_ID VARCHAR(255),
    GOOGLE_CLIENT_SECRET VARCHAR(255),
    redirect_uri VARCHAR(255),
    auto_create_jobs BOOLEAN DEFAULT TRUE,
    check_interval_minutes INTEGER DEFAULT 30,
    meeting_start_buffer_minutes INTEGER DEFAULT 5,
    
    -- Google webhook channel fields
    channel_id VARCHAR(255),
    resource_id VARCHAR(255),
    expiration DATETIME
);
```

## Workflow

### 1. OAuth Integration Flow

```
1. User connects Google Calendar via OAuth
2. System stores access/refresh tokens in UserIntegration
3. System automatically creates webhook in WebhookModel
4. Google Calendar webhook channel is established
5. Webhook starts monitoring calendar changes
```

### 2. Meeting Detection Flow

```
1. Google sends webhook notification for calendar change
2. Webhook receiver validates and processes notification
3. System fetches event details from Google Calendar API
4. Event is parsed to determine if it's a meeting
5. Meeting timing is checked against buffer window
6. If within buffer, bot job is automatically created
```

### 3. Bot Creation Flow

```
1. Meeting detected within buffer time (e.g., 5 minutes)
2. JobModel entry is created with meeting details
3. Bot is configured to join the meeting
4. Meeting link and credentials are stored
5. Bot joins meeting at scheduled time
```

## Integration with Calendar System

The webhook system integrates seamlessly with the multi-platform calendar system:

### Automatic Webhook Creation

After successful OAuth integration in `multiPlatformCalendarRoutes.py`:

```python
# Create webhook for automatic bot creation
webhook = webhook_scheduler.register_webhook(
    user_id=user_id,
    webhook_url=f"{base_url}/webhooks/receive/google",
    platform=platform,
    event_types=['meeting_created', 'meeting_updated'],
    calendar_email=result.get('user_email'),
    access_token=result['access_token'],
    refresh_token=result.get('refresh_token', ''),
    auto_create_jobs=True,
    meeting_start_buffer_minutes=5,
    check_interval_minutes=30
)
```

### Meeting Event Processing

The system identifies meetings by checking for:
- Google Meet links (`meet.google.com`)
- Google Hangout links (`hangouts.google.com`)
- Zoom links (`zoom.us`)
- Conference data in event
- Video meeting indicators

## Security Features

### Token Management
- Secure storage of OAuth tokens
- Automatic token refresh on expiration
- Encrypted credential storage

### Webhook Validation
- Channel ID validation
- Request signature verification (optional)
- Resource state validation

### Access Control
- User-specific webhook isolation
- JWT-based authentication for management APIs
- Permission-based access control

## Error Handling

### Common Errors and Solutions

1. **Webhook Channel Expiration**
   - Automatic renewal before expiration
   - Fallback to polling if webhook fails

2. **Token Refresh Failure**
   - Re-authentication required
   - User notification for re-authorization

3. **API Rate Limits**
   - Exponential backoff retry
   - Request queuing and throttling

4. **Meeting Detection Failures**
   - Multiple meeting link patterns
   - Fallback parsing methods

## Monitoring and Logging

### Log Levels
- **INFO**: Webhook registration, job creation, meeting detection
- **WARNING**: Token refresh, webhook renewal
- **ERROR**: API failures, authentication issues

### Key Metrics
- Webhook registration success rate
- Meeting detection accuracy
- Bot creation success rate
- Token refresh frequency

## Deployment Considerations

### Production Requirements

1. **Public Webhook URL**
   - HTTPS endpoint required
   - Static IP address recommended
   - DNS configuration

2. **Webhook Renewal**
   - Celery beat schedule for renewal
   - Monitoring for expired webhooks
   - Automated cleanup

3. **Scalability**
   - Horizontal scaling support
   - Database connection pooling
   - Redis for task queue

### Environment Variables

```bash
# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_SECRET_KEY=your-webhook-secret

# Google Calendar API
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Testing

### Local Development

1. **Use ngrok for public webhook URL**
   ```bash
   ngrok http 5000
   ```

2. **Test webhook creation**
   ```bash
   curl -X POST http://localhost:5000/webhooks/register \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "platform": "google", "webhook_url": "https://ngrok-url/webhooks/receive/google"}'
   ```

3. **Simulate webhook notifications**
   ```bash
   curl -X POST http://localhost:5000/webhooks/receive/google \
     -H "X-Goog-Channel-ID: test-channel" \
     -H "X-Goog-Resource-State: exists" \
     -H "X-Goog-Resource-URI: https://www.googleapis.com/calendar/v3/calendars/primary/events/event-id"
   ```

### Integration Testing

- Test complete OAuth → webhook → job creation flow
- Verify meeting detection with different link formats
- Test token refresh scenarios
- Validate webhook renewal process

## Future Enhancements

### Planned Features

1. **Multi-calendar Support**
   - Multiple calendar monitoring per user
   - Calendar-specific webhook configurations

2. **Advanced Meeting Detection**
   - AI-based meeting classification
   - Custom meeting pattern recognition

3. **Real-time Dashboard**
   - Webhook status monitoring
   - Meeting analytics and insights

4. **Enhanced Error Recovery**
   - Automatic webhook re-registration
   - Intelligent retry mechanisms

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**
   - Check webhook URL accessibility
   - Verify channel ID and resource ID
   - Confirm Google Calendar API permissions

2. **Bot Jobs Not Created**
   - Verify meeting detection logic
   - Check buffer time configuration
   - Review job creation logs

3. **Token Expiration Issues**
   - Monitor refresh token validity
   - Check OAuth scope permissions
   - Verify token storage encryption

### Debug Commands

```python
# Check webhook status
webhook = WebhookModel.query.filter_by(user_id=user_id, is_active=True).first()
print(f"Webhook expires at: {webhook.expiration}")

# Test webhook channel
calendar_service = CalendarServiceFactory.create_service('google')
result = calendar_service.create_webhook_channel(access_token, webhook_url)
print(f"Channel created: {result}")
```

## Support

For webhook system issues:
1. Check application logs for detailed error messages
2. Verify Google Calendar API configuration
3. Test webhook URL accessibility
4. Review OAuth token validity

---

**Last Updated**: March 2026  
**Version**: 2.0  
**Compatible**: Google Calendar API v3, Flask 2.0+
