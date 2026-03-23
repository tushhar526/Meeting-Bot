"""
Multi-Platform Calendar Controller
Handles OAuth flow, event fetching, and webhook setup across platforms.

store_meeting_information has been moved to SchedulerService where it belongs.
This controller only handles OAuth + calendar data — it no longer imports
WebhookController or calls store_meeting_information directly.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

import jwt
from flask import current_app

from app.services.CalendarServiceFactory import CalendarServiceFactory
from app.utils.webhookResponseParser import WebhookResponseParser
from app.utils.ngrokWebhookManager import NgrokWebhookManager
from app.helper.logger import get_logger

logger = get_logger(__name__)


class CalendarController:

    def __init__(self):
        self._services = {}
        self.supported_platforms = CalendarServiceFactory.get_supported_platforms()

    def _get_service(self, platform: str):
        if platform not in self._services:
            self._services[platform] = CalendarServiceFactory.create_service(platform)
        return self._services[platform]

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, platform: str, user_id: int, redirect_uri: str = None) -> Dict[str, Any]:
        if not CalendarServiceFactory.is_platform_supported(platform):
            raise ValueError(f"Unsupported platform: {platform}")
        if not user_id:
            raise ValueError("user_id is required")

        state_payload = {
            "user_id": str(user_id),
            "platform": platform,
            "exp": int(time.time()) + 600,
        }
        secret = current_app.config.get("SECRET_KEY", "dev-secret")
        state = jwt.encode(state_payload, secret, algorithm="HS256")

        service = self._get_service(platform)
        if redirect_uri:
            service.redirect_uri = redirect_uri

        auth_url = service.get_authorization_url(state)
        logger.info(f"[{platform}] Generated auth URL for user {user_id}")
        return {
            "platform": platform,
            "authorization_url": auth_url,
            "state": state,
            "redirect_uri": redirect_uri,
        }

    def handle_callback(
        self,
        platform: str,
        code: str,
        state: str,
        redirect_uri: str = None,
        app_user_id: int = None,  # your app's integer user ID, decoded from JWT state by the route
    ) -> Dict[str, Any]:
        """
        Exchange code for tokens, fetch user info, create webhook, and do initial sync.

        FIX: Enforces one-email-one-user BEFORE touching any DB rows or webhooks.
        If the calendar email is already connected to a different app user, raises
        ValueError immediately with a clear message — zero side-effects.

        NOTE: The calling route should decode app_user_id from the JWT `state`
        and pass it here. Example:
            payload = jwt.decode(state, secret, algorithms=["HS256"])
            app_user_id = int(payload["user_id"])
            result = controller.handle_callback(..., app_user_id=app_user_id)
        """
        from app.models.userIntegrationModel import UserIntegration

        if not code:
            raise ValueError("Authorization code not provided")

        service = self._get_service(platform)
        if redirect_uri:
            service.redirect_uri = redirect_uri

        tokens = service.exchange_code_for_tokens(code)
        user_info = service.get_user_info(tokens["access_token"])
        calendar_email = user_info.get("email")

        # ── One-email-one-user guard ──────────────────────────────────────────
        # Block the connection if this calendar email is already live on another
        # app account. Same user reconnecting is always fine (token refresh case).
        if app_user_id and calendar_email:
            allowed, reason = UserIntegration.claim_or_reject(
                user_id=app_user_id,
                platform=platform,
                account_email=calendar_email,
            )
            if not allowed:
                logger.warning(
                    f"[{platform}] Blocked duplicate connection attempt: "
                    f"'{calendar_email}' already owned by a different user"
                )
                raise ValueError(reason)
        # ─────────────────────────────────────────────────────────────────────

        result = {
            "platform": platform,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
            "token_expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
                if tokens.get("expires_in")
                else None
            ),
            "token_type": tokens.get("token_type", "Bearer"),
            "user_email": calendar_email,
            "user_name": user_info.get("name"),
            "user_id": user_info.get("id"),     # platform's own user ID string (e.g. Google sub)
            "app_user_id": app_user_id,         # YOUR app's integer user ID
        }

        # --- Webhook setup (pass app_user_id so cleanup targets the right rows) ---
        result.update(self._setup_webhook(platform, service, result))

        # --- Initial sync (via SchedulerService to avoid circular imports) ---
        self._initial_sync(platform, service, result)

        return result

    def _setup_webhook(self, platform: str, service, result: Dict) -> Dict:
        """
        Clean up all old webhooks for this app user + platform, then create a fresh one.

        FIX: Was querying by result["user_id"] which is the PLATFORM's user ID string
        (e.g. Google's "118302..."), not your app's integer user_id. WebhookModel.user_id
        stores the app integer, so the old query never matched anything — stale webhook
        rows from previous connections were never cleaned up, causing duplicate channels
        to pile up and fire bots for every connected account.

        Now uses result["app_user_id"] (your app's integer) for the DB lookup.
        """
        from app.models.webhookModel import WebhookModel
        from app.extension import db

        # Use the app's integer user ID, not the platform's string user ID
        app_user_id = result.get("app_user_id")

        try:
            existing_webhooks = WebhookModel.query.filter_by(
                user_id=app_user_id, platform=platform
            ).all()

            if existing_webhooks:
                logger.info(
                    f"[{platform}] Found {len(existing_webhooks)} existing webhook(s) "
                    f"for user {app_user_id} — stopping and removing before creating new one"
                )
                for w in existing_webhooks:
                    try:
                        if w.channel_id:
                            service.stop_webhook_channel(
                                result["access_token"], w.channel_id, w.resource_id
                            )
                            logger.info(f"[{platform}] Stopped old channel: {w.channel_id}")
                    except Exception as e:
                        logger.warning(
                            f"[{platform}] Could not stop old channel {w.channel_id}: {e}"
                        )
                    db.session.delete(w)
                db.session.commit()

            # Create fresh webhook
            webhook_url = NgrokWebhookManager.get_webhook_url(platform)
            webhook_result = service.create_webhook_channel(
                access_token=result["access_token"],
                webhook_url=webhook_url,
            )

            parsed = WebhookResponseParser.get_platform_identifiers_for_storage(
                platform, webhook_result
            )
            if not parsed["success"]:
                logger.error(
                    f"[{platform}] Failed to parse webhook response: {parsed['error']}"
                )
                return {"webhook_created": False, "webhook_error": parsed["error"]}

            identifiers = parsed["platform_identifiers"]
            logger.info(
                f"[{platform}] Created fresh webhook for user {app_user_id}: "
                f"{identifiers.get('channel_id')}"
            )
            return {
                "webhook_created": True,
                "webhook_url": webhook_url,
                "webhook_identifiers": identifiers,
                "webhook_channel_id": identifiers.get("channel_id"),
                "webhook_resource_id": identifiers.get("resource_id"),
                "webhook_expiration": identifiers.get("expiration"),
            }

        except Exception as e:
            logger.error(f"[{platform}] Webhook creation failed: {e} — falling back to polling")
            return {
                "webhook_created": False,
                "webhook_error": str(e),
                "fallback_polling": True,
            }

    def _initial_sync(self, platform: str, service, result: Dict):
        """Fetch upcoming meetings and schedule bots. Uses SchedulerService."""
        try:
            from app.services.schedulerService import scheduler_service

            # Prefer app_user_id (integer) — fall back to platform user_id for compat
            user_id = result.get("app_user_id") or result.get("user_id")

            events = service.get_upcoming_meetings(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token"),
            )
            synced = 0
            for event in events:
                if event.get("meeting_link"):
                    scheduler_service.store_and_schedule(event, user_id)
                    synced += 1

            logger.info(f"[{platform}] Initial sync: {synced} meetings scheduled")

        except Exception as e:
            logger.error(f"[{platform}] Initial sync failed: {e}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def get_events(
        self,
        platform: str,
        access_token: str,
        refresh_token: str,
        days_ahead: int = 7,
    ) -> Dict[str, Any]:
        if not access_token:
            raise ValueError("access_token is required")

        service = self._get_service(platform)
        meetings = service.get_upcoming_meetings(
            access_token=access_token,
            refresh_token=refresh_token,
            days_ahead=days_ahead,
        )
        return {
            "platform": platform,
            "meetings": meetings,
            "count": len(meetings),
        }

    # ------------------------------------------------------------------
    # Token refresh (thin wrapper — real logic is in TokenService)
    # ------------------------------------------------------------------

    def refresh_token(self, platform: str, refresh_token: str, **client_credentials) -> Dict[str, Any]:
        """Kept for backward compatibility with TokenService calls."""
        from app.services.tokenService import TokenService
        return TokenService._refresh_token(platform, refresh_token)

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    def disconnect_calendar(self, platform: str, access_token: str, refresh_token: str) -> Dict:
        try:
            if platform == "google" and access_token:
                import requests
                try:
                    requests.post(
                        f"https://oauth2.googleapis.com/revoke?token={access_token}"
                    )
                    logger.info("[Google] Revoked access token")
                except Exception as e:
                    logger.warning(f"[Google] Token revocation failed (non-fatal): {e}")

            logger.info(f"[{platform}] Calendar disconnected")
            return {"message": "Calendar disconnected successfully"}

        except Exception as e:
            logger.error(f"[{platform}] Disconnect failed: {e}")
            raise

    def get_supported_platforms(self) -> List[str]:
        return self.supported_platforms