from flask import Blueprint, request, jsonify, current_app
import logging
import os
import jwt
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

auth_callback_bp = Blueprint('auth_callback', __name__, url_prefix="/auth")

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
                    Your Google Calendar has been connected successfully.
                </p>
                
                <div class="integration-info">
                    <strong>Integration Details:</strong><br>
                    Platform: Google Calendar<br>
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
                        platform: 'google',
                        integration_id: {data.get('integration_id', 'null')},
                        user_email: '{data.get('user_email', '')}'
                    }}, '*');
                }}
            </script>
        </body>
        </html>
        """
        return html_template, 200, {'Content-Type': 'text/html'}
    else:
        response_data = {
            "type": "google_auth_error", 
            "success": False,
            "error": message
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
                        window.opener.postMessage(authData, '{frontend_origin}');
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

@auth_callback_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback and store integration securely"""
    try:
        # Extract OAuth parameters
        code = request.args.get('code')
        state = request.args.get('state')
        scope = request.args.get('scope')
        error = request.args.get('error')
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            return _popup_response("error", f"OAuth error: {error}")
        
        if not code:
            logger.error("No authorization code received")
            return _popup_response("error", "No authorization code received")
        
        # Decode state to get user_id
        try:
            state_data = jwt.decode(
                state, 
                current_app.config.get('SECRET_KEY', 'dev-secret'), 
                algorithms=['HS256']
            )
            user_id = state_data.get('user_id')
            if not user_id:
                raise ValueError("Invalid state parameter")
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            return _popup_response("error", "Invalid state parameter")
        
        logger.info(f"Processing Google OAuth for user {user_id}")
        
        # Exchange code for tokens
        from app.services.platform.GoogleCalendarService import GoogleCalendarService
        from app.models.userIntegrationModel import UserIntegration
        from app.extension import db
        
        try:
            google_service = GoogleCalendarService()
            tokens = google_service.exchange_code_for_tokens(code)
            user_info = google_service.get_user_info(tokens['access_token'])
            
            # Calculate expiry time
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens.get('expires_in', 3600)
            )
            
            # Find existing integration for this user and platform
            existing_integration = UserIntegration.query.filter_by(
                user_id=user_id,
                platform='google'
            ).first()
            
            if existing_integration:
                # Reactivate and update existing integration
                existing_integration.is_active = True
                existing_integration.update_tokens(
                    access_token=tokens['access_token'],
                    refresh_token=tokens.get('refresh_token', ''),
                    expires_in=tokens.get('expires_in', 3600)
                )
                existing_integration.account_email = user_info.get('email')
                existing_integration.expires_at = expires_at
                db.session.commit()
                integration_id = existing_integration.id
                logger.info(f"Reactivated existing integration {integration_id}")
            else:
                # Create new integration
                new_integration = UserIntegration(
                    user_id=user_id,
                    platform='google',
                    account_email=user_info.get('email'),
                    access_token=tokens['access_token'],
                    refresh_token=tokens.get('refresh_token', ''),
                    expires_at=expires_at
                )
                db.session.add(new_integration)
                db.session.commit()
                integration_id = new_integration.id
                logger.info(f"Created new integration {integration_id}")
            
            # Return minimal popup response
            return _popup_response("success", "Google Calendar connected", {
                "integration_id": integration_id,
                "platform": "google",
                "user_email": user_info.get('email'),
                "user_name": user_info.get('name')
            })
            
        except Exception as e:
            logger.error(f"Failed to process Google OAuth: {e}")
            return _popup_response("error", "Failed to process authorization")
        
    except Exception as e:
        logger.error(f"Unexpected error in Google callback: {e}")
        return _popup_response("error", "Authentication failed")

@auth_callback_bp.route('/zoom/callback', methods=['GET'])
def zoom_callback():
    """Handle Zoom OAuth callback"""
    try:
        # Get all query parameters
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return jsonify({"error": f"OAuth error: {error}"}), 400
        
        if not code:
            return jsonify({"error": "No authorization code received"}), 400
        
        logger.info(f"Received Zoom OAuth callback with code: {code[:10]}...")
        
        # Always return JSON response
        return jsonify({
            "success": True,
            "message": "Authorization successful",
            "code": code,
            "state": state
        })
        
    except Exception as e:
        logger.error(f"Error in Zoom auth callback: {e}")
        return jsonify({"error": "Authentication callback failed"}), 500
