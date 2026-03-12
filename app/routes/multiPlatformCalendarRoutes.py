from flask import Blueprint, request, jsonify
import logging
from app.controller.calendarController.multiPlatformCalendar import MultiPlatformCalendarController

logger = logging.getLogger(__name__)

multi_calendar_bp = Blueprint('multi_calendar', __name__, url_prefix="/calendar")
calendar_controller = MultiPlatformCalendarController()


@multi_calendar_bp.route('/platforms', methods=['GET'])
def get_supported_platforms():
    """Get list of supported calendar platforms"""
    try:
        result = calendar_controller.get_supported_platforms()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        return jsonify({"error": str(e)}), 500


@multi_calendar_bp.route('/<platform>/auth', methods=['GET'])
def get_calendar_auth_url(platform):
    """Get OAuth authorization URL for specified platform"""
    try:
        redirect_uri = request.args.get('redirect_uri')
        result = calendar_controller.get_auth_url(platform, redirect_uri)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to generate {platform} auth URL: {e}")
        return jsonify({"error": str(e)}), 500


@multi_calendar_bp.route('/<platform>/callback', methods=['GET'])
def handle_calendar_callback(platform):
    """Handle OAuth callback and exchange code for tokens"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        client_id = request.args.get('client_id')
        client_secret = request.args.get('client_secret')
        redirect_uri = request.args.get('redirect_uri')
        
        result = calendar_controller.handle_callback(
            platform, code, state, client_id, client_secret, redirect_uri
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to handle {platform} auth callback: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route('/<platform>/events', methods=['POST'])
def get_calendar_events(platform):
    """Get upcoming calendar events with meeting links"""
    try:
        data = request.get_json()
        
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        days_ahead = data.get('days_ahead', 7)
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        result = calendar_controller.get_events(
            platform, access_token, refresh_token, days_ahead, client_id, client_secret
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to get {platform} calendar events: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route('/<platform>/events/create-job', methods=['POST'])
def create_job_from_calendar_event(platform):
    """Create a meeting bot job from a calendar event"""
    try:
        data = request.get_json()
        
        event_id = data.get('event_id')
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        user_id = data.get('user_id')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        result = calendar_controller.create_job_from_event(
            platform, event_id, access_token, refresh_token, user_id, client_id, client_secret
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to create job from {platform} calendar event: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route('/<platform>/token/refresh', methods=['POST'])
def refresh_calendar_token(platform):
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        result = calendar_controller.refresh_token(
            platform, refresh_token, client_id, client_secret
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to refresh {platform} token: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route('/<platform>/disconnect', methods=['DELETE'])
def disconnect_calendar(platform):
    """Disconnect calendar integration (revoke tokens)"""
    try:
        data = request.get_json()
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        
        result = calendar_controller.disconnect_calendar(platform, access_token, refresh_token)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to disconnect {platform} calendar: {e}")
        return jsonify({"error": str(e)}), 400
