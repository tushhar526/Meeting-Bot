# Ngrok Webhook Management

This system solves the common problem of ngrok URLs changing when you restart ngrok, which breaks webhook integrations.

## 🎯 Problem Solved

- **Before**: Webhook URLs hardcoded as `localhost:5000` → don't work with ngrok
- **Before**: Ngrok URL changes on restart → all webhooks break
- **After**: Dynamic webhook URL detection and automatic updates

## 🚀 Quick Start

### 1. Start Ngrok
```bash
ngrok http 5000
```

### 2. Start Your Flask App
```bash
python app.py
```

### 3. Update Webhooks (when ngrok URL changes)
```bash
# Option 1: Use the management script
python scripts/manage_ngrok_webhooks.py

# Option 2: Use API endpoints
curl -X POST https://your-ngrok-url.ngrok.io/webhooks/ngrok/update-webhooks
```

## 📋 Available API Endpoints

### Check Ngrok Status
```bash
GET /webhooks/ngrok/status
```

Response:
```json
{
  "ngrok_running": true,
  "current_url": "https://abc123.ngrok.io",
  "webhook_base_url": "https://abc123.ngrok.io",
  "status": "active"
}
```

### Update All Webhook URLs
```bash
POST /webhooks/ngrok/update-webhooks
```

Response:
```json
{
  "message": "Webhook URLs updated successfully",
  "total_updated": 3,
  "platform_counts": {
    "google": 1,
    "zoom": 1,
    "microsoft": 1
  },
  "new_base_url": "https://abc123.ngrok.io"
}
```

### Get Webhook URL for Platform
```bash
GET /webhooks/ngrok/webhook-url/google
```

Response:
```json
{
  "platform": "google",
  "webhook_url": "https://abc123.ngrok.io/webhooks/receive/google",
  "base_url": "https://abc123.ngrok.io"
}
```

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: Override webhook base URL (useful for production)
WEBHOOK_BASE_URL=https://your-domain.com

# Required for webhook verification
ZOOM_SECRET_KEY=your_zoom_secret
MICROSOFT_CLIENT_SECRET=your_microsoft_secret
```

### Ngrok Configuration (Optional)
Create `ngrok.yml` for consistent subdomain:
```yaml
version: "2"
authtoken: your_auth_token

tunnels:
  webhook:
    proto: http
    addr: 5000
    bind_tls: true
    subdomain: your-app-name  # Get consistent subdomain with paid plan
```

## 🔄 How It Works

### 1. Dynamic URL Detection
- Automatically detects current ngrok URL via ngrok API (`http://127.0.0.1:4040/api/tunnels`)
- Falls back to `WEBHOOK_BASE_URL` environment variable
- Final fallback to `localhost:5000`

### 2. Webhook Creation
- When creating new webhooks, uses current ngrok URL
- Stores both the URL and webhook metadata in database
- Webhook URLs are now: `{ngrok_url}/webhooks/receive/{platform}`

### 3. URL Updates
- When ngrok restarts with new URL, call update endpoint
- Updates all webhook URLs in database
- Attempts to update webhooks on platform (if supported)

## 🛠️ Management Script

The `manage_ngrok_webhooks.py` script provides an easy way to manage webhooks:

```bash
python scripts/manage_ngrok_webhooks.py
```

**Features:**
- ✅ Checks if ngrok is running
- ✅ Gets current ngrok URL
- ✅ Checks webhook status
- ✅ Updates all webhook URLs
- ✅ Provides clear feedback

## 📁 File Structure

```
app/
├── utils/
│   └── ngrokWebhookManager.py     # Core webhook management logic
├── routes/
│   └── webhookReceieveRoutes.py    # API endpoints for webhook management
├── controller/
│   └── webhookController.py       # Webhook processing logic
scripts/
└── manage_ngrok_webhooks.py      # Management script
```

## 🚨 Important Notes

### Security
- Ngrok URLs are public and accessible to anyone
- Always use webhook verification (implemented for Zoom/Microsoft)
- Consider authentication for production

### Platform Limitations
- **Google**: Webhooks expire after 7 days, need renewal
- **Zoom**: Webhooks are persistent but can be updated
- **Microsoft**: Uses subscription validation, less URL-dependent

### Production
- Use a real domain instead of ngrok
- Set `WEBHOOK_BASE_URL` environment variable
- Consider HTTPS certificates

## 🔧 Troubleshooting

### Ngrok Not Running
```
❌ Ngrok is not running or not accessible on port 4040
💡 Start ngrok with: ngrok http 5000
```
**Solution**: Start ngrok with `ngrok http 5000`

### App Not Running
```
❌ Cannot connect to app at https://abc123.ngrok.io
💡 Make sure your Flask app is running
```
**Solution**: Start your Flask application

### Webhook Update Failed
```
❌ Failed to update webhooks: Platform does not support webhook updates
```
**Solution**: Some platforms don't support updating existing webhooks. You may need to recreate them.

## 📚 Examples

### Manual Webhook URL Check
```bash
# Check current status
curl http://localhost:5000/webhooks/ngrok/status

# Get Google webhook URL
curl http://localhost:5000/webhooks/ngrok/webhook-url/google

# Update all webhooks
curl -X POST http://localhost:5000/webhooks/ngrok/update-webhooks
```

### Programmatic Usage
```python
from app.utils.ngrokWebhookManager import NgrokWebhookManager

# Get current webhook URL
webhook_url = NgrokWebhookManager.get_webhook_url('google')

# Update all webhooks
result = NgrokWebhookManager.update_all_webhook_urls()

# Check ngrok status
status = NgrokWebhookManager.check_ngrok_status()
```

This system ensures your webhooks always work with ngrok during development! 🎉
