import logging
import re

logger = logging.getLogger(__name__)


class Meet:
    def __init__(self, url, page):
        self.url = url
        self.page = page

    def join(self):
        logger.info("Handling Google meet's meeting join ...")

        self.page.goto(self.url)

        self.page.wait_for_load_state("networkidle")

        try:

            logger.info("Finding the name input tag")
            self.page.locator("input[placeholder = 'Your name']").fill("Meeting Bot")
            logger.info("Entered name Meeting bot")

            logger.info("Finding the joining button")

            no_AV = self.page.get_by_role(
                "button", name=re.compile("Continue without microphone and camera")
            )

            no_AV.click()

            join_btn = self.page.get_by_role(
                "button", name=re.compile("Join now|Ask to join")
            )

            join_btn.click()
            logger.info("Pressed the Ask to Join btn")

            return True
        except Exception as e:
            logger.warning(f" The type of error = {type(e)}")
            logger.error(f"Google Meet specific Error = {e}")
            return False

    def detect_end(self):
        try:
            if self.page.get_by_text(re.compile(r"1 joined Just you")).is_visible():
                return True

            return False
        except:
            return False
