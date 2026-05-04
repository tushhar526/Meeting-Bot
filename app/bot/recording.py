import os
import logging
import subprocess
import time

logger = logging.getLogger("RECORDING")


def diagnose_pulse_audio():
    """Diagnose pulse audio setup for debugging recording issues"""
    logger.info("=== PULSE AUDIO DIAGNOSTIC ===")

    try:
        # List all sinks
        result = subprocess.run(
            ["pactl", "list", "sinks", "short"], capture_output=True, text=True
        )
        logger.info(f"Available sinks:\n{result.stdout}")

        # List all sources (including monitors)
        result = subprocess.run(
            ["pactl", "list", "sources", "short"], capture_output=True, text=True
        )
        logger.info(f"Available sources:\n{result.stdout}")

        # Get default sink
        result = subprocess.run(
            ["pactl", "get-default-sink"], capture_output=True, text=True
        )
        logger.info(f"Default sink: {result.stdout.strip()}")

        # Get default source
        result = subprocess.run(
            ["pactl", "get-default-source"], capture_output=True, text=True
        )
        logger.info(f"Default source: {result.stdout.strip()}")

    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")

    logger.info("=== END DIAGNOSTIC ===")


class PulseAudio:

    # 1. init function for setting up self variables
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id
        self.sink_name = f"sink_{self.meeting_id}"
        self.module_id = None

    # 2. creating sink function where sink works as output device
    def create_sink(self):
        try:
            result = subprocess.Popen(
                [
                    "pactl",
                    "load-module",
                    "module-null-sink",
                    f"sink_name={self.sink_name}",
                    f'sink_properties=device.description="Meeting_{self.meeting_id}"',
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = result.communicate()

            if result.returncode != 0:
                logger.error(f"Failed to create pulse audio sink due to = {stderr}")
                return False

            self.module_id = int(stdout.strip())

            logger.info(
                f"Created a pulse audio sink with sink name = {self.sink_name} and with module id = {self.module_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error occured in running subprocess {e}")
            return False

    # 3. Getting the moniter device which works as the input device
    def get_moniter(self):
        try:
            result = subprocess.Popen(
                ["pactl", "list", "sources", "short"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = result.communicate()

            if result.returncode != 0:
                logger.error(f"couldn't list pulse audio sinks due to {stderr}")
                return None

            lines = stdout.split("\n")

            for line in lines:
                if f"{self.sink_name}.monitor" in line:
                    return line.split()[1]

            logger.warning(f"Couldn't Find moniter device for sink {self.sink_name}")
            return None
        except Exception as e:
            logger.error(f"Couldn't find the moniter due to error = {e}")
            return None

    # 4. Deleting sink after the meeting ends.
    def delete_sink(self):
        if not self.module_id:
            logger.warning("No module id present to delete")
            return False
        try:
            result = subprocess.Popen(
                ["pactl", "unload-module", str(self.module_id)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = result.communicate()

            if result.returncode != 0:
                logger.error(
                    f"Couldn't delete the sink named {self.sink_name} due to {stderr}"
                )
                return False

            logger.info(f"sink named {self.sink_name} is deleted")
            return True
        except Exception as e:
            logger.error(f"Couldn't delete the sink due to error = {e}")
            return False
        pass


class AudioRecorder:

    # 1. inti function for Setting up self variable
    def __init__(self, meeting_id, original_path, processed_path):
        self.output_path = original_path
        self.processed_path = processed_path
        self.ffmpeg_process = None
        self.pulse_audio = PulseAudio(meeting_id)
        self.monitor_device = None
        self.is_recording = False
        self.record_log = None

    # 2. Preaparing sink which works as
    def prepare_sink(self):
        if not self.pulse_audio.create_sink():
            return False
        return True

    # Configure sink - unmute and set volume (no global default change)
    def configure_sink(self):
        try:
            sink_name = self.get_sink_name
            logger.info(f"Configuring sink {sink_name}: unmuting and setting volume")
            subprocess.run(
                ["pactl", "set-sink-mute", sink_name, "0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["pactl", "set-sink-volume", sink_name, "100%"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to configure sink: {e}")
            return False

    # 3. Starting the recording process for the meeting
    def start(self):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.processed_path), exist_ok=True)

            # Skip diagnostics to reduce startup delay (enable only for debugging)
            # diagnose_pulse_audio()

            self.monitor_device = self.pulse_audio.get_moniter()

            if not self.monitor_device:
                logger.error("Failed to get moniter")
                return False

            logger.info(f"Using monitor device: {self.monitor_device}")

            # Get current default sink to restore later
            result = subprocess.run(
                ["pactl", "get-default-sink"], capture_output=True, text=True
            )
            original_sink = result.stdout.strip()
            logger.info(f"Original default sink: {original_sink}")

            # IMPORTANT: Move audio output to our sink for recording
            logger.info(f"Setting {self.get_sink_name} as default sink")
            subprocess.run(
                ["pactl", "set-default-sink", self.get_sink_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Unmute and set volume for our sink
            subprocess.run(
                ["pactl", "set-sink-mute", self.get_sink_name, "0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subprocess.run(
                ["pactl", "set-sink-volume", self.get_sink_name, "100%"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(
                f"Starting recording for meeting with meeting id = {self.pulse_audio.meeting_id}",
            )

            cmd = [
                "ffmpeg",
                "-y",
                "-nostdin",
                "-fflags",
                "nobuffer",
                "-flags",
                "low_delay",
                # Input
                "-f",
                "pulse",
                "-i",
                self.monitor_device,
                # Split + process
                "-filter_complex",
                "[0:a]asplit=2[a1][a2];"
                "[a1]highpass=f=200,lowpass=f=3000,dynaudnorm,"
                "aresample=16000,pan=mono|c0=c0[a_proc]",
                # Output 1 → ORIGINAL (for user)
                "-map",
                "[a2]",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                "-ar",
                "44100",
                "-ac",
                "2",
                self.output_path,
                # Output 2 → PROCESSED (for Whisper)
                "-map",
                "[a_proc]",
                "-c:a",
                "pcm_s16le",
                self.processed_path,
            ]

            env = os.environ.copy()
            env["PULSE_LATENCY_MSEC"] = "30"

            self.record_log = open("app.log", "a")

            self.ffmpeg_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=self.record_log, env=env
            )

            logger.info(f" Starting FFmpeg recording with command = {cmd}")

            self.is_recording = True
            logger.info(f" Recording audio at path = {self.output_path}")

            # Store original sink for restoration
            self.original_sink = original_sink
            return True

        except Exception as e:
            logger.error(f" Error in recording audio = {e}")
            return False

    # 4. Stopping the recording after the meeting ends
    def stop(self):

        if not self.record_log:
            self.record_log.close()
            self.record_log = None

        if self.ffmpeg_process is None:

            logger.info("Recording is already inactive")
            return True

        try:
            self.is_recording = False

            self.ffmpeg_process.terminate()

            try:
                self.ffmpeg_process.wait(timeout=5)
                logger.info("Terminated the Ffmpeg Successfully")

            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg did not terminate gracefully, forcing kill")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()

            # IMPORTANT: Restore original audio sink
            if hasattr(self, "original_sink") and self.original_sink:
                logger.info(f"Restoring original sink: {self.original_sink}")
                subprocess.run(
                    ["pactl", "set-default-sink", self.original_sink],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Clean up pulse audio sink
            self.pulse_audio.delete_sink()

            return True

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False

    # 5. To get the sink name.
    @property
    def get_sink_name(self):
        return self.pulse_audio.sink_name

    # To check the stream of sound comming from chrome
    def wait_for_stream(self, timeout=5):
        return self.pulse_audio.sink_name
