import logging
import re

logger = logging.getLogger(__name__)


class Zoom:

    def __init__(self, url, page):
        self.url = url
        self.page = page

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

    def detect_end(self):
        try:
            if self.page.get_by_text(
                re.compile(r"This meeting has been ended by host")
            ).is_visible():
                return True

            return False
        except:
            return False
