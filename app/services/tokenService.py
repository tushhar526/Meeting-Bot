"""
Token Service — handles OAuth token refresh across platforms.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Union

from app.models.webhookModel import WebhookModel
from app.models.userIntegrationModel import UserIntegration
from app.extension import db

logger = logging.getLogger(__name__)

# Token refresh endpoints per platform
_REFRESH_URLS = {
    "google": "https://oauth2.googleapis.com/token",
    "microsoft": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "zoom": "https://zoom.us/oauth/token",
}

# Env var names for client credentials per platform
_CREDENTIAL_KEYS: Dict[str, Dict[str, str]] = {
    "google": {
        "client_id": "GOOGLE_CLIENT_ID",
        "client_secret": "GOOGLE_CLIENT_SECRET",
    },
    "microsoft": {
        "client_id": "MICROSOFT_CLIENT_ID",
        "client_secret": "MICROSOFT_CLIENT_SECRET",
    },
    "zoom": {
        "client_id": "ZOOM_CLIENT_ID",
        "client_secret": "ZOOM_CLIENT_SECRET",
    },
}


class TokenService:
    """Handles token expiry checks and OAuth refresh for WebhookModel and UserIntegration."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def get_valid_access_token(
        obj: Union[WebhookModel, UserIntegration],
    ) -> Optional[str]:
        """
        Return a valid access token, refreshing first if the token is expired.
        Falls back to the stored token if refresh fails.
        """
        refreshed = TokenService.refresh_access_token_if_needed(obj)
        if refreshed:
            return refreshed
        # Fallback — return whatever is stored (may still work)
        return getattr(obj, "access_token", None)

    @staticmethod
    def refresh_access_token_if_needed(
        obj: Union[WebhookModel, UserIntegration],
    ) -> Optional[str]:
        """
        Refresh the access token only if it is expired or expiring soon.
        Persists the new token to the DB on success.
        Returns the new access token, or the current one if refresh wasn't needed.
        """
        try:
            platform = obj.platform
            user_id = obj.user_id

            if not TokenService._is_token_expired(obj):
                return obj.access_token

            logger.info(f"[TokenService] Refreshing expired {platform} token for user {user_id}")

            refresh_token = obj.refresh_token
            if not refresh_token:
                logger.error(f"[TokenService] No refresh token available for {platform} user {user_id}")
                return None

            token_result = TokenService._refresh_token(platform, refresh_token)

            # Persist new tokens
            obj.access_token = token_result["access_token"]
            if token_result.get("refresh_token"):
                obj.refresh_token = token_result["refresh_token"]

            # Update expiry
            expires_in = token_result.get("expires_in")
            if expires_in:
                new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                if isinstance(obj, WebhookModel):
                    obj.token_expires_at = new_expiry  # ← correct field name
                elif isinstance(obj, UserIntegration) and hasattr(obj, "update_tokens"):
                    obj.update_tokens(
                        access_token=token_result["access_token"],
                        refresh_token=token_result.get("refresh_token", refresh_token),
                        expires_in=expires_in,
                    )

            db.session.commit()
            logger.info(f"[TokenService] Successfully refreshed {platform} token for user {user_id}")
            return token_result["access_token"]

        except Exception as e:
            logger.error(f"[TokenService] Failed to refresh token: {e}")
            db.session.rollback()
            return None

    @staticmethod
    def revoke_tokens(obj: Union[WebhookModel, UserIntegration]) -> bool:
        """Mark tokens as revoked and deactivate the record."""
        try:
            if isinstance(obj, WebhookModel):
                obj.is_active = False
                obj.access_token = None
                obj.refresh_token = None
            elif isinstance(obj, UserIntegration):
                obj.deactivate()
            db.session.commit()
            logger.info(f"[TokenService] Revoked tokens for {type(obj).__name__}")
            return True
        except Exception as e:
            logger.error(f"[TokenService] Failed to revoke tokens: {e}")
            db.session.rollback()
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_token_expired(obj: Union[WebhookModel, UserIntegration]) -> bool:
        """Return True if the token is expired or will expire within 5 minutes."""
        try:
            if isinstance(obj, UserIntegration):
                return obj.is_expired()

            if isinstance(obj, WebhookModel):
                expires_at = obj.token_expires_at  # correct field name
                if not expires_at:
                    # No expiry info stored — cannot proactively refresh.
                    # Handlers will catch 401s and force a refresh.
                    return False
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                return datetime.now(timezone.utc) >= expires_at - timedelta(minutes=5)

            return False

        except Exception as e:
            logger.error(f"[TokenService] Error checking token expiration: {e}")
            return False

    @staticmethod
    def _refresh_token(platform: str, refresh_token: str) -> Dict[str, Any]:
        """Call the platform token endpoint and return the raw token response."""
        import requests

        url = _REFRESH_URLS.get(platform)
        if not url:
            raise ValueError(f"Unsupported platform for token refresh: {platform}")

        cred_keys = _CREDENTIAL_KEYS.get(platform, {})
        client_id = os.getenv(cred_keys.get("client_id", ""))
        client_secret = os.getenv(cred_keys.get("client_secret", ""))

        if not client_id or not client_secret:
            raise ValueError(f"Missing client credentials for {platform}")

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", refresh_token),
            "expires_in": tokens.get("expires_in", 3600),
        }