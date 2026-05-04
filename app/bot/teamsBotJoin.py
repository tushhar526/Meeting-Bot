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
    BotDetection,
)

logger = get_logger("TEAMS_JOIN")

# Text patterns that appear when bot is in Teams waiting room
_WAITING_ROOM_PHRASES = [
    "Someone will let you in shortly",
    "Waiting to be admitted",
    "Your request to join has been sent",
    "Waiting for host to admit you",
]

# Text patterns that appear when host denies access to the meeting
_DENIED_PHRASES = [
    "Sorry, but you were denied access to the meeting",
    "Your request to join was denied",
    "You were not admitted to the meeting",
]

# Selectors that only appear once you are INSIDE the Teams meeting
_INSIDE_MEETING_SELECTORS = [
    "#roster-button",  # Roster/participants button
    "[data-tid='toolbar-item-badge']",  # Participant count badge
    "[data-tid='roster-button-badge']",  # Lobby waiting indicator
    "button[aria-label*='participants']",
    "button[aria-label*='raise hand']",
    "button[aria-label*='more options']",
]

# Text patterns that indicate the meeting has ended
_END_MEETING_PHRASES = re.compile(
    r"Enjoy your call\? Join Teams today for free|Did you leave by mistake\?|The meeting has ended",
    re.IGNORECASE,
)


class TeamsJoin(ScreenshotMixin):

    def __init__(self, url, page, bot_name, meeting_id, update_bot_callback=None):
        self.url = url
        self.page = page
        self.bot_name = bot_name
        self.meeting_id = meeting_id
        self._join_denied = False
        self.update_bot_callback = update_bot_callback
        self._screenshot_step = 0
        self.max_participant_count = 0
        logger.info(f"Teams handler initialized for URL: {url}")

    # 1. Join — retried up to 3× UNLESS the request was explicitly denied
    @retry(times=3, delay=5)
    def join(self):
        # If a previous attempt was explicitly denied, stop immediately.
        if self._join_denied:
            logger.error("Join was explicitly denied in a previous attempt — aborting")
            raise JoinDeniedError()

        logger.info("Attempting to join Teams meeting")
        self._screenshot_step = 0
        try:
            self.page.goto(self.url)
            self.page.wait_for_load_state("networkidle")
            logger.info("Page loaded")

            time.sleep(random.uniform(2, 5))

            # Handle browser continuation if needed
            self._step_continue_on_browser()

            # Handle audio/video settings
            self._step_no_av()

            # Fill in bot name
            self._step_fill_name()

            time.sleep(random.uniform(2, 4))

            # Click join button
            logger.info("Clicking join button")
            self._step_join_now()

            # Wait a moment for the page to transition
            time.sleep(3)

            # Check if we landed in waiting room (lobby)
            is_waiting_room = self._check_waiting_room()

            if is_waiting_room:
                logger.info("Detected waiting room — waiting for host to admit...")
                self._update_bot(
                    bot_status=BotStatus.WAITING_ROOM,
                    waiting_room_entered_at=get_ist_now(),
                )

                # Wait up to 180 seconds to be admitted
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
                # Not in waiting room — check if we got directly into meeting
                logger.info("Not in waiting room — checking if directly joined...")
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

            # These exceptions should NOT trigger a retry
            if isinstance(
                exc,
                (
                    WaitingRoomTimeoutError,
                    DirectJoinTimeoutError,
                    JoinButtonNotFoundError,
                    BotDetection,
                ),
            ):
                raise

            # Check for denial in generic exceptions
            if self._is_denied():
                self._update_bot(bot_status=BotStatus.DENIED)
                self._join_denied = True
                logger.error("Access denied during join process")
                raise JoinDeniedError()

            logger.error(f"Teams join error: {exc}")

            self._update_bot(retry_count=lambda x: x + 1)
            raise JoinProcessError()

    # 2. Continue on browser to continue the meeting join process on the browser
    def _step_continue_on_browser(self):
        """
        Handles the 'Join your Teams meeting' landing page.
        Teams SPA renders button before it's interactive - we need force click
        and proper navigation handling.
        """
        # Try data-tid selector first (more reliable than text)
        SELECTORS = [
            "button[data-tid='joinOnWeb']",
            "button:has-text('Continue on this browser')",
            "[data-tid='joinOnWeb']",
        ]

        btn = None
        used_selector = None
        for sel in SELECTORS:
            try:
                candidate = self.page.locator(sel).first
                candidate.wait_for(state="visible", timeout=8000)
                btn = candidate
                used_selector = sel
                logger.info(f"Found 'Continue on this browser' via: {sel}")
                break
            except Exception:
                continue

        if not btn:
            logger.info("No 'Continue on this browser' button — skipping")
            return

        # Human-like: pause as if reading the page
        time.sleep(random.uniform(1.5, 2.5))

        # Ensure button is in viewport and try different click methods
        for attempt in range(3):
            try:
                # Scroll into view
                btn.scroll_into_view_if_needed()
                time.sleep(0.5)

                # Try force click (bypasses actionability checks)
                btn.click(force=True)
                logger.info(
                    f"Force-clicked 'Continue on this browser' (attempt {attempt + 1})"
                )

                # Wait for navigation or URL change
                try:
                    self.page.wait_for_selector(
                        "input[data-tid='toggle-mute'], "
                        "[data-tid='prejoin-join-button'], "
                        "input[placeholder='Type your name'], "
                        "input[data-tid='prejoin-display-name-input']",
                        timeout=15000,
                    )
                    logger.info("Page transitioned to pre-join screen successfully")
                    break
                except Exception:
                    still_on_landing = self.page.locator(
                        "button[data-tid='joinOnWeb']"
                    ).is_visible(timeout=2000)
                    if still_on_landing and attempt < 2:
                        logger.warning(f"Still on landing page — retrying...")
                        time.sleep(random.uniform(2.0, 3.0))
                    else:
                        logger.info("Proceeding — button no longer visible")
                        break

            except Exception as e:
                logger.warning(f"Click attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(random.uniform(1.5, 2.5))

        # Extra wait for SPA to fully load pre-join screen
        time.sleep(random.uniform(3.0, 4.0))

        # Verify we're on pre-join screen by checking for AV controls
        try:
            self.page.wait_for_selector(
                "input[data-tid='toggle-mute'], [data-tid='prejoin-join-button']",
                timeout=10000,
            )
            logger.info("Pre-join screen elements detected")
        except Exception:
            logger.warning("Pre-join screen elements not found after waiting")

    # 3. Turn off camera and mic on Teams pre-join screen
    def _step_no_av(self):
        """
        Turn off camera and mic on Teams pre-join screen.
        Tries multiple selector patterns for different Teams UI versions.
        """
        MIC_SELECTORS = [
            "input[data-tid='toggle-mute']",
            "button[data-tid='toggle-mute']",
            "[data-tid='pre-join-mic-toggle']",
            "button[aria-label*='microphone' i]",
            "button[aria-label*='mute' i]",
        ]
        CAM_SELECTORS = [
            "input[data-tid='toggle-video']",
            "button[data-tid='toggle-video']",
            "[data-tid='pre-join-camera-toggle']",
            "button[aria-label*='camera' i]",
            "button[aria-label*='video' i]",
        ]

        # Wait for ANY mic selector - 8s each
        mic_appeared = False
        for sel in MIC_SELECTORS:
            try:
                self.page.wait_for_selector(sel, timeout=8000)
                logger.info(f"AV controls detected via: {sel}")
                mic_appeared = True
                break
            except Exception:
                continue

        if not mic_appeared:
            logger.warning("AV controls not found with any known selector — skipping")
            return

        # Turn off mic - try different patterns
        for sel in MIC_SELECTORS:
            try:
                el = self.page.locator(sel).first
                if not el.is_visible(timeout=2000):
                    continue

                # Check if it's a checkbox input or a button
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                if tag == "input":
                    if el.is_checked():
                        el.click(force=True)
                        logger.info("Microphone turned off (checkbox)")
                    else:
                        logger.info("Microphone already off")
                else:
                    # It's a button - check aria-pressed or just click
                    pressed = el.get_attribute("aria-pressed")
                    if pressed == "true":
                        el.click(force=True)
                        logger.info("Microphone turned off (button)")
                    else:
                        logger.info("Microphone already off or state unknown")
                break
            except Exception as e:
                logger.warning(f"Mic toggle failed for {sel}: {e}")
                continue

        # Turn off camera
        for sel in CAM_SELECTORS:
            try:
                el = self.page.locator(sel).first
                if not el.is_visible(timeout=2000):
                    continue

                tag = el.evaluate("e => e.tagName.toLowerCase()")
                if tag == "input":
                    if el.is_checked():
                        el.click(force=True)
                        logger.info("Camera turned off (checkbox)")
                    else:
                        logger.info("Camera already off")
                else:
                    pressed = el.get_attribute("aria-pressed")
                    if pressed == "true":
                        el.click(force=True)
                        logger.info("Camera turned off (button)")
                    else:
                        logger.info("Camera already off or state unknown")
                break
            except Exception as e:
                logger.warning(f"Camera toggle failed for {sel}: {e}")
                continue

    # 4. Fill in the bot name
    def _step_fill_name(self):
        """Fill in the bot name with multiple selector attempts."""
        NAME_SELECTORS = [
            "input[placeholder='Type your name']",
            "input[data-tid='prejoin-display-name-input']",
            "input[aria-label*='Enter your name' i]",
            "input[aria-label*='Your name' i]",
            "input[aria-label*='name' i]",
            "input[type='text']",
        ]

        name_input = None
        for sel in NAME_SELECTORS:
            try:
                el = self.page.locator(sel).first
                el.wait_for(state="visible", timeout=5000)
                name_input = el
                logger.info(f"Found name input via: {sel}")
                break
            except Exception:
                continue

        if not name_input:
            raise JoinButtonNotFoundError(
                "Name input field not found with any known selector"
            )

        try:
            # Clear and fill with retry
            name_input.fill("")
            time.sleep(0.3)
            name_input.fill(self.bot_name)
            logger.info(f"Filled name field with '{self.bot_name}'")
        except Exception as e:
            raise JoinButtonNotFoundError(f"Failed to fill name field: {e}")

    # 5. Click the final join button
    def _step_join_now(self):
        """Click the final join button with multiple selector attempts."""
        JOIN_SELECTORS = [
            "[data-tid='prejoin-join-button']",
            "[data-tid='join-btn']",
        ]
        JOIN_PATTERNS = [
            re.compile("Join now", re.IGNORECASE),
            re.compile(r"\bJoin\b", re.IGNORECASE),
        ]

        # Try data-tid selectors first (more reliable)
        for sel in JOIN_SELECTORS:
            try:
                btn = self.page.locator(sel).first
                btn.wait_for(state="visible", timeout=5000)
                btn.click(force=True)
                logger.info(f"Clicked join button via: {sel}")
                return
            except Exception:
                continue

        # Try role-based selectors with text patterns
        for pattern in JOIN_PATTERNS:
            try:
                btn = self.page.get_by_role("button", name=pattern)
                if btn.count() > 0:
                    btn.first.wait_for(state="visible", timeout=3000)
                    btn.first.click(force=True)
                    logger.info(f"Clicked join button (matched: {pattern.pattern})")
                    return
            except Exception:
                continue

        raise JoinButtonNotFoundError(
            "Join now button not found with any known selector"
        )

    # 6. Check if the meeting was ended by the host or the bot was kicked
    def host_end_screen(self):
        try:
            if self.page.get_by_text(_END_MEETING_PHRASES).is_visible():
                raise JoinDeniedError("The meeting was ended by the host")
            return False
        except:
            return False

    # 7. Check if bot is in Teams waiting room
    def _check_waiting_room(self) -> bool:
        """Check if bot is in Teams waiting room"""
        try:
            # Look for waiting room messages with bot name (partial match)
            # The text format is: "Hi, {bot_name}. Someone will let you in"
            if self.page.get_by_text(
                re.compile(r"Someone will let you in", re.IGNORECASE)
            ).is_visible():
                logger.info("Waiting room detected: 'Someone will let you in'")
                return True

            # Check for other waiting room indicators
            for phrase in _WAITING_ROOM_PHRASES:
                if self.page.get_by_text(
                    re.compile(phrase, re.IGNORECASE)
                ).is_visible():
                    logger.info(f"Waiting room detected: '{phrase}'")
                    return True

            # Additional check: look for lobby-related text
            lobby_indicators = [
                "Waiting to be admitted",
                "Your request to join has been sent",
                "Waiting for host to admit you",
            ]
            for indicator in lobby_indicators:
                if self.page.get_by_text(
                    re.compile(indicator, re.IGNORECASE)
                ).is_visible():
                    logger.info(f"Waiting room detected: '{indicator}'")
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error checking waiting room: {e}")
            return False

    # 8. Check if bot's join request was denied (returns bool, does NOT raise)
    def _is_denied(self) -> bool:
        """Check if bot's join request was denied. Returns True if denied, False otherwise."""
        try:
            for phrase in _DENIED_PHRASES:
                if self.page.get_by_text(
                    re.compile(phrase, re.IGNORECASE)
                ).is_visible():
                    logger.error(f"Access denied detected: '{phrase}'")
                    return True
            return False
        except Exception as e:
            logger.warning(f"Error checking denied access: {e}")
            return False

    # 9. wait until bot enters waiting room
    def _wait_until_waiting_room(self, timeout=15) -> bool:
        """Wait until we can confirm we're in the waiting room"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_waiting_room():
                logger.info("Successfully entered waiting room")
                return True
            time.sleep(1)
        return False

    # 10. wait untill the bot is inside the meeting
    def _wait_until_inside(self, timeout=180) -> bool:
        """Wait until we can confirm we're inside the meeting. Returns True if inside, raises JoinDeniedError if denied, returns False on timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for denied access first - raise immediately
            if self._is_denied():
                logger.error("Access denied while waiting to enter meeting")
                raise JoinDeniedError("Access to the meeting was denied by host")

            # Check for meeting end
            if self.host_end_screen():
                return False

            # Check if we're inside the meeting (roster button visible)
            try:
                if self.page.locator("#roster-button").is_visible():
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

    # 11. Detect if the meeting has ended and stay in the meeting for a grace period
    def detect_end(self, grace_period=60) -> tuple[bool, int]:
        """Returns (ended: bool, max_participant_count: int)"""

        try:
            roster_btn = self.page.locator("#roster-button")
        except Exception as e:
            logger.warning(f"Could not read roster button: {e}")

        # Track participant count
        count = self._get_participant_count()
        if count > 0 and count > self.max_participant_count:
            self.max_participant_count = count
            logger.info(f"Updated max participant count to: {count}")

        if self._is_someone_in_meeting():
            return False, self.max_participant_count

        # Active participants in meeting — stay
        if self._is_someone_in_meeting():
            return False, self.max_participant_count

        # Someone waiting in lobby — stay
        if self._is_someone_in_lobby():
            return False, self.max_participant_count

        # Host ended the meeting — leave immediately
        if self.host_end_screen():
            self._update_bot(
                ended_at=get_ist_now(),
                bot_leave_time=get_ist_now(),
                bot_status=BotStatus.MEETING_ENDED,
            )
            logger.info("Host ended the meeting")
            return True, self.max_participant_count

        # Bot is alone — grace period
        self._update_bot(ended_at=get_ist_now(), bot_status=BotStatus.GRACE_PERIOD)
        logger.info(f"Bot is alone, starting {grace_period}s grace period...")
        start_time = time.time()

        while time.time() - start_time < grace_period:
            try:
                # Track participant count during grace period
                count = self._get_participant_count()
                if count > 0 and count > self.max_participant_count:
                    self.max_participant_count = count
                    logger.info(f"Updated max participant count to: {count}")

                if self._is_someone_in_meeting():
                    logger.info("Someone joined during grace period — staying")
                    return False, self.max_participant_count

                if self._is_someone_in_lobby():
                    logger.info("Someone in lobby during grace period — staying")
                    return False, self.max_participant_count

                if self.host_end_screen():
                    logger.info("Host ended meeting during grace period")
                    return True, self.max_participant_count

            except Exception as e:
                logger.warning(f"Error during grace period check: {e}")

            time.sleep(2)

        self._update_bot(
            bot_status=BotStatus.MEETING_ENDED,
            bot_leave_time=get_ist_now(),
        )
        logger.info("Grace period expired — leaving")
        return True, self.max_participant_count

    # 12. Check if someone is in the meeting
    def _is_someone_in_meeting(self) -> bool:
        """Check if there are participants in the meeting using toolbar badge"""
        try:
            return self.page.locator('[data-tid="toolbar-item-badge"]').count() > 0
        except:
            return False

    # 13. Check if someone is in the lobby
    def _is_someone_in_lobby(self) -> bool:
        """Check if someone is waiting in the lobby using roster badge"""
        try:
            return self.page.locator('[data-tid="roster-button-badge"]').count() > 0
        except:
            return False

    # 14. Get participant count
    def _get_participant_count(self) -> int:
        """Return participant count, or 0 if it cannot be determined."""
        try:
            # Try to get count from toolbar badge
            badge = self.page.locator('[data-tid="toolbar-item-badge"]')
            if badge.count() > 0:
                text = badge.first.inner_text().strip()
                # Badge usually shows like "3" for 3 participants
                if text.isdigit():
                    return int(text)
        except Exception:
            pass

        # Fallback: check if roster button indicates participants
        try:
            if self.page.locator("#roster-button").is_visible():
                # If roster is visible but no badge, we have at least 1 (the bot)
                return 1
        except Exception:
            pass

        return 0
