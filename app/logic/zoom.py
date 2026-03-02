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

    def detect_end(self, gracePeriod=60):

        if self.host_ended():
            return True

        counter = self.page.locator(".footer-button__number-counter span")

        if counter.count() == 0:
            return True

        try:
            count = int(counter.first.inner_text().strip())
        except:
            return False

        if count > 1:
            return False

        start = time.time()

        while time.time() - start < gracePeriod:
            try:
                count = int(counter.first.inner_text().strip())
            except:
                time.sleep(2)
                continue

            if count > 1:
                return False

            if self.host_ended():
                return True

            time.sleep(2)

        return True
