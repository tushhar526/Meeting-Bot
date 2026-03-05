import logging
import time
import re
from app.helper.decorators import retry

logger = logging.getLogger(__name__)


class Teams:
    def __init__(self, url, page):
        self.url = url
        self.page = page

    # @retry(times=3, delay=5)
    # def join(self):
    #     logger.info("Handling Teams meeting join ...")

    #     self.page.goto(self.url)

    #     steps = [
    #         self._step_continue_on_browser,
    #         self._step_no_av,
    #         self._step_fill_name,
    #         self._step_join_now,
    #     ]

    #     for step in steps:
    #         try:
    #             step()
    #         except Exception as e:
    #             logger.warning(f"Step {step.__name__} failed or was skipped: {e}")
    #             # non-fatal — some steps may not appear depending on Teams version

    #     # Final check — if we're still on the pre-join page, something went wrong
    #     if self.page.locator("button[data-focus-target='gum-continue']").is_visible():
    #         logger.error("Still on pre-join screen after all steps — join failed")
    #         self.page.screenshot(
    #             path=f"/tmp/debug/teams_fail_{self.job_id}.png", full_page=True
    #         )
    #         return False

    #     logger.info("Join sequence completed successfully")
    #     return True
    def join(self):
        logger.info("Handling Teams meeting join ...")

        # Block Teams from redirecting to light experience
        # self.page.route(
        #     "**/light-meetings/launch**",
        #     lambda route: route.fulfill(status=302, headers={"Location": self.url}),
        # )

        self.page.goto(self.url)

        steps = [
            self._step_continue_on_browser,
            self._step_no_av,
            self._step_fill_name,
            self._step_join_now,
        ]

        for step in steps:
            try:
                step()
            except Exception as e:
                logger.warning(f"Step {step.__name__} failed or was skipped: {e}")

        # Final check — confirm we're past the pre-join screen
        # Final check — wait to get past pre-join/lobby into the actual meeting
        try:
            # roster-button only appears inside the actual meeting
            self.page.locator("#roster-button").wait_for(
                state="visible", timeout=120000
            )  # 2 min for host to admit
            logger.info("Join sequence completed successfully")
            return True
        except Exception as e:
            logger.error(f"Never made it into the meeting — {e}")
            self.page.screenshot(path=f"/tmp/debug/teams_fail.png", full_page=True)
            return False

    def _step_continue_on_browser(self):
        """
        Optional step — only appears sometimes depending on
        how Teams loads. Skipped silently if not present.
        """
        btn = self.page.locator(
            "button:has-text('Continue on this browser'), "
            "button[data-tid='joinOnWeb']"
        ).first

        try:
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            logger.info("Clicked 'Continue on this browser'")
        except:
            logger.info("No 'Continue on this browser' button — skipping")

    def _step_no_av(self):
        """Turn off camera and mic — works on both pre-join and lobby screens."""

        # Wait for either the AV controls to appear (pre-join or lobby)
        try:
            self.page.wait_for_selector(
                "button[data-tid='video-flyout-open-button'], "
                "button[data-inp='video-button']",
                timeout=30000,
            )
            logger.info("AV controls detected")
        except Exception as e:
            logger.warning(f"AV controls not found — skipping: {e}")
            return

        # Turn off camera toggle (the blue switch)
        try:
            cam_toggle = self.page.get_by_role("switch").first
            if cam_toggle.is_checked():
                cam_toggle.click()
                logger.info("Camera turned off")
            else:
                logger.info("Camera already off")
        except Exception as e:
            logger.warning(f"Could not turn off camera: {e}")

        # Select "Don't use audio"
        try:
            dont_use_audio = self.page.locator('text="Don\'t use audio"')
            dont_use_audio.wait_for(state="visible", timeout=5000)
            dont_use_audio.click()
            logger.info("Selected 'Don't use audio'")
        except Exception as e:
            logger.warning(f"Could not select 'Don't use audio': {e}")

    def _step_fill_name(self):
        """Fill in the bot name."""
        name_input = self.page.locator(
            "input[placeholder='Type your name'], "
            "input[aria-label*='name' i], "  # case insensitive
            "input[type='text']"
        ).first
        name_input.wait_for(state="visible", timeout=10000)
        name_input.fill("Meeting Bot")
        logger.info("Filled name")

    def _step_join_now(self):
        """Click the final join button."""
        join_btn = self.page.get_by_role(
            "button", name=re.compile("Join now", re.IGNORECASE)
        )
        join_btn.wait_for(state="visible", timeout=10000)
        join_btn.click()
        logger.info("Clicked Join now")  # def join(self):

    # def join_diagnostic(self):
    #     # """Run this temporarily to see exactly what Teams renders now"""

    #     self.page.goto(self.url)
    #     self.page.wait_for_load_state("networkidle")

    #     # Wait a bit extra for JS to render
    #     self.page.wait_for_timeout(5000)

    #     # Take screenshot
    #     self.page.screenshot(path=f"/tmp/debug/teams_diag_.png", full_page=True)
    #     logger.info(f"Screenshot saved: /tmp/debug/teams_diag.png")

    #     # Log full URL after redirects
    #     logger.info(f"Final URL: {self.page.url}")

    #     # Check for every selector we care about
    #     selectors = {
    #         "Continue on this browser (text)": "button:has-text('Continue on this browser')",
    #         "joinOnWeb (data-tid)": "button[data-tid='joinOnWeb']",
    #         "gum-continue (no AV)": "button[data-focus-target='gum-continue']",
    #         "name input (placeholder)": "input[placeholder='Type your name']",
    #         "name input (type=text)": "input[type='text']",
    #         "Join now button": "button:has-text('Join now')",
    #         "prejoin-join-button": "button[data-tid='prejoin-join-button']",
    #         "loading screen still visible": "#loading-screen",
    #         "light experience marker": "[class*='prejoin']",
    #     }

    #     for label, selector in selectors.items():
    #         try:
    #             count = self.page.locator(selector).count()
    #             visible = (
    #                 self.page.locator(selector).first.is_visible()
    #                 if count > 0
    #                 else False
    #             )
    #             logger.info(f"  [{label}] count={count}, visible={visible}")
    #         except Exception as e:
    #             logger.info(f"  [{label}] ERROR: {e}")

    #     # Dump all buttons on page
    #     buttons = self.page.locator("button").all()
    #     logger.info(f"All buttons on page ({len(buttons)} total):")
    #     for btn in buttons:
    #         try:
    #             logger.info(
    #                 f"  button | text='{btn.inner_text().strip()}' | aria-label='{btn.get_attribute('aria-label')}' | data-tid='{btn.get_attribute('data-tid')}'"
    #             )
    #         except:
    #             pass

    def host_end_screen(self):
        try:
            # Checks if the meeting was ended by the host or the bot was kicked
            return self.page.get_by_text(
                re.compile(
                    "Enjoy your call? Join Teams today for free|Did you leave by mistake?"
                )
            ).is_visible()
        except:
            return False

    def detect_end(self, grace_period=60) -> bool:

        try:
            roster_btn = self.page.locator("#roster-button")
            # logger.info(f"Roster button HTML: {roster_btn.inner_html()}")
        except Exception as e:
            logger.warning(f"Could not read roster button: {e}")

        if self._is_someone_in_meeting():
            return False

        # Active participants in meeting — stay
        if self._is_someone_in_meeting():
            return False

        # Someone waiting in lobby — stay
        if self._is_someone_in_lobby():
            return False

        # Host ended the meeting — leave immediately
        if self.host_end_screen():
            logger.info("Host ended the meeting")
            return True

        # Bot is alone — grace period
        logger.info(f"Bot is alone, starting {grace_period}s grace period...")
        start_time = time.time()

        while time.time() - start_time < grace_period:
            try:
                if self._is_someone_in_meeting():
                    logger.info("Someone joined during grace period — staying")
                    return False

                if self._is_someone_in_lobby():
                    logger.info("Someone in lobby during grace period — staying")
                    return False

                if self.host_end_screen():
                    logger.info("Host ended meeting during grace period")
                    return True

            except Exception as e:
                logger.warning(f"Error during grace period check: {e}")

            time.sleep(2)

        logger.info("Grace period expired — leaving")
        return True

    def _is_someone_in_meeting(self) -> bool:
        """toolbar-item-badge appears when there are 2+ people in the meeting"""
        try:
            return self.page.locator('[data-tid="toolbar-item-badge"]').count() > 0
        except:
            return False

    def _is_someone_in_lobby(self) -> bool:
        """roster-button-badge appears when someone is waiting to join"""
        try:
            return self.page.locator('[data-tid="roster-button-badge"]').count() > 0
        except:
            return False
