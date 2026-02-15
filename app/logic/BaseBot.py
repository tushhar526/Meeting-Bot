import time
import logging
from app.helper.recording import AudioRecorder
from app.helper.decorators import retry
from app.logic.zoom import Zoom
from app.logic.meet import Meet
from app.logic.teams import Teams


from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


class BaseBot:

    def __init__(self, job_id, meeting_url):
        self.job_id = job_id
        self.meeting_url = meeting_url
        self.recording_path = f"app/recordings/{self.job_id}.mp3"
        self.handler = None
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_meeting_active = False
        self.recorder = AudioRecorder(self.recording_path)

    def setup_driver(self):
        try:

            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.launch(
                headless=False,
            )
            self.context = self.browser.new_context(permissions=[])
            self.page = self.context.new_page()

            logger.info(f" Chrome Browser setup is successful")
            return True

        except Exception as e:
            logger.error(f" Error in settting up driver = {e}")
            return False

    def setup_handler(self):
        if "zoom.us" in self.meeting_url:
            self.handler = Zoom(url=self.meeting_url, page=self.page)
        elif "meet.google.com" in self.meeting_url:
            self.handler = Meet(self.meeting_url, page=self.page)
        elif "teams.live.com" in self.meeting_url:
            self.handler = Teams(url=self.meeting_url, page=self.page)
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

        if self.browser and self.pw:
            try:
                self.browser.close()
                self.pw.stop()
                logger.info(
                    f" Browser closed as the meeting ended for Job {self.job_id}"
                )
            except Exception as e:
                logger.error(
                    f" Error occured in closing the browser for Job {self.job_id}"
                )
