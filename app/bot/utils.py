import os
from datetime import datetime
from app.core.middlewares.global_logger import get_logger

logger = get_logger("SCREENSHOT")


class ScreenshotMixin:
    """Mixin to provide screenshot functionality for meeting bot platforms."""

    def _take_screenshot(self, step_name: str, platform: str = "unknown") -> None:
        """
        Take a screenshot and save to app/debug/{platform}/{meeting_id}/{step_name}.png

        Args:
            step_name: Name of the step for the screenshot filename
            platform: Platform name (google, microsoft, zoom) for folder organization
        """
        try:
            meeting_id = getattr(self, "meeting_id", "unknown")
            debug_dir = f"app/debug/{platform}/{meeting_id}"
            os.makedirs(debug_dir, exist_ok=True)

            # Get step counter, initialize if not present
            step_counter = getattr(self, "_screenshot_step", 0)
            timestamp = datetime.now().strftime("%H%M%S")
            filepath = f"{debug_dir}/{step_counter:02d}_{step_name}_{timestamp}.png"

            self.page.screenshot(path=filepath, full_page=True)
            logger.info(f"[SCREENSHOT] [{platform.upper()}] Saved: {filepath}")

            # Increment step counter
            self._screenshot_step = step_counter + 1
        except Exception as e:
            logger.warning(f"[SCREENSHOT] Failed to capture {step_name}: {e}")
