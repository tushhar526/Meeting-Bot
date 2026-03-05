import logging
import re
from app.helper.decorators import retry
import time

logger = logging.getLogger(__name__)


class Zoom:

    def __init__(self, url, page):
        self.url = url
        self.page = page

    @retry(times=3, delay=5)
    def join(self):
        logger.info("Handling Zoom meeting join...")

        self.url = self.url.replace("/j/", "/wc/join/")

        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

        try:
            self.page.locator("input[type = 'text'], input[placeholder='name']").fill(
                "Meeting Bot"
            )

            join_btn = self.page.get_by_role("button", name=re.compile("Join"))

            join_btn.click()

            return True

        except Exception as e:
            logger.exception(f"Zoom-specific handling error: {e}")
            return False

    def host_ended(self):
        try:
            if self.page.get_by_text(
                re.compile(r"This meeting has been ended by host")
            ).is_visible():
                return True

            return False
        except:
            return False

    def detect_end(self, grace_period=60) -> bool:

        if self.host_ended():
            logger.info("Host ended the meeting")
            return True

        count = self._get_participant_count()

        if count is None:
            logger.warning("Could not read participant count — staying to be safe")
            return False

        if count > 1:
            return False

        # Bot is alone — start grace period
        logger.info(
            f"Bot is alone ({count} participant), starting {grace_period}s grace period..."
        )
        start_time = time.time()

        while time.time() - start_time < grace_period:
            try:
                if self.host_ended():
                    logger.info("Host ended meeting during grace period")
                    return True

                count = self._get_participant_count()

                if count is None:
                    time.sleep(2)
                    continue

                if count > 1:
                    logger.info(
                        f"Someone joined during grace period ({count} participants) — staying"
                    )
                    return False

            except Exception as e:
                logger.warning(f"Error during grace period check: {e}")

            time.sleep(2)

        logger.info("Grace period expired — leaving")
        return True

    def _get_participant_count(self):
        """
        Returns participant count as int, or None if unreadable.
        Zoom shows count in .footer-button__number-counter span
        """
        try:
            counter = self.page.locator(".footer-button__number-counter span")
            if counter.count() == 0:
                return None
            return int(counter.first.inner_text().strip())
        except:
            return None
