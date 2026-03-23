# Webhook Flow Documentation - Active Version Backend

## Overview

The webhook system in the Active Version backend enables real-time notifications for calendar events from Google Calendar and Zoom. This system automatically creates jobs for upcoming meetings within a configurable buffer time, ensuring the meeting bot can prepare recordings and transcripts.

## Supported Platforms

- **Google Calendar**: Uses Google Calendar API watch channels
- **Zoom**: Uses Zoom webhooks for meeting events

## Architecture Components

### 1. WebhookModel (`app/models/webhookModel.py`)
Database model that stores webhook configurations:

- `webhook_url`: Endpoint URL for receiving notifications
- `platform`: Calendar platform (google/zoom)
- `access_token`/`refresh_token`: OAuth tokens
- `channel_id`/`resource_id`: Platform-specific webhook identifiers
- `auto_create_jobs`: Flag to automatically create bot jobs
- `meeting_start_buffer_minutes`: Time buffer before meeting start
- `is_active`: Webhook status

### 2. Webhook Receiver Routes (`app/routes/webhookReceieveRoutes.py`)
Handles incoming webhook notifications at `/webhooks/receive/{platform}`.

#### Zoom Webhook Processing
- **Endpoint**: `POST /webhooks/receive/zoom`
- **Verification**: HMAC-SHA256 signature verification using `ZOOM_SECRET_KEY`
- **Supported Events**:
  - `meeting.created`
  - `meeting.updated`
  - `meeting.started`
- **Processing**: Extracts meeting details and stores meeting information

#### Google Webhook Processing
- **Endpoint**: `POST /webhooks/receive/google`
- **Headers**: Uses Google-specific headers (`X-Goog-Channel-ID`, `X-Goog-Resource-ID`, etc.)
- **States**:
  - `sync`: Initial webhook activation confirmation
  - `exists`: Calendar event change notification
- **Processing**: Fetches event details, checks if it's a meeting, and creates jobs if within buffer time

### 3. Calendar Services (`app/services/platform/`)

#### BaseCalendarService (`app/services/base/BaseCalendarService.py`)
Abstract base class defining webhook interface:
- `create_webhook_channel()`: Creates webhook subscription
- `stop_webhook_channel()`: Removes webhook subscription

#### GoogleCalendarService
- Creates watch channels on `/calendars/primary/events/watch`
- Channel expires after 7 days (renewable)
- Monitors all calendar events

#### ZoomCalendarService
- Creates webhooks on `/users/me/webhooks`
- Monitors specific meeting events
- Requires secret key for signature verification

### 4. Controller (`app/controller/MultiPlatformCalendarController.py`)
Manages webhook lifecycle during calendar integration:

#### Authorization Callback (`handle_callback`)
1. Exchanges OAuth code for tokens
2. Creates webhook channel if supported
3. Returns webhook details (ID, resource ID, URL)

#### Disconnect (`disconnect_calendar`)
1. Stops webhook channel via platform service
2. Cleans up webhook records

### 5. Routes (`app/routes/multiPlatformCalendarRoutes.py`)
Integration endpoints that manage webhook persistence:

#### Authorization Callback Route
- Stores webhook configuration in database after successful OAuth
- Links webhook to user and platform
- Sets up auto-job creation parameters

#### Disconnect Route
- Stops active webhooks before deactivating integration
- Marks webhooks as inactive in database

## Complete Webhook Flow

### 1. Integration Setup
```
User initiates OAuth flow
    ↓
Frontend redirects to platform auth URL
    ↓
User grants permissions
    ↓
Platform redirects to callback URL with auth code
    ↓
Backend exchanges code for tokens
    ↓
Creates webhook channel via platform API
    ↓
Stores webhook config in WebhookModel
    ↓
Returns success to frontend
```

### 2. Webhook Activation
```
Platform creates webhook subscription
    ↓
Sends initial 'sync' notification (Google)
    ↓
Webhook marked as active
    ↓
Ready to receive event notifications
```

### 3. Event Processing
```
Calendar event occurs (meeting created/updated)
    ↓
Platform sends webhook to registered URL
    ↓
Backend verifies webhook signature (Zoom)
    ↓
Extracts event/meeting details
    ↓
Checks if event is a meeting
    ↓
Calculates time until meeting start
    ↓
If within buffer time AND auto_create_jobs enabled:
    Creates bot job for recording/transcription
    ↓
Stores meeting information
    ↓
Returns success response
```

### 4. Job Creation Logic
```python
# Check conditions for job creation
time_until_meeting = start_time_utc - now_utc
if (time_until_meeting <= buffer_minutes and
    time_until_meeting > 0 and
    no_existing_job and
    webhook.auto_create_jobs):
    create_job()
```

### 5. Webhook Cleanup
```
User disconnects calendar integration
    ↓
Stops webhook channel via platform API
    ↓
Marks webhook as inactive in database
    ↓
Removes integration record
```

## Configuration

### Environment Variables
- `ZOOM_SECRET_KEY`: Required for Zoom webhook signature verification
- `GOOGLE_CLIENT_ID`: OAuth client ID
- `GOOGLE_CLIENT_SECRET`: OAuth client secret

### Database Schema
The `webhooks` table stores all webhook configurations with platform-specific fields for Google (channel_id, resource_id) and Zoom (webhook_secret).

## Error Handling

- **Signature Verification**: Invalid Zoom webhooks return 401
- **Missing Webhooks**: Returns 404 if no active webhook found
- **Platform Errors**: Logs errors but doesn't fail entire process
- **Token Expiry**: Webhooks may need renewal (Google expires after 7 days)

## Monitoring

- All webhook events are logged with event type and processing status
- Failed webhook creations are logged as warnings
- Meeting storage confirmations logged as info

## Security

- Zoom webhooks use HMAC-SHA256 signature verification
- Google webhooks rely on channel/resource ID validation
- All webhook data includes user context for proper isolation

## Future Enhancements

- Webhook renewal automation (Google channels expire)
- Support for additional platforms (Microsoft Teams, etc.)
- Configurable event filtering
- Webhook health monitoring and alerting
