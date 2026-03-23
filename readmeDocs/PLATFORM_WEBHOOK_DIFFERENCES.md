# Platform Webhook Response Differences

This document explains how different calendar platforms handle webhook creation and the differences in their response formats.

## 🎯 Overview

Each calendar platform (Google, Zoom, Microsoft) has a completely different webhook API and response format. Our system handles these differences using the `WebhookResponseParser`.

## 📋 Platform Comparison

### **Google Calendar**
```json
// Webhook Creation Response
{
  "id": "channel-id-12345",           // Channel identifier
  "resourceId": "resource-id-67890",  // Resource identifier  
  "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
  "expiration": "1694395200000",       // Timestamp
  "kind": "api#channel"
}

// Webhook Headers
X-Goog-Channel-ID: channel-id-12345
X-Goog-Resource-ID: resource-id-67890
X-Goog-Resource-State: exists
X-Goog-Resource-URI: https://www.googleapis.com/calendar/v3/calendars/primary/events
```

**Key Points:**
- ✅ Uses `channel_id` + `resource_id`
- ✅ Supports webhook updates
- ✅ Webhooks expire after 7 days
- ✅ Requires channel validation

### **Zoom**
```json
// Webhook Creation Response
{
  "id": "webhook-id-12345",           // Webhook identifier
  "url": "https://your-url.ngrok.io/webhooks/receive/zoom",
  "events": ["meeting.created", "meeting.updated", "meeting.started"],
  "active": true
}

// Webhook Event Payload
{
  "event": "meeting.created",
  "payload": {
    "object": { ... },
    "account_id": "account-123"
  }
}
```

**Key Points:**
- ✅ Uses `webhook_id` (mapped to `channel_id`)
- ❌ No `resource_id` concept
- ✅ Supports webhook updates
- ✅ Persistent webhooks (no expiration)
- ✅ Uses account_id for user identification

### **Microsoft Teams**
```json
// Webhook Creation Response (Graph API Subscription)
{
  "id": "subscription-id-12345",      // Subscription identifier
  "changeType": "created,updated",
  "notificationUrl": "https://your-url.ngrok.io/webhooks/receive/microsoft",
  "resource": "me/events",
  "expirationDateTime": "2024-03-24T18:23:45.9356913Z"
}

// Webhook Event Payload
{
  "value": [
    {
      "changeType": "created",
      "resourceData": {
        "id": "event-id-12345",
        "organizer": { "emailAddress": { "address": "user@example.com" } }
      }
    }
  ]
}
```

**Key Points:**
- ✅ Uses `subscription_id` (mapped to `channel_id`)
- ❌ No `resource_id` concept
- ✅ Supports webhook updates
- ✅ Webhooks expire after subscription period
- ✅ Uses organizer email for user identification

## 🔧 How Our System Handles Differences

### **1. Response Parsing**
```python
# Before: Assumed all platforms return the same format
channel_id = webhook_result.get('id')
resource_id = webhook_result.get('resourceId')

# After: Platform-specific parsing
parsed = WebhookResponseParser.parse_webhook_response(platform, webhook_result)
identifiers = parsed['platform_identifiers']
```

### **2. Database Storage**
```python
# Store all possible fields (platform-specific)
webhook = WebhookModel(
    # Standard fields
    channel_id=identifiers.get('channel_id'),
    resource_id=identifiers.get('resource_id'),
    
    # Platform-specific fields
    webhook_id=identifiers.get('webhook_id'),           # Zoom
    subscription_id=identifiers.get('subscription_id'), # Microsoft
    events=identifiers.get('events', []),               # Zoom
    change_type=identifiers.get('change_type'),         # Microsoft
    notification_url=identifiers.get('notification_url') # Microsoft
)
```

### **3. Webhook Updates**
```python
# Platform-specific update identifiers
if platform == 'google':
    update_ids = {'channel_id': webhook.channel_id, 'resource_id': webhook.resource_id}
elif platform == 'zoom':
    update_ids = {'webhook_id': webhook.webhook_id}
elif platform == 'microsoft':
    update_ids = {'subscription_id': webhook.webhook_id}
```

## 📊 Platform Capabilities

| Feature | Google | Zoom | Microsoft |
|---------|--------|------|-----------|
| **Webhook Updates** | ✅ | ✅ | ✅ |
| **Expiration** | 7 days | No | Subscription period |
| **Channel ID** | ✅ | ✅ (mapped) | ✅ (mapped) |
| **Resource ID** | ✅ | ❌ | ❌ |
| **Event Types** | Limited | Rich | Moderate |
| **User Identification** | Email | Account ID | Organizer Email |

## 🚨 Important Considerations

### **Google Calendar**
- Webhooks expire after 7 days → Need renewal
- Requires channel validation during setup
- Uses both `channel_id` and `resource_id`

### **Zoom**
- Persistent webhooks (no expiration)
- Simpler response format
- Uses `account_id` instead of email for identification

### **Microsoft Teams**
- Uses Graph API subscriptions
- Different event payload structure
- Subscription-based (not permanent)

## 🔍 Debugging Different Platforms

### **Google Webhook Issues**
```bash
# Check channel validation
curl -X POST https://your-url.ngrok.io/webhooks/receive/google \
  -H "X-Goog-Channel-ID: test-channel" \
  -H "X-Goog-Resource-State: sync"
```

### **Zoom Webhook Issues**
```bash
# Check webhook signature
curl -X POST https://your-url.ngrok.io/webhooks/receive/zoom \
  -H "x-zm-signature: v0=hash" \
  -d '{"event": "meeting.created"}'
```

### **Microsoft Webhook Issues**
```bash
# Check subscription validation
curl -X POST https://your-url.ngrok.io/webhooks/receive/microsoft \
  -H "Authorization: Bearer token" \
  -d '{"value": [{"changeType": "created"}]}'
```

## 🎯 Best Practices

1. **Always parse responses platform-specifically**
2. **Store all possible identifiers** for future updates
3. **Handle missing fields gracefully**
4. **Log platform-specific errors**
5. **Test webhook updates for each platform**
6. **Monitor webhook expiration** (Google/Microsoft)

This system ensures we can handle any platform's webhook format while maintaining a consistent internal API! 🎉
