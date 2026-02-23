import logging
import re

logger = logging.getLogger(__name__)


class Teams:
    def __init__(self,url, page):
        self.url = url
        self.page = page

    def join(self):

        logger.info("Handling Teams meeting join ...")

        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

        try:

            logger.info("Finding the browser join btn")
            self.page.locator("button:has-text('Continue on this browser')").click()
            logger.info("Finding the no audio and video button")

            no_AV = self.page.locator("button[data-focus-target='gum-continue']")
            no_AV.click()

            
            logger.info("Finding the name input")
            self.page.locator(
                "input[type='test'] , input[placeholder='Type your name']"
            ).fill("Meeting Bot")


            
            logger.info("Finding the Join button")
            join_btn = self.page.get_by_role("button", name=re.compile("Join now"))
            join_btn.click()

            return True

        except Exception as e:
            logger.error(f"Exception type: {type(e)}")
            logger.error(f" Error occured in joining Teams meeting due to error = {e}")
            return False

    def detect_end(self):
        try:
            if self.page.get_by_text(
                re.compile(
                    "Enjoy your call? Join Teams today for free|Did you leave by mistake?"
                )
            ).is_visible():
                return True

            return False
        except:
            return False
