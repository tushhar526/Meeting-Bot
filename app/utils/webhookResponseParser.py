"""
Platform-specific webhook response parser
Handles different webhook response formats from Google, Zoom, and Microsoft
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class WebhookResponseParser:
    """Parses webhook creation responses from different platforms"""
    
    @staticmethod
    def parse_webhook_response(platform: str, webhook_result: dict) -> dict:
        """Parse webhook response and extract platform-specific identifiers"""
        
        if not webhook_result:
            logger.warning(f"Empty webhook result for {platform}")
            return {
                'success': False,
                'error': 'Empty webhook response',
                'platform_identifiers': {}
            }
        
        try:
            if platform.lower() == 'google':
                return WebhookResponseParser._parse_google_response(webhook_result)
            elif platform.lower() == 'zoom':
                return WebhookResponseParser._parse_zoom_response(webhook_result)
            elif platform.lower() == 'microsoft':
                return WebhookResponseParser._parse_microsoft_response(webhook_result)
            else:
                logger.error(f"Unsupported platform: {platform}")
                return {
                    'success': False,
                    'error': f'Unsupported platform: {platform}',
                    'platform_identifiers': {}
                }
                
        except Exception as e:
            logger.error(f"Error parsing {platform} webhook response: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform_identifiers': {}
            }
    
    @staticmethod
    def _parse_google_response(webhook_result: dict) -> dict:
        """Parse Google Calendar webhook response"""
        logger.info(f"Parsing Google webhook response: {webhook_result}")
        
        # Google returns: id, resourceId, resourceUri, expiration, kind
        identifiers = {
            'channel_id': webhook_result.get('id'),
            'resource_id': webhook_result.get('resourceId'),
            'resource_uri': webhook_result.get('resourceUri'),
            'expiration': webhook_result.get('expiration'),
            'kind': webhook_result.get('kind')
        }
        
        # Validate required fields
        if not identifiers['channel_id']:
            return {
                'success': False,
                'error': 'Missing channel_id in Google webhook response',
                'platform_identifiers': identifiers
            }
        
        return {
            'success': True,
            'platform_identifiers': identifiers,
            'message': 'Google webhook created successfully'
        }
    
    @staticmethod
    def _parse_zoom_response(webhook_result: dict) -> dict:
        """Parse Zoom webhook response"""
        logger.info(f"Parsing Zoom webhook response: {webhook_result}")
        
        # Zoom returns: id, url, events, active, etc.
        # Note: Zoom doesn't use channel_id/resource_id like Google
        identifiers = {
            'webhook_id': webhook_result.get('id'),
            'webhook_url': webhook_result.get('url') or webhook_result.get('endpoint_url'),
            'events': webhook_result.get('events', []),
            'active': webhook_result.get('active', True),
            'event': webhook_result.get('event')  # Single event type
        }
        
        # For consistency, map Zoom's webhook_id to channel_id
        if identifiers['webhook_id']:
            identifiers['channel_id'] = identifiers['webhook_id']
        
        # Validate required fields
        if not identifiers['webhook_id']:
            return {
                'success': False,
                'error': 'Missing webhook_id in Zoom webhook response',
                'platform_identifiers': identifiers
            }
        
        return {
            'success': True,
            'platform_identifiers': identifiers,
            'message': 'Zoom webhook created successfully'
        }
    
    @staticmethod
    def _parse_microsoft_response(webhook_result: dict) -> dict:
        """Parse Microsoft Graph webhook response"""
        logger.info(f"Parsing Microsoft webhook response: {webhook_result}")
        
        # Microsoft Graph returns: id, changeType, notificationUrl, resource, expirationDateTime
        identifiers = {
            'subscription_id': webhook_result.get('id'),
            'change_type': webhook_result.get('changeType'),
            'notification_url': webhook_result.get('notificationUrl'),
            'resource': webhook_result.get('resource'),
            'expiration_datetime': webhook_result.get('expirationDateTime'),
            'client_state': webhook_result.get('clientState')
        }
        
        # For consistency, map Microsoft's subscription_id to channel_id
        if identifiers['subscription_id']:
            identifiers['channel_id'] = identifiers['subscription_id']
        
        # Microsoft doesn't use resource_id like Google
        # But we can use the resource field as a reference
        if identifiers['resource']:
            identifiers['resource_id'] = identifiers['resource']
        
        # Validate required fields
        if not identifiers['subscription_id']:
            return {
                'success': False,
                'error': 'Missing subscription_id in Microsoft webhook response',
                'platform_identifiers': identifiers
            }
        
        return {
            'success': True,
            'platform_identifiers': identifiers,
            'message': 'Microsoft webhook subscription created successfully'
        }
    
    @staticmethod
    def get_platform_identifiers_for_storage(platform: str, webhook_result: dict) -> dict:
        """Get standardized identifiers for database storage"""
        
        parsed = WebhookResponseParser.parse_webhook_response(platform, webhook_result)
        
        if not parsed['success']:
            return parsed
        
        identifiers = parsed['platform_identifiers']
        
        # Standardize for database storage
        storage_fields = {
            'channel_id': identifiers.get('channel_id'),
            'resource_id': identifiers.get('resource_id'),
            'resource_uri': identifiers.get('resource_uri'),
            'expiration': identifiers.get('expiration') or identifiers.get('expiration_datetime'),
            'events': identifiers.get('events', []),
            'active': identifiers.get('active', True),
            'webhook_id': identifiers.get('webhook_id') or identifiers.get('subscription_id'),
            'notification_url': identifiers.get('notification_url'),
            'change_type': identifiers.get('change_type'),
            'resource': identifiers.get('resource')
        }
        
        return {
            'success': True,
            'platform_identifiers': storage_fields,
            'message': parsed['message']
        }
    
    @staticmethod
    def get_update_identifiers(platform: str, webhook_result: dict) -> dict:
        """Get identifiers needed for webhook updates"""
        
        parsed = WebhookResponseParser.parse_webhook_response(platform, webhook_result)
        
        if not parsed['success']:
            return parsed
        
        identifiers = parsed['platform_identifiers']
        
        # Different platforms need different identifiers for updates
        update_fields = {
            'google': {
                'channel_id': identifiers.get('channel_id'),
                'resource_id': identifiers.get('resource_id')
            },
            'zoom': {
                'webhook_id': identifiers.get('webhook_id'),
                'channel_id': identifiers.get('channel_id')  # Mapped for consistency
            },
            'microsoft': {
                'subscription_id': identifiers.get('subscription_id'),
                'channel_id': identifiers.get('channel_id')  # Mapped for consistency
            }
        }
        
        return {
            'success': True,
            'update_identifiers': update_fields.get(platform.lower(), {}),
            'platform_identifiers': identifiers,
            'message': parsed['message']
        }
