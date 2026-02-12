from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
import time
from selenium.webdriver.support import expected_conditions as EC
import logging

logger = logging.getLogger(__name__)


class Zoom:

    def __init__(self, url, driver):
        self.driver = driver
        self.url = url

    def join(self):
        logger.info("Handling Zoom meeting join...")

        self.url = self.url.replace("/j/", "/wc/join/")
        self.driver.get(self.url)

        wait = WebDriverWait(self.driver, 10)

        try:
            name_input = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(@placeholder,'name') or @type='text']",
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

            wait.until(
                lambda d: d.find_element(
                    By.XPATH, "//button[contains(., 'Join')]"
                ).is_enabled()
            )

            join_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Join')]")
                )
            )

            join_btn.click()

            return True

        except Exception as e:
            logger.exception(f"Zoom-specific handling error: {e}")
            return False

    def detect_end(self):
        try:
            modals = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(),'This meeting has been ended by host') or "
                "contains(text(),'host has ended') or "
                "contains(text(),'ended by the host')]",
            )

            for modal in modals:
                if modal.is_displayed():
                    return True

            return False
        except:
            return False
