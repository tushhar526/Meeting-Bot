from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging
import time

logger = logging.getLogger(__name__)


class Teams:
    def __init__(self, driver, url):
        self.url = url
        self.driver = driver

    def join(self):

        logger.info("Handling Teams meeting join ...")

        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 20)
        try:

            logger.info("Finding the browser join btn")

            browser_btn = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//button[.//h3[contains(text(), 'Continue on this browser')]]",
                    )
                )
            )

            browser_btn.click()

            time.sleep(10)

            logger.info("Finding the no audio and video button")

            # no_AV = wait.until(
            #     EC.element_to_be_clickable(
            #         (
            #             By.XPATH,
            #             "//button[contains(., 'Continue without audio or video') or @type='button']",
            #         )
            #     )
            # )

            # no_AV.click()

            no_AV = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@data-focus-target='gum-continue']")
                )
            )

            no_AV.click()

            time.sleep(10)

            logger.info("Finding the name input")

            name_input = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(@placeholder, 'Type your name') or @type='text']",
                    )
                )
            )

            if name_input:
                logger.info("Entering Name in input")
                name_input.clear()
                name_input.send_keys("Meeting Bot")

            logger.info("Finding the Join button")

            join_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Join now')]")
                )
            )

            join_btn.click()

            return True

        except Exception as e:
            logger.error(f"Exception type: {type(e)}")
            logger.error(f" Error occured in joining Teams meeting due to error = {e}")
            return False

    def detect_end(self):
        try:
            modals = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(),'Enjoy your call? Join Teams today for free') or "
                "contains(text(),'Did you leave by mistake?') or ", 
            )

            for modal in modals:
                if modal.is_displayed():
                    return True

            return False
        except:
            return False
