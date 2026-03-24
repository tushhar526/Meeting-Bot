# import logging
# import time
# import re
# import random

# from app.helper.decorators import retry
# from app.helper.logger import get_logger

# logger = get_logger(__name__)


# class Meet:
#     def __init__(self, url, page):
#         self.url = url
#         self.page = page
#         self._waiting_start = None
#         logger.info(f"Google Meet handler initialized for URL: {url}")

#     @retry(times=3, delay=5)
#     def join(self):
#         logger.info("Handling Google Meet joining ...")

#         try:
#             self.page.goto(self.url)
#             self.page.wait_for_load_state("networkidle")
#             logger.info("Page loaded successfully")

#             time.sleep(random.uniform(2, 5))

#             # Fast fail — blocked immediately
#             if self._is_blocked():
#                 logger.error("Bot blocked by Google Meet immediately")
#                 return False

#             # Dismiss AV prompt if present
#             try:
#                 no_av = self.page.get_by_role(
#                     "button",
#                     name=re.compile(
#                         "Continue without microphone and camera", re.IGNORECASE
#                     ),
#                 )
#                 no_av.wait_for(state="visible", timeout=5000)
#                 no_av.click()
#                 logger.info("Clicked 'Continue without microphone and camera'")
#             except Exception:
#                 logger.info("No AV prompt — proceeding")

#             # Fill name
#             name = self.page.locator(
#                 "input[type='text'], input[placeholder='Your name']"
#             ).first
#             if name.count() == 0:
#                 logger.error("Name input not found")
#                 self._screenshot("meet_no_name_input")
#                 return False
#             name.wait_for(state="visible", timeout=10000)
#             time.sleep(random.uniform(1, 3))
#             name.fill("Meeting Bot")
#             logger.info("Filled name")

#             # Dismiss popups
#             try:
#                 got_it = self.page.get_by_role(
#                     "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
#                 )
#                 if got_it.count() > 0 and got_it.first.is_visible(timeout=2000):
#                     got_it.first.click()
#                     logger.info("Dismissed popup")
#             except Exception:
#                 pass

#             time.sleep(random.uniform(2, 4))

#             # Find join button
#             join_btn, is_ask_to_join = self._find_join_button()
#             if not join_btn:
#                 logger.error("No join button found")
#                 self._screenshot("meet_no_join_btn")
#                 return False

#             logger.info(f"Clicking join button — is_ask_to_join: {is_ask_to_join}")
#             time.sleep(random.uniform(1, 2))
#             join_btn.click()
#             logger.info("Clicked join button")

#             if is_ask_to_join:
#                 # Don't loop here — detect_end owns the waiting room timeout.
#                 # Just mark that we're in the waiting room and return True
#                 # so BaseBot proceeds to detect_meeting_end polling.
#                 self._waiting_start = time.time()
#                 logger.info(
#                     "Bot sent join request — in waiting room, detect_end will manage timeout"
#                 )
#                 time.sleep(2)
#                 return True
#             else:
#                 time.sleep(3)
#                 logger.info("Joined meeting directly (no waiting room)")
#                 return True

#         except Exception as e:
#             if self._is_blocked():
#                 logger.error("Bot redirected to blocked page")
#                 return False
#             logger.error(f"Google Meet join error: {e}", exc_info=True)
#             return False

#     # ------------------------------------------------------------------
#     # End detection
#     # ------------------------------------------------------------------

#     def detect_end(self, gracePeriod=60, waitingPeriod=180) -> bool:
#         try:
#             # Get participant count first — used by both waiting room
#             # and in-meeting logic below
#             count = self._get_participant_count()

#             # --- Waiting room check ---
#             if self._is_in_waiting_room():
#                 if self._waiting_start is None:
#                     self._waiting_start = time.time()
#                     logger.info(
#                         f"Entered waiting room, {waitingPeriod}s timeout started"
#                     )

#                 # Check if we've been admitted — participant count > 1
#                 if count > 1:
#                     logger.info(
#                         f"Admitted from waiting room ({count} participants detected)"
#                     )
#                     self._waiting_start = None
#                     return False  # stay in meeting

#                 elapsed = time.time() - self._waiting_start
#                 if elapsed < waitingPeriod:
#                     logger.info(
#                         f"Waiting room: {int(elapsed)}s elapsed of {waitingPeriod}s"
#                     )
#                     return False
#                 else:
#                     logger.info(f"Waiting room timeout ({int(elapsed)}s) — leaving")
#                     return True

#             # Not in waiting room — clear the timer
#             self._waiting_start = None

#             # --- Host ended or bot removed ---
#             if self.page.get_by_text(
#                 re.compile(
#                     r"You've been removed|The meeting has ended|You left the meeting",
#                     re.IGNORECASE,
#                 )
#             ).is_visible():
#                 logger.info("Meeting ended or bot was removed")
#                 return True

#             # --- Participant count check ---
#             if count == -1:
#                 return False  # can't determine, stay

#             if count > 1:
#                 return False  # others present, stay

#             # --- Bot is alone — grace period ---
#             logger.info(
#                 f"Bot is alone ({count} participant), starting {gracePeriod}s grace period"
#             )
#             start = time.time()

#             while time.time() - start < gracePeriod:
#                 if self.page.get_by_text(
#                     re.compile(
#                         r"You've been removed|The meeting has ended", re.IGNORECASE
#                     )
#                 ).is_visible():
#                     return True

#                 current = self._get_participant_count()
#                 if current > 1:
#                     logger.info(
#                         f"Someone joined during grace period ({current} participants) — staying"
#                     )
#                     return False

#                 time.sleep(2)

#             logger.info("Grace period expired — leaving")
#             return True

#         except Exception as e:
#             logger.warning(f"detect_end error: {e}")
#             return False

#     # ------------------------------------------------------------------
#     # Helpers
#     # ------------------------------------------------------------------

#     def _find_join_button(self):
#         """Find the join button and determine if it's a waiting room request."""
#         # Try Ask to join first (waiting room)
#         try:
#             btn = self.page.get_by_role(
#                 "button", name=re.compile("Ask to join", re.IGNORECASE)
#             )
#             if btn.count() > 0 and btn.first.is_visible():
#                 return btn.first, True
#         except Exception:
#             pass

#         # Try Join now (direct)
#         try:
#             btn = self.page.get_by_role(
#                 "button", name=re.compile("Join now", re.IGNORECASE)
#             )
#             if btn.count() > 0 and btn.first.is_visible():
#                 return btn.first, False
#         except Exception:
#             pass

#         # Fallback — any visible button with "Join"
#         try:
            # btns = self.page.get_by_role(
#                 "button", name=re.compile(r"\bJoin\b", re.IGNORECASE)
#             )
#             for i in range(btns.count()):
#                 btn = btns.nth(i)
#                 if btn.is_visible():
#                     is_ask = "ask" in btn.inner_text().lower()
#                     logger.info(f"Fallback join button: '{btn.inner_text()}'")
#                     return btn, is_ask
#         except Exception:
#             pass

#         return None, False

#     def _get_participant_count(self) -> int:
#         """Return participant count, or -1 if undetermined."""
#         locators = [
#             ".uGOf1d",
#             ".wnPUne",
#             "button[aria-label*='everyone']",
#             "[data-participant-count]",
#             "[data-avatar-count]",
#         ]
#         for selector in locators:
#             try:
#                 elements = self.page.locator(selector)
#                 if elements.count() > 0:
#                     text = elements.first.inner_text().strip()
#                     match = re.search(r"\d+", text)
#                     if match:
#                         return int(match.group())
#             except Exception:
#                 continue

#         # Fallback: participant tiles
#         try:
#             tiles = self.page.locator("div[data-participant-id]")
#             if tiles.count() > 0:
#                 return tiles.count()
#         except Exception:
#             pass

#         return -1

#     def _is_in_waiting_room(self) -> bool:
#         """Return True if the waiting room UI is currently visible."""
#         indicators = [
#             "Please wait until a meeting host brings you into the call",
#             "Waiting to be admitted",
#             "Someone will let you in soon",
#             "Your request to join has been sent",
#             "Waiting for host to admit you",
#         ]
#         for indicator in indicators:
#             try:
#                 if self.page.get_by_text(
#                     re.compile(indicator, re.IGNORECASE)
#                 ).is_visible():
#                     return True
#             except Exception:
#                 continue
#         return False

#     def _is_blocked(self) -> bool:
#         """Return True if Google Meet blocked the bot."""
#         try:
#             return self.page.get_by_text(
#                 re.compile(
#                     r"You Can't Join this video call|You can't join this call",
#                     re.IGNORECASE,
#                 )
#             ).is_visible()
#         except Exception:
#             return False

#     def _screenshot(self, label: str):
#         """Save a debug screenshot."""
#         import os

#         try:
#             os.makedirs("/tmp/debug", exist_ok=True)
#             path = f"/tmp/debug/{label}_{int(time.time())}.png"
#             self.page.screenshot(path=path, full_page=True)
#             logger.info(f"Screenshot saved: {path}")
#         except Exception as e:
#             logger.warning(f"Screenshot failed: {e}")


import os
import re
import random
import time

from app.helper.decorators import retry
from app.helper.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BOT_NAME = "Meeting Bot"

_WAITING_ROOM_INDICATORS = [
    "Please wait until a meeting host brings you into the call",
    "Waiting to be admitted",
    "Someone will let you in soon",
    "Your request to join has been sent",
    "Waiting for host to admit you",
]

# Selectors that only appear once you are INSIDE the meeting.
# We use these as positive proof of admission.
_INSIDE_MEETING_SELECTORS = [
    "[data-call-ended]",            # call container
    "div[data-participant-id]",     # at least one participant tile
    ".crqnQb",                      # in-call toolbar
    "[data-tooltip='Leave call']",  # leave button only shown inside
    "button[aria-label='Leave call']",
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


# ---------------------------------------------------------------------------
# Meet handler
# ---------------------------------------------------------------------------

class Meet:
    """
    Handles joining and monitoring a Google Meet session.

    join()        — navigate, fill name, click join, block until CONFIRMED inside (retried up to 3x)
    detect_end()  — called periodically by BaseBot to decide when to leave
    """

    def __init__(self, url: str, page) -> None:
        self.url = url
        self.page = page
        logger.info(f"Google Meet handler initialised for URL: {url}")

    # ------------------------------------------------------------------
    # Join
    # ------------------------------------------------------------------

    @retry(times=3, delay=5)
    def join(self) -> bool:
        """
        Navigate to the meeting, complete the pre-join flow, then wait for
        POSITIVE confirmation that the bot is inside before returning True.

        We look for in-call UI elements rather than absence of waiting-room
        text — because waiting-room text can be absent for many reasons
        (page not yet rendered, UI change, locator miss) which would cause
        a false "admitted" signal.
        """
        logger.info("Google Meet — attempting to join...")
        try:
            self.page.goto(self.url)
            self.page.wait_for_load_state("networkidle")
            logger.info("Page loaded")

            time.sleep(random.uniform(2, 5))

            if self._is_blocked():
                logger.error("Bot blocked immediately by Google Meet")
                return False

            self._dismiss_av_prompt()
            self._fill_name()
            self._dismiss_popups()

            time.sleep(random.uniform(2, 4))

            join_btn, is_waiting_room = self._find_join_button()
            if not join_btn:
                logger.error("No join button found")
                self._save_screenshot("meet_no_join_btn")
                return False

            logger.info(f"Clicking join button (waiting_room={is_waiting_room})")
            time.sleep(random.uniform(1, 2))
            join_btn.click()

            if is_waiting_room:
                logger.info("Join request sent — waiting for host to admit...")
                # Block until we see in-call UI (positive proof of admission)
                # rather than checking for absence of waiting room text.
                if not self._wait_until_inside(timeout=180):
                    logger.error("Waiting room timeout — bot was never admitted")
                    self._save_screenshot("meet_waiting_room_timeout")
                    return False
                logger.info("Bot confirmed inside meeting")
            else:
                # Even for direct joins, wait for in-call UI to confirm we're in.
                if not self._wait_until_inside(timeout=30):
                    logger.error("Direct join timed out — never detected in-call UI")
                    self._save_screenshot("meet_direct_join_timeout")
                    return False
                logger.info("Bot confirmed inside meeting (direct join)")

            return True

        except Exception as exc:
            if self._is_blocked():
                logger.error("Bot redirected to a blocked page")
                return False
            logger.error(f"Google Meet join error: {exc}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # End detection
    # ------------------------------------------------------------------

    def detect_end(self, grace_period: int = 60) -> bool:
        """
        Return True when the bot should leave the meeting.

        By the time this is called, join() has already confirmed the bot
        is inside the meeting, so we only need to handle:
          1. Explicit end message — host ended, bot removed, etc.
          2. Bot is alone — leave after `grace_period` seconds.
        """
        try:
            if self._end_message_visible():
                logger.info("End message detected — leaving")
                return True

            count = self._get_participant_count()
            if count == -1:
                return False  # Cannot determine count; stay safe.
            if count > 1:
                return False  # Others are present.

            return self._run_grace_period(grace_period)

        except Exception as exc:
            logger.warning(f"detect_end error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Private — join helpers
    # ------------------------------------------------------------------

    def _wait_until_inside(self, timeout: int) -> bool:
        """
        Poll every 3 seconds until a known in-call UI element is visible,
        which is POSITIVE proof the bot is inside the meeting.

        This is intentionally stricter than checking for the absence of
        waiting-room text, which can disappear for unrelated reasons and
        produce false admission signals.
        """
        deadline = time.time() + timeout
        poll_interval = 3

        while time.time() < deadline:
            if self._is_inside_meeting():
                return True
            elapsed = int(time.time() - (deadline - timeout))
            logger.info(f"Not yet inside meeting... {elapsed}s / {timeout}s elapsed")
            time.sleep(poll_interval)

        return False

    def _is_inside_meeting(self) -> bool:
        """
        Return True only when at least one known in-call UI element is visible.
        These elements do not appear in the pre-join screen or waiting room.
        """
        for selector in _INSIDE_MEETING_SELECTORS:
            try:
                el = self.page.locator(selector)
                if el.count() > 0 and el.first.is_visible():
                    logger.info(f"In-call UI confirmed via selector: {selector}")
                    return True
            except Exception:
                continue
        return False

    def _dismiss_av_prompt(self) -> None:
        try:
            btn = self.page.get_by_role(
                "button",
                name=re.compile("Continue without microphone and camera", re.IGNORECASE),
            )
            btn.wait_for(state="visible", timeout=5000)
            btn.click()
            logger.info("Dismissed AV prompt")
        except Exception:
            logger.info("No AV prompt — skipping")

    def _fill_name(self) -> None:
        name_input = self.page.locator(
            "input[type='text'], input[placeholder='Your name']"
        ).first

        if name_input.count() == 0:
            logger.error("Name input not found")
            self._save_screenshot("meet_no_name_input")
            return

        name_input.wait_for(state="visible", timeout=10_000)
        time.sleep(random.uniform(1, 3))
        name_input.fill(_BOT_NAME)
        logger.info(f"Filled name field with '{_BOT_NAME}'")

    def _dismiss_popups(self) -> None:
        try:
            btn = self.page.get_by_role(
                "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
            )
            if btn.count() > 0 and btn.first.is_visible(timeout=2000):
                btn.first.click()
                logger.info("Dismissed popup")
        except Exception:
            pass

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
                if btn.count() > 0 and btn.first.is_visible():
                    return btn.first, is_waiting_room
            except Exception:
                pass

        # Fallback: any visible button containing "Join"
        try:
            btns = self.page.get_by_role(
                "button", name=re.compile(r"\bJoin\b", re.IGNORECASE)
            )
            for i in range(btns.count()):
                btn = btns.nth(i)
                if btn.is_visible():
                    is_waiting_room = "ask" in btn.inner_text().lower()
                    logger.info(f"Fallback join button: '{btn.inner_text()}'")
                    return btn, is_waiting_room
        except Exception:
            pass

        return None, False

    # ------------------------------------------------------------------
    # Private — end detection helpers
    # ------------------------------------------------------------------

    def _run_grace_period(self, duration: int) -> bool:
        logger.info(f"Bot is alone — starting {duration}s grace period")
        deadline = time.time() + duration

        while time.time() < deadline:
            if self._end_message_visible():
                return True
            count = self._get_participant_count()
            if count != -1 and count > 1:
                logger.info("Someone joined during grace period — staying")
                return False
            time.sleep(2)

        logger.info("Grace period expired — leaving")
        return True

    def _end_message_visible(self) -> bool:
        try:
            return self.page.get_by_text(_END_PHRASES).is_visible()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private — participant count
    # ------------------------------------------------------------------

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

        # Fallback: count participant tiles directly.
        try:
            tiles = self.page.locator("div[data-participant-id]")
            if tiles.count() > 0:
                return tiles.count()
        except Exception:
            pass

        return -1

    # ------------------------------------------------------------------
    # Private — state queries
    # ------------------------------------------------------------------

    def _is_blocked(self) -> bool:
        try:
            return self.page.get_by_text(_BLOCKED_PHRASES).is_visible()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private — debug utilities
    # ------------------------------------------------------------------

    def _save_screenshot(self, label: str) -> None:
        try:
            os.makedirs("/tmp/debug", exist_ok=True)
            path = f"/tmp/debug/{label}_{int(time.time())}.png"
            self.page.screenshot(path=path, full_page=True)
            logger.info(f"Screenshot saved: {path}")
        except Exception as exc:
            logger.warning(f"Screenshot failed: {exc}")