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
            job_env = {
                **os.environ,
                "LD_PRELOAD": "libpulse.so.0",
                "ALSA_CONFIG_PATH": "/etc/asound.conf",
                "PULSE_SINK": self.recorder.get_sink_name,
                "PULSE_SERVER": "unix:/var/run/user/1000/pulse/native",
            }

            self.pw = sync_playwright().start()

            self.browser = self.pw.chromium.launch(
                headless=True,
                env=job_env,
                ignore_default_args=["--mute-audio"],
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--enable-features=WebRTCPulseAudio",
                    "--alsa-output-device=pulse",
                ],
            )

            self.context = self.browser.new_context(permissions=[])
            self.page = self.context.new_page()

            logger.info("Chrome Browser setup is successful")
            return True

        except Exception as e:
            logger.error(f"Error in setting up driver = {e}")
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

    def wait_and_assign_sink(self, timeout=20):
        import re
        import time

        target_sink = self.recorder.get_sink_name
        start_time = time.time()

        logger.info(
            f"Waiting for Chromium to appear in PulseAudio (Target: {target_sink})..."
        )

        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"], capture_output=True, text=True
            )
            output = result.stdout

            matches = re.findall(
                r"Sink Input #(\d+).*?application\.name = \"(.*?)\"", output, re.DOTALL
            )

            for input_index, app_name in matches:
                if "chrom" in app_name.lower():
                    logger.info(
                        f"Found Chromium stream (Input #{input_index}). Moving to {target_sink}"
                    )
                    move_res = subprocess.run(
                        ["pactl", "move-sink-input", input_index, target_sink]
                    )
                    if move_res.returncode == 0:
                        return True

            time.sleep(1)

        logger.error("Chromium never connected to PulseAudio within timeout.")
        return False

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

    def check_chrome_sink(self):
        try:
            chrome_check = subprocess.run(
                ["pgrep", "-f", "chromium"], capture_output=True, text=True, timeout=5
            )

            if chrome_check.returncode != 0:
                logger.error("❌ Chrome process NOT running")
                return

            pids = chrome_check.stdout.strip().split("\n")
            logger.info(f"✓ Chrome PIDs found: {pids}")

            result = subprocess.run(
                ["pactl", "list", "sink-inputs"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            all_sink = subprocess.run(
                ["pactl", "list", "sinks", "short"], capture_output=True, text=True
            )

            if all_sink.stdout.strip():
                logger.info(f"The sinks present are = {all_sink.stdout}")

            logger.info(f"Sink inputs output:\n{result.stdout}")

            if not result.stdout.strip():
                logger.error("❌ NO applications connected to PulseAudio at all")
                logger.error("This means Chrome is using ALSA directly, not PulseAudio")
                logger.error("You MUST use route_chrome_to_sink() to move it")
                return

            lines = result.stdout.split("\n")
            chrome_found = False

            for i, line in enumerate(lines):
                if "application.name" in line and "chromium" in line.lower():
                    chrome_found = True
                    logger.info(f"✓ Chrome found in sink inputs at line {i}")
                    for j in range(max(0, i - 5), min(len(lines), i + 5)):
                        logger.info(f"  {lines[j]}")
                    break

            if not chrome_found:
                logger.error("❌ Chrome NOT in PulseAudio sink inputs")
                logger.error("Chrome is using ALSA, not PulseAudio")

        except Exception as e:
            logger.error(f"Error checking Chrome sink: {e}")

    @retry(times=3, delay=5)
    def run(self):
        try:
            if not self.recorder.prepare_sink():
                return False

            time.sleep(2)

            if not self.setup_driver():
                return False

            self.setup_handler()

            if not self.join_meeting():
                return False

            if not self.wait_and_assign_sink():
                logger.error("Couldn't assign Sink to the chromium")
                return False

            self.check_chrome_sink()

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
