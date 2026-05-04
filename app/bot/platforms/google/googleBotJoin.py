# import os
# import re
# import random
# import time
# from datetime import datetime
# from app.util.response_util.custom_exception import (
#     JoinButtonNotFoundError,
#     JoinDeniedError,
#     WaitingRoomTimeoutError,
#     BotDetection,
#     DirectJoinTimeoutError,
#     JoinProcessError,
#     NoRetryException,
# )
# from app.core.decorators.retry import retry
# from app.core.middlewares.global_logger import get_logger
# from app.util.time_util import get_ist_now
# from app.meetings.meetingModel import BotStatus

# logger = get_logger("MEET_JOIN")

# # Selectors that appear once you are INSIDE the waiting room of the meeting.
# _WAITING_ROOM_INDICATORS = [
#     "Please wait until a meeting host brings you into the call",  # FIX: was missing comma — these were being concatenated into one string
#     "Waiting to be admitted",
#     "Someone will let you in soon",
#     "Your request to join has been sent",
#     "Waiting for host to admit you",
# ]

# # Selectors that only appear once you are INSIDE the meeting.
# # In-call action buttons are the most reliable positive signal —
# # they never appear in the pre-join screen or the waiting room.
# _INSIDE_MEETING_SELECTORS = [
#     # "[data-call-ended]",
#     # ".crqnQb",
#     # Leave call button
#     # "[data-tooltip='Leave call']",
#     # "button[aria-label='Leave call']",
#     # In-call action buttons — strong positive signal that we are inside
#     "button[aria-label='Raise your hand']",
#     "button[aria-label='Turn on captions']",
#     "button[aria-label='Turn off captions']",
#     "button[aria-label='Share Screen']",  # Share screen
#     "button[aria-label='Send a reaction']",
# ]

# _PARTICIPANT_SELECTORS = [
#     ".uGOf1d",
#     ".wnPUne",
#     "button[aria-label*='everyone']",
#     "[data-participant-count]",
#     "[data-avatar-count]",
# ]

# _END_PHRASES = re.compile(
#     r"You've been removed|The meeting has ended|You left the meeting",
#     re.IGNORECASE,
# )

# _BLOCKED_PHRASES = re.compile(
#     r"You Can't Join this video call|You can't join this call",
#     re.IGNORECASE,
# )

# # Shown when a host/participant explicitly denies the bot's join request.
# # This is a hard stop — no point retrying, the human made a deliberate choice.
# _DENIED_PHRASES = re.compile(
#     r"Someone in the call denied your request to join",
#     re.IGNORECASE,
# )


# # ---------------------------------------------------------------------------
# # Meet_Join handler
# # ---------------------------------------------------------------------------


# class MeetJoin:

#     def __init__(
#         self, url: str, page, meeting_id: int, bot_name: str, update_bot_callback=None
#     ) -> None:
#         self.url = url
#         self.page = page
#         self.bot_name = bot_name
#         self.meeting_id = meeting_id
#         self._join_denied = False
#         self.update_bot_callback = update_bot_callback
#         self._debug_step = 0  # Step counter for screenshots
#         self.max_participant_count = 0  # Track max participants during meeting
#         logger.info(f"Google Meet handler initialised for URL: {url}")


#     # 1. Join — retried up to 3× UNLESS the request was explicitly denied
#     @retry(times=3, delay=5)
#     def join(self) -> bool:

#         # If a previous attempt was explicitly denied, stop immediately.
#         if self._join_denied:
#             logger.error("Join was explicitly denied in a previous attempt — aborting")
#             raise JoinDeniedError()

#         logger.info("Attempting to join the meeting")
#         self._debug_step = 0  # Reset step counter for new join attempt
#         try:
#             self.page.goto(self.url, timeout=30000)  # 30s timeout
#             self.page.wait_for_load_state("networkidle", timeout=30000)  # 30s timeout

#             time.sleep(random.uniform(2, 5))

#             if self._is_blocked():
#                 logger.error("Bot blocked immediately by Google Meet")
#                 raise BotDetection()

#             self._dismiss_av_prompt()
#             self._fill_name()
#             self._dismiss_popups()

#             time.sleep(random.uniform(2, 4))

#             join_btn, is_waiting_room = self._find_join_button()
#             if not join_btn:
#                 logger.error("No join button found")
#                 raise JoinButtonNotFoundError()

#             logger.info(f"Clicking join button (waiting_room={is_waiting_room})")
#             time.sleep(random.uniform(1, 2))
#             join_btn.click()

#             if is_waiting_room:
#                 logger.info("Join request sent — confirming waiting room entry...")
#                 if not self._wait_until_waiting_room(timeout=15):
#                     logger.error(
#                         "Never landed in waiting room after clicking join — click may not have registered"
#                     )
#                     raise JoinProcessError(
#                         "Failed to enter waiting room after clicking join"
#                     )

#                 logger.info("Waiting room confirmed — waiting for host to admit...")
#                 self._update_bot(
#                     bot_status=BotStatus.WAITING_ROOM,
#                     waiting_room_entered_at=get_ist_now(),
#                 )
#                 admitted = self._wait_until_inside(timeout=180)

#                 # Check whether the failure was an explicit denial.
#                 if not admitted:
#                     self._update_bot(bot_status=BotStatus.CANCELLED)
#                     if self._is_join_denied():
#                         # Flag it so the @retry decorator does NOT try again.
#                         self._update_bot(bot_status=BotStatus.DENIED)
#                         self._join_denied = True
#                         logger.error(
#                             "Join request explicitly denied by a participant — stopping"
#                         )
#                         raise JoinDeniedError()

#                     logger.error("Waiting room timeout — bot was never admitted")
#                     raise WaitingRoomTimeoutError()

#                 self._update_bot(
#                     bot_status=BotStatus.MEETING_JOINED,
#                     bot_join_time=get_ist_now(),
#                     started_at=get_ist_now(),
#                 )
#                 logger.info("Bot confirmed inside meeting")

#             else:
#                 # Even for direct joins, wait for in-call UI to confirm we're in.
#                 if not self._wait_until_inside(timeout=30):
#                     logger.error("Direct join timed out — never detected in-call UI")
#                     raise DirectJoinTimeoutError()
#                 self._update_bot(
#                     bot_status=BotStatus.MEETING_JOINED,
#                     bot_join_time=get_ist_now(),
#                     started_at=get_ist_now(),
#                 )
#                 logger.info("Bot confirmed inside meeting (direct join)")

#             return True

#         except Exception as exc:

#             # Set status for non-retryable exceptions before re-raising
#             if isinstance(exc, JoinDeniedError):
#                 self._update_bot(bot_status=BotStatus.DENIED)
#                 self._join_denied = True
#                 raise

#             if isinstance(
#                 exc,
#                 (
#                     WaitingRoomTimeoutError,
#                     JoinButtonNotFoundError,
#                     DirectJoinTimeoutError,
#                     BotDetection,
#                 ),
#             ):
#                 raise

#             if isinstance(exc, NoRetryException):
#                 raise

#             if self._is_blocked():
#                 logger.error("Bot redirected to a blocked page")
#                 raise BotDetection()

#             logger.error(f"Google Meet join error: {exc}")

#             self._update_bot(retry_count=lambda x: x + 1)
#             raise JoinProcessError()


#     def set_update_bot_callback(self, callback):
#         """Set the callback function for updating bot status."""
#         self.update_bot_callback = callback


#     def _update_bot(self, **kwargs):
#         """Internal helper to call update_bot callback if set."""
#         if self.update_bot_callback:
#             self.update_bot_callback(**kwargs)

#     # 2. Main end-detection
#     def detect_end(self, grace_period: int = 60) -> tuple[bool, int]:
#         """Returns (ended: bool, max_participant_count: int)"""
#         try:
#             if self._end_message_visible():
#                 self._update_bot(
#                     bot_status=BotStatus.MEETING_ENDED,
#                     ended_at=get_ist_now(),
#                 )
#                 logger.info("End message detected — leaving")
#                 return True, self.max_participant_count

#             count = self._get_participant_count()
#             if count > 0 and count > self.max_participant_count:
#                 self.max_participant_count = count
#                 logger.info(f"Updated max participant count to: {count}")

#             if count == -1:
#                 return False, self.max_participant_count
#             if count > 1:
#                 return False, self.max_participant_count

#             self._update_bot(bot_status=BotStatus.GRACE_PERIOD, ended_at=get_ist_now())
#             ended = self._run_grace_period(grace_period)
#             return ended, self.max_participant_count

#         except Exception as exc:
#             logger.warning(f"detect_end error: {exc}")
#             return False, self.max_participant_count

#     # 3. Wait until confirmed inside the meeting
#     def _wait_until_inside(self, timeout: int) -> bool:
#         """
#         Poll every 3 seconds until a known in-call UI element is visible
#         (POSITIVE proof the bot is inside), OR until an explicit denial is
#         detected (raises JoinDeniedError immediately rather than timing out).
#         Returns True if inside, raises JoinDeniedError if denied, returns False on timeout.
#         """
#         deadline = time.time() + timeout
#         poll_interval = 3
#         checks = 0

#         while time.time() < deadline:
#             checks += 1
#             if self._is_inside_meeting():
#                 return True

#             # Surface an explicit denial early — raise immediately
#             if self._is_join_denied():
#                 raise JoinDeniedError("Join request was denied by host")

#             elapsed = int(time.time() - (deadline - timeout))
#             logger.info(f"Not yet inside meeting... {elapsed}s / {timeout}s elapsed")
#             time.sleep(poll_interval)

#         return False

#     # 4. Confirm the bot landed in the waiting room
#     def _wait_until_waiting_room(self, timeout: int = 15) -> bool:
#         """
#         Poll until at least one waiting-room indicator phrase is visible.
#         Called immediately after clicking 'Ask to join' to confirm the
#         click registered and the bot is genuinely queued — not stuck on
#         the pre-join screen due to a missed click or a slow render.
#         """
#         logger.info(f"[JOIN STEP 9.1] Waiting for waiting room confirmation (timeout={timeout}s)...")
#         deadline = time.time() + timeout
#         poll_interval = 2
#         checks = 0

#         while time.time() < deadline:
#             checks += 1
#             if self._is_in_waiting_room():
#                 logger.info(f"[JOIN STEP 9.2] Waiting room confirmed after {checks} checks")
#                 return True
#             logger.info(f"[JOIN STEP 9.1] Waiting room check {checks} - not yet in waiting room")
#             time.sleep(poll_interval)

#         logger.error(f"[JOIN STEP 9.3] Waiting room timeout after {checks} checks")
#         return False


#     def _is_in_waiting_room(self) -> bool:
#         """
#         Return True when any known waiting-room indicator text is visible.
#         These phrases only appear after the join request has been sent and
#         the bot is queued, never on the pre-join screen or inside the call.
#         """
#         for phrase in _WAITING_ROOM_INDICATORS:
#             try:
#                 el = self.page.get_by_text(re.compile(re.escape(phrase), re.IGNORECASE))
#                 if el.count() > 0 and el.first.is_visible(timeout=3000):
#                     logger.info(f"[JOIN STEP 9.1] Waiting room confirmed via phrase: '{phrase}'")
#                     return True
#             except Exception:
#                 continue
#         return False

#     # 5. Confirm inside the meeting via positive UI signals
#     def _is_inside_meeting(self) -> bool:
#         """
#         Return True only when at least one known in-call UI element is visible.
#         In-call action buttons (raise hand, captions, share screen, reactions)
#         are included because they are exclusively rendered inside an active call.
#         """
#         for selector in _INSIDE_MEETING_SELECTORS:
#             try:
#                 el = self.page.locator(selector)
#                 if el.count() > 0 and el.first.is_visible(timeout=3000):
#                     logger.info(f"[JOIN STEP 10.1] In-call UI confirmed via selector: {selector}")
#                     return True
#             except Exception:
#                 continue
#         return False

#     # 5. Dismiss audio/video prompt
#     def _dismiss_av_prompt(self) -> None:
#         try:
#             btn = self.page.get_by_role(
#                 "button",
#                 name=re.compile(
#                     "Continue without microphone and camera", re.IGNORECASE
#                 ),
#             )
#             btn.wait_for(state="visible", timeout=5000)
#             btn.click()
#             logger.info("Dismissed AV prompt")
#         except Exception:
#             logger.info("No AV prompt — skipping")

#     # 6. Fill name field
#     def _fill_name(self) -> None:
#         name_input = self.page.locator(
#             "input[type='text'], input[placeholder='Your name']"
#         ).first

#         if name_input.count() == 0:
#             logger.error("Name input not found")
#             return

#         name_input.wait_for(state="visible", timeout=10_000)
#         time.sleep(random.uniform(1, 3))
#         name_input.fill(self.bot_name)
#         logger.info(f"Filled name field with '{self.bot_name}'")

#     # 7. Dismiss incidental popups
#     def _dismiss_popups(self) -> None:
#         try:
#             btn = self.page.get_by_role(
#                 "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
#             )
#             if btn.count() > 0 and btn.first.is_visible(timeout=2000):
#                 btn.first.click()
#                 logger.info("Dismissed popup")
#         except Exception:
#             pass

#     # 8. Locate the join button
#     def _find_join_button(self):
#         """Return (button, is_waiting_room) or (None, False) if not found."""
#         candidates = [
#             ("Ask to join", True),
#             ("Join now", False),
#         ]
#         for label, is_waiting_room in candidates:
#             try:
#                 btn = self.page.get_by_role(
#                     "button", name=re.compile(label, re.IGNORECASE)
#                 )
#                 count = btn.count()
#                 logger.info(f"[JOIN STEP 7.2] Checking for '{label}' button: count={count}")
#                 if count > 0 and btn.first.is_visible(timeout=5000):
#                     logger.info(f"[JOIN STEP 7.3] Found '{label}' button (waiting_room={is_waiting_room})")
#                     return btn.first, is_waiting_room
#             except Exception as e:
#                 logger.warning(f"[JOIN STEP 7.2] Error checking for '{label}': {e}")
#                 pass

#         # Fallback: any visible button containing "Join"
#         try:
#             btns = self.page.get_by_role(
#                 "button", name=re.compile(r"\bJoin\b", re.IGNORECASE)
#             )
#             count = btns.count()
#             for i in range(count):
#                 btn = btns.nth(i)
#                 if btn.is_visible(timeout=5000):
#                     text = btn.inner_text()
#                     is_waiting_room = "ask" in text.lower()
#                     return btn, is_waiting_room
#         except Exception as e:
#             pass
#         return None, False

#     # 9. Grace period — stay until someone rejoins or time is up
#     def _run_grace_period(self, duration: int) -> bool:
#         logger.info(f"Bot is alone — starting {duration}s grace period")
#         deadline = time.time() + duration

#         while time.time() < deadline:
#             if self._end_message_visible():
#                 return True
#             count = self._get_participant_count()
#             if count != -1 and count > 1:
#                 logger.info("Someone joined during grace period — staying")
#                 return False
#             time.sleep(2)

#         self._update_bot(
#             bot_status=BotStatus.MEETING_ENDED,
#             bot_leave_time=get_ist_now(),
#         )
#         logger.info("Grace period expired — leaving")
#         return True

#     # 10. Detect explicit end-of-meeting text
#     def _end_message_visible(self) -> bool:
#         try:
#             return self.page.get_by_text(_END_PHRASES).is_visible()
#         except Exception:
#             return False

#     # 11. Get participant count
#     def _get_participant_count(self) -> int:
#         """Return participant count, or -1 if it cannot be determined."""
#         for selector in _PARTICIPANT_SELECTORS:
#             try:
#                 elements = self.page.locator(selector)
#                 if elements.count() > 0:
#                     text = elements.first.inner_text().strip()
#                     match = re.search(r"\d+", text)
#                     if match:
#                         return int(match.group())
#             except Exception:
#                 continue

#         # Fallback: count participant tiles directly.
#         try:
#             tiles = self.page.locator("div[data-participant-id]")
#             if tiles.count() > 0:
#                 return tiles.count()
#         except Exception:
#             pass

#         return -1

#     # 12. Detect Google's own "can't join" block page
#     def _is_blocked(self) -> bool:
#         try:
#             return self.page.get_by_text(_BLOCKED_PHRASES).is_visible(timeout=5000)
#         except Exception:
#             return False

#     # 13. Detect explicit join denial by a call participant
#     def _is_join_denied(self) -> bool:
#         """
#         Return True when a host or participant explicitly clicks 'Deny' on
#         the bot's join request. This is a hard stop — unlike a timeout, it
#         represents a deliberate human action and should not be retried.
#         """
#         try:
#             return self.page.get_by_text(_DENIED_PHRASES).is_visible(timeout=3000)
#         except Exception:
#             return False



import os
import re
import random
import time
from datetime import datetime
from app.core.middlewares.global_logger import get_logger
from app.bot.utils import ScreenshotMixin
from app.util.response_util.custom_exception import (
    JoinButtonNotFoundError,
    JoinDeniedError,
    WaitingRoomTimeoutError,
    BotDetection,
    DirectJoinTimeoutError,
    JoinProcessError,
    NoRetryException,
)
from app.core.decorators.retry import retry
from app.core.middlewares.global_logger import get_logger
from app.util.time_util import get_ist_now
from app.meetings.meetingModel import BotStatus

logger = get_logger("MEET_JOIN")

# Selectors that appear once you are INSIDE the waiting room of the meeting.
_WAITING_ROOM_INDICATORS = [
    "Please wait until a meeting host brings you into the call",
    "Waiting to be admitted",
    "Someone will let you in soon",
    "Your request to join has been sent",
    "Waiting for host to admit you",
]

# Selectors that only appear once you are INSIDE the meeting.
_INSIDE_MEETING_SELECTORS = [
    "button[aria-label='Raise your hand']",
    "button[aria-label='Turn on captions']",
    "button[aria-label='Turn off captions']",
    "button[aria-label='Share Screen']",
    "button[aria-label='Send a reaction']",
]

_PARTICIPANT_SELECTORS = [
    ".uGOf1d",
    ".wnPUne",
    "button[aria-label*='everyone']",
    "[data-participant-count]",
    "[data-avatar-count]",
]

_END_PHRASES = re.compile(
    r"You've been removed|The meeting has ended|You left the meeting",
    re.IGNORECASE,
)

_BLOCKED_PHRASES = re.compile(
    r"You Can't Join this video call|You can't join this call",
    re.IGNORECASE,
)

_DENIED_PHRASES = re.compile(
    r"Someone in the call denied your request to join",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Human-like behaviour helpers
# ---------------------------------------------------------------------------

def _human_delay(min_s: float = 0.5, max_s: float = 1.5) -> None:
    """Sleep for a random duration to simulate human reaction time."""
    time.sleep(random.uniform(min_s, max_s))


def _move_mouse_naturally(page, target_x: int, target_y: int) -> None:
    """
    Move the mouse from its current position to (target_x, target_y)
    in small curved steps rather than teleporting — mimics human hand movement.
    """
    try:
        # Generate a bezier-like curved path with 6-10 intermediate points
        steps = random.randint(6, 10)
        # Start from a random nearby position (we can't read current pos easily)
        start_x = target_x + random.randint(-200, 200)
        start_y = target_y + random.randint(-150, 150)

        # Control point for a slight curve
        ctrl_x = (start_x + target_x) / 2 + random.randint(-80, 80)
        ctrl_y = (start_y + target_y) / 2 + random.randint(-60, 60)

        for i in range(1, steps + 1):
            t = i / steps
            # Quadratic bezier interpolation
            x = int((1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * target_x)
            y = int((1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * target_y)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.01, 0.04))  # ~10-40ms per step

    except Exception:
        # Non-critical — just skip if it fails
        pass


def _human_click(page, element) -> None:
    """
    Click an element the way a human would:
    move mouse toward it, pause briefly, then click.
    """
    try:
        box = element.bounding_box()
        if box:
            # Aim for a random spot inside the element (not always dead-centre)
            target_x = int(box["x"] + box["width"] * random.uniform(0.3, 0.7))
            target_y = int(box["y"] + box["height"] * random.uniform(0.3, 0.7))
            _move_mouse_naturally(page, target_x, target_y)
            _human_delay(0.1, 0.4)
            page.mouse.click(target_x, target_y)
        else:
            element.click()
    except Exception:
        element.click()  # fallback


def _human_type(element, text: str) -> None:
    """
    Type text character by character with random inter-key delays,
    occasional short pauses, and a pre-type hesitation — like a real person.
    """
    element.click()
    _human_delay(0.3, 0.7)
    element.fill("")  # Clear first

    for char in text:
        element.press_sequentially(char, delay=random.randint(60, 180))
        # Occasionally pause mid-word as if thinking
        if random.random() < 0.08:
            time.sleep(random.uniform(0.2, 0.5))


def _idle_mouse_wander(page, duration: float = 3.0) -> None:
    """
    Move the mouse to a few random positions over `duration` seconds
    while waiting — simulates a human idly moving their mouse.
    """
    deadline = time.time() + duration
    viewport = page.viewport_size or {"width": 1280, "height": 720}

    while time.time() < deadline:
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        _move_mouse_naturally(page, x, y)
        time.sleep(random.uniform(0.5, 1.5))


def _random_scroll(page) -> None:
    """Scroll the page slightly up or down — humans do this while waiting."""
    try:
        delta = random.choice([-1, 1]) * random.randint(50, 200)
        page.mouse.wheel(0, delta)
        _human_delay(0.3, 0.8)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Meet_Join handler
# ---------------------------------------------------------------------------


class MeetJoin(ScreenshotMixin):

    def __init__(
        self, url: str, page, meeting_id: int, bot_name: str, update_bot_callback=None
    ) -> None:
        self.url = url
        self.page = page
        self.bot_name = bot_name
        self.meeting_id = meeting_id
        self._join_denied = False
        self.update_bot_callback = update_bot_callback
        self._screenshot_step = 0
        self.max_participant_count = 0
        logger.info(f"Google Meet handler initialised for URL: {url}")

    # 1. Join — retried up to 3× UNLESS the request was explicitly denied
    @retry(times=3, delay=5)
    def join(self) -> bool:

        if self._join_denied:
            logger.error("Join was explicitly denied in a previous attempt — aborting")
            raise JoinDeniedError()

        logger.info("Attempting to join the meeting")
        self._debug_step = 0
        try:
            self.page.goto(self.url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=30000)
            self._take_screenshot("page_loaded", platform="google")

            # Human-like pause after page load — don't act immediately
            _human_delay(2, 4)

            # Wander mouse a bit as if the page is loading and you're waiting
            _idle_mouse_wander(self.page, duration=random.uniform(1.5, 3.0))

            if self._is_blocked():
                logger.error("Bot blocked immediately by Google Meet")
                self._take_screenshot("blocked", platform="google")
                raise BotDetection()

            self._dismiss_av_prompt()
            self._take_screenshot("av_prompt_dismissed", platform="google")

            # Small pause between actions
            _human_delay(0.8, 1.8)

            self._fill_name()
            self._take_screenshot("name_filled", platform="google")

            # Pause after typing name — like reading it over before proceeding
            _human_delay(1.0, 2.5)
            _random_scroll(self.page)

            self._dismiss_popups()
            self._take_screenshot("popups_dismissed", platform="google")

            # Idle mouse wander while "deciding" to click join
            _idle_mouse_wander(self.page, duration=random.uniform(1.0, 2.5))

            join_btn, is_waiting_room = self._find_join_button()
            self._take_screenshot("join_button_found", platform="google")
            if not join_btn:
                logger.error("No join button found")
                raise JoinButtonNotFoundError()

            logger.info(f"Clicking join button (waiting_room={is_waiting_room})")

            # Hover near the button first before clicking (human behaviour)
            _human_delay(0.5, 1.5)
            _human_click(self.page, join_btn)
            self._take_screenshot("join_button_clicked", platform="google")

            if is_waiting_room:
                logger.info("Join request sent — confirming waiting room entry...")
                self._take_screenshot("waiting_for_room", platform="google")
                if not self._wait_until_waiting_room(timeout=15):
                    logger.error(
                        "Never landed in waiting room after clicking join — click may not have registered"
                    )
                    raise JoinProcessError(
                        "Failed to enter waiting room after clicking join"
                    )

                logger.info("Waiting room confirmed — waiting for host to admit...")
                self._take_screenshot("in_waiting_room", platform="google")
                self._update_bot(
                    bot_status=BotStatus.WAITING_ROOM,
                    waiting_room_entered_at=get_ist_now(),
                )
                admitted = self._wait_until_inside(timeout=180)

                if not admitted:
                    self._update_bot(bot_status=BotStatus.CANCELLED)
                    if self._is_join_denied():
                        self._update_bot(bot_status=BotStatus.DENIED)
                        self._join_denied = True
                        logger.error(
                            "Join request explicitly denied by a participant — stopping"
                        )
                        raise JoinDeniedError()

                    logger.error("Waiting room timeout — bot was never admitted")
                    self._take_screenshot("waiting_timeout", platform="google")
                    raise WaitingRoomTimeoutError()

                self._update_bot(
                    bot_status=BotStatus.MEETING_JOINED,
                    bot_join_time=get_ist_now(),
                    started_at=get_ist_now(),
                )
                self._take_screenshot("inside_meeting", platform="google")
                logger.info("Bot confirmed inside meeting")

            else:
                if not self._wait_until_inside(timeout=30):
                    logger.error("Direct join timed out — never detected in-call UI")
                    self._take_screenshot("direct_join_timeout", platform="google")
                    raise DirectJoinTimeoutError()
                self._update_bot(
                    bot_status=BotStatus.MEETING_JOINED,
                    bot_join_time=get_ist_now(),
                    started_at=get_ist_now(),
                )
                self._take_screenshot("inside_meeting_direct", platform="google")
                logger.info("Bot confirmed inside meeting (direct join)")

            self._take_screenshot("join_success", platform="google")
            return True

        except Exception as exc:

            if isinstance(exc, JoinDeniedError):
                self._take_screenshot("join_denied", platform="google")
                self._update_bot(bot_status=BotStatus.DENIED)
                self._join_denied = True
                raise

            if isinstance(
                exc,
                (
                    WaitingRoomTimeoutError,
                    JoinButtonNotFoundError,
                    DirectJoinTimeoutError,
                    BotDetection,
                ),
            ):
                raise

            if isinstance(exc, NoRetryException):
                raise

            if self._is_blocked():
                logger.error("Bot redirected to a blocked page")
                raise BotDetection()

            logger.error(f"Google Meet join error: {exc}")
            self._take_screenshot(f"error_{type(exc).__name__}", platform="google")

            self._update_bot(retry_count=lambda x: x + 1)
            raise JoinProcessError()

    def set_update_bot_callback(self, callback):
        """Set the callback function for updating bot status."""
        self.update_bot_callback = callback

    def _update_bot(self, **kwargs):
        """Internal helper to call update_bot callback if set."""
        if self.update_bot_callback:
            self.update_bot_callback(**kwargs)

    # 2. Main end-detection
    def detect_end(self, grace_period: int = 60) -> tuple[bool, int]:
        """Returns (ended: bool, max_participant_count: int)"""
        try:
            if self._end_message_visible():
                self._update_bot(
                    bot_status=BotStatus.MEETING_ENDED,
                    ended_at=get_ist_now(),
                )
                logger.info("End message detected — leaving")
                return True, self.max_participant_count

            count = self._get_participant_count()
            if count > 0 and count > self.max_participant_count:
                self.max_participant_count = count
                logger.info(f"Updated max participant count to: {count}")

            if count == -1:
                return False, self.max_participant_count
            if count > 1:
                return False, self.max_participant_count

            self._update_bot(bot_status=BotStatus.GRACE_PERIOD, ended_at=get_ist_now())
            ended = self._run_grace_period(grace_period)
            return ended, self.max_participant_count

        except Exception as exc:
            logger.warning(f"detect_end error: {exc}")
            return False, self.max_participant_count

    # 3. Wait until confirmed inside the meeting
    def _wait_until_inside(self, timeout: int) -> bool:
        """
        Poll every 3 seconds until a known in-call UI element is visible.
        While waiting, perform occasional idle mouse movements to look human.
        """
        deadline = time.time() + timeout
        poll_interval = 3
        checks = 0
        last_wander = time.time()

        while time.time() < deadline:
            checks += 1
            if self._is_inside_meeting():
                return True

            if self._is_join_denied():
                raise JoinDeniedError("Join request was denied by host")

            # Every ~15s, do a small mouse wander while waiting to be admitted
            if time.time() - last_wander > 15:
                _idle_mouse_wander(self.page, duration=random.uniform(1.0, 2.0))
                last_wander = time.time()

            elapsed = int(time.time() - (deadline - timeout))
            logger.info(f"Not yet inside meeting... {elapsed}s / {timeout}s elapsed")
            time.sleep(poll_interval)

        return False

    # 4. Confirm the bot landed in the waiting room
    def _wait_until_waiting_room(self, timeout: int = 15) -> bool:
        logger.info(f"[JOIN STEP 9.1] Waiting for waiting room confirmation (timeout={timeout}s)...")
        deadline = time.time() + timeout
        poll_interval = 2
        checks = 0

        while time.time() < deadline:
            checks += 1
            if self._is_in_waiting_room():
                logger.info(f"[JOIN STEP 9.2] Waiting room confirmed after {checks} checks")
                return True
            logger.info(f"[JOIN STEP 9.1] Waiting room check {checks} - not yet in waiting room")
            time.sleep(poll_interval)

        logger.error(f"[JOIN STEP 9.3] Waiting room timeout after {checks} checks")
        return False

    def _is_in_waiting_room(self) -> bool:
        for phrase in _WAITING_ROOM_INDICATORS:
            try:
                el = self.page.get_by_text(re.compile(re.escape(phrase), re.IGNORECASE))
                if el.count() > 0 and el.first.is_visible(timeout=3000):
                    logger.info(f"[JOIN STEP 9.1] Waiting room confirmed via phrase: '{phrase}'")
                    return True
            except Exception:
                continue
        return False

    # 5. Confirm inside the meeting via positive UI signals
    def _is_inside_meeting(self) -> bool:
        for selector in _INSIDE_MEETING_SELECTORS:
            try:
                el = self.page.locator(selector)
                if el.count() > 0 and el.first.is_visible(timeout=3000):
                    logger.info(f"[JOIN STEP 10.1] In-call UI confirmed via selector: {selector}")
                    return True
            except Exception:
                continue
        return False

    # 5. Dismiss audio/video prompt
    def _dismiss_av_prompt(self) -> None:
            """
            Handles two different mic/camera prompts Google Meet shows:

            Prompt A (old): "Continue without microphone and camera"  — single button
            Prompt B (new): "Do you want people to hear you in the meeting?"
                            with "Use microphone" and "Continue without microphone" buttons

            We always click the 'without' option so the bot joins muted.
            """
            # Candidates in priority order — most specific first
            dismiss_labels = [
                "Continue without microphone and camera",  # Prompt A (combined mic+cam)
                "Continue without microphone",             # Prompt B (mic only)
                "Continue without camera",                 # fallback camera-only variant
            ]

            for label in dismiss_labels:
                try:
                    btn = self.page.get_by_role(
                        "button",
                        name=re.compile(re.escape(label), re.IGNORECASE),
                    )
                    if btn.count() > 0 and btn.first.is_visible(timeout=4000):
                        _human_delay(0.4, 0.9)
                        _human_click(self.page, btn.first)
                        logger.info(f"Dismissed AV prompt via: '{label}'")
                        # Brief pause after dismissing — let the UI settle
                        _human_delay(0.5, 1.0)
                        return
                except Exception:
                    continue

            logger.info("No AV prompt found — skipping")

    # 6. Fill name field with human-like typing
    def _fill_name(self) -> None:
        name_input = self.page.locator(
            "input[type='text'], input[placeholder='Your name']"
        ).first

        if name_input.count() == 0:
            logger.error("Name input not found")
            return

        name_input.wait_for(state="visible", timeout=10_000)

        # Move mouse to the input field naturally before clicking
        _human_delay(0.5, 1.2)
        _human_click(self.page, name_input)

        # Type like a human — character by character with variable delays
        _human_type(name_input, self.bot_name)
        logger.info(f"Filled name field with '{self.bot_name}'")

    # 7. Dismiss incidental popups
    def _dismiss_popups(self) -> None:
        try:
            btn = self.page.get_by_role(
                "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
            )
            if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                _human_delay(0.3, 0.8)
                _human_click(self.page, btn.first)
                logger.info("Dismissed popup")
        except Exception:
            pass

    # 8. Locate the join button
    def _find_join_button(self):
        """Return (button, is_waiting_room) or (None, False) if not found."""
        candidates = [
            ("Ask to join", True),
            ("Join now", False),
        ]
        for label, is_waiting_room in candidates:
            try:
                btn = self.page.get_by_role(
                    "button", name=re.compile(label, re.IGNORECASE)
                )
                count = btn.count()
                logger.info(f"[JOIN STEP 7.2] Checking for '{label}' button: count={count}")
                if count > 0 and btn.first.is_visible(timeout=5000):
                    logger.info(f"[JOIN STEP 7.3] Found '{label}' button (waiting_room={is_waiting_room})")
                    return btn.first, is_waiting_room
            except Exception as e:
                logger.warning(f"[JOIN STEP 7.2] Error checking for '{label}': {e}")
                pass

        # Fallback: any visible button containing "Join"
        try:
            btns = self.page.get_by_role(
                "button", name=re.compile(r"\bJoin\b", re.IGNORECASE)
            )
            count = btns.count()
            for i in range(count):
                btn = btns.nth(i)
                if btn.is_visible(timeout=5000):
                    text = btn.inner_text()
                    is_waiting_room = "ask" in text.lower()
                    return btn, is_waiting_room
        except Exception:
            pass
        return None, False

    # 9. Grace period — stay until someone rejoins or time is up
    def _run_grace_period(self, duration: int) -> bool:
        logger.info(f"Bot is alone — starting {duration}s grace period")
        deadline = time.time() + duration
        last_wander = time.time()

        while time.time() < deadline:
            if self._end_message_visible():
                return True
            count = self._get_participant_count()
            if count != -1 and count > 1:
                logger.info("Someone joined during grace period — staying")
                return False

            # Occasional mouse movement during grace period
            if time.time() - last_wander > 20:
                _idle_mouse_wander(self.page, duration=random.uniform(0.8, 1.5))
                last_wander = time.time()

            time.sleep(2)

        self._update_bot(
            bot_status=BotStatus.MEETING_ENDED,
            bot_leave_time=get_ist_now(),
        )
        logger.info("Grace period expired — leaving")
        return True

    # 10. Detect explicit end-of-meeting text
    def _end_message_visible(self) -> bool:
        try:
            return self.page.get_by_text(_END_PHRASES).is_visible()
        except Exception:
            return False

    # 11. Get participant count
    def _get_participant_count(self) -> int:
        """Return participant count, or -1 if it cannot be determined."""
        for selector in _PARTICIPANT_SELECTORS:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    text = elements.first.inner_text().strip()
                    match = re.search(r"\d+", text)
                    if match:
                        return int(match.group())
            except Exception:
                continue

        try:
            tiles = self.page.locator("div[data-participant-id]")
            if tiles.count() > 0:
                return tiles.count()
        except Exception:
            pass

        return -1

    # 12. Detect Google's own "can't join" block page
    def _is_blocked(self) -> bool:
        try:
            return self.page.get_by_text(_BLOCKED_PHRASES).is_visible(timeout=5000)
        except Exception:
            return False

    # 13. Detect explicit join denial by a call participant
    def _is_join_denied(self) -> bool:
        try:
            return self.page.get_by_text(_DENIED_PHRASES).is_visible(timeout=3000)
        except Exception:
            return False