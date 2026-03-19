import logging
from typing import Dict

from .base.basewebhookController import BaseWebhookHandler, HandlerResult
from .platform.googlewebhookController import GoogleWebhookHandler
from .platform.microsoftwebhookController import MicrosoftWebhookHandler
from .platform.zoomwebhookController import ZoomWebhookHandler

logger = logging.getLogger(__name__)


class WebhookController:
    """Central dispatcher — maps platform name → handler instance."""

    _registry: Dict[str, BaseWebhookHandler] = {
        "google": GoogleWebhookHandler(),
        "microsoft": MicrosoftWebhookHandler(),
        "zoom": ZoomWebhookHandler(),
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def dispatch(cls, platform: str, request) -> HandlerResult:
        """
        Verify and handle an incoming webhook for the given platform.

        Returns (response_dict, http_status_code).
        """
        handler = cls._registry.get(platform)
        if not handler:
            logger.error(f"No handler registered for platform: {platform}")
            return {"error": f"Unsupported platform: {platform}"}, 400

        if not handler.verify(request):
            logger.warning(f"[{platform}] Webhook verification failed")
            return {"error": "Webhook verification failed"}, 401

        return handler.handle(request)

    @classmethod
    def register(cls, platform: str, handler: BaseWebhookHandler) -> None:
        """Register a new platform handler at runtime."""
        cls._registry[platform] = handler
        logger.info(f"Registered webhook handler for platform: {platform}")

    @classmethod
    def supported_platforms(cls):
        return list(cls._registry.keys())