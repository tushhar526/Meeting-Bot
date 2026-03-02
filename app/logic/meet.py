import logging
import re
import time
from app.helper.decorators import retry

logger = logging.getLogger(__name__)


class Meet:
    def __init__(self, url, page):
        self.url = url
        self.page = page

    @retry(times=3, delay=5)
    def join(self):
        logger.info("Handling Google meet's meeting join ...")

        self.page.goto(self.url)

        self.page.wait_for_load_state("networkidle")

        try:

            time.sleep(5)

            import re

            logger.info("Continue without microphone and camera")

            no_av = self.page.get_by_role(
                "button",
                name=re.compile(
                    "Continue without microphone and camera", re.IGNORECASE
                ),
            )

            no_av.wait_for(state="visible", timeout=10000)
            no_av.click()

            logger.info("Finding the name input tag")
            name = self.page.locator("input[placeholder = 'Your name']")
            time.sleep(2)
            name.fill("Meeting Bot")
            logger.info("Entered name Meeting bot")

            logger.info("Finding the joining button")
            time.sleep(3)
            join_btn = self.page.get_by_role(
                "button", name=re.compile("Join now|Ask to join")
            )
            join_btn.click()
            logger.info("Pressed the Ask to Join btn")

            return True
        except Exception as e:
            if self.page.get_by_text(
                re.compile(r"This meeting has been ended by host")
            ).is_visible():
                logger.error(
                    "Bot got redirected to the You can't join this meeeting page"
                )
                return False
            logger.warning(f" The type of error = {type(e)}")
            logger.error(f"Google Meet specific Error = {e}")
            return False

    def detect_end(self, gracePeriod=60):
        try:
            participant = self.page.locator("[data-avatar-count]")

            if participant.count() == 0:
                return True

            try:
                count = int(participant.first.inner_text().strip())
            except:
                return False

            if count > 1:
                return False

            start = time.time()

            while time.time() - start < gracePeriod:
                if participant.count() == 0:
                    return True
                try:
                    count = int(participant.first.inner_text().strip())
                except:
                    time.sleep(2)
                    continue

                if count > 1:
                    return False

                time.sleep(2)

            return True
        except:
            return False
