import logging
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


class Meet:
    def __init__(self, url, driver):
        self.url = url
        self.driver = driver

    def join(self):

        logger.info("Handling Google meet's meeting join ...")
        self.driver.get(self.url)

        wait = WebDriverWait(self.driver, 10)

        try:
            name_input = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(@placeholder,'Your name') or @type='text']",
                    )
                )
            )

            if name_input:
                name_input.clear()
                name_input.send_keys("Meeting Bot")
                logger.info("Entered name: Meeting Bot")
                time.sleep(1)
            else:
                logger.warning("Name input field not found, proceeding anyway")

            # wait.until(
            #     lambda d: d.find_element(
            #         By.XPATH, "//button[contains(., 'Join now') or contains(.,'Ask to join')]"
            #     ).is_enabled()
            # )

            join_btn = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(text(), 'Join now') or contains(text(), 'Ask to join')]",
                    )
                )
            ).click()

            # join_btn.click()
            logger.info("Pressed the Ask to Join btn")
        except Exception as e:
            logger.error(f" Error occured in joining google meet meeting due to = {e}")

    def detect_end():
        return False