import os
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


class AudioRecorder:

    def __init__(self, output_path):
        self.output_path = output_path
        self.ffmpeg_process = None
        self.is_recording = False

    def start(self):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            system = platform.system()

            if system == "Windows":
                audio_input = "Microphone (Realtek(R) Audio)"
                ffmpeg_input_format = "dshow"
            # elif system == "Darwin":
            #     audio_input = ":0"
            #     ffmpeg_input_format = "avfoundation"
            # else:
            #     audio_input = "default"
            #     ffmpeg_input_format = "pulse"

            cmd = f'ffmpeg -f {ffmpeg_input_format} -i audio="{audio_input}" -acodec libmp3lame -q:a 5 -y "{self.output_path}"'

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=True,
            )

            logger.info(f" Starting FFmpeg recording with command = {cmd}")

            self.is_recording = True
            logger.info(f" Recording audio at path = {self.output_path}")
            return True

        except Exception as e:
            logger.error(f" Error in recording audio = {e}")
            return False

    def stop(self):
        if not self.is_active():
            logger.info("Recording is already inactive")
            return True

        try:
            self.is_recording = False

            try:
                self.ffmpeg_process.stdin.write(b"q")
                self.ffmpeg_process.stdin.flush()

                logger.info("Sent the q command to Ffmpeg")

                self.ffmpeg_process.wait(timeout=5)
                logger.info("Stopped recording normally with out any complications")
                return True

            except subprocess.TimeoutExpired:
                logger.warning(
                    "Recording didn't stopped normally, terminating the process"
                )

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
                    return True
        except Exception as e:
            logger.warning(f"Recording failed to stop due to error = {e}")
            return False

    def is_active(self):

        if not self.ffmpeg_process:
            return False

        return self.is_recording and self.ffmpeg_process.poll() is None
