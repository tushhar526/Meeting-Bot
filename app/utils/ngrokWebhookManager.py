import os
import logging
import requests
from typing import Dict, Optional, Any
from app.models.webhookModel import WebhookModel
from app.extension import db
from app.services.CalendarServiceFactory import CalendarServiceFactory

logger = logging.getLogger(__name__)


class NgrokWebhookManager:
    """Manages webhook URLs for ngrok development environment"""

    @staticmethod
    def get_current_ngrok_url() -> Optional[str]:
        """Get current ngrok URL from ngrok API"""
        try:
            # Ngrok API endpoint
            ngrok_host = os.getenv("NGROK_HOST", "host.docker.internal")
            ngrok_api_key = os.getenv("NGROK_API_KEY")
            
            headers = {"Authorization": f"Bearer {ngrok_api_key}"} if ngrok_api_key else {}
            response = requests.get(f"http://{ngrok_host}:4040/api/tunnels",headers=headers)
            response.raise_for_status()

            tunnels = response.json().get("tunnels", [])
            for tunnel in tunnels:
                if tunnel.get("proto") == "https" and tunnel.get("status") == "running":
                    return tunnel.get("public_url")

            logger.warning("No active ngrok HTTPS tunnel found")
            return None

        except requests.exceptions.ConnectionError:
            logger.error("Ngrok not running or not accessible on port 4040")
            return None
        except Exception as e:
            logger.error(f"Error getting ngrok URL: {e}")
            return None

    @staticmethod
    def get_webhook_base_url() -> str:
        """Get webhook base URL from environment or ngrok"""
        # Check if webhook base URL is explicitly set
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL")
        if webhook_base_url:
            return webhook_base_url.rstrip("/")

        # Try to get ngrok URL
        ngrok_url = NgrokWebhookManager.get_current_ngrok_url()
        if ngrok_url:
            logger.info(f"Using ngrok URL: {ngrok_url}")
            return ngrok_url

        # Fallback to localhost
        logger.warning("No webhook base URL found, falling back to localhost")
        return "http://localhost:5000"

    @staticmethod
    def get_webhook_url(platform: str) -> str:
        """Get full webhook URL for platform"""
        base_url = NgrokWebhookManager.get_webhook_base_url()
        return f"{base_url}/webhooks/receive/{platform}"

    @staticmethod
    def update_all_webhook_urls() -> Dict[str, int]:
        """Update all webhook URLs to current ngrok URL"""
        try:
            current_base_url = NgrokWebhookManager.get_webhook_base_url()
            updated_count = 0
            platform_counts = {}
            reintegration_required = {}  # Track platforms needing reintegration

            # Get all active webhooks
            webhooks = WebhookModel.query.filter_by(is_active=True).all()

            for webhook in webhooks:
                old_url = webhook.webhook_url
                new_url = f"{current_base_url}/webhooks/receive/{webhook.platform}"

                if old_url != new_url:
                    # Update webhook URL in database
                    webhook.webhook_url = new_url
                    logger.info(
                        f"Updated webhook URL for {webhook.platform}: {old_url} -> {new_url}"
                    )
                    updated_count += 1

                    # Track by platform
                    platform_counts[webhook.platform] = (
                        platform_counts.get(webhook.platform, 0) + 1
                    )

                    # Update webhook on platform if supported
                    platform_updated = NgrokWebhookManager._update_platform_webhook(
                        webhook, new_url
                    )

                    if not platform_updated:
                        # Platform doesn't support updates - mark for reintegration
                        reintegration_required[webhook.platform] = True
                        logger.warning(f"⚠️ {webhook.platform} requires reintegration")

            # Commit changes
            db.session.commit()

            result = {
                "total_updated": updated_count,
                "platform_counts": platform_counts,
                "new_base_url": current_base_url,
            }

            # Add reintegration info if needed
            if reintegration_required:
                result["reintegration_required"] = list(reintegration_required.keys())
                result["message"] = (
                    f"Updated {updated_count} webhook URLs. Some platforms require reintegration: {', '.join(reintegration_required.keys())}"
                )
            else:
                result["message"] = f"Successfully updated {updated_count} webhook URLs"

            logger.info(f"Updated {updated_count} webhook URLs to {current_base_url}")
            return result

        except Exception as e:
            logger.error(f"Error updating webhook URLs: {e}")
            db.session.rollback()
            return {"error": str(e)}

    @staticmethod
    def _update_platform_webhook(webhook: WebhookModel, new_url: str) -> bool:
        """Update webhook on the platform (if supported)"""
        try:
            calendar_service = CalendarServiceFactory.create_service(webhook.platform)

            # Check if platform supports webhook updates
            if hasattr(calendar_service, "update_webhook_channel"):
                # Get platform-specific identifiers for update
                update_identifiers = NgrokWebhookManager._get_update_identifiers(
                    webhook
                )

                success = calendar_service.update_webhook_channel(
                    access_token=webhook.access_token,
                    new_webhook_url=new_url,
                    **update_identifiers,  # Pass platform-specific identifiers
                )

                if success:
                    logger.info(f"✅ Updated {webhook.platform} webhook on platform")
                    return True
                else:
                    logger.warning(
                        f"❌ Failed to update {webhook.platform} webhook on platform"
                    )
                    return False
            else:
                logger.info(
                    f"⚠️ Platform {webhook.platform} does not support webhook updates - reintegration required"
                )
                return False

        except Exception as e:
            logger.error(
                f"❌ Error updating {webhook.platform} webhook on platform: {e}"
            )
            return False

    @staticmethod
    def _get_update_identifiers(webhook: WebhookModel) -> Dict[str, Any]:
        """Get platform-specific identifiers needed for webhook updates"""
        platform = webhook.platform.lower()

        if platform == "google":
            return {
                "channel_id": webhook.channel_id,
                "resource_id": webhook.resource_id,
            }
        elif platform == "zoom":
            return {
                "webhook_id": webhook.webhook_platform_id,  # Use the correct field name
                "channel_id": webhook.channel_id,  # Mapped for consistency
            }
        elif platform == "microsoft":
            return {
                "subscription_id": webhook.webhook_platform_id,  # Use the correct field name
                "channel_id": webhook.channel_id,  # Mapped for consistency
            }
        else:
            return {}

    @staticmethod
    def create_webhook_with_dynamic_url(
        platform: str, user_id: int, access_token: str, **kwargs
    ) -> Dict[str, Any]:
        """Create webhook with dynamic URL support"""
        try:
            # Get current webhook URL
            webhook_url = NgrokWebhookManager.get_webhook_url(platform)

            # Create webhook
            calendar_service = CalendarServiceFactory.create_service(platform)

            if hasattr(calendar_service, "create_webhook_channel"):
                webhook_result = calendar_service.create_webhook_channel(
                    access_token=access_token, webhook_url=webhook_url
                )

                # Store webhook with current URL
                webhook = WebhookModel(
                    user_id=user_id,
                    webhook_url=webhook_url,  # Store current URL
                    platform=platform,
                    channel_id=webhook_result.get("id"),
                    resource_id=webhook_result.get("resourceId"),
                    access_token=access_token,
                    **kwargs,
                )

                db.session.add(webhook)
                db.session.commit()

                logger.info(f"Created {platform} webhook with URL: {webhook_url}")
                return {
                    "success": True,
                    "webhook_id": webhook.webhook_id,
                    "webhook_url": webhook_url,
                    "platform_result": webhook_result,
                }
            else:
                logger.info(f"Platform {platform} does not support webhooks")
                return {
                    "success": False,
                    "message": "Platform does not support webhooks",
                }

        except Exception as e:
            logger.error(f"Error creating webhook with dynamic URL: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_ngrok_status() -> Dict[str, Any]:
        """Check ngrok status and current URL"""
        try:
            ngrok_url = NgrokWebhookManager.get_current_ngrok_url()

            if ngrok_url:
                return {
                    "ngrok_running": True,
                    "current_url": ngrok_url,
                    "webhook_base_url": ngrok_url,
                    "status": "active",
                }
            else:
                return {
                    "ngrok_running": False,
                    "current_url": None,
                    "webhook_base_url": NgrokWebhookManager.get_webhook_base_url(),
                    "status": "inactive",
                }

        except Exception as e:
            return {
                "ngrok_running": False,
                "current_url": None,
                "webhook_base_url": NgrokWebhookManager.get_webhook_base_url(),
                "status": "error",
                "error": str(e),
            }
