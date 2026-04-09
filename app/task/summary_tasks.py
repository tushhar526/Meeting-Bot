import os
from langchain.chat_models import init_chat_model
import json
import logging
from app.extension import celery, db
from app.models import SummaryModel, SummaryStatus, TranscriptionsModel
from app.schema import MeetingSummary, DiscussionItem
from app.helper import get_ist_now
from langchain_core.messages import SystemMessage, HumanMessage
import logging

# from requests.exceptions import ConnectionError, Timeout, ChunkedEncodingError
import re


logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> str:
    """
    Robustly extract a JSON string from an LLM response.
    Handles these real-world cases:
      1. ```json ... ```   (standard markdown fence)
      2. ``` ... ```       (fence without language label)
      3. Bare JSON with leading/trailing whitespace or stray text
      4. JSON embedded mid-text (finds first { ... } block)
    """
    content = raw.strip()

    # Case 1 & 2 — strip any markdown code fence
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    # Case 3 — already clean JSON
    if content.startswith("{") or content.startswith("["):
        return content

    # Case 4 — JSON buried in surrounding text (e.g. "Sure! Here you go: {...}")
    embedded = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
    if embedded:
        return embedded.group(1).strip()

    raise ValueError(f"No JSON found in LLM response.\nRaw content: {repr(raw)}")


@celery.task()
def process_transcription(summary_id: int):

    summary_obj = SummaryModel.query.filter(
        SummaryModel.summary_id == summary_id
    ).first()
    print(
        f"Ok as it said processing lets check here , the summary status is like this {summary_obj.status}"
    )

    if not summary_obj:
        logger.error(f"[Summary] Row not found: {summary_id}")
        return {"error": "Summary not found"}

    summary_obj.status = "processing"
    summary_obj.started_at = get_ist_now()
    db.session.commit()

    print(
        f"Ok as it said processing lets check here , the summary status is like this {summary_obj.status}"
    )

    try:
        transcript_path = summary_obj.transcription.file_path
        if not transcript_path or not os.path.exists(transcript_path):
            raise FileNotFoundError(f"Audio file not found: {transcript_path}")

        # Guard against broken/empty recordings
        file_size = os.path.getsize(transcript_path)

        logger.info(
            f"[Summary] Sending transcription to LLM: {transcript_path} ({file_size} bytes)"
        )

        dm = os.getenv("DEFAULT_MODEL")
        url = os.getenv("OLLAMA_BASE_URL")

        model = init_chat_model(model=dm, base_url=url)

        # Read fully into memory before sending — avoids IncompleteRead on HuggingFace
        with open(transcript_path, "rb") as f:
            data = json.load(f)
            transcript = data["text"]

        system_prompt = """You are a meeting analyst. Given a transcript, return a JSON object.
        Rules:
        - If the transcript contains problems and solutions, populate "discussions" as a list 
        of objects with "problem", "solution", and optionally "decision".
        - If the transcript has NO clear problems/solutions (e.g. casual chat, status updates, 
        announcements), return "discussions" as an empty list [] and populate "overview" 
        with a short plain-English summary of what was discussed.
        - Always populate "conclusion" with a closing paragraph regardless of transcript type.

        Return ONLY valid JSON. No markdown, no explanation."""

        user_prompt = f"Transcript:\n\n{transcript}"

        response = model.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )

        # data = json.loads(response.content)
        print("RAW RESPONSE:", repr(response.content))

        # Strip markdown fences Gemini sometimes adds despite instructions
        content = _extract_json(response.content)

        try:
            summary = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM returned unparseable response: {e}\nContent was: {repr(content)}"
            )

        if not summary:
            raise ValueError("LLM returned empty Summary")

        structured_summary = MeetingSummary(**summary).model_dump()

        # Build output JSON
        output = {
            "summary": structured_summary,
            "job_id": summary_obj.job_id,
        }

        # Save to disk
        os.makedirs(os.path.dirname(summary_obj.file_path), exist_ok=True)
        with open(summary_obj.file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # Update DB
        summary_obj.status = "completed"
        summary_obj.completed_at = get_ist_now()
        db.session.commit()

        logger.info(f"[Summary] Completed: {summary_id}")
        return {
            "status": "completed",
            "summary_id": summary_id,
        }

    except Exception as e:
        logger.error(f"[Summary] Failed: {summary_id} — {e}")
        try:
            db.session.rollback()
            summary_obj.status = "failed"
            summary_obj.completed_at = get_ist_now()
            db.session.commit()
        except Exception:
            pass

        return {
            "status": "failed",
            "summary_id": summary_id,
            "error": str(e),
        }
