import re
import time
import random
from app.core.decorators.retry import retry
from app.core.middlewares.global_logger import get_logger
from app.bot.utils import ScreenshotMixin
from app.util.time_util import get_ist_now
from app.meetings.meetingModel import BotStatus
from app.util.response_util.custom_exception import (
    DirectJoinTimeoutError,
    JoinButtonNotFoundError,
    JoinProcessError,
    JoinDeniedError,
    WaitingRoomTimeoutError,
)

logger = get_logger("ZOOM_JOIN")

# Text patterns that appear when bot is in Zoom waiting room
_WAITING_ROOM_PHRASES = [
    "The host will admit you when they're ready",
    "Host has joined. We've let them know you're here",
    "Waiting for the host to start the meeting.",
    "Waiting for host to admit you",
    "Please wait, the meeting host will let you in soon",
    "Your request to join this meeting is waiting for host approval",
]

# Text patterns that appear when host denies access to the meeting
_DENIED_PHRASES = [
    "You have been removed",
    "You have been removed from this meeting by the host",
    "Your request to join was denied",
    "The host has denied your entry",
]

# Text patterns that indicate the meeting has ended
_END_MEETING_PHRASES = re.compile(
    r"This meeting has been ended by host|The host has ended the meeting", re.IGNORECASE
)

# Selectors that only appear once you are INSIDE the Zoom meeting
_INSIDE_MEETING_SELECTORS = [
    ".footer-button__number-counter",  # Participant counter
    "[data-testid='participants-button']",  # Participants button
    "[data-testid='more-button']",  # More options button
    ".footer-button__participants",  # Footer participants button
    "[aria-label*='participants']",
]


class ZoomJoin(ScreenshotMixin):

    def __init__(
        self, url: str, page, meeting_id: str, bot_name: str, update_bot_callback=None
    ):
        self.page = page
        self.url = url
        self._join_denied = False
        self.meeting_id = meeting_id
        self.bot_name = bot_name
        self.update_bot_callback = update_bot_callback
        self._screenshot_step = 0
        self.max_participant_count = 0

    # 1. Main Join Fucntion orchestrating the whole join process
    @retry(times=3, delay=5)
    def join(self):
        # If a previous attempt was explicitly denied, stop immediately.
        if self._join_denied:
            logger.error("Join was explicitly denied in a previous attempt — aborting")
            raise JoinDeniedError()

        logger.info("Attempting to join Zoom meeting")
        self._screenshot_step = 0
        try:
            self.url = self.url.replace("/j/", "/wc/join/")
            logger.info(f"Modified Zoom URL: {self.url}")

            self.page.goto(self.url)
            self.page.wait_for_load_state("networkidle")
            logger.info("Zoom page loaded successfully")

            time.sleep(random.uniform(2, 5))

            # Fill in bot name
            name_input = self.page.locator(
                "input[type='text'], input[placeholder='name']"
            )
            if not name_input.is_visible():
                raise JoinButtonNotFoundError("Name input field not found")

            name_input.fill(self.bot_name)
            logger.info(f"Filled name field with '{self.bot_name}'")

            time.sleep(random.uniform(2, 4))

            # Click join button and handle waiting room
            join_btn = self.page.get_by_role("button", name=re.compile("Join"))
            if not join_btn.is_visible():
                raise JoinButtonNotFoundError("Join button not found")

            logger.info("Clicking join button")
            join_btn.click()

            # Wait for page to transition after clicking join
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")

            # Check if we're in waiting room or directly joining
            logger.info("Checking if bot is in waiting room...")
            is_waiting_room = self._check_waiting_room()
            logger.info(f"Waiting room check result: {is_waiting_room}")

            if is_waiting_room:
                logger.info("Join request sent — confirming waiting room entry...")
                if not self._wait_until_waiting_room(timeout=15):
                    logger.error(
                        "Never landed in waiting room after clicking join — click may not have registered"
                    )
                    raise JoinProcessError(
                        "Failed to enter waiting room after clicking join"
                    )

                logger.info("Waiting room confirmed — waiting for host to admit...")
                self._update_bot(
                    bot_status=BotStatus.WAITING_ROOM,
                    waiting_room_entered_at=get_ist_now(),
                )
                admitted = self._wait_until_inside(timeout=180)

                # Check whether the failure was an explicit denial.
                if not admitted:
                    # Check for denial first (higher priority than timeout)
                    if self._is_denied():
                        self._update_bot(bot_status=BotStatus.DENIED)
                        self._join_denied = True
                        logger.error(
                            "Join request explicitly denied by a participant — stopping"
                        )
                        raise JoinDeniedError()

                    # Not denied, just timeout — set CANCELLED and don't retry
                    self._update_bot(bot_status=BotStatus.CANCELLED)
                    logger.error("Waiting room timeout — bot was never admitted")
                    raise WaitingRoomTimeoutError()

                self._update_bot(
                    bot_status=BotStatus.MEETING_JOINED,
                    bot_join_time=get_ist_now(),
                    started_at=get_ist_now(),
                )
                logger.info("Bot confirmed inside meeting")

            else:
                # Even for direct joins, wait for in-call UI to confirm we're in.
                if not self._wait_until_inside(timeout=30):
                    logger.error("Direct join timed out — never detected in-call UI")
                    raise DirectJoinTimeoutError()
                self._update_bot(
                    bot_status=BotStatus.MEETING_JOINED,
                    bot_join_time=get_ist_now(),
                    started_at=get_ist_now(),
                )
                logger.info("Bot confirmed inside meeting (direct join)")

            return True

        except Exception as exc:

            # Set status for non-retryable exceptions before re-raising
            if isinstance(exc, JoinDeniedError):
                self._update_bot(bot_status=BotStatus.DENIED)
                self._join_denied = True
                raise

            if isinstance(
                exc,
                (
                    WaitingRoomTimeoutError,
                    JoinButtonNotFoundError,
                    DirectJoinTimeoutError,
                ),
            ):
                raise

            # Check for denial in generic exceptions
            if self._is_denied():
                self._update_bot(bot_status=BotStatus.DENIED)
                self._join_denied = True
                logger.error("Access denied during join process")
                raise JoinDeniedError()

            logger.error(f"Zoom join error: {exc}")

            self._update_bot(retry_count=lambda x: x + 1)
            raise JoinProcessError()

    # 2. Fucntion to check whether the host has ended the meeting
    def host_ended(self):
        """Check if the meeting was ended by the host"""
        try:
            if self.page.get_by_text(_END_MEETING_PHRASES).is_visible():
                return True
            return False
        except:
            return False

    # 3. Function to check if bot is in Zoom waiting room
    def _check_waiting_room(self) -> bool:
        """Check if bot is in Zoom waiting room"""
        try:
            for phrase in _WAITING_ROOM_PHRASES:
                # Use regex matching with count() to avoid strict mode violation
                locator = self.page.get_by_text(re.compile(phrase, re.IGNORECASE))
                if locator.count() > 0:
                    logger.info(f"Waiting room detected with phrase: '{phrase}'")
                    return True
            return False
        except Exception as e:
            logger.warning(f"Error checking waiting room: {e}")
            return False

    # 4. Function to check if bot's join request was denied or bot was removed
    def _is_denied(self) -> bool:
        """Check if bot's join request was denied. Returns True if denied, False otherwise."""
        try:
            for phrase in _DENIED_PHRASES:
                # Use count() to avoid strict mode violation when multiple elements match
                locator = self.page.get_by_text(re.compile(phrase, re.IGNORECASE))
                if locator.count() > 0:
                    logger.error(f"Access denied detected: '{phrase}'")
                    return True
            return False
        except Exception as e:
            logger.warning(f"Error checking denied access: {e}")
            return False

    # 5. Function to wait until we can confirm we're in the waiting room
    def _wait_until_waiting_room(self, timeout=15) -> bool:
        """Wait until we can confirm we're in the waiting room"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_waiting_room():
                logger.info("Successfully entered waiting room")
                return True
            time.sleep(1)
        return False

    # 6. Function to wait until we can confirm we're inside the meeting
    def _wait_until_inside(self, timeout=180) -> bool:
        """Wait until we can confirm we're inside the meeting. Returns True if inside, raises JoinDeniedError if denied, returns False on timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for denied access first - raise immediately
            if self._is_denied():
                logger.error("Access denied while waiting to enter meeting")
                raise JoinDeniedError("Access to the meeting was denied by host")

            # Check for meeting end
            if self.host_ended():
                return False

            # Check if we're inside the meeting (participant counter visible)
            try:
                if self.page.locator(".footer-button__number-counter").is_visible():
                    logger.info("Successfully entered the meeting")
                    return True
            except:
                pass

            time.sleep(2)
        return False

    def set_update_bot_callback(self, callback):
        """Set the callback function for updating bot status."""
        self.update_bot_callback = callback

    def _update_bot(self, **kwargs):
        """Internal helper to call update_bot callback if set."""
        if self.update_bot_callback:
            self.update_bot_callback(**kwargs)

    # 7. Main Detection Function to check if the meeting has ended
    def detect_end(self, grace_period=60) -> tuple[bool, int]:
        """Returns (ended: bool, max_participant_count: int)"""

        if self.host_ended():
            logger.info("Host ended the meeting")
            self._update_bot(
                bot_status=BotStatus.MEETING_ENDED,
                bot_leave_time=get_ist_now(),
                ended_at=get_ist_now(),
            )
            return True, self.max_participant_count

        count = self._get_participant_count()

        # Track max participant count
        if count is not None and count > self.max_participant_count:
            self.max_participant_count = count
            logger.info(f"Updated max participant count to: {count}")

        if count is None:
            logger.warning("Could not read participant count — staying to be safe")
            return False, self.max_participant_count

        if count > 1:
            return False, self.max_participant_count

        # Bot is alone — start grace period
        self._update_bot(bot_status=BotStatus.GRACE_PERIOD)
        logger.info(
            f"Bot is alone ({count} participant), starting {grace_period}s grace period..."
        )
        start_time = time.time()

        while time.time() - start_time < grace_period:
            try:
                if self.host_ended():
                    self._update_bot(
                        ended_at=get_ist_now(),
                        bot_leave_time=get_ist_now(),
                        bot_status=BotStatus.MEETING_ENDED,
                    )
                    logger.info("Host ended meeting during grace period")
                    return True, self.max_participant_count

                count = self._get_participant_count()

                # Track max participant count during grace period
                if count is not None and count > self.max_participant_count:
                    self.max_participant_count = count
                    logger.info(f"Updated max participant count to: {count}")

                if count is None:
                    time.sleep(2)
                    continue

                if count > 1:
                    logger.info(
                        f"Someone joined during grace period ({count} participants) — staying"
                    )
                    return False, self.max_participant_count

            except Exception as e:
                logger.warning(f"Error during grace period check: {e}")

            time.sleep(2)

        self._update_bot(
            status=BotStatus.MEETING_ENDED,
            bot_leave_time=get_ist_now(),
        )
        logger.info("Grace period expired — leaving")
        return True, self.max_participant_count

    # 8. Get Participant's Count in the Meeting
    def _get_participant_count(self):
        """
        Returns participant count as int, or None if unreadable.
        Zoom shows count in .footer-button__number-counter span
        """
        try:
            counter = self.page.locator(".footer-button__number-counter span")
            if counter.count() == 0:
                return None
            return int(counter.first.inner_text().strip())
        except:
            return None
