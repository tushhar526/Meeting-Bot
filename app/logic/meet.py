import logging
import re
import time
from app.helper.decorators import retry

logger = logging.getLogger(__name__)


class Meet:
    def __init__(self, url, page):
        self.url = url
        self.page = page

    @retry(times=3, delay=5)
    def join(self):
        logger.info("Handling Google meet's meeting join ...")

        self.page.goto(self.url)

        self.page.wait_for_load_state("networkidle")

        try:

            time.sleep(5)

            import re

            # Fast fail check: Did Google block us immediately?
            if self.page.get_by_text(
                re.compile(
                    r"You Can't Join this meeting|You can't join this call",
                    re.IGNORECASE,
                )
            ).is_visible():
                logger.error(
                    "Bot got completely blocked by Google Meet immediately upon loading."
                )
                return False

            logger.info("Checking for 'Continue without microphone and camera' button")

            try:
                no_av = self.page.get_by_role(
                    "button",
                    name=re.compile(
                        "Continue without microphone and camera", re.IGNORECASE
                    ),
                )

                # Use a shorter timeout since this button doesn't always appear
                no_av.wait_for(state="visible", timeout=5000)
                no_av.click()
                logger.info("Clicked 'Continue without microphone and camera'")
            except Exception as e:
                logger.info(
                    "No 'Continue without microphone and camera' button found or needed. Proceeding..."
                )

            logger.info("Finding the name input tag")
            name = self.page.locator("input[placeholder = 'Your name']")
            time.sleep(2)
            name.fill("Meeting Bot")
            logger.info("Entered name Meeting bot")

            logger.info("Closing any 'Got it' or 'Dismiss' popups if present")
            try:
                got_it_btn = self.page.get_by_role(
                    "button", name=re.compile("Got it|Dismiss|Close", re.IGNORECASE)
                )
                if got_it_btn.count() > 0 and got_it_btn.first.is_visible(timeout=2000):
                    got_it_btn.first.click()
                    logger.info("Dismissed popup")
            except Exception as e:
                logger.info(f"No popup to dismiss: {e}")

            logger.info("Finding the joining button")
            time.sleep(3)
            join_btn = self.page.get_by_role(
                "button", name=re.compile("Join now|Ask to join")
            )

            # Check if it's "Ask to join" (Waiting room) or "Join now"
            is_ask_to_join = "ask to join" in join_btn.inner_text().lower()

            logger.info("Taking screenshot before clicking join...")
            self.page.screenshot(path="before_join.png")

            join_btn.click()
            logger.info("Pressed the Join btn")

            time.sleep(2)
            logger.info("Taking screenshot after clicking join...")
            self.page.screenshot(path="after_join.png")

            if is_ask_to_join:
                logger.info("Bot is in the waiting room. Waiting to be admitted...")
                # Wait up to 5 minutes to be admitted
                wait_start = time.time()
                while time.time() - wait_start < 300:
                    # Check if we got rejected
                    if self.page.get_by_text(
                        re.compile(
                            r"You Can't Join this meeting|You can't join this call|Someone denied your request",
                            re.IGNORECASE,
                        )
                    ).is_visible():
                        logger.error("Join request was denied or meeting is blocked.")
                        return False

                    # Check if we are in the meeting
                    participant_icon = self.page.locator("[data-avatar-count]")
                    if participant_icon.count() > 0:
                        logger.info("Successfully admitted from the waiting room!")
                        return True

                    time.sleep(2)

                logger.error("Timed out waiting in the lobby to be admitted.")
                return False

            return True

        except Exception as e:
            if self.page.get_by_text(
                re.compile(
                    r"You Can't Join this meeting|You can't join this call",
                    re.IGNORECASE,
                )
            ).is_visible():
                logger.error(
                    "Bot got redirected to the You can't join this meeting page"
                )
                return False
            logger.warning(f" The type of error = {type(e)}")
            logger.error(f"Google Meet specific Error = {e}")
            return False

    def detect_end(self, gracePeriod=60):
        try:
            # Check if host ended meeting
            if self.page.get_by_text(
                re.compile(
                    r"You've been removed|The meeting has ended|You left the meeting",
                    re.IGNORECASE,
                )
            ).is_visible():
                logger.info("Meeting ended or bot was removed.")
                return True

            # Attempt to find the participant count indicator
            count = -1
            locators = [
                ".uGOf1d",
                ".wnPUne",
                "button[aria-label*='everyone']",
                "[data-participant-count]",
                "[data-avatar-count]",
            ]

            for selector in locators:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    # Look at the first visible one
                    text = elements.first.inner_text().strip()
                    match = re.search(r"\d+", text)
                    if match:
                        count = int(match.group())
                        break

            if count == -1:
                # Fallback: Count participant tiles
                tiles = self.page.locator("div[data-participant-id]")
                if tiles.count() > 0:
                    count = tiles.count()
                else:
                    return False

            # If there are 2 or more people, stay in meeting
            if count > 1:
                return False

            # If exactly 1 person (the bot), start grace period
            logger.info(
                f"Bot is alone ({count} participant), starting {gracePeriod}s grace period..."
            )
            start = time.time()

            while time.time() - start < gracePeriod:
                if self.page.get_by_text(
                    re.compile(
                        r"You've been removed|The meeting has ended", re.IGNORECASE
                    )
                ).is_visible():
                    return True

                current_count = -1
                for selector in locators:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        text = elements.first.inner_text().strip()
                        match = re.search(r"\d+", text)
                        if match:
                            current_count = int(match.group())
                            break

                if current_count == -1:
                    tiles = self.page.locator("div[data-participant-id]")
                    if tiles.count() > 0:
                        current_count = tiles.count()

                if current_count > 1:
                    logger.info(
                        f"Someone joined during grace period ({current_count} participants) - staying"
                    )
                    return False

                time.sleep(2)

            logger.info("Grace period expired - leaving meeting")
            return True

        except Exception as e:
            logger.warning(f"Error checking meeting end: {e}")
            return False


# def detect_end(self, grace_period=60) -> bool:
#     try:
#         # Check if host ended meeting or bot was removed
#         if self._is_meeting_over():
#             logger.info("Meeting ended or bot was removed")
#             return True

#         count = self._get_participant_count()

#         if count is None:
#             logger.warning("Could not read participant count — staying to be safe")
#             return False

#         if count > 1:
#             return False

#         # Bot is alone — start grace period
#         logger.info(f"Bot is alone ({count} participant), starting {grace_period}s grace period...")
#         start = time.time()

#         while time.time() - start < grace_period:
#             if self._is_meeting_over():
#                 logger.info("Meeting ended during grace period")
#                 return True

#             count = self._get_participant_count()

#             if count is None:
#                 time.sleep(2)
#                 continue

#             if count > 1:
#                 logger.info(f"Someone joined during grace period ({count} participants) — staying")
#                 return False

#             time.sleep(2)

#         logger.info("Grace period expired — leaving meeting")
#         return True

#     except Exception as e:
#         logger.warning(f"Error in detect_end: {e}")
#         return False


# def _is_meeting_over(self) -> bool:
#     """Returns True if Meet shows an end/removal screen."""
#     try:
#         return self.page.get_by_text(
#             re.compile(
#                 r"You've been removed|The meeting has ended|You left the meeting",
#                 re.IGNORECASE,
#             )
#         ).count() > 0   # count() not is_visible() — more reliable
#     except:
#         return False


# def _get_participant_count(self):
#     """
#     Returns participant count as int, or None if unreadable.
#     Google Meet shows count in [data-avatar-count] attribute.
#     """
#     try:
#         participant = self.page.locator("[data-avatar-count]")
#         if participant.count() == 0:
#             return None
#         return int(participant.first.inner_text().strip())
#     except:
#         return None
