from flask import Blueprint, request, jsonify, redirect
import logging
import os
import json
from datetime import datetime, timezone, timedelta
from app.controller.calendar.calendarController import (
    CalendarController,
)

logger = logging.getLogger(__name__)

multi_calendar_bp = Blueprint("multi_calendar", __name__, url_prefix="/calendar")
calendar_controller = CalendarController()


def _popup_response(status, message, data=None):
    """Return response for OAuth popup window"""
    if status == "success":
        # Return HTML page for successful integration
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Calendar Integration Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f8f9fa;
                }}
                .success-container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 48px;
                    color: #28a745;
                    margin-bottom: 20px;
                }}
                .success-title {{
                    color: #333;
                    margin-bottom: 10px;
                    font-size: 24px;
                }}
                .success-message {{
                    color: #666;
                    margin-bottom: 20px;
                    line-height: 1.5;
                }}
                .integration-info {{
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 20px;
                }}
                .next-steps {{
                    margin-top: 20px;
                    font-size: 14px;
                }}
                .next-steps h4 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .next-steps ul {{
                    text-align: left;
                    color: #666;
                }}
                .next-steps li {{
                    margin-bottom: 8px;
                }}
                .close-btn {{
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }}
                .close-btn:hover {{
                    background: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="success-container">
                <div class="success-icon">✅</div>
                <h1 class="success-title">Calendar Integrated Successfully!</h1>
                <p class="success-message">
                    Your {data.get('platform', 'Calendar').title()} has been connected successfully.
                </p>
                
                <div class="integration-info">
                    <strong>Integration Details:</strong><br>
                    Platform: {data.get('platform', 'N/A').title()}<br>
                    Email: {data.get('user_email', 'N/A')}<br>
                    Status: Active
                </div>
                
                <div class="next-steps">
                    <h4>Next Steps:</h4>
                    <ul>
                        <li>This window will close automatically</li>
                        <li>Go to your calendar events page</li>
                        <li>Your events will appear automatically</li>
                        <li>You can create meeting bots from calendar events</li>
                    </ul>
                </div>
                
                <button class="close-btn" onclick="window.close()">Close Window</button>
            </div>
            
            <script>
                // Auto-close after 3 seconds
                setTimeout(function() {{
                    window.close();
                }}, 3000);
                
                // Optional: Send success message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'calendar_integration_success',
                        platform: '{data.get('platform', '')}',
                        integration_id: {data.get('integration_id', 'null')},
                        user_email: '{data.get('user_email', '')}'
                    }}, '*');
                }}
            </script>
        </body>
        </html>
        """
        return html_template, 200, {"Content-Type": "text/html"}
    else:
        response_data = {
            "type": "calendar_auth_error",
            "success": False,
            "error": message,
        }

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #f44336; }}
            </style>
        </head>
        <body>
            <h1 class="error">✗ {message}</h1>
            <p>This window will close automatically.</p>
            <script>
                const authData = {str(response_data).replace("'", '"')};
                
                try {{
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage(authData, '*');
                    }} else {{
                        sessionStorage.setItem('auth_result', JSON.stringify(authData));
                    }}
                }} catch (e) {{
                    sessionStorage.setItem('auth_result', JSON.stringify(authData));
                }}
                
                setTimeout(window.close, 2000);
            </script>
        </body>
        </html>
        """


@multi_calendar_bp.route("/platforms", methods=["GET"])
def get_supported_platforms():
    """Get list of supported calendar platforms"""
    try:
        result = calendar_controller.get_supported_platforms()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        return jsonify({"error": str(e)}), 500


@multi_calendar_bp.route("/integrations", methods=["GET"])
def get_user_integrations():
    """Get current user's calendar integrations"""
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

        # Get user's integrations
        from app.models.userIntegrationModel import UserIntegration

        integrations = UserIntegration.query.filter_by(
            user_id=user_id, is_active=True
        ).all()

        logger.info(f"Found {len(integrations)} active integrations for user {user_id}")
        for integration in integrations:
            logger.info(
                f"Integration: {integration.platform} (ID: {integration.id}, Active: {integration.is_active})"
            )

        result = []
        for integration in integrations:
            result.append(
                {
                    "id": integration.id,
                    "platform": integration.platform,
                    "account_email": integration.account_email,
                    "created_at": (
                        integration.created_at.isoformat()
                        if integration.created_at
                        else None
                    ),
                    "expires_at": (
                        integration.expires_at.isoformat()
                        if integration.expires_at
                        else None
                    ),
                }
            )

        return jsonify({"integrations": result})

    except Exception as e:
        logger.error(f"Failed to get user integrations: {e}")
        return jsonify({"error": str(e)}), 500


@multi_calendar_bp.route("/<platform>/auth", methods=["GET"])
def get_calendar_auth_url(platform):
    """Get OAuth authorization URL for specified platform"""
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

        redirect_uri = request.args.get("redirect_uri")
        result = calendar_controller.get_auth_url(platform, int(user_id), redirect_uri)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to generate {platform} auth URL: {e}")
        return jsonify({"error": str(e)}), 500


@multi_calendar_bp.route("/<platform>/callback", methods=["GET"])
def handle_calendar_callback(platform):
    """Handle OAuth callback and exchange code for tokens"""
    try:
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            logger.error(f"{platform.title()} OAuth error: {error}")
            return _popup_response("error", f"OAuth error: {error}")

        if not code:
            logger.error("No authorization code received")
            return _popup_response("error", "No authorization code received")

        # Decode state to get user_id
        try:
            import jwt
            from flask import current_app

            state_data = jwt.decode(
                state,
                current_app.config.get("SECRET_KEY", "dev-secret"),
                algorithms=["HS256"],
            )
            user_id = state_data.get("user_id")
            if not user_id:
                raise ValueError("Invalid state parameter")
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            return _popup_response("error", "Invalid state parameter")

        # Get credentials from environment variables based on platform
        if platform == "google":
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            redirect_uri = os.getenv(
                "GOOGLE_REDIRECT_URI", "http://localhost:5000/calendar/google/callback"
            )
        elif platform == "zoom":
            client_id = os.getenv("ZOOM_CLIENT_ID")
            client_secret = os.getenv("ZOOM_CLIENT_SECRET")
            redirect_uri = os.getenv(
                "ZOOM_REDIRECT_URI", "http://localhost:5000/calendar/zoom/callback"
            )

            if not client_id or not client_secret:
                logger.error("❌ Zoom credentials not found in environment variables")
                return (
                    jsonify(
                        {
                            "error": "Zoom credentials not configured",
                            "details": {
                                "ZOOM_CLIENT_ID": "SET" if client_id else "NOT_SET",
                                "ZOOM_CLIENT_SECRET": (
                                    "SET" if client_secret else "NOT_SET"
                                ),
                                "ZOOM_REDIRECT_URI": redirect_uri,
                            },
                        }
                    ),
                    500,
                )
        elif platform == "microsoft":
            client_id = os.getenv("MICROSOFT_CLIENT_ID")
            client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
            redirect_uri = os.getenv(
                "MICROSOFT_REDIRECT_URI",
                "http://localhost:5000/calendar/microsoft/callback",
            )
        else:
            return jsonify({"error": f"Unsupported platform: {platform}"}), 400

        # Handle token exchange and storage
        from app.models.userIntegrationModel import UserIntegration
        from app.models.webhookModel import WebhookModel
        from app.extension import db

        try:
            result = calendar_controller.handle_callback(
                platform, code, state, redirect_uri
            )

            # Calculate expiry time
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=result.get("expires_in", 3600)
            )

            # Find existing integration for this user and platform
            existing_integration = UserIntegration.query.filter_by(
                user_id=user_id, platform=platform
            ).first()

            logger.info(
                f"Looking for existing integration for user {user_id}, platform {platform}"
            )
            logger.info(f"Found existing integration: {existing_integration}")

            if existing_integration:
                # Update existing integration
                logger.info(
                    f"Updating existing integration {existing_integration.id} for platform {platform}"
                )

                # Handle refresh token properly
                refresh_token = result.get("refresh_token")
                if not refresh_token:
                    logger.warning(
                        f"No refresh token returned for {platform}, keeping existing one"
                    )
                    refresh_token = existing_integration.refresh_token

                existing_integration.update_tokens(
                    access_token=result["access_token"],
                    refresh_token=refresh_token,
                    expires_in=result.get("expires_in", 3600),
                )
                # Ensure it's active
                existing_integration.is_active = True
                integration = existing_integration
                logger.info(f"Updated existing integration {integration.id}")

                # Check if we still don't have a refresh token
                if not integration.refresh_token:
                    logger.error(
                        f"❌ {platform.title()} integration has no refresh token after update!"
                    )
                    return _popup_response(
                        "error",
                        f"No refresh token available for {platform.title()}. Please re-authenticate.",
                    )
            else:
                # Create new integration
                refresh_token = result.get("refresh_token")
                if not refresh_token:
                    logger.error(
                        f"❌ No refresh token returned for new {platform} integration!"
                    )
                    return _popup_response(
                        "error",
                        f"No refresh token available for {platform.title()}. Please re-authenticate.",
                    )

                integration = UserIntegration(
                    user_id=user_id,
                    platform=platform,
                    account_email=result.get("user_email"),
                    access_token=result["access_token"],
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                )

                db.session.add(integration)
                db.session.flush()  # Get the ID without committing
                logger.info(f"Created new integration {integration.id}")

            # Create webhook if controller created one
            if result.get("webhook_created"):
                try:
                    from app.utils.ngrokWebhookManager import NgrokWebhookManager

                    # Get dynamic webhook URL
                    webhook_url = NgrokWebhookManager.get_webhook_url(platform)
                    logger.info(f"Using dynamic webhook URL: {webhook_url}")

                    # Get parsed identifiers from controller result
                    identifiers = result.get("webhook_identifiers", {})

                    webhook = WebhookModel(
                        user_id=user_id,
                        webhook_url=webhook_url,
                        platform=platform,
                        event_types=(
                            '["meeting_created", "meeting_updated"]'
                            if platform == "google"
                            else '["meeting.created", "meeting.updated", "meeting.started"]'
                        ),
                        calendar_email=result.get("user_email"),
                        access_token=result["access_token"],
                        refresh_token=result.get("refresh_token", ""),
                        auto_create_jobs=True,
                        meeting_start_buffer_minutes=5,
                        # Use parsed identifiers (platform-specific)
                        channel_id=identifiers.get("channel_id"),
                        resource_id=identifiers.get("resource_id"),
                        expiration=datetime.now(timezone.utc) + timedelta(days=7),
                        # Store platform-specific fields
                        webhook_platform_id=identifiers.get(
                            "webhook_id"
                        ),  # Zoom webhook_id / Microsoft subscription_id
                        webhook_events=(
                            json.dumps(identifiers.get("events", []))
                            if identifiers.get("events")
                            else None
                        ),  # Zoom events as JSON
                        webhook_active=identifiers.get(
                            "active", True
                        ),  # Zoom active status
                        notification_url=identifiers.get(
                            "notification_url"
                        ),  # Microsoft notification URL
                        change_type=identifiers.get(
                            "change_type"
                        ),  # Microsoft change types
                        subscription_resource=identifiers.get(
                            "resource"
                        ),  # Microsoft resource
                        client_state=identifiers.get(
                            "client_state"
                        ),  # Microsoft client state
                        token_expires_at=result.get("token_expires_at"),
                    )

                    db.session.add(webhook)
                    logger.info(
                        f"Created {platform} webhook: {result.get('webhook_channel_id')}"
                    )

                except Exception as webhook_error:
                    logger.error(f"Failed to store {platform} webhook: {webhook_error}")

            logger.info(
                f"Committing integration to database: {integration.platform} (ID: {integration.id}, Active: {integration.is_active})"
            )
            db.session.commit()
            logger.info(f"Database commit successful")

            # Redirect to frontend
            redirect_url = f"http://localhost:5173/auth/{platform}/callback?status=success&platform={platform}"
            return redirect(redirect_url)

        except Exception as e:
            logger.error(f"Failed to process {platform} auth callback: {e}")
            frontend_url = f"http://localhost:5173/auth/{platform}/callback?status=error&error=Failed to process authorization"
            return redirect(frontend_url)

    except Exception as e:
        logger.error(f"Failed to handle {platform} auth callback: {e}")
        frontend_url = f"http://localhost:5173/auth/{platform}/callback?status=error&error=Authentication failed"
        return redirect(frontend_url)


@multi_calendar_bp.route("/<platform>/events", methods=["GET"])
def get_calendar_events(platform):
    """Get upcoming calendar events with meeting links"""
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

        days_ahead = request.args.get("days_ahead", 7, type=int)

        # Get user's integration for this platform
        from app.models.userIntegrationModel import UserIntegration

        integration = UserIntegration.query.filter_by(
            user_id=user_id, platform=platform, is_active=True
        ).first()

        if not integration:
            logger.error(
                f"❌ No active {platform} integration found for user {user_id}"
            )
            return jsonify({"error": f"No active {platform} integration found"}), 404

        # Check if token is expired and refresh if needed
        now_utc = datetime.now(timezone.utc)

        # Handle both timezone-aware and naive datetimes
        if integration.expires_at:
            # If expires_at is naive, assume it's UTC
            if integration.expires_at.tzinfo is None:
                expires_at_utc = integration.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at_utc = integration.expires_at

            if expires_at_utc < now_utc:
                try:

                    # Get client credentials for token refresh
                    client_credentials = {}
                    if platform == "google":
                        client_credentials = {
                            "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
                            "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
                        }
                    elif platform == "microsoft":
                        client_credentials = {
                            "MICROSOFT_CLIENT_ID": os.getenv("MICROSOFT_CLIENT_ID"),
                            "MICROSOFT_CLIENT_SECRET": os.getenv(
                                "MICROSOFT_CLIENT_SECRET"
                            ),
                        }
                    elif platform == "zoom":
                        client_credentials = {
                            "ZOOM_CLIENT_ID": os.getenv("ZOOM_CLIENT_ID"),
                            "ZOOM_CLIENT_SECRET": os.getenv("ZOOM_CLIENT_SECRET"),
                        }

                    refresh_result = calendar_controller.refresh_token(
                        platform, integration.refresh_token, **client_credentials
                    )
                    integration.update_tokens(
                        access_token=refresh_result["access_token"],
                        refresh_token=refresh_result.get(
                            "refresh_token", integration.refresh_token
                        ),
                        expires_in=refresh_result.get("expires_in", 3600),
                    )
                    from app.extension import db

                    db.session.commit()
                except Exception as e:
                    logger.error(f"❌ Failed to refresh {platform} token: {e}")
                    return jsonify({"error": "Token expired and refresh failed"}), 401

        result = calendar_controller.get_events(
            platform, integration.access_token, integration.refresh_token, days_ahead
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Failed to get {platform} calendar events: {e}")
        import traceback

        logger.error(f"🐛 Full traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route("/<platform>/events/create-job", methods=["POST"])
def create_job_from_calendar_event(platform):
    """Create a meeting bot job from a calendar event"""
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        event_id = data.get("event_id")

        if not event_id:
            return jsonify({"error": "event_id is required"}), 400

        # Get user's integration for this platform (active or inactive)
        from app.models.userIntegrationModel import UserIntegration

        integration = UserIntegration.query.filter_by(
            user_id=user_id, platform=platform
        ).first()

        if not integration:
            return jsonify({"error": f"No {platform} integration found"}), 404

        result = calendar_controller.create_job_from_event(
            platform,
            event_id,
            integration.access_token,
            integration.refresh_token,
            user_id,
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to create job from {platform} calendar event: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route("/<platform>/token/refresh", methods=["POST"])
def refresh_calendar_token(platform):
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        refresh_token = data.get("refresh_token")
        GOOGLE_CLIENT_ID = data.get("GOOGLE_CLIENT_ID")
        GOOGLE_CLIENT_SECRET = data.get("GOOGLE_CLIENT_SECRET")

        result = calendar_controller.refresh_token(
            platform, refresh_token, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to refresh {platform} token: {e}")
        return jsonify({"error": str(e)}), 400


@multi_calendar_bp.route("/<platform>/disconnect", methods=["DELETE"])
def disconnect_calendar(platform):
    """Disconnect calendar integration (revoke tokens)"""
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        # Get user_id from JWT token
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

        # Get user's integration for this platform
        from app.models.userIntegrationModel import UserIntegration
        from app.extension import db

        # Get user's integration for this platform (active or inactive)
        integration = UserIntegration.query.filter_by(
            user_id=user_id, platform=platform
        ).first()

        if not integration:
            return jsonify({"error": f"No {platform} integration found"}), 404

        # Revoke tokens and remove integration completely
        result = calendar_controller.disconnect_calendar(
            platform, integration.access_token, integration.refresh_token
        )

        # Stop and remove webhook if exists
        # Stop and remove ALL webhook rows for this user+platform
        try:
            from app.models.webhookModel import WebhookModel

            webhooks = WebhookModel.query.filter_by(
                user_id=user_id, platform=platform
            ).all()  # .all() not .first() — multiple stale rows may exist

            for webhook in webhooks:
                # Stop channel on platform side
                if webhook.channel_id:
                    try:
                        calendar_service = calendar_controller._get_service(platform)
                        calendar_service.stop_webhook_channel(
                            integration.access_token,
                            webhook.channel_id,
                            webhook.resource_id,
                        )
                        logger.info(f"Stopped webhook channel {webhook.channel_id}")
                    except Exception as e:
                        logger.warning(
                            f"Could not stop channel {webhook.channel_id}: {e}"
                        )

                # Delete the row regardless of whether stop succeeded
                db.session.delete(webhook)
                logger.info(f"Deleted webhook row {webhook.webhook_id} for {platform}")

        except Exception as webhook_error:
            logger.error(
                f"Error cleaning up webhooks during disconnect: {webhook_error}"
            )

        # Clear sensitive data and delete integration completely
        logger.info(
            f"Clearing tokens and deleting {platform} integration for user {user_id}"
        )

        # Clear tokens first (in case deletion fails)
        integration.access_token = None
        integration.refresh_token = None
        integration.is_active = False

        # Delete the integration completely
        db.session.delete(integration)
        db.session.commit()

        logger.info(
            f"✅ Successfully disconnected and deleted {platform} calendar integration"
        )

        return jsonify(
            {
                "message": "Calendar disconnected successfully",
                "action": "deleted",
                "platform": platform,
                "was_active": integration.is_active,
            }
        )

    except Exception as e:
        logger.error(f"Failed to disconnect {platform} calendar: {e}")
        return jsonify({"error": str(e)}), 400
