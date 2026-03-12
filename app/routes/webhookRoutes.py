from flask import Blueprint, request, jsonify
import logging
import json
from app.services.webhookScheduler import WebhookScheduler
from app.services.calendarServiceFactory import CalendarServiceFactory
from app.models.webhookModel import WebhookModel

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__, url_prefix="/webhooks")
webhook_scheduler = WebhookScheduler()


@webhook_bp.route('/register', methods=['POST'])
def register_webhook():
    """Register a new webhook for calendar events"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        webhook_url = data.get('webhook_url')
        platform = data.get('platform', 'google')
        event_types = data.get('event_types', ['job_created'])
        calendar_email = data.get('calendar_email')
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        webhook_secret = data.get('webhook_secret')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        redirect_uri = data.get('redirect_uri')
        auto_create_jobs = data.get('auto_create_jobs', True)
        check_interval_minutes = data.get('check_interval_minutes', 30)
        meeting_start_buffer_minutes = data.get('meeting_start_buffer_minutes', 5)
        
        if not all([user_id, webhook_url, platform]):
            return jsonify({"error": "user_id, webhook_url, and platform are required"}), 400
        
        webhook = webhook_scheduler.register_webhook(
            user_id=user_id,
            webhook_url=webhook_url,
            platform=platform,
            event_types=event_types,
            calendar_email=calendar_email,
            access_token=access_token,
            refresh_token=refresh_token,
            webhook_secret=webhook_secret,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            auto_create_jobs=auto_create_jobs,
            check_interval_minutes=check_interval_minutes,
            meeting_start_buffer_minutes=meeting_start_buffer_minutes
        )
        
        return jsonify({
            "webhook": webhook.to_json(),
            "message": "Webhook registered successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to register webhook: {e}")
        return jsonify({"error": str(e)}), 400


@webhook_bp.route('/platforms', methods=['GET'])
def get_supported_platforms():
    """Get list of supported calendar platforms"""
    try:
        platforms = CalendarServiceFactory.get_supported_platforms()
        return jsonify({
            "platforms": platforms,
            "message": "Supported platforms retrieved successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        return jsonify({"error": "Failed to get supported platforms"}), 500


@webhook_bp.route('/list', methods=['GET'])
def list_webhooks():
    """List all webhooks for a user"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        webhooks = WebhookModel.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            "webhooks": [webhook.to_json() for webhook in webhooks],
            "count": len(webhooks)
        })
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        return jsonify({"error": "Failed to list webhooks"}), 400


@webhook_bp.route('/<int:webhook_id>', methods=['GET'])
def get_webhook(webhook_id):
    """Get a specific webhook"""
    try:
        webhook = WebhookModel.query.get(webhook_id)
        
        if not webhook:
            return jsonify({"error": "Webhook not found"}), 404
        
        return jsonify({
            "webhook": webhook.to_json()
        })
        
    except Exception as e:
        logger.error(f"Failed to get webhook: {e}")
        return jsonify({"error": "Failed to get webhook"}), 400


@webhook_bp.route('/<int:webhook_id>', methods=['PUT'])
def update_webhook(webhook_id):
    """Update a webhook"""
    try:
        data = request.get_json()
        
        success = webhook_scheduler.update_webhook(webhook_id, **data)
        
        if not success:
            return jsonify({"error": "Webhook not found"}), 404
        
        webhook = WebhookModel.query.get(webhook_id)
        
        return jsonify({
            "webhook": webhook.to_json(),
            "message": "Webhook updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to update webhook: {e}")
        return jsonify({"error": "Failed to update webhook"}), 400


@webhook_bp.route('/<int:webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    """Delete a webhook"""
    try:
        success = webhook_scheduler.delete_webhook(webhook_id)
        
        if not success:
            return jsonify({"error": "Webhook not found"}), 404
        
        return jsonify({
            "message": "Webhook deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        return jsonify({"error": "Failed to delete webhook"}), 400


@webhook_bp.route('/<int:webhook_id>/toggle', methods=['POST'])
def toggle_webhook(webhook_id):
    """Toggle webhook active status"""
    try:
        webhook = WebhookModel.query.get(webhook_id)
        
        if not webhook:
            return jsonify({"error": "Webhook not found"}), 404
        
        webhook.is_active = not webhook.is_active
        webhook.save()
        
        status = "activated" if webhook.is_active else "deactivated"
        
        return jsonify({
            "webhook": webhook.to_json(),
            "message": f"Webhook {status} successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to toggle webhook: {e}")
        return jsonify({"error": "Failed to toggle webhook"}), 400


@webhook_bp.route('/test', methods=['POST'])
def test_webhook():
    """Test a webhook by sending a test payload"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        webhook_secret = data.get('webhook_secret')
        
        if not webhook_url:
            return jsonify({"error": "webhook_url is required"}), 400
        
        test_payload = {
            "event": "test",
            "message": "This is a test webhook payload",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        if webhook_secret:
            headers['X-Webhook-Secret'] = webhook_secret
        
        import requests
        response = requests.post(webhook_url, json=test_payload, headers=headers, timeout=10)
        
        return jsonify({
            "status_code": response.status_code,
            "response_text": response.text,
            "message": "Test webhook sent successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to test webhook: {e}")
        return jsonify({"error": "Failed to test webhook"}), 400
