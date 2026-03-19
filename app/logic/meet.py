# import logging
# import re
# import time
# import random
# from app.helper.decorators import retry
# from app.helper.logger import get_logger

# logger = get_logger(__name__)


# class Meet:
#     def __init__(self, url, page):
#         self.url = url
#         self.page = page
#         logger.info(f"Google Meet handler initialized for URL: {url}")

#     @retry(times=3, delay=5)
#     def join(self):
#         logger.info("Handling Google meet's meeting join ...")

#         try:
#             self.page.goto(self.url)
#             logger.info(f"Navigated to: {self.page.url}")

#             self.page.wait_for_load_state("networkidle")
#             logger.info("Page loaded successfully")

#             time.sleep(random.uniform(2, 5))  # Random delay to seem more human

#             # Fast fail check: Did Google block us immediately?
#             if self.page.get_by_text(
#                 re.compile(
#                     r"You Can't Join this video call|You can't join this call",
#                     re.IGNORECASE,
#                 )
#             ).is_visible():
#                 logger.error("Bot got completely blocked by Google Meet immediately upon loading")
#                 return False

#             logger.info("Checking for 'Continue without microphone and camera' button")

#             try:
#                 no_av = self.page.get_by_role(
#                     "button",
#                     name=re.compile(
#                         "Continue without microphone and camera", re.IGNORECASE
#                     ),
#                 )

#                 # Use a shorter timeout since this button doesn't always appear
#                 no_av.wait_for(state="visible", timeout=5000)
#                 no_av.click()
#                 logger.info("Clicked 'Continue without microphone and camera'")
#             except Exception as e:
#                 logger.info(
#                     "No 'Continue without microphone and camera' button found or needed. Proceeding..."
#                 )

#             logger.info("Finding name input tag")
#             name = self.page.locator(
#                 "input[type='text'], input[placeholder='Your name']"
#             ).first

#             # Check if name input actually exists and is visible
#             if name.count() == 0:
#                 logger.error(
#                     "Name input field not found! Meeting might be in different state"
#                 )
#                 # Take screenshot for debugging
#                 try:
#                     self.page.screenshot(
#                         path=f"debug_name_input_{self.page.url.split('/')[-1]}.png"
#                     )
#                     logger.info("Saved debug screenshot")
#                 except:
#                     pass
#                 return False

#             name.wait_for(state="visible", timeout=10000)
#             time.sleep(random.uniform(1, 3))  # Random delay before entering name
#             name.fill("Meeting Bot")
#             logger.info("Entered name Meeting bot")

#             logger.info("Closing any 'Got it' or 'Dismiss' popups if present")
#             try:
#                 got_it_btn = self.page.get_by_role(
#                     "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
#                 )
#                 if got_it_btn.count() > 0 and got_it_btn.first.is_visible(timeout=2000):
#                     got_it_btn.first.click()
#                     logger.info("Dismissed popup")
#             except Exception as e:
#                 logger.info(f"No popup to dismiss: {e}")

#             logger.info("Finding joining button")
#             time.sleep(random.uniform(2, 4))  # Random delay before finding join button

#             # Try multiple approaches to find the right join button
#             join_btn = None

#             # Method 1: Look for "Ask to join" specifically (waiting room)
#             try:
#                 ask_to_join = self.page.get_by_role(
#                     "button",
#                     name=re.compile("Ask to join", re.IGNORECASE)
#                 )
#                 if ask_to_join.count() > 0:
#                     join_btn = ask_to_join
#                     is_ask_to_join = True
#                     logger.info("Found 'Ask to join' button (waiting room)")
#             except:
#                 pass

#             # Method 2: Look for "Join now" specifically (direct join)
#             if not join_btn:
#                 try:
#                     join_now = self.page.get_by_role(
#                         "button",
#                         name=re.compile("Join now", re.IGNORECASE)
#                     )
#                     if join_now.count() > 0:
#                         join_btn = join_now
#                         is_ask_to_join = False
#                         logger.info("Found 'Join now' button (direct join)")
#                 except:
#                     pass

#             # Method 3: Fallback - look for any button with "Join" in text
#             if not join_btn:
#                 try:
#                     all_join_buttons = self.page.get_by_role(
#                         "button",
#                         name=re.compile(r"\bJoin\b", re.IGNORECASE)  # Word boundary for "Join"
#                     )
#                     if all_join_buttons.count() > 0:
#                         # Use the first visible one
#                         for i in range(all_join_buttons.count()):
#                             btn = all_join_buttons.nth(i)
#                             if btn.is_visible():
#                                 join_btn = btn
#                                 is_ask_to_join = "ask" in btn.inner_text().lower()
#                                 logger.info(f"Found fallback join button: '{btn.inner_text()}'")
#                                 break
#                 except:
#                     pass

#             # Check if we found a join button
#             if not join_btn:
#                 logger.error("No join button found! Meeting might be in different state")
#                 try:
#                     self.page.screenshot(path=f"debug_no_join_btn_{self.page.url.split('/')[-1]}.png")
#                     logger.info("Saved debug screenshot")
#                 except:
#                     pass
#                 return False

#             # Check if it's "Ask to join" (Waiting room) or "Join now"
#             btn_text = join_btn.inner_text()
#             logger.info(f"Join button text: '{btn_text}', is_ask_to_join: {is_ask_to_join}")

#             logger.info("Join button found, clicking...")
#             time.sleep(random.uniform(1, 2))  # Random delay before clicking join
#             join_btn.click()
#             logger.info("Pressed Join btn")

#             if is_ask_to_join:
#                 logger.info("Bot is in waiting room. Waiting to be admitted...")
#                 # Wait up to 5 minutes to be admitted
#                 wait_start = time.time()
#                 iteration = 0
#                 while time.time() - wait_start < 300:
#                     iteration += 1
#                     logger.debug(f"Waiting room check #{iteration}, elapsed: {int(time.time() - wait_start)}s")
#                     # Check if we got rejected
#                     if self.page.get_by_text(
#                         re.compile(
#                             r"You Can't Join this meeting|You can't join this video call|Someone denied your request",
#                             re.IGNORECASE,
#                         )
#                     ).is_visible():
#                         logger.error("Join request was denied or meeting is blocked.")
#                         return False

#                     # Check if we are in meeting (reliable indicators)
#                     in_meeting = False

#                     # Method 1: Check for waiting room specific elements first
#                     try:
#                         waiting_indicators = [
#                             "Please wait until a meeting host brings you into the call",
#                             "Waiting to be admitted",
#                             "Someone will let you in soon",
#                             "Your request to join has been sent",
#                             "Waiting for host to admit you"
#                         ]

#                         for indicator in waiting_indicators:
#                             if self.page.get_by_text(re.compile(indicator, re.IGNORECASE)).is_visible():
#                                 logger.info(f"Still in waiting room - found: '{indicator}'")
#                                 in_meeting = False
#                                 break
#                     except:
#                         pass

#                     # Method 2: Look for participant count/people account (only appears in actual meeting)
#                     if not in_meeting:
#                         try:
#                             # Use the same locators as detect_end for consistency
#                             count = -1
#                             locators = [
#                                 ".uGOf1d",
#                                 ".wnPUne",
#                                 "button[aria-label*='everyone']",
#                                 "[data-participant-count]",
#                                 "[data-avatar-count]",
#                             ]

#                             for selector in locators:
#                                 elements = self.page.locator(selector)
#                                 if elements.count() > 0:
#                                     # Look at the first visible one
#                                     text = elements.first.inner_text().strip()
#                                     match = re.search(r"\d+", text)
#                                     if match:
#                                         count = int(match.group())
#                                         logger.info(f"Found participant count: {count} from selector '{selector}'")
#                                         break

#                             # Fallback: Count participant tiles (more reliable for actual meeting)
#                             if count == -1:
#                                 tiles = self.page.locator("div[data-participant-id]")
#                                 if tiles.count() > 0:
#                                     count = tiles.count()
#                                     logger.info(f"Found participant tiles: {count}")

#                             # If we have 2+ participants, we're definitely in the meeting
#                             if count > 1:
#                                 in_meeting = True
#                                 logger.info(f"Confirmed in meeting - {count} participants detected!")
#                             elif count == 1:
#                                 logger.info("Only 1 participant detected - might still be in waiting room or alone")
#                         except Exception as e:
#                             logger.debug(f"Error checking participant count: {e}")

#                     # Method 3: Additional verification - look for meeting toolbar (only in actual meeting)
#                     if not in_meeting:
#                         try:
#                             toolbar = self.page.locator(".uGOf1d, .wnPUne, [data-meeting-controls]")
#                             if toolbar.count() > 0 and toolbar.first.is_visible():
#                                 logger.info("Found meeting toolbar - likely in actual meeting")
#                                 # Don't set in_meeting=True yet, need participant confirmation
#                         except:
#                             pass

#                     if in_meeting:
#                         logger.info("Successfully admitted from waiting room!")
#                         return True

#                     time.sleep(2)

#                 logger.error("Timed out waiting in lobby to be admitted.")
#                 # Take final screenshot for debugging
#                 try:
#                     self.page.screenshot(path=f"debug_waiting_room_timeout_{self.page.url.split('/')[-1]}.png")
#                     logger.info("Saved debug screenshot of waiting room timeout")
#                 except:
#                     pass
#                 return False
#             else:
#                 # Join now - should be in meeting immediately
#                 time.sleep(3)
#                 logger.info("Joined meeting directly (no waiting room)")
#                 return True

#             return True

#         except Exception as e:
#             if self.page.get_by_text(
#                 re.compile(
#                     r"You Can't Join this meeting|You can't join this video call",
#                     re.IGNORECASE,
#                 )
#             ).is_visible():
#                 logger.error(
#                     "Bot got redirected to the You can't join this meeting page"
#                 )
#                 return False
#             logger.warning(f" The type of error = {type(e)}")
#             logger.error(f"Google Meet specific Error = {e}")
#             return False

#     def detect_end(self, gracePeriod=60, waitingPeriod=180):
#         try:
#             # Check if bot is still in waiting room
#             waiting_indicators = [
#                 "Please wait until a meeting host brings you into the call",
#                 "Waiting to be admitted",
#                 "Someone will let you in soon",
#                 "Your request to join has been sent",
#                 "Waiting for host to admit you"
#             ]

#             in_waiting = False
#             for indicator in waiting_indicators:
#                 if self.page.get_by_text(re.compile(indicator, re.IGNORECASE)).is_visible():
#                     in_waiting = True
#                     break

#             if in_waiting:
#                 # Check if we've been waiting too long
#                 if not hasattr(self, '_waiting_start'):
#                     self._waiting_start = time.time()
#                     logger.info(f"Bot is in waiting room, starting {waitingPeriod}s waiting period...")

#                 elapsed = time.time() - self._waiting_start
#                 if elapsed < waitingPeriod:
#                     logger.info(f"Still in waiting room ({int(elapsed)}s elapsed), staying...")
#                     return False
#                 else:
#                     logger.info(f"Waiting period expired ({int(elapsed)}s), leaving meeting")
#                     return True

#             # Reset waiting timer if not in waiting room
#             if hasattr(self, '_waiting_start'):
#                 delattr(self, '_waiting_start')

#             # Check if host ended meeting
#             if self.page.get_by_text(
#                 re.compile(
#                     r"You've been removed|The meeting has ended|You left the meeting",
#                     re.IGNORECASE,
#                 )
#             ).is_visible():
#                 logger.info("Meeting ended or bot was removed.")
#                 return True

#             # Attempt to find the participant count indicator
#             count = -1
#             locators = [
#                 ".uGOf1d",
#                 ".wnPUne",
#                 "button[aria-label*='everyone']",
#                 "[data-participant-count]",
#                 "[data-avatar-count]",
#             ]

#             for selector in locators:
#                 elements = self.page.locator(selector)
#                 if elements.count() > 0:
#                     # Look at the first visible one
#                     text = elements.first.inner_text().strip()
#                     match = re.search(r"\d+", text)
#                     if match:
#                         count = int(match.group())
#                         break

#             if count == -1:
#                 # Fallback: Count participant tiles
#                 tiles = self.page.locator("div[data-participant-id]")
#                 if tiles.count() > 0:
#                     count = tiles.count()
#                 else:
#                     return False

#             # If there are 2 or more people, stay in meeting
#             if count > 1:
#                 return False

#             # If exactly 1 person (the bot), start grace period
#             logger.info(
#                 f"Bot is alone ({count} participant), starting {gracePeriod}s grace period..."
#             )
#             start = time.time()

#             while time.time() - start < gracePeriod:
#                 if self.page.get_by_text(
#                     re.compile(
#                         r"You've been removed|The meeting has ended", re.IGNORECASE
#                     )
#                 ).is_visible():
#                     return True

#                 current_count = -1
#                 for selector in locators:
#                     elements = self.page.locator(selector)
#                     if elements.count() > 0:
#                         text = elements.first.inner_text().strip()
#                         match = re.search(r"\d+", text)
#                         if match:
#                             current_count = int(match.group())
#                             break

#                 if current_count == -1:
#                     tiles = self.page.locator("div[data-participant-id]")
#                     if tiles.count() > 0:
#                         current_count = tiles.count()

#                 if current_count > 1:
#                     logger.info(
#                         f"Someone joined during grace period ({current_count} participants) - staying"
#                     )
#                     return False

#                 time.sleep(2)

#             logger.info("Grace period expired - leaving meeting")
#             return True

#         except Exception as e:
#             logger.warning(f"Error checking meeting end: {e}")
#             return False


import logging
import time
import re
import random

from app.helper.decorators import retry
from app.helper.logger import get_logger

logger = get_logger(__name__)


class Meet:
    def __init__(self, url, page):
        self.url = url
        self.page = page
        self._waiting_start = None  # tracks when we entered the waiting room
        logger.info(f"Google Meet handler initialized for URL: {url}")

    @retry(times=3, delay=5)
    def join(self):
        logger.info("Handling Google Meet joining ...")

        try:
            self.page.goto(self.url)
            self.page.wait_for_load_state("networkidle")
            logger.info("Page loaded successfully")

            time.sleep(random.uniform(2, 5))

            # Fast fail — blocked immediately
            if self._is_blocked():
                logger.error("Bot blocked by Google Meet immediately")
                return False

            # Dismiss AV prompt if present
            try:
                no_av = self.page.get_by_role(
                    "button",
                    name=re.compile(
                        "Continue without microphone and camera", re.IGNORECASE
                    ),
                )
                no_av.wait_for(state="visible", timeout=5000)
                no_av.click()
                logger.info("Clicked 'Continue without microphone and camera'")
            except Exception:
                logger.info("No AV prompt — proceeding")

            # Fill name
            name = self.page.locator(
                "input[type='text'], input[placeholder='Your name']"
            ).first
            if name.count() == 0:
                logger.error("Name input not found")
                self._screenshot("meet_no_name_input")
                return False
            name.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(1, 3))
            name.fill("Meeting Bot")
            logger.info("Filled name")

            # Dismiss popups
            try:
                got_it = self.page.get_by_role(
                    "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
                )
                if got_it.count() > 0 and got_it.first.is_visible(timeout=2000):
                    got_it.first.click()
                    logger.info("Dismissed popup")
            except Exception:
                pass

            time.sleep(random.uniform(2, 4))

            # Find join button
            join_btn, is_ask_to_join = self._find_join_button()
            if not join_btn:
                logger.error("No join button found")
                self._screenshot("meet_no_join_btn")
                return False

            logger.info(f"Clicking join button — is_ask_to_join: {is_ask_to_join}")
            time.sleep(random.uniform(1, 2))
            join_btn.click()
            logger.info("Clicked join button")

            if is_ask_to_join:
                # Don't loop here — detect_end owns the waiting room timeout.
                # Just mark that we're in the waiting room and return True
                # so BaseBot proceeds to detect_meeting_end polling.
                self._waiting_start = time.time()
                logger.info(
                    "Bot sent join request — in waiting room, detect_end will manage timeout"
                )
                time.sleep(2)
                return True
            else:
                time.sleep(3)
                logger.info("Joined meeting directly (no waiting room)")
                return True

        except Exception as e:
            if self._is_blocked():
                logger.error("Bot redirected to blocked page")
                return False
            logger.error(f"Google Meet join error: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # End detection
    # ------------------------------------------------------------------

    def detect_end(self, gracePeriod=60, waitingPeriod=180) -> bool:
        try:
            # Get participant count first — used by both waiting room
            # and in-meeting logic below
            count = self._get_participant_count()

            # --- Waiting room check ---
            if self._is_in_waiting_room():
                if self._waiting_start is None:
                    self._waiting_start = time.time()
                    logger.info(
                        f"Entered waiting room, {waitingPeriod}s timeout started"
                    )

                # Check if we've been admitted — participant count > 1
                if count > 1:
                    logger.info(
                        f"Admitted from waiting room ({count} participants detected)"
                    )
                    self._waiting_start = None
                    return False  # stay in meeting

                elapsed = time.time() - self._waiting_start
                if elapsed < waitingPeriod:
                    logger.info(
                        f"Waiting room: {int(elapsed)}s elapsed of {waitingPeriod}s"
                    )
                    return False
                else:
                    logger.info(f"Waiting room timeout ({int(elapsed)}s) — leaving")
                    return True

            # Not in waiting room — clear the timer
            self._waiting_start = None

            # --- Host ended or bot removed ---
            if self.page.get_by_text(
                re.compile(
                    r"You've been removed|The meeting has ended|You left the meeting",
                    re.IGNORECASE,
                )
            ).is_visible():
                logger.info("Meeting ended or bot was removed")
                return True

            # --- Participant count check ---
            if count == -1:
                return False  # can't determine, stay

            if count > 1:
                return False  # others present, stay

            # --- Bot is alone — grace period ---
            logger.info(
                f"Bot is alone ({count} participant), starting {gracePeriod}s grace period"
            )
            start = time.time()

            while time.time() - start < gracePeriod:
                if self.page.get_by_text(
                    re.compile(
                        r"You've been removed|The meeting has ended", re.IGNORECASE
                    )
                ).is_visible():
                    return True

                current = self._get_participant_count()
                if current > 1:
                    logger.info(
                        f"Someone joined during grace period ({current} participants) — staying"
                    )
                    return False

                time.sleep(2)

            logger.info("Grace period expired — leaving")
            return True

        except Exception as e:
            logger.warning(f"detect_end error: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_join_button(self):
        """Find the join button and determine if it's a waiting room request."""
        # Try Ask to join first (waiting room)
        try:
            btn = self.page.get_by_role(
                "button", name=re.compile("Ask to join", re.IGNORECASE)
            )
            if btn.count() > 0 and btn.first.is_visible():
                return btn.first, True
        except Exception:
            pass

        # Try Join now (direct)
        try:
            btn = self.page.get_by_role(
                "button", name=re.compile("Join now", re.IGNORECASE)
            )
            if btn.count() > 0 and btn.first.is_visible():
                return btn.first, False
        except Exception:
            pass

        # Fallback — any visible button with "Join"
        try:
            btns = self.page.get_by_role(
                "button", name=re.compile(r"\bJoin\b", re.IGNORECASE)
            )
            for i in range(btns.count()):
                btn = btns.nth(i)
                if btn.is_visible():
                    is_ask = "ask" in btn.inner_text().lower()
                    logger.info(f"Fallback join button: '{btn.inner_text()}'")
                    return btn, is_ask
        except Exception:
            pass

        return None, False

    def _get_participant_count(self) -> int:
        """Return participant count, or -1 if undetermined."""
        locators = [
            ".uGOf1d",
            ".wnPUne",
            "button[aria-label*='everyone']",
            "[data-participant-count]",
            "[data-avatar-count]",
        ]
        for selector in locators:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    text = elements.first.inner_text().strip()
                    match = re.search(r"\d+", text)
                    if match:
                        return int(match.group())
            except Exception:
                continue

        # Fallback: participant tiles
        try:
            tiles = self.page.locator("div[data-participant-id]")
            if tiles.count() > 0:
                return tiles.count()
        except Exception:
            pass

        return -1

    def _is_in_waiting_room(self) -> bool:
        """Return True if the waiting room UI is currently visible."""
        indicators = [
            "Please wait until a meeting host brings you into the call",
            "Waiting to be admitted",
            "Someone will let you in soon",
            "Your request to join has been sent",
            "Waiting for host to admit you",
        ]
        for indicator in indicators:
            try:
                if self.page.get_by_text(
                    re.compile(indicator, re.IGNORECASE)
                ).is_visible():
                    return True
            except Exception:
                continue
        return False

    def _is_blocked(self) -> bool:
        """Return True if Google Meet blocked the bot."""
        try:
            return self.page.get_by_text(
                re.compile(
                    r"You Can't Join this video call|You can't join this call",
                    re.IGNORECASE,
                )
            ).is_visible()
        except Exception:
            return False

    def _screenshot(self, label: str):
        """Save a debug screenshot."""
        import os

        try:
            os.makedirs("/tmp/debug", exist_ok=True)
            path = f"/tmp/debug/{label}_{int(time.time())}.png"
            self.page.screenshot(path=path, full_page=True)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
