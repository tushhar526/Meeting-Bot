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


# def handle_meet(driver):
#     logger.info("Handling Google Meet's meeting join")

#     try:
#         wait = WebDriverWait(driver, 10)

#         try:
#             error_messages = driver.find_elements(
#                 By.XPATH, "//*[contains(text(), \"can't\") or contains(text(), 'not')]"
#             )
#             for error_msg in error_messages:
#                 error_text = error_msg.text.lower()
#                 if any(
#                     phrase in error_text
#                     for phrase in [
#                         "can't join",
#                         "can't access",
#                         "doesn't exist",
#                         "not allowed",
#                         "not found",
#                     ]
#                 ):
#                     logger.error(f"Meeting error detected: {error_msg.text}")
#                     return False
#         except:
#             pass

#         logger.info("Page loaded, checking for join interface")
#         try:
#             logger.info("Looking for name input field")

#             name_input = None
#             selectors = [
#                 "//input[@type='text']",
#                 "//input[@placeholder='Your name']",
#                 "//input[@aria-label='Your name']",
#             ]

#             for selector in selectors:
#                 try:
#                     elements = driver.find_elements(By.XPATH, selector)
#                     if elements:
#                         name_input = elements[0]
#                         logger.info(f"Found name input with selector: {selector}")
#                         break
#                 except:
#                     continue

#             if name_input:
#                 name_input.clear()
#                 name_input.send_keys("Meeting Bot")
#                 logger.info("Entered name: Meeting Bot")
#                 time.sleep(1)
#             else:
#                 logger.warning("Name input field not found, proceeding anyway")

#         except Exception as e:
#             logger.warning(f"Error entering name: {e}")

#         try:
#             logger.info("Looking for 'Ask to join' or 'Join' button")

#             join_button = None
#             button_selectors = [
#                 "//button[./span[contains(text(), 'Ask to join')]]",
#                 "//button[contains(text(), 'Ask to join')]",
#                 "//button[.//span[contains(text(), 'Join')]]",
#                 "//button[contains(text(), 'Join')]",
#                 "//button[contains(@aria-label, 'Join')]",
#             ]

#             for selector in button_selectors:
#                 try:
#                     buttons = driver.find_elements(By.XPATH, selector)
#                     if buttons:
#                         join_button = buttons[0]
#                         logger.info(f"Found join button with selector: {selector}")
#                         break
#                 except:
#                     continue

#             if join_button:
#                 driver.execute_script("arguments[0].scrollIntoView(true);", join_button)
#                 time.sleep(0.5)

#                 join_button.click()
#                 logger.info("Clicked 'Ask to join' / 'Join' button")
#                 time.sleep(3)
#             else:
#                 logger.warning("Join button not found")
#                 if "meeting" in driver.page_source.lower():
#                     logger.info("Appears to be in meeting already")
#                     return True
#                 else:
#                     logger.error("Cannot find join button and not in meeting")
#                     return False

#         except Exception as e:
#             logger.error(f"Error clicking join button: {e}")
#             return False

#         try:
#             logger.info("Waiting for meeting to load...")

#             wait.until(
#                 lambda d: "meet" in d.current_url
#                 and (
#                     "meeting" in d.page_source.lower()
#                     or "participant" in d.page_source.lower()
#                 )
#             )

#             logger.info("Successfully joined Google Meet")
#             time.sleep(2)
#             return True

#         except TimeoutException:
#             logger.warning("Timeout waiting for meeting UI, but might still be joining")
#             page_source = driver.page_source.lower()
#             if "participant" in page_source or "meeting" in page_source:
#                 logger.info("Detected in meeting despite timeout")
#                 return True
#             else:
#                 logger.error("Failed to join meeting - not in meeting UI")
#                 return False

#     except Exception as e:
#         logger.error(f"Google Meet handling error: {e}")
#         return False


# def check_meeting_error(driver):
#     """
#     Check if Google Meet has an error preventing join
#     """
#     try:
#         page_source = driver.page_source.lower()

#         error_patterns = [
#             "can't join",
#             "can't access",
#             "doesn't exist",
#             "invalid meeting",
#             "ended",
#             "permission",
#             "sign in",
#             "authenticate",
#         ]

#         for pattern in error_patterns:
#             if pattern in page_source:
#                 return True

#         return False
#     except:
#         return False
