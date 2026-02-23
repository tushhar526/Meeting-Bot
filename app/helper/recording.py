import os
import logging
import subprocess
import time

logger = logging.getLogger(__name__)


class PulseAudio:

    def __init__(self, job_id):
        self.job_id = job_id
        self.sink_name = f"sink_{self.job_id}"
        self.module_id = None

    def create_sink(self):
        try:
            result = subprocess.Popen(
                [
                    "pactl",
                    "load-module",
                    "module-null-sink",
                    f"sink_name={self.sink_name}",
                    f'sink_properties=device.description="Meeting_{self.job_id}"',
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

    def __init__(self, job, output_path):
        self.output_path = output_path
        self.ffmpeg_process = None
        self.pulse_audio = PulseAudio(job.job_id)
        self.monitor_device = None
        self.is_recording = False

    def prepare_sink(self):
        if not self.pulse_audio.create_sink():
            return False
        return True

    def wait_for_chromium_audio(self, timeout=60):
        start = time.time()

        while time.time() - start < timeout:
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"],
                capture_output=True,
                text=True,
            )

            if self.get_sink_name in result.stdout or "Chromium" in result.stdout:
                logger.info("Chromium audio stream detected")
                return True

            time.sleep(1)

        return False

    def start(self):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            self.monitor_device = self.pulse_audio.get_moniter()

            if not self.monitor_device:
                logger.error("Failed to get moniter")
                return False

            logger.info("Waiting for Chromium audio stream...")
            if not self.wait_for_chromium_audio():
                logger.error("Chromium never produced audio")
                return False

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

            cmd = [
                "ffmpeg",
                "-f",
                "pulse",
                "-i",
                self.monitor_device,
                "-ac","2",
                "-c:a",
                "libmp3lame",
                "-q:a","5",
                "-y",
                self.output_path,
            ]

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(f" Starting FFmpeg recording with command = {cmd}")

            self.is_recording = True
            logger.info(f" Recording audio at path = {self.output_path}")
            return True

        except Exception as e:
            logger.error(f" Error in recording audio = {e}")
            return False

    def stop(self):
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
                logger.warning(
                    "Couldn't terminate the process, killing the Ffmpeg process as a last resort"
                )

                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
                logger.info("Recording process killed successfully")

            finally:
                time.sleep(2)
                try:
                    self.pulse_audio.delete_sink()
                except Exception as e:
                    logger.error(f"Couldn't delete sink due to {e}")
                self.ffmpeg_process = None

            return True

        except Exception as e:
            logger.warning(f"Recording failed to stop due to error = {e}")
            return False

    @property
    def get_sink_name(self):
        return self.pulse_audio.sink_name
