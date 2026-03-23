# Calendar Integration & Bot Job Creation Flow

This document explains the complete flow of calendar integration and how meeting bot jobs are created from calendar events.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   Calendar APIs │
│                 │    │                  │    │                 │
│ - OAuth Init    │◄──►│ - MultiPlatform  │◄──►│ - Google OAuth  │
│ - Event Display │    │   Calendar       │    │ - Microsoft     │
│ - Job Creation  │    │   Controller     │    │ - Zoom/Teams    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Backend Core  │
                       │                 │
                       │ - Job Models    │
                       │ - Bot Tasks     │
                       │ - Webhook System│
                       └─────────────────┘
```

## 1. Calendar Integration Flow

### 1.1 OAuth Authorization Flow

**Step 1: Initialize OAuth**
```http
POST /api/calendar/google/auth-url
{
  "redirect_uri": "http://localhost:5173/auth/callback"
}
```

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_security_token",
  "platform": "google"
}
```

**Step 2: User Authorization**
1. User clicks the authorization URL
2. Google asks for permission to access calendar
3. User grants permission
4. Google redirects to `redirect_uri` with authorization code

**Step 3: Exchange Code for Tokens**
```http
POST /api/calendar/google/exchange-code
{
  "code": "authorization_code_from_google",
  "state": "random_security_token"
}
```

**Response:**
```json
{
  "access_token": "ya29.access_token_here",
  "refresh_token": "1//refresh_token_here",
  "user_info": {
    "email": "user@gmail.com",
    "name": "User Name"
  }
}
```

### 1.2 Calendar Event Fetching

**Get Upcoming Meetings:**
```http
GET /api/calendar/google/events?days_ahead=7
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "events": [
    {
      "id": "event_123",
      "title": "Team Meeting",
      "start_time": "2026-03-12T10:00:00Z",
      "end_time": "2026-03-12T11:00:00Z",
      "meeting_link": "https://meet.google.com/abc-def-ghi",
      "platform": "google"
    }
  ]
}
```

## 2. Bot Job Creation Flow

### 2.1 Manual Job Creation

**From Frontend:**
```http
POST /api/bot/meeting/start
{
  "meeting_url": "https://meet.google.com/abc-def-ghi",
  "platform": "google"
}
```

**Backend Process:**
1. ✅ Validate JWT authentication
2. ✅ Extract user_id from token
3. ✅ Validate request data
4. ✅ Create JobModel record
5. ✅ Increment user's meeting count
6. ✅ Generate audio file path
7. ✅ Commit to database
8. ✅ Queue Celery task: `start_bot.delay(job_id, audio_path, meeting_url)`

### 2.2 Calendar-Triggered Job Creation

**From Calendar Event:**
```http
POST /api/calendar/google/events/create-job
{
  "event_id": "event_123",
  "access_token": "ya29.access_token_here",
  "refresh_token": "1//refresh_token_here"
}
```

**Backend Process:**
1. ✅ Validate tokens
2. ✅ Fetch event details from Google Calendar API
3. ✅ Extract meeting URL and platform
4. ✅ Create JobModel record
5. ✅ Queue Celery task for bot start

### 2.3 Webhook-Automated Job Creation

**Automated Process:**
1. **Cron Service** runs every minute
2. **Webhook Scheduler** checks active webhooks
3. **Calendar API** fetches upcoming meetings
4. **Meeting Filter** checks if meeting starts within buffer time
5. **Duplicate Check** prevents multiple jobs for same meeting
6. **Auto-Create Job** if conditions met

## 3. File Structure

```
app/
├── logic/
│   └── calendar.py                 # Core Google Calendar logic
├── services/
│   └── calendarServiceFactory.py   # Factory pattern for multi-platform
├── controller/
│   └── calendarController/
│       ├── googleCal.py           # Google-specific controller
│       └── multiPlatformCalendar.py # Multi-platform controller
├── routes/
│   ├── calendar.py                # Google calendar routes
│   └── multiPlatformCalendarRoutes.py # Multi-platform routes
├── models/
│   ├── webhookModel.py            # Webhook configurations
│   └── jobModel.py                # Job records
└── services/
    └── webhookScheduler.py        # Automated job creation
```

## 4. Key Components

### 4.1 CalendarServiceFactory
- **Purpose**: Factory pattern to create platform-specific calendar services
- **Supported Platforms**: Google, Microsoft (planned), Zoom (planned)
- **Usage**: `CalendarServiceFactory.create_service("google")`

### 4.2 MultiPlatformCalendarController
- **Purpose**: Unified controller for all calendar platforms
- **Methods**:
  - `get_auth_url(platform, redirect_uri)`
  - `exchange_code_for_tokens(platform, code)`
  - `get_upcoming_events(platform, access_token, refresh_token)`
  - `create_job_from_event(platform, event_id, tokens)`

### 4.3 WebhookScheduler
- **Purpose**: Automatic job creation from calendar events
- **Features**:
  - Checks webhooks every minute
  - Filters meetings by start time buffer
  - Prevents duplicate job creation
  - Handles token refresh automatically

## 5. Authentication Flow

### 5.1 JWT Authentication
- **Access Token**: 1 hour expiration, stored in HTTP-only cookies
- **Refresh Token**: 2 days expiration, stored in HTTP-only cookies
- **Location**: `JWT_TOKEN_LOCATION = "cookies"`
- **CORS**: `supports_credentials = True`

### 5.2 OAuth Token Storage
- **Access Token**: Used for API calls to Google Calendar
- **Refresh Token**: Used to get new access tokens
- **Storage**: Stored in WebhookModel for automated processing

## 6. Error Handling

### 6.1 Common Errors
- **401 Unauthorized**: JWT token expired or missing
- **400 Bad Request**: Missing required fields (meeting_url, platform)
- **409 Conflict**: Job already exists for this meeting
- **500 Internal Server Error**: Database or external API failures

### 6.2 Error Recovery
- **Token Refresh**: Automatic refresh token usage
- **Database Rollback**: Transaction rollback on errors
- **Retry Logic**: Multiple attempts for database operations

## 7. Configuration

### 7.1 Environment Variables
```bash
# Google OAuth
GOOGLE_CLIENT_ID = "your_google_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET = "your_google_GOOGLE_CLIENT_SECRET"

# JWT Configuration
JWT_SECRET_KEY = "32_character_minimum_secret"
JWT_TOKEN_LOCATION = "cookies"
JWT_COOKIE_SECURE = False
JWT_COOKIE_SAMESITE = "Lax"
JWT_ACCESS_TOKEN_EXPIRES = 1  # hours
JWT_REFRESH_TOKEN_EXPIRES = 2  # days
```

### 7.2 CORS Configuration
```python
CORS(app, supports_credentials=True, expose_headers=["Set-Cookie"])
```

## 8. Testing

### 8.1 Manual Testing
1. **Login**: Get JWT tokens
2. **Calendar Auth**: Get OAuth tokens
3. **Fetch Events**: Verify calendar access
4. **Create Job**: Test manual job creation
5. **Webhook Test**: Test automated job creation

### 8.2 API Testing
```bash
# Test Google OAuth
curl -X POST http://localhost:5000/api/calendar/google/auth-url

# Test job creation
curl -X POST http://localhost:5000/api/bot/meeting/start \
  -H "Content-Type: application/json" \
  -d '{"meeting_url": "https://meet.google.com/test", "platform": "google"}'
```

## 9. Monitoring & Debugging

### 9.1 Logging
- **Level**: INFO for normal operations, ERROR for failures
- **Format**: `%(asctime)s %(levelname)s %(name)s %(message)s`
- **File**: `app.log`

### 9.2 Key Log Messages
- `"Cron service started"` - Webhook scheduler running
- `"Created job {job_id} from meeting"` - Job created successfully
- `"Job already exists for meeting"` - Duplicate prevention
- `"Failed to refresh token"` - OAuth token issues

## 10. Security Considerations

### 10.1 Token Security
- **JWT Secret**: Minimum 32 characters
- **HTTP-Only Cookies**: Prevent XSS attacks
- **CSRF Protection**: Disabled for development
- **Secure Cookies**: Disabled for localhost

### 10.2 OAuth Security
- **State Parameter**: Prevents CSRF attacks
- **PKCE**: Recommended for mobile apps
- **Token Scope**: Minimum required permissions
- **Token Revocation**: Implement logout functionality

## 11. Performance Optimization

### 11.1 Database Optimization
- **Indexing**: Job URLs, user IDs, timestamps
- **Connection Pooling**: SQLAlchemy connection management
- **Transaction Management**: Proper commit/rollback

### 11.2 API Optimization
- **Caching**: Calendar event caching
- **Rate Limiting**: Prevent API abuse
- **Async Processing**: Celery for background tasks

## 12. Troubleshooting

### 12.1 Common Issues
1. **401 Errors**: Check JWT token expiration
2. **OAuth Failures**: Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
3. **Missing Events**: Check calendar permissions
4. **Duplicate Jobs**: Check webhook timing settings

### 12.2 Debug Steps
1. Check application logs
2. Verify environment variables
3. Test API endpoints manually
4. Check database state
5. Verify external API access

---

**Note**: This flow is designed to be extensible for additional calendar platforms (Microsoft, Zoom, Teams) through the factory pattern implementation.
