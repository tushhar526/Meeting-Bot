# from flask import Blueprint, request, jsonify, redirect, url_for
# from typing import Dict, List, Optional
# import logging
# from app.logic.calendar import CalendarManager
# from app.models.jobModel import JobModel
# from app.schema.calendar import (
#     CalendarAuthRequest,
#     CalendarAuthResponse,
#     CalendarEventsResponse,
#     CalendarTokenRequest
# )

# logger = logging.getLogger(__name__)

# calendar_bp = Blueprint('calendar', __name__)
# calendar_manager = CalendarManager()


# @calendar_bp.route('/auth/google', methods=['GET'])
# def google_calendar_auth():
#     """Get Google OAuth authorization URL"""
#     try:
#         # Generate state parameter for security
#         import secrets
#         state = secrets.token_urlsafe(32)
        
#         # Store state in session (you'll need to implement session storage)
#         # For now, we'll return it in the response
        
#         auth_url = calendar_manager.google_service.get_authorization_url(state)
        
#         return jsonify({
#             "authorization_url": auth_url,
#             "state": state,
#             "message": "Use this URL to authorize Google Calendar access"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to generate Google auth URL: {e}")
#         return jsonify({"error": "Failed to generate authorization URL"}), 500


# @calendar_bp.route('/auth/google/callback', methods=['GET'])
# def google_calendar_callback():
#     """Handle Google OAuth callback and exchange code for tokens"""
#     try:
#         code = request.args.get('code')
#         state = request.args.get('state')
        
#         if not code:
#             return jsonify({"error": "Authorization code not provided"}), 400
        
#         # Exchange authorization code for tokens
#         tokens = calendar_manager.google_service.exchange_code_for_tokens(code)
        
#         # Get user information
#         user_info = calendar_manager.google_service.get_user_info(tokens['access_token'])
        
#         # Here you should store the tokens securely in your database
#         # For now, we'll return them (in production, store in database)
        
#         return jsonify({
#             "access_token": tokens['access_token'],
#             "refresh_token": tokens.get('refresh_token'),
#             "expires_in": tokens.get('expires_in'),
#             "token_type": tokens.get('token_type', 'Bearer'),
#             "user_email": user_info.get('email'),
#             "user_name": user_info.get('name'),
#             "message": "Successfully authorized Google Calendar"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to handle Google auth callback: {e}")
#         return jsonify({"error": "Failed to authorize Google Calendar"}), 400


# @calendar_bp.route('/events', methods=['POST'])
# def get_calendar_events():
#     """Get upcoming calendar events with meeting links"""
#     try:
#         data = request.get_json()
        
#         access_token = data.get('access_token')
#         refresh_token = data.get('refresh_token')
#         days_ahead = data.get('days_ahead', 7)
        
#         if not access_token or not refresh_token:
#             return jsonify({"error": "Access token and refresh token required"}), 400
        
#         meetings = calendar_manager.get_upcoming_meetings(
#             access_token=access_token,
#             refresh_token=refresh_token,
#             days_ahead=days_ahead
#         )
        
#         return jsonify({
#             "meetings": meetings,
#             "count": len(meetings),
#             "message": f"Found {len(meetings)} upcoming meetings"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to get calendar events: {e}")
#         return jsonify({"error": "Failed to fetch calendar events"}), 400


# @calendar_bp.route('/events/create-job', methods=['POST'])
# def create_job_from_calendar_event():
#     """Create a meeting bot job from a calendar event"""
#     try:
#         data = request.get_json()
        
#         event_id = data.get('event_id')
#         access_token = data.get('access_token')
#         refresh_token = data.get('refresh_token')
        
#         if not all([event_id, access_token, refresh_token]):
#             return jsonify({"error": "event_id, access_token, and refresh_token required"}), 400
        
#         # Get specific event details
#         events = calendar_manager.get_upcoming_meetings(
#             access_token=access_token,
#             refresh_token=refresh_token,
#             days_ahead=7
#         )
        
#         # Find the specific event
#         target_event = None
#         for event in events:
#             if event['id'] == event_id:
#                 target_event = event
#                 break
        
#         if not target_event:
#             return jsonify({"error": "Event not found"}), 404
        
#         # Create job from event
#         job = JobModel(
#             meeting_url=target_event['meeting_link'],
#             meeting_title=target_event['title'],
#             scheduled_time=target_event['start_time'],
#             platform=target_event['platform'],
#             status="Scheduled"
#         )
        
#         job.save()
        
#         return jsonify({
#             "job_id": job.id,
#             "meeting_url": target_event['meeting_link'],
#             "meeting_title": target_event['title'],
#             "scheduled_time": target_event['start_time'],
#             "message": "Job created successfully from calendar event"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to create job from calendar event: {e}")
#         return jsonify({"error": "Failed to create job from calendar event"}), 400


# @calendar_bp.route('/token/refresh', methods=['POST'])
# def refresh_calendar_token():
#     """Refresh access token using refresh token"""
#     try:
#         data = request.get_json()
#         refresh_token = data.get('refresh_token')
        
#         if not refresh_token:
#             return jsonify({"error": "Refresh token required"}), 400
        
#         new_tokens = calendar_manager.google_service.refresh_access_token(refresh_token)
        
#         return jsonify({
#             "access_token": new_tokens['access_token'],
#             "expires_in": new_tokens.get('expires_in'),
#             "token_type": new_tokens.get('token_type', 'Bearer'),
#             "message": "Token refreshed successfully"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to refresh token: {e}")
#         return jsonify({"error": "Failed to refresh token"}), 400


# @calendar_bp.route('/disconnect', methods=['DELETE'])
# def disconnect_calendar():
#     """Disconnect calendar integration (revoke tokens)"""
#     try:
#         data = request.get_json()
#         user_email = data.get('user_email')
        
#         if not user_email:
#             return jsonify({"error": "User email required"}), 400
        
#         # Here you would typically:
#         # 1. Revoke the tokens at Google
#         # 2. Remove tokens from your database
#         # 3. Clean up any related data
        
#         # For now, we'll just log the disconnection
#         logger.info(f"Calendar disconnected for user: {user_email}")
        
#         return jsonify({
#             "message": "Calendar disconnected successfully"
#         })
        
#     except Exception as e:
#         logger.error(f"Failed to disconnect calendar: {e}")
#         return jsonify({"error": "Failed to disconnect calendar"}), 400
