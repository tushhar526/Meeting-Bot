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
            result = subprocess.run(
                [
                    "pactl",
                    "load-module",
                    "module-null-sink",
                    f"sink_name={self.sink_name}",
                    f'sink_properties = device.description="Meeting_{self.job_id}"',
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(
                    f"Failed to create pulse audio sink due to = {result.stderr}"
                )
                return False

            self.module_id = int(result.stdout.strip())

            logger.info(
                f"Created a pulse audio sink with sink name = {self.sink_name} and with module id = {self.module_id}"
            )
            return True
        except Exception as e:
            logger.error("Error occured in running subprocess")
            return False

    def get_moniter(self):
        try:
            result = subprocess.run(
                ["pactl", "list", "sink"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                logger.error(f"couldn't list pulse audio sinks due to {result.stderr}")
                return None

            lines = result.stdout.split("\n")
            in_traget_sink = False

            for line in lines:
                if f"Name : {self.sink_name}" in line:
                    in_traget_sink = True
                if in_traget_sink and "Moniter Source" in line:
                    moniter_device = line.splite(": ")[1].strip()
                    logger.info(
                        f" Found moniter for sink {self.sink_name} : {moniter_device}"
                    )

                    return moniter_device

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
            result = subprocess.run(
                ["pactl", "unload-module", str(self.module_id)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(
                    f"Couldn't delete the sink named {self.sink_name} due to {result.stderr}"
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
        self.moiter_device = None
        self.is_recording = False

    @property
    def prepare_sink(self):
        if not self.pulse_audio.create_sink():
            return False

        os.environ["PULSE_SINK"] = self.get_sink_name
        return True

    def start(self):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            self.moiter_device = self.pulse_audio.get_moniter()

            if not self.moiter_device:
                logger.error("Failed to get moniter")
                return False

            cmd = f'ffmpeg -f pulse -i {self.moiter_device} -c:a -aac -q:a 5 -y "{self.output_path}"'

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
