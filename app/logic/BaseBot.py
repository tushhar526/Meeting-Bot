import time
import logging
import random
import os
from app.helper.recording import AudioRecorder
import subprocess
import re
from app.helper.decorators import retry
from app.models.jobModel import JobModel
from app.extension import db
from app.logic.zoom import Zoom
from app.logic.meet import Meet
from app.logic.teams import Teams
from playwright.sync_api import sync_playwright
from app.helper.logger import get_logger

logger = get_logger(__name__)


class BaseBot:

    def __init__(self, job_id, meeting_url, output_path):
        self.meeting_url = meeting_url
        self.job_id = job_id
        self.recording_path = output_path
        self.handler = None
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_meeting_active = False
        self.recorder = AudioRecorder(job_id, output_path=self.recording_path)
        self.result = "Failed"

        # Set initial status when bot is created
        self.update_Status("Bot Created")

        logger.info(
            f"BaseBot initialized for job {job_id}",
            details=f"meeting_url: {meeting_url}, output_path: {output_path}",
        )

    def update_Status(self, status):
        """Update job status."""
        try:
            job = JobModel.query.get(self.job_id)
            if job:
                job.status = status
                db.session.commit()
                logger.info(f"Updated job {self.job_id} status to '{status}'")

                # Also log to database with meeting category
                logger.meeting(
                    f"Job status updated",
                    job_id=self.job_id,
                    details=f"status: {status}",
                )
        except Exception as e:
            logger.error(
                f"Failed to update status to '{status}' for job {self.job_id}",
                exception=e,
            )
            db.session.rollback()

    def setup_driver(self):
        try:
            job_env = {
                **os.environ,
                "LD_PRELOAD": "libpulse.so.0",
                "ALSA_CONFIG_PATH": "/etc/asound.conf",
                "PULSE_SINK": self.recorder.get_sink_name,
                "PULSE_SERVER": "unix:/var/run/user/1000/pulse/native",
                "PULSE_LATENCY_MSEC": "30",
            }

            # Use sync_playwright for better compatibility with Celery workers
            self.pw = sync_playwright().start()

            browser_args = [
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--enable-features=WebRTCPulseAudio",
                "--alsa-output-device=pulse",
                "--use-fake-device-for-media-stream",
                "--disable-blink-features=AutomationControlled",
                "--disable-background-media-suspend",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-extensions",
                "--start-maximized",
                "--use-gl=swiftshader",
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--enable-features=WebRtcAllowInputVolumeAdjustment",
            ]

            self.browser = self.pw.chromium.launch(
                headless=True,
                env=job_env,
                ignore_default_args=["--mute-audio"],
                args=browser_args,
            )

            self.context = self.browser.new_context(
                permissions=[],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                locale="en-US",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            # Hide webdriver property to bypass basic bot detection
            self.context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            self.page = self.context.new_page()

            logger.info("Chrome Browser setup is successful")
            logger.meeting(
                "Browser setup completed",
                job_id=self.job_id,
                details="Chrome browser configured for meeting",
            )
            return True

        except Exception as e:
            logger.error(
                f"Error in setting up driver for job {self.job_id}", exception=e
            )
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
            self.result = "Failed"
            self.update_Status("Failed")
            logger.error(
                f"Unsupported meeting platform for job {self.job_id}: {self.meeting_url}"
            )
            raise ValueError("Unsupported meeting platform")

    def wait_for_stream(self, timeout=15):
        start_time = time.time()
        logger.info(
            "Waiting for Chrome audio stream to begin before recording to avoid empty silence..."
        )

        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"], capture_output=True, text=True
            )

            # Check if chrome/chromium is connected yet.
            if "chrome" in result.stdout.lower() or "chromium" in result.stdout.lower():
                logger.info(f"Chromium audio stream detected for job {self.job_id}")
                return True

            time.sleep(0.2)

        logger.warning(
            f"Chromium stream not detected within timeout for job {self.job_id}, starting recording anyway"
        )
        # Don't fail here - continue with recording even if stream not detected
        return True

    def join_meeting(self):

        if not self.handler.join():
            self.result = "Failed"
            self.update_Status("Failed")
            logger.error(f"Failed to join meeting for job {self.job_id}")
            return False

        self.is_meeting_active = True
        self.update_Status("Meeting Joined")
        logger.meeting(
            f"Meeting joined successfully",
            job_id=self.job_id,
            platform=self._get_platform_name(),
        )
        return True

    def detect_meeting_end(self, timeout_min=120):

        logger.info(f"Inside the meeting for f{self.job_id}")

        start_time = time.time()
        last_check = time.time()
        timeout_sec = timeout_min * 60

        while self.is_meeting_active:
            try:
                current_time = time.time()

                if (current_time - start_time) > timeout_sec:
                    logger.warning(
                        f"Meeting timeout limit reached for job {self.job_id}, refreshing timeout"
                    )
                    start_time = current_time

                if (current_time - last_check) > 10:
                    last_check = time.time()

                    if self.handler.detect_end():
                        logger.info(f"Meeting end detected for job {self.job_id}")
                        # self.job.status = "Meeting Ended"
                        # self.job.save()
                        self.is_meeting_active = False
                        break

                time.sleep(1)
            except Exception as e:
                logger.error(
                    f"Failed to monitor the meeting for job {self.job_id}", exception=e
                )
                self.result = "Failed"
                self.update_Status("Failed")
                break

    @retry(times=3, delay=5)
    def run(self, _attempt=None, _max_attempts=None):
        try:
            if not self.recorder.prepare_sink():
                if _attempt == _max_attempts:
                    self.result = "Failed"
                    self.update_Status("Failed")
                logger.error(f"Failed to prepare audio sink for job {self.job_id}")
                return False

            # time.sleep(2)

            if not self.setup_driver():
                if _attempt == _max_attempts:
                    self.result = "Failed"
                    self.update_Status("Failed")
                logger.error(f"Failed to setup browser driver for job {self.job_id}")
                return False

            self.setup_handler()

            logger.meeting(
                f"Joining meeting",
                job_id=self.job_id,
                platform=self._get_platform_name(),
            )
            if not self.join_meeting():
                if _attempt == _max_attempts:
                    return False  # join_meeting already sets status to Failed
                return False

            # Wait for stream before recording so we don't capture dead silence
            # and avoid the 9-sec start delay issue.
            self.wait_for_stream()

            logger.meeting(
                f"Starting recording",
                job_id=self.job_id,
                platform=self._get_platform_name(),
            )
            if not self.recorder.start():
                if _attempt == _max_attempts:
                    self.result = "Failed"
                    self.update_Status("Failed")
                logger.error(f"Failed to start recording for job {self.job_id}")
                return False

            self.update_Status("Recording Started")
            logger.meeting(
                f"Recording started successfully",
                job_id=self.job_id,
                platform=self._get_platform_name(),
                details="Meeting joined and recording active",
            )

            logger.info("Waiting for meeting to settle...")
            time.sleep(10)

            self.detect_meeting_end()

            self.result = "Completed"
            self.update_Status("Completed")
            logger.meeting(
                f"Meeting completed successfully",
                job_id=self.job_id,
                platform=self._get_platform_name(),
                success=True,
            )
            return True

        except Exception as e:
            # Roll back any broken DB session so the next retry starts clean
            try:
                db.session.rollback()
            except Exception:
                pass

            if _attempt == _max_attempts:
                logger.error(
                    f"Unexpected error in run method for job {self.job_id}", exception=e
                )
                self.result = "Failed"
                self.update_Status("Failed")
            else:
                logger.warning(
                    f"Attempt {_attempt}/{_max_attempts}: Unexpected error in run method for job {self.job_id} - {e}",
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

        logger.info(f"Recording stopped for Job {self.job_id}")

    def close(self):
        self.is_meeting_active = False
        self.update_Status(self.result)

        if self.browser or self.pw:
            try:
                if self.browser:
                    self.browser.close()
                if self.pw:
                    self.pw.stop()
                logger.info(
                    f"Browser closed as the meeting ended for Job {self.job_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error occurred in closing the browser for Job {self.job_id}",
                    exception=e,
                )

    def _get_platform_name(self):
        """Extract platform name from meeting URL"""
        if "zoom.us" in self.meeting_url:
            return "zoom"
        elif "meet.google.com" in self.meeting_url:
            return "google_meet"
        elif (
            "teams.live.com" in self.meeting_url
            or "teams.microsoft.com" in self.meeting_url
        ):
            return "teams"
        else:
            return "unknown"
