import time
import logging
from selenium import webdriver
from app.helper.recording import AudioRecorder
from app.helper.decorators import retry
from app.logic.zoom import Zoom
from app.logic.meet import Meet
from app.logic.teams import Teams


logger = logging.getLogger(__name__)


class BaseBot:

    def __init__(self, job_id, meeting_url):
        self.job_id = job_id
        self.meeting_url = meeting_url
        self.recording_path = f"app/recordings/{self.job_id}.mp3"
        self.driver = None
        self.handler = None
        self.is_meeting_active = False
        self.recorder = AudioRecorder(self.recording_path)

    def setup_driver(self):
        try:
            options = webdriver.ChromeOptions()

            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            options.add_argument("--disable-gpu")
            options.add_argument("--start-maximize")
            options.add_argument("--diable-notifications")
            # options.add_argument("--use-fake-ui-for-media-stream")
            # options.add_argument("--use-fake-device-for-media-stream")
            options.add_experimental_option(
                "prefs",
                {
                    "profile.default_content_setting_values.media_stream_mic": 2,
                    "profile.default_content_setting_values.media_stream_camera": 2,
                    "profile.default.content_setting_values.notification": 2,
                },
            )

            self.driver = webdriver.Chrome(options=options)

            stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false,
        });
        """

            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js}
            )

            logger.info(f" Chrome webdriver setup is successful")
            return True

        except Exception as e:
            logger.error(f" Error in settting up driver = {e}")
            return False

    def setup_handler(self):
        if "zoom.us" in self.meeting_url:
            self.handler = Zoom(driver=self.driver, url=self.meeting_url)
        elif "meet.google.com" in self.meeting_url:
            self.handler = Meet(driver=self.driver, url=self.meeting_url)
        elif "teams.live.com" in self.meeting_url:
            self.handler = Teams(driver=self.driver, url=self.meeting_url)
        else:
            raise Exception("Unsupported Meeting Platform")

    @retry(times=3, delay=5)
    def join_meeting(self):

        if not self.handler.join():
            return False

        self.is_meeting_active = True
        logger.info("Metting started")
        return True

    def detect_meeting_end(self, timeout_min=120):

        start_time = time.time()
        last_check = time.time()
        timeout_sec = timeout_min * 60

        while self.is_meeting_active:
            try:
                current_time = time.time()

                if (current_time - start_time) > timeout_sec:
                    logger.warning(
                        "Meeting timeout limit reached ... ... refreshing it"
                    )
                    start_time = current_time

                if (current_time - last_check) > 10:
                    last_check = time.time()

                    if self.handler.detect_end():
                        logger.info("Meeting has ended as detect_end returned true")
                        self.is_meeting_active = False
                        break

                time.sleep(1)
            except Exception as e:
                logger.error(f" Failed to moniter the meeting due to error = {e}")
                break

    def run(self):
        try:
            if not self.setup_driver():
                return False

            self.setup_handler()

            if not self.join_meeting():
                return False
            if not self.recorder.start():
                return False

            logger.info(f"Meeting Joined for Job {self.job_id} and recording started")

            self.detect_meeting_end()

            logger.info(f"Meeting ended for Job {self.job_id} and recording ended")
            return True
        except Exception as e:
            logger.error(
                f" Error occured in starting and joining meeting with Job {self.job_id} due to error = {e}"
            )
            return False
        finally:
            self.stop()

    def stop(self):

        try:
            self.recorder.stop()
        except:
            pass

        self.close()

        logger.info(f" Recording stopped for Job {self.job_id}")
        pass

    def close(self):

        self.is_meeting_active = False

        if self.driver:
            try:
                self.driver.quit()
                logger.info(
                    f" Browser closed as the meeting ended for Job {self.job_id}"
                )
            except Exception as e:
                logger.error(
                    f" Error occured in closing the browser for Job {self.job_id}"
                )
