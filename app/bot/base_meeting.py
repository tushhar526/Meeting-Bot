import os
import time
import subprocess
from .recording import AudioRecorder
from app.core.middlewares.global_logger import get_logger
from app.core.decorators.retry import retry
from app.util.time_util import get_ist_now
from playwright.sync_api import sync_playwright

# from playwright_stealth import stealth_sync
from .platforms.googleBotJoin import MeetJoin
from .teamsBotJoin import TeamsJoin
from .zoomBotJoin import ZoomJoin
from app.meetings.meetingModel import BotStatus, MeetingPlatform
from app.util.response_util.custom_exception import (
    RecordingError,
    RetryException,
    JoinDeniedError,
    WaitingRoomTimeoutError,
)

logger = get_logger("BASE_MEETING")


class BaseBot:

    # Setting up the basebot class with required variables to be used throughout the class
    def __init__(
        self,
        meeting_id: int,
        meeting_url: str,
        original_path: str,
        processed_path: str,
        bot_alias: str,
        update_bot=None,
    ):
        self.meeting_id = meeting_id
        self.meeting_id = meeting_id  # alias for logging compatibility
        self.meeting_url = meeting_url
        self.audio_path = original_path
        self.processed_path = processed_path
        self.update_bot = update_bot
        self.handler = None
        self.bot_alias = bot_alias
        self.recorder = AudioRecorder(meeting_id, original_path, processed_path)
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_meeting_active = False

        # audio related meta data self vars
        self.audio_created_at = None
        self.recording_started_at = None
        self.recording_ended_at = None

        # meeting metadata
        self.max_participant_count = 0

    # For Updating any fields of meeting bot
    def update_bot_fields(self, **kwargs):
        if self.update_bot:
            self.update_bot(self.meeting_id, **kwargs)

    # For setting up the Playwright browser for joining the meeting
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

            self.pw = sync_playwright().start()

            browser_args = [
                # "--use-file-for-fake-audio-capture=/dev/null",
                # "--use-file-for-fake-video-capture=/dev/null",
                # "--no-first-run",
                # "--no-default-browser-check",
                # "--disable-infobars",
                # "--disable-gpu",
                # "--use-fake-device-for-media-stream",
                # "--disable-blink-features=AutomationControlled",
                # "--disable-extensions",
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-device-for-media-stream",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--enable-features=WebRTCPulseAudio",
                "--alsa-output-device=pulse",
                "--disable-background-media-suspend",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-notifications",
                "--start-maximized",
                "--use-gl=swiftshader",
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--enable-features=WebRtcAllowInputVolumeAdjustment",
            ]

            self.browser = self.pw.chromium.launch(
                # headless=True,
                channel="chrome",
                env=job_env,
                ignore_default_args=["--mute-audio"],
                args=browser_args,
            )

            self.context = self.browser.new_context(
                permissions=["microphone", "camera"],
                # user_agent=(
                #     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                #     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                # ),
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

            # stealth_sync(self.page)

            logger.info(
                f"Chrome Browser setup is successful for meeting {self.meeting_id}"
            )
            return True

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error in setting up driver for meeting {self.meeting_id}: {error_message}",
            )
            return False

    # To detect the platform as per the meeting url
    def detect_platform(self):
        url = self.meeting_url.lower()

        if "meet.google.com" in url:
            return MeetingPlatform.GOOGLE_MEET
        elif "zoom.us" in url:
            return MeetingPlatform.ZOOM
        elif "teams.live.com" in url or "teams.microsoft.com" in url:
            return MeetingPlatform.MICROSOFT_TEAMS

        raise ValueError("Unsupported meeting platform")

    # For defining which handler to use as per platform to join the meeting
    def setup_handler(self):
        platform = self.detect_platform()

        handler_map = {
            MeetingPlatform.ZOOM: ZoomJoin,
            MeetingPlatform.GOOGLE_MEET: MeetJoin,
            MeetingPlatform.MICROSOFT_TEAMS: TeamsJoin,
        }

        handler_class = handler_map.get(platform)

        if not handler_class:
            logger.error(
                f"Unsupported meeting platform for job {self.meeting_id}: {self.meeting_url}"
            )
            raise ValueError("Unsupported meeting platform")

        self.handler = handler_class(
            url=self.meeting_url,
            page=self.page,
            bot_name=self.bot_alias,
            meeting_id=self.meeting_id,
            update_bot_callback=self.update_bot_fields,
        )

    # To check the stream of sound coming from chrome for THIS specific meeting
    def wait_for_stream(self, timeout=5):
        start_time = time.time()
        sink_name = self.recorder.get_sink_name  # e.g., "sink_123"
        logger.info(
            f"Waiting for audio stream on sink '{sink_name}' to begin before recording..."
        )

        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"], capture_output=True, text=True
            )

            # Check if OUR specific sink has a chrome/chromium input connected
            # Parse sink-inputs to find: "Sink: sink_123" AND "Client: Chromium"
            sink_inputs = result.stdout.split("Sink Input")
            for sink_input in sink_inputs:
                if f"Sink: {sink_name}" in sink_input:
                    # Found our sink, check if chrome is connected to it
                    if (
                        "chromium" in sink_input.lower()
                        or "chrome" in sink_input.lower()
                    ):
                        logger.info(
                            f"Chromium audio stream detected on sink '{sink_name}' for job {self.meeting_id}"
                        )
                        return True

            time.sleep(0.3)

        logger.warning(
            f"No chromium stream on sink '{sink_name}' within timeout for job {self.meeting_id}, starting recording anyway"
        )
        return True  # Don't fail - continue recording

    # Calls the join meeting function as per the handler
    @retry(times=3, delay=2, retry_on=(RetryException,), retry_on_false=True)
    def join_meeting(self):
        self.created_at = get_ist_now()

        if not self.setup_driver():
            logger.error(f"Failed to setup browser driver for job {self.meeting_id}")
            return False, None

        self.update_bot_fields(created_at=get_ist_now())

        # Setup handler AFTER driver setup so it gets valid page
        self.setup_handler()

        """Join meeting with retry - only returns False after all retries exhausted."""
        try:
            if not self.handler.join():
                logger.error(
                    f"Failed to join meeting for meeting id = {self.meeting_id}"
                )
                raise RetryException("Join returned False")
        except JoinDeniedError:
            # Close browser and re-raise JoinDeniedError without wrapping to preserve DENIED status
            self.close()
            raise
        except WaitingRoomTimeoutError as e:
            # Close browser and re-raise WaitingRoomTimeoutError without wrapping to preserve CANCELLED status
            logger.error(
                f"[WAITING_TIMEOUT] Waiting room timeout for meeting {self.meeting_id}, closing browser..."
            )
            self.close()
            logger.error(
                f"[WAITING_TIMEOUT] Browser closed for meeting {self.meeting_id}, re-raising exception"
            )
            raise
        except Exception as e:
            self.close()
            logger.error(f"Exception during join for meeting {self.meeting_id}: {e}")
            raise RetryException(f"Join failed: {e}")

        self.is_meeting_active = True
        return True

    # Start recording with isolated retry using @retry decorator
    @retry(times=2, delay=2, retry_on=(RetryException,), retry_on_false=True)
    def start_recording_with_retry(self):
        """Start recording with retry - isolated from join retry."""
        logger.info(f"Recording attempt for meeting {self.meeting_id}")

        # Wait for stream before recording
        self.wait_for_stream()

        if self.recorder.start():
            self.update_bot_fields(bot_status=BotStatus.RECORDING_STARTED)
            self.recording_started_at = get_ist_now()
            logger.info(f"Recording started successfully for meeting {self.meeting_id}")
            return True

        logger.warning(f"Recorder.start() returned False for meeting {self.meeting_id}")
        raise RetryException("Recording start returned False")

    # Polling function for Checking whether the meeting has ended or not
    def detect_meeting_end(self, timeout_min=120):

        start_time = time.time()
        last_check = time.time()
        timeout_sec = timeout_min * 60

        while self.is_meeting_active:
            try:
                current_time = time.time()

                if (current_time - start_time) > timeout_sec:
                    logger.warning(
                        f"Meeting timeout limit reached for job {self.meeting_id}, refreshing timeout"
                    )
                    start_time = current_time

                if (current_time - last_check) > 10:
                    last_check = time.time()

                    ended, participant_count = self.handler.detect_end()
                    if participant_count > self.max_participant_count:
                        self.max_participant_count = participant_count

                    if ended:
                        logger.info(f"Meeting end detected for job {self.meeting_id}")
                        self.is_meeting_active = False
                        break

                time.sleep(1)
            except Exception as e:
                logger.error(
                    f"Failed to monitor the meeting for job {self. meeting_id} due to {str(e)}"
                )
                break

    # Main Function Orchestrating the whole basebot class functions
    # NOTE: No @retry here - join has its own retry via @retry on join() method
    # Recording errors raise RecordingError (NoRetryException) so we don't re-join
    def run(self):
        success = False
        try:
            if not self.recorder.prepare_sink():
                logger.error(f"Failed to prepare audio sink for job {self.meeting_id}")
                return False, None

            # NOTE: For concurrent meetings, we use PULSE_SINK env var per Chrome process
            # instead of setting global default sink to avoid interference between meetings

            # Note: setup_handler() is called inside join_meeting() after setup_driver()
            # so the handler gets a valid page reference

            logger.info(f"Joining meeting with meeting id = {self.meeting_id}")
            if not self.join_meeting():
                return False, None  # join_meeting already sets status to Failed

            # Start recording with isolated retry (stays in meeting, retries only recording)
            if not self.start_recording_with_retry():
                logger.error(
                    f"Failed to start recording after retries for job {self.meeting_id}"
                )
                raise RecordingError("Failed to start audio recording after retries")

            logger.info(
                f"Recording started for meeting with meeting id = {self.meeting_id}, detecting meeting end...",
            )

            self.detect_meeting_end()

            logger.info(
                f"Completed meeting successfully for meeting id = {self.meeting_id}",
            )
            success = True

            return True, {
                "recording_started_at": self.recording_started_at,
                "created_at": self.audio_created_at,
                "recording_ended_at": self.recording_ended_at,
                "participant_count": self.max_participant_count,
            }

        except JoinDeniedError:
            # Re-raise to let meeting_task.py handle DENIED status
            raise
        except WaitingRoomTimeoutError:
            # Re-raise to let meeting_task.py handle CANCELLED status
            raise
        except RecordingError:
            # Recording failure - don't retry, just mark as failed
            logger.error(
                f"Recording failed for meeting {self.meeting_id}, not retrying"
            )
            self.update_bot_fields(
                bot_status=BotStatus.FAILED, error_message="Recording failed"
            )
            return False, None
        except RetryException as e:
            # Join or recording retry exhausted - mark as failed
            logger.error(f"Retry exhausted for meeting {self.meeting_id}: {e}")
            self.update_bot_fields(bot_status=BotStatus.FAILED, error_message=str(e))
            return False, None
        except Exception as e:
            logger.warning(f"An unexpected error occurred: {str(e)}")
            self.update_bot_fields(bot_status=BotStatus.FAILED)
            logger.error(
                f"Unexpected error in run method for meeting {self.meeting_id}: {str(e)}",
            )
            return False, None

        finally:
            if not success:
                # Get current retry count and increment
                self.update_bot_fields(retry_count=lambda x: x + 1)
            self.stop()

            file_exists = os.path.exists(self.audio_path)
            file_size = os.path.getsize(self.audio_path) if file_exists else 0
            MIN_VALID_SIZE = 50 * 1024

            if not file_exists or file_size < MIN_VALID_SIZE:
                self._cleanup_audio_file()

    # For stoping the recording for the meeting
    def stop(self):

        try:
            self.recorder.stop()
        except:
            pass

        self.close()

        logger.info(
            f"Recording stopped for meeting with meeting id = {self.meeting_id}"
        )

    # For Closing the playwright browser instance and ending the meeting job
    def close(self):
        logger.info(
            f"[BROWSER_CLOSE] Closing browser for meeting {self.meeting_id}, browser={self.browser is not None}, pw={self.pw is not None}"
        )
        self.is_meeting_active = False

        # Force disconnect from meeting by navigating to blank page before closing
        if self.page:
            try:
                logger.info(
                    f"[BROWSER_CLOSE] Navigating away from meeting to force disconnect for meeting {self.meeting_id}"
                )
                self.page.goto("about:blank", timeout=5000)
                time.sleep(0.5)  # Brief pause to let disconnect propagate
            except Exception as e:
                logger.warning(f"[BROWSER_CLOSE] Error navigating to blank page: {e}")

        if self.browser or self.pw:
            try:
                if self.browser:
                    self.browser.close()
                if self.pw:
                    self.pw.stop()
                logger.info(
                    f"Browser closed as the meeting ended for meeting id = {self.meeting_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error occurred in closing the browser for meeting with meeting id = {self.meeting_id} with exception as {str(e)}",
                )
            finally:
                self.browser = None
                self.pw = None
                self.context = None
                self.page = None

    # For cleaning up files which were not recorded
    def _cleanup_audio_file(self):
        try:
            if os.path.exists(self.audio_path):
                os.remove(self.audio_path)
                logger.info(f"Cleaned up failed recording at {self.audio_path}")
        except Exception as e:
            logger.error(f"Failed to clean up audio file: {e}")
