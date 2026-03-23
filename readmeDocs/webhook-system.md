# Multi-Platform Calendar Webhook System

This system provides automatic job creation from calendar events using webhooks and cron jobs, supporting multiple calendar platforms including Google Calendar, Microsoft Graph (Outlook), and Zoom.

## Supported Platforms

- **Google Calendar** - Full OAuth integration with Google Calendar API
- **Microsoft Graph** - Integration with Outlook and Microsoft 365 calendars
- **Zoom** - Integration with Zoom meetings and calendar

## Features

- **Multi-Platform Support**: Handle calendar events from Google, Microsoft, and Zoom
- **Automatic Job Creation**: Automatically creates meeting bot jobs from upcoming calendar events
- **Webhook Notifications**: Sends webhook notifications when jobs are created
- **Configurable Timing**: Configurable buffer time before meeting start
- **Cron-based Processing**: Runs periodically to check for upcoming meetings
- **Webhook Management**: Full CRUD operations for webhook management
- **Platform-Specific Configuration**: Support for platform-specific API keys and credentials

## API Endpoints

### Webhook Management

#### Register a Webhook
```
POST /webhooks/register
```

Request Body:
```json
{
  "user_id": 123,
  "webhook_url": "https://your-app.com/webhook",
  "platform": "google",
  "calendar_email": "user@example.com",
  "access_token": "google_access_token",
  "refresh_token": "google_refresh_token",
  "client_id": "microsoft_client_id",
  "client_secret": "microsoft_client_secret",
  "redirect_uri": "https://your-app.com/callback",
  "webhook_secret": "optional_secret_key",
  "auto_create_jobs": true,
  "check_interval_minutes": 30,
  "meeting_start_buffer_minutes": 5,
  "event_types": ["job_created"]
}
```

#### Get Supported Platforms
```
GET /webhooks/platforms
```

#### List Webhooks
```
GET /webhooks/list?user_id=123
```

#### Get Webhook
```
GET /webhooks/{webhook_id}
```

#### Update Webhook
```
PUT /webhooks/{webhook_id}
```

#### Delete Webhook
```
DELETE /webhooks/{webhook_id}
```

#### Toggle Webhook
```
POST /webhooks/{webhook_id}/toggle
```

#### Test Webhook
```
POST /webhooks/test
```

Request Body:
```json
{
  "webhook_url": "https://your-app.com/webhook",
  "webhook_secret": "optional_secret_key"
}
```

### Multi-Platform Calendar API

#### Get Supported Platforms
```
GET /calendar/platforms
```

#### Get Authorization URL
```
GET /calendar/{platform}/auth?redirect_uri={callback_url}
```

#### Handle OAuth Callback
```
GET /calendar/{platform}/callback?code={code}&state={state}&client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}
```

#### Get Calendar Events
```
POST /calendar/{platform}/events
```

Request Body:
```json
{
  "access_token": "platform_access_token",
  "refresh_token": "platform_refresh_token",
  "days_ahead": 7,
  "client_id": "platform_client_id",
  "client_secret": "platform_client_secret"
}
```

#### Create Job from Event
```
POST /calendar/{platform}/events/create-job
```

#### Refresh Token
```
POST /calendar/{platform}/token/refresh
```

#### Disconnect Calendar
```
DELETE /calendar/{platform}/disconnect
```

### Admin Endpoints

#### Cron Service Status
```
GET /admin/cron/status
```

## How It Works

1. **Multi-Platform Webhook Registration**: Users register webhooks with their calendar platform credentials (Google, Microsoft, or Zoom)
2. **Platform-Specific Authentication**: Each platform uses its own OAuth flow with platform-specific endpoints
3. **Cron Job Processing**: A background service runs every minute to check for upcoming meetings across all platforms
4. **Meeting Detection**: The system checks for meetings starting within the configured buffer time for each platform
5. **Job Creation**: If a meeting is detected and no job exists, a new job is created with platform-specific details
6. **Webhook Notification**: A webhook notification is sent to the registered URL with meeting and job details

## Platform-Specific Setup

### Google Calendar
- Uses Google OAuth 2.0
- Requires Google Calendar API credentials
- No additional client_id/client_secret needed in webhook (uses existing Google service)

### Microsoft Graph (Outlook)
- Requires Microsoft App Registration
- Needs `client_id` and `client_secret` from Azure Portal
- Redirect URI must be configured in Azure Portal
- Scopes: `Calendars.Read`, `User.Read`

### Zoom
- Requires Zoom App credentials
- Needs `client_id` and `client_secret` from Zoom Marketplace
- Redirect URI must be configured in Zoom App settings
- OAuth 2.0 with PKCE

## Webhook Payload

When a job is created, the following payload is sent to the webhook URL:

```json
{
  "event": "job_created",
  "job": {
    "id": 123,
    "meeting_url": "https://meet.google.com/xxx-xxxx-xxx",
    "platform": "Google Meet",
    "status": "Registered",
    "created_at": "2024-01-01T10:00:00"
  },
  "meeting": {
    "id": "event_id",
    "title": "Team Meeting",
    "start_time": "2024-01-01T10:05:00",
    "end_time": "2024-01-01T11:00:00",
    "meeting_link": "https://meet.google.com/xxx-xxxx-xxx",
    "platform": "Google Meet"
  },
  "webhook_id": 456,
  "timestamp": "2024-01-01T10:00:00"
}
```

## Configuration

### Environment Variables

No additional environment variables are required for the webhook system.

### Cron Service Configuration

The cron service runs with the following default settings:
- **Check Interval**: Every 60 seconds
- **Meeting Buffer**: 5 minutes before meeting start
- **Auto Create Jobs**: Enabled by default

These can be customized when registering a webhook.

## Security

### Webhook Secrets

Webhook URLs can be secured with a secret key. When provided:
- The secret is included in the `X-Webhook-Secret` header
- Your webhook endpoint should verify this header

### Token Storage

Google Calendar tokens are stored securely in the database:
- Access tokens are used for API calls
- Refresh tokens are used to get new access tokens
- Tokens are automatically refreshed when needed

## Database Schema

### Webhooks Table

| Column | Type | Description |
|--------|------|-------------|
| webhook_id | Integer | Primary key |
| user_id | Integer | User ID |
| webhook_url | String | Webhook URL |
| webhook_secret | String | Optional secret key |
| event_types | Text | JSON string of event types |
| is_active | Boolean | Webhook status |
| created_at | DateTime | Creation timestamp |
| last_triggered | DateTime | Last trigger timestamp |
| calendar_email | String | Google Calendar email |
| access_token | Text | Google access token |
| refresh_token | Text | Google refresh token |
| auto_create_jobs | Boolean | Auto-create jobs flag |
| check_interval_minutes | Integer | Check interval in minutes |
| meeting_start_buffer_minutes | Integer | Buffer time before meeting |

## Error Handling

The system includes comprehensive error handling:
- Failed webhook calls are logged
- Token refresh errors are handled gracefully
- Database errors are logged
- Network timeouts are handled

## Logging

All webhook and cron activities are logged to:
- Application log file (`app.log`)
- Console output (when running in debug mode)

## Examples

### Register a Webhook for Google Calendar

```bash
curl -X POST http://localhost:5000/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "webhook_url": "https://your-app.com/webhook",
    "calendar_email": "user@gmail.com",
    "access_token": "ya29.a0AfH6SMB...",
    "refresh_token": "1//0g...",
    "auto_create_jobs": true,
    "meeting_start_buffer_minutes": 10
  }'
```

### Check Cron Service Status

```bash
curl http://localhost:5000/admin/cron/status
```

## Troubleshooting

### Common Issues

1. **Jobs not being created**: Check if the cron service is running and webhooks are active
2. **Webhook notifications failing**: Verify the webhook URL is accessible and the secret (if used) matches
3. **Token errors**: Ensure Google Calendar tokens are valid and refresh tokens are properly stored

### Debugging

1. Check the cron service status: `GET /admin/cron/status`
2. Review application logs for error messages
3. Test webhook endpoints using the test endpoint
4. Verify Google Calendar permissions and tokens
