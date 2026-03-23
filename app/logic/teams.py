import logging
import time
import re
import random
from app.helper.decorators import retry
from app.helper.logger import get_logger

logger = get_logger(__name__)


class Teams:
    def __init__(self, url, page):
        self.url = url
        self.page = page
        logger.info(f"Teams handler initialized for URL: {url}")

    @retry(times=3, delay=5)
    def join(self):
        logger.info("Handling Teams meeting join ...")

        self.page.goto(self.url)

        steps = [
            self._step_continue_on_browser,
            self._step_no_av,
            self._step_fill_name,
            self._step_join_now,
        ]

        for step in steps:
            try:
                step()
            except Exception as e:
                logger.warning(f"Step {step.__name__} failed or was skipped: {e}")

        try:
            self.page.locator("#roster-button").wait_for(state="visible", timeout=120000)
            logger.info("Join sequence completed successfully")
            return True
        except Exception as e:
            logger.error(f"Never made it into the meeting — {e}")
            return False

    def _step_continue_on_browser(self):
        """
        Optional step — only appears sometimes depending on
        how Teams loads. Skipped silently if not present.
        """
        btn = self.page.locator(
            "button:has-text('Continue on this browser'), "
            "button[data-tid='joinOnWeb']"
        ).first

        try:
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            logger.info("Clicked 'Continue on this browser'")
        except:
            logger.info("No 'Continue on this browser' button — skipping")

    def _step_no_av(self):
        """Turn off camera and mic on Teams pre-join screen."""
        
        # Wait for mic toggle to appear
        try:
            self.page.wait_for_selector(
                "input[data-tid='toggle-mute']",
                timeout=30000,
            )
            logger.info("AV controls detected")
        except Exception as e:
            logger.warning(f"AV controls not found — skipping: {e}")
            return

        # Turn off mic (it's a checkbox input, not a button)
        try:
            mic_input = self.page.locator("input[data-tid='toggle-mute']")
            if mic_input.is_checked():
                mic_input.click()
                logger.info("Microphone turned off")
            else:
                logger.info("Microphone already off")
        except Exception as e:
            logger.warning(f"Could not turn off microphone: {e}")

        # Turn off camera (look for the camera toggle the same way)
        try:
            cam_input = self.page.locator("input[data-tid='toggle-video']")
            if cam_input.count() > 0 and cam_input.is_checked():
                cam_input.click()
                logger.info("Camera turned off")
            else:
                logger.info("Camera already off or not found")
        except Exception as e:
            logger.warning(f"Could not turn off camera: {e}")  
            
    def _step_fill_name(self):
        """Fill in the bot name."""
        name_input = self.page.locator(
            "input[placeholder='Type your name'], "
            "input[aria-label*='name' i], "  # case insensitive
            "input[type='text']"
        ).first
        name_input.wait_for(state="visible", timeout=10000)
        name_input.fill("Meeting Bot")
        logger.info("Filled name")

    def _step_join_now(self):
        """Click the final join button."""
        join_btn = self.page.get_by_role(
            "button", name=re.compile("Join now", re.IGNORECASE)
        )
        join_btn.wait_for(state="visible", timeout=10000)
        join_btn.click()
        logger.info("Clicked Join now")  # def join(self):

    def host_end_screen(self):
        try:
            # Checks if the meeting was ended by the host or the bot was kicked
            return self.page.get_by_text(
                re.compile(
                    "Enjoy your call? Join Teams today for free|Did you leave by mistake?"
                )
            ).is_visible()
        except:
            return False

    def detect_end(self, grace_period=60) -> bool:

        try:
            roster_btn = self.page.locator("#roster-button")
            # logger.info(f"Roster button HTML: {roster_btn.inner_html()}")
        except Exception as e:
            logger.warning(f"Could not read roster button: {e}")

        if self._is_someone_in_meeting():
            return False

        # Active participants in meeting — stay
        if self._is_someone_in_meeting():
            return False

        # Someone waiting in lobby — stay
        if self._is_someone_in_lobby():
            return False

        # Host ended the meeting — leave immediately
        if self.host_end_screen():
            logger.info("Host ended the meeting")
            return True

        # Bot is alone — grace period
        logger.info(f"Bot is alone, starting {grace_period}s grace period...")
        start_time = time.time()

        while time.time() - start_time < grace_period:
            try:
                if self._is_someone_in_meeting():
                    logger.info("Someone joined during grace period — staying")
                    return False

                if self._is_someone_in_lobby():
                    logger.info("Someone in lobby during grace period — staying")
                    return False

                if self.host_end_screen():
                    logger.info("Host ended meeting during grace period")
                    return True

            except Exception as e:
                logger.warning(f"Error during grace period check: {e}")

            time.sleep(2)

        logger.info("Grace period expired — leaving")
        return True

    def _is_someone_in_meeting(self) -> bool:
        """toolbar-item-badge appears when there are 2+ people in the meeting"""
        try:
            return self.page.locator('[data-tid="toolbar-item-badge"]').count() > 0
        except:
            return False

    def _is_someone_in_lobby(self) -> bool:
        """roster-button-badge appears when someone is waiting to join"""
        try:
            return self.page.locator('[data-tid="roster-button-badge"]').count() > 0
        except:
            return False
