import os
import json
import requests
from app.extension import celery, db
from app.models.transcriptionModel import TranscriptionsModel
from app.models.jobModel import get_ist_now
import logging
from requests.exceptions import ConnectionError, Timeout, ChunkedEncodingError
from http.client import IncompleteRead

logger = logging.getLogger(__name__)

HF_API_URL = os.getenv("HF_API_URL")
HF_API_TOKEN = os.getenv("HF_ACCES_TOKEN")


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def transcribe_audio(self, transcription_id):
    """
    Celery task — sends audio to HuggingFace Whisper and saves result.

    Flow:
    1. Fetch transcription row from DB
    2. Validate audio file exists and is large enough
    3. Read audio into memory and send to HuggingFace Whisper API
    4. Save result as JSON to disk
    5. Update TranscriptionsModel with status + metadata
    """
    transcription = TranscriptionsModel.query.filter_by(
        transcription_id=transcription_id
    ).first()

    if not transcription:
        logger.error(f"[Transcription] Row not found: {transcription_id}")
        return {"error": "Transcription not found"}

    # Mark as processing
    transcription.status = "processing"
    transcription.started_at = get_ist_now()
    db.session.commit()

    try:
        audio_path = transcription.job.audio_path
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Guard against broken/empty recordings
        file_size = os.path.getsize(audio_path)
        if file_size < 10_000:  # less than 10KB — recording likely failed
            raise ValueError(
                f"Audio file too small ({file_size} bytes) — recording likely failed or was cut off"
            )

        logger.info(
            f"[Transcription] Sending audio to HuggingFace: {audio_path} ({file_size} bytes)"
        )

        # Read fully into memory before sending — avoids IncompleteRead on HuggingFace
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        # headers = {
        #     "Authorization": f"Bearer {HF_API_TOKEN}",
        #     "Content-Type": "audio/mpeg",
        # }

        import mimetypes

        mime_type, _ = mimetypes.guess_type(audio_path)

        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": mime_type or "application/octet-stream",
        }

        response = requests.post(
            HF_API_URL,
            headers=headers,
            data=audio_data,
            timeout=300,  # 5 min timeout — HF cold starts can be slow
        )

        # HuggingFace returns 503 when model is loading (cold start)
        if response.status_code == 503:
            logger.warning(
                f"[Transcription] HuggingFace model loading, retrying in 20s..."
            )
            raise self.retry(countdown=20)

        response.raise_for_status()
        result = response.json()

        print(f"Response from hugging face = {result}")

        transcript_text = result.get("text", "")
        if not transcript_text:
            raise ValueError("HuggingFace returned empty transcript")

        # Build output JSON
        output = {
            "text": transcript_text,
            "engine": "whisper-base",
            "source": "huggingface",
            "job_id": transcription.job_id,
        }

        # Save to disk
        os.makedirs(os.path.dirname(transcription.file_path), exist_ok=True)
        with open(transcription.file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # Update DB
        word_count = len(transcript_text.split())
        transcription.status = "completed"
        transcription.completed_at = get_ist_now()
        transcription.word_count = word_count
        transcription.file_size = os.path.getsize(transcription.file_path)
        db.session.commit()

        logger.info(
            f"[Transcription] Completed: {transcription_id} ({word_count} words)"
        )
        return {
            "status": "completed",
            "transcription_id": transcription_id,
            "word_count": word_count,
        }

    except (ConnectionError, Timeout, ChunkedEncodingError, IncompleteRead) as e:
        # Network errors — retry with exponential backoff
        logger.error(f"[Transcription] Network error: {transcription_id} — {e}")

        if self.request.retries < self.max_retries:
            retry_delay = 30 * (2**self.request.retries)  # 30s, 60s, 120s
            logger.warning(
                f"[Transcription] Retrying {self.request.retries + 1}/{self.max_retries} in {retry_delay}s"
            )
            raise self.retry(countdown=retry_delay, exc=e)

        try:
            db.session.rollback()
            transcription.status = "failed"
            transcription.error_message = (
                f"Network error after {self.max_retries} retries: {str(e)}"
            )
            transcription.completed_at = get_ist_now()
            db.session.commit()
        except Exception:
            pass

        return {
            "status": "failed",
            "transcription_id": transcription_id,
            "error": f"Network error after {self.max_retries} retries: {str(e)}",
        }

    except Exception as e:
        logger.error(f"[Transcription] Failed: {transcription_id} — {e}")
        try:
            db.session.rollback()
            transcription.status = "failed"
            transcription.error_message = str(e)
            transcription.completed_at = get_ist_now()
            db.session.commit()
        except Exception:
            pass

        return {
            "status": "failed",
            "transcription_id": transcription_id,
            "error": str(e),
        }
