import time
import logging
from app.helper.recording import AudioRecorder
import subprocess
import os
from app.helper.decorators import retry
from app.models.jobModel import JobModel
from app.logic.zoom import Zoom
from app.logic.meet import Meet
from app.logic.teams import Teams


from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


class BaseBot:

    def __init__(self, job_id, meeting_url):
        job = JobModel.query.get(job_id)
        self.meeting_url = meeting_url
        self.job = job
        self.job_id = job_id
        self.recording_path = f"app/recordings/{self.job_id}.mp3"
        self.handler = None
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_meeting_active = False
        self.recorder = AudioRecorder(job=job, output_path=self.recording_path)

    def setup_driver(self):
        try:

            self.pw = sync_playwright().start()
            env = os.environ.copy()
            self.browser = self.pw.chromium.launch(
                headless=False,
                env=env,
            )
            self.context = self.browser.new_context(permissions=[])
            self.page = self.context.new_page()

            logger.info(f" Chrome Browser setup is successful")
            return True

        except Exception as e:
            logger.error(f" Error in settting up driver = {e}")
            return False

    def setup_handler(self):
        handlers = {
            "zoom.us": Zoom(url=self.meeting_url, page=self.page),
            "meet.google.com": Meet(self.meeting_url, page=self.page),
            "teams.live.com": Teams(url=self.meeting_url, page=self.page),
        }

        self.handler = next(
            (value for key, value in handlers.items() if key in self.meeting_url), None
        )

        if not self.handler:
            raise ValueError("Unsupported meeting platform")

    # def route_chrome_to_sink(self):
    #     try:
    #         sink_name = self.recorder.get_sink_name

    #         result = subprocess.run(
    #             ["pgrep", "-f", "chromium"], capture_output=True, text=True, timeout=10
    #         )

    #         if result.returncode != 0:
    #             logger.error(f"Couldn't load all chromium process")
    #             return False

    #         chrome_pids = result.stdout.strip().split("\n")

    #         if not chrome_pids or not chrome_pids[0]:
    #             logger.error("Couldn't find Chromium Process id")

    #         chrome_pid = chrome_pids[-1]

    #         logger.info(f"Found Chromium process id = {chrome_pid}")

    #         result = subprocess.run(
    #             ["pactl", "list", "sink-input"],
    #             capture_output=True,
    #             text=True,
    #             timeout=10,
    #         )

    #         if result.returncode != 0:
    #             logger.error("Couldn't list all pulse audio sinks ")

    #         lines = result.stdout.split("\n")
    #         current_input_idx = None

    #         for line in lines:
    #             if "Sink Input #" in line:
    #                 current_input_idx = line.split("#")[1].strip()
    #             if current_input_idx and "application.process.id" in line:
    #                 pid_in_line = line.split("=")[1].strip().strip('"')

    #                 if pid_in_line == chrome_pid:

    #                     move_result = subprocess.run(
    #                         ["pactl", "move-sink-input", current_input_idx, sink_name],
    #                         capture_output=True,
    #                         text=True,
    #                         timeout=10,
    #                     )

    #                     if move_result.returncode != 0:
    #                         logger.error(
    #                             f"couldn't route sink {sink_name} to chromium due to {move_result.stderr}"
    #                         )
    #                         return False

    #                     logger.info(
    #                         f"Succesfully Routed the sink {sink_name} to chromium"
    #                     )
    #                     return False

    #         logger.error(
    #             f"Couldn't find meeting sink for Chromiun process id {chrome_pid}"
    #         )

    #     except Exception as e:
    #         logger.error(f" Error in Routing browser with audio sink = {e}")
    #     pass

    @retry(times=3, delay=5)
    def join_meeting(self):

        if not self.handler.join():
            return False

        self.is_meeting_active = True
        self.job
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
                        logger.info(
                            "The meeting seems to be ended, the bot has entered Grace period"
                        )
                        time.sleep(60)

                        if self.handler.detect_end():
                            logger.info(
                                "The grace period has ended and Meeting still is at end as detect_end returned true"
                            )
                            self.is_meeting_active = False
                            break

                time.sleep(1)
            except Exception as e:
                logger.error(f" Failed to moniter the meeting due to error = {e}")
                break

    @retry(times=3, delay=5)
    def run(self):
        try:
            if not self.recorder.prepare_sink:
                return False

            if not self.setup_driver():
                return False

            self.setup_handler()

            if not self.recorder.start():
                return False

            if not self.join_meeting():
                return False

            # if not self.route_chrome_to_sink():
            #     logger.error("Couldn't route the audio pulse sink to the browser")
            #     return False

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
