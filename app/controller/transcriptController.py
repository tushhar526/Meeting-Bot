import os
import io
import json
from http import HTTPStatus
from weasyprint import HTML
from flask import jsonify, send_file
from app.extension import db
from app.helper.logger import get_logger
from app.models import JobModel, get_ist_now, userModel
from app.models.transcriptionModel import TranscriptionsModel

logger = get_logger(__name__)

TRANSCRIPTION_DIR = "app/transcriptions"


def make_transcript(request, user_id):
    """
    Start transcription for a completed job.
    Creates a TranscriptionsModel row and fires the Celery task.
    """
    try:
        logger.info(f"Transcription requested by user {user_id}")

        data = request.json
        job_id = data.get("job_id")

        if not job_id:
            logger.error(f"Transcription failed - missing job_id for user {user_id}")
            return jsonify({"error": "job_id is required"}), 400

        job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()
        if not job:
            logger.error(
                f"Transcription failed - job {job_id} not found for user {user_id}"
            )
            return jsonify({"error": "Job not found"}), 404

        if job.status != "Completed":
            return jsonify({"error": "Job is not completed yet"}), 400

        if not job.audio_path:
            return jsonify({"error": "No audio file found for this job"}), 400

        if not os.path.exists(job.audio_path):
            return jsonify({"error": "Audio file not found on disk"}), 404

        # Check if transcription already exists for this job
        existing = TranscriptionsModel.query.filter_by(
            job_id=job_id, is_deleted=False
        ).first()

        if existing:
            if existing.status in ("pending", "processing"):
                return (
                    jsonify(
                        {
                            "message": "Transcription already in progress",
                            "transcription_id": existing.transcription_id,
                            "status": existing.status,
                        }
                    ),
                    200,
                )
            if existing.status == "completed":
                return (
                    jsonify(
                        {
                            "message": "Transcription already completed",
                            "transcription_id": existing.transcription_id,
                            "status": existing.status,
                        }
                    ),
                    200,
                )

        user = userModel.query.filter_by(user_id=user_id).first()
        username = user.username if user else f"user_{user_id}"

        os.makedirs(TRANSCRIPTION_DIR, exist_ok=True)
        file_path = os.path.join(
            TRANSCRIPTION_DIR, f"{job_id}_job_{username}_transcript.json"
        )

        transcription = TranscriptionsModel(
            user_id=user_id,
            job_id=job_id,
            file_path=file_path,
            status="pending",
        )
        db.session.add(transcription)
        db.session.commit()

        logger.info(
            f"Transcription row created: {transcription.transcription_id} for job {job_id}"
        )

        from app.task.transcript_tasks import transcribe_audio

        transcribe_audio.delay(transcription.transcription_id)

        return (
            jsonify(
                {
                    "message": "Transcription started",
                    "transcription_id": transcription.transcription_id,
                    "status": "pending",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"make_transcript error for user {user_id}", exception=e)
        db.session.rollback()
        return jsonify({"error": f"Failed to start transcription: {str(e)}"}), 500


def get_transcript(job_id, user_id):
    """Get the full transcript content for a completed transcription."""
    try:

        transcription = TranscriptionsModel.query.filter_by(
            job_id=job_id, user_id=user_id, is_deleted=False
        ).first()

        if not transcription:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "No Transcript Found for meeting",
                        "error": {"status": 404, "type": "TRANSCRIPT_NOT_FOUND"},
                    }
                ),
                HTTPStatus.NOT_FOUND,
            )

        if transcription.status != "completed":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Transcription is not completed yet",
                        "error": {
                            "status": transcription.status,
                            "type": "TANSCRIPT_NOT_COMPLETED",
                        },
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )

        if not transcription.file_path or not os.path.exists(transcription.file_path):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Transcript Not completed successfully yet",
                        "data": {
                            "status": transcription.status,
                            "transcript": transcription.to_json,
                        },
                    }
                ),
                HTTPStatus.OK,
            )

        with open(transcription.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Transcription Found successfully",
                    "data": {
                        "status": transcription.status,
                        "text": data["text"],
                        "transcript": transcription.to_json,
                    },
                }
            ),
            HTTPStatus.OK,
        )

        return (
            jsonify(
                {
                    "transcription_id": transcription.transcription_id,
                    "job_id": transcription.job_id,
                    "meeting_title": (
                        transcription.job.meeting_title if transcription.job else None
                    ),
                    "platform": (
                        transcription.job.platform if transcription.job else None
                    ),
                    "status": transcription.status,
                    "text": data.get("text", ""),
                    "engine": data.get("engine", transcription.transcription_engine),
                    "language": transcription.language,
                    "word_count": transcription.word_count,
                    "confidence_score": transcription.confidence_score,
                    "created_at": (
                        transcription.created_at.isoformat()
                        if transcription.created_at
                        else None
                    ),
                    "completed_at": (
                        transcription.completed_at.isoformat()
                        if transcription.completed_at
                        else None
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"get_transcript error for user {user_id}", exception=e)
        return jsonify({"error": f"Failed to get transcript: {str(e)}"}), 500


def update_transcript(transcription_id, user_id, request):
    """
    Update transcript text — called when user edits and saves from the modal.
    Overwrites the JSON file on disk and updates word_count in DB.
    """
    try:
        transcription = TranscriptionsModel.query.filter_by(
            transcription_id=transcription_id, user_id=user_id, is_deleted=False
        ).first()

        if not transcription:
            return jsonify({"error": "Transcription not found"}), 404

        if transcription.status != "completed":
            return jsonify({"error": "Can only edit completed transcriptions"}), 400

        data = request.json
        new_text = data.get("text", "").strip()

        if not new_text:
            return jsonify({"error": "Text cannot be empty"}), 400

        # Read existing file to preserve metadata
        existing_data = {}
        if os.path.exists(transcription.file_path):
            with open(transcription.file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)

        existing_data["text"] = new_text
        existing_data["edited"] = True
        existing_data["edited_at"] = get_ist_now().isoformat()

        with open(transcription.file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        transcription.word_count = len(new_text.split())
        transcription.file_size = os.path.getsize(transcription.file_path)
        db.session.commit()

        logger.info(f"Transcript {transcription_id} updated by user {user_id}")
        return (
            jsonify(
                {
                    "message": "Transcript updated successfully",
                    "transcription_id": transcription_id,
                    "word_count": transcription.word_count,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"update_transcript error for user {user_id}", exception=e)
        db.session.rollback()
        return jsonify({"error": f"Failed to update transcript: {str(e)}"}), 500


def list_transcripts(user_id):
    """
    List all transcriptions for a user — all statuses.
    Frontend splits them into in-progress / completed / failed sections.
    """
    try:
        logger.info(f"Transcription list request by user {user_id}")

        transcripts = (
            db.session.query(TranscriptionsModel)
            .filter(
                TranscriptionsModel.user_id == user_id,
                TranscriptionsModel.is_deleted == False,
            )
            .order_by(TranscriptionsModel.created_at.desc())
            .all()
        )

        transcripts_list = []
        for transcript in transcripts:
            transcripts_list.append(
                {
                    "transcription_id": transcript.transcription_id,
                    "job_id": transcript.job_id,
                    "meeting_title": (
                        transcript.job.meeting_title if transcript.job else None
                    ),
                    "platform": transcript.job.platform if transcript.job else None,
                    "status": transcript.status,
                    "word_count": transcript.word_count,
                    "file_size": transcript.file_size,
                    # "error_message": transcript.error_message,
                    "created_at": (
                        transcript.created_at.isoformat()
                        if transcript.created_at
                        else None
                    ),
                    "created_at_formatted": (
                        transcript.created_at.strftime("%d-%m-%Y %I:%M %p")
                        if transcript.created_at
                        else None
                    ),
                    "completed_at": (
                        transcript.completed_at.isoformat()
                        if transcript.completed_at
                        else None
                    ),
                }
            )

        return (
            jsonify(
                {
                    "transcriptions": transcripts_list,
                    "total_count": len(transcripts_list),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(
            f"Error listing transcriptions for user {user_id} due to {str(e)}",
            exception=e,
        )
        return jsonify({"error": f"Failed to list transcriptions: {str(e)}"}), 500


def get_transcript_status(transcription_id, user_id):
    """Get current status — used by frontend polling. Lightweight, no file reading."""
    try:
        transcription = TranscriptionsModel.query.filter_by(
            transcription_id=transcription_id, user_id=user_id, is_deleted=False
        ).first()

        if not transcription:
            return jsonify({"error": "Transcription not found"}), 404

        response = {
            "success": True,
            "message": "Status for the required Summary is like this",
            "status": transcription.status,
        }

        if transcription.status == "completed":
            response["word_count"] = transcription.word_count
            response["confidence_score"] = transcription.confidence_score

        if transcription.status == "failed":
            response["error_message"] = transcription.error_message

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"get_transcript_status error for user {user_id}", exception=e)
        return jsonify({"error": f"Failed to get status: {str(e)}"}), 500


def download_transcript_json(transcription_id, user_id):
    """Download the raw transcript JSON file."""
    try:
        transcription = TranscriptionsModel.query.filter_by(
            transcription_id=transcription_id, user_id=user_id, is_deleted=False
        ).first()

        if not transcription:
            return jsonify({"error": "Transcription not found"}), 404

        if transcription.status != "completed":
            return jsonify({"error": "Transcription not ready yet"}), 400

        if not transcription.file_path or not os.path.exists(transcription.file_path):
            return jsonify({"error": "Transcript file not found on disk"}), 404

        filename = os.path.basename(transcription.file_path)
        return send_file(
            transcription.file_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"download_transcript_json error for user {user_id}", exception=e)
        return jsonify({"error": f"Failed to download transcript: {str(e)}"}), 500


def download_transcript_pdf(transcription_id, user_id):
    """
    Generate and download transcript as PDF.
    Uses reportlab if available, falls back to plain text if not.
    """
    try:
        transcription = TranscriptionsModel.query.filter_by(
            transcription_id=transcription_id, user_id=user_id, is_deleted=False
        ).first()

        if not transcription:
            return jsonify({"error": "Transcription not found"}), 404

        if transcription.status != "completed":
            return jsonify({"error": "Transcription not ready yet"}), 400

        if not transcription.file_path or not os.path.exists(transcription.file_path):
            return jsonify({"error": "Transcript file not found on disk"}), 404

        with open(transcription.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        transcript_text = data.get("text", "")
        meeting_title = (
            transcription.job.meeting_title
            if transcription.job
            else f"Job #{transcription.job_id}"
        )
        platform = (
            (transcription.job.platform or "Unknown").title()
            if transcription.job
            else "Unknown"
        )
        completed_at = (
            transcription.completed_at.strftime("%d-%m-%Y %I:%M %p")
            if transcription.completed_at
            else "Unknown"
        )
        word_count = transcription.word_count or 0

        # try:
        #     from reportlab.lib.pagesizes import A4
        #     from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        #     from reportlab.lib.units import cm
        #     from reportlab.lib import colors
        #     from reportlab.platypus import (
        #         SimpleDocTemplate,
        #         Paragraph,
        #         Spacer,
        #         HRFlowable,
        #     )

        # buffer = io.BytesIO()
        # doc = SimpleDocTemplate(
        #     buffer,
        #     pagesize=A4,
        #     rightMargin=2 * cm,
        #     leftMargin=2 * cm,
        #     topMargin=2 * cm,
        #     bottomMargin=2 * cm,
        # )

        # styles = getSampleStyleSheet()
        # title_style = ParagraphStyle(
        #     "CustomTitle",
        #     parent=styles["Heading1"],
        #     fontSize=16,
        #     spaceAfter=6,
        #     textColor=colors.HexColor("#1a1a2e"),
        # )
        # meta_style = ParagraphStyle(
        #     "Meta",
        #     parent=styles["Normal"],
        #     fontSize=9,
        #     textColor=colors.HexColor("#6b7280"),
        #     spaceAfter=4,
        # )
        # body_style = ParagraphStyle(
        #     "Body",
        #     parent=styles["Normal"],
        #     fontSize=11,
        #     leading=18,
        #     textColor=colors.HexColor("#1f2937"),
        #     spaceAfter=12,
        # )

        # story = []
        # story.append(Paragraph(meeting_title or "Meeting Transcript", title_style))
        # story.append(Paragraph(f"Platform: {platform}", meta_style))
        # story.append(Paragraph(f"Date: {completed_at}", meta_style))
        # story.append(Paragraph(f"Words: {word_count}", meta_style))
        # story.append(Spacer(1, 0.3 * cm))
        # story.append(
        #     HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"))
        # )
        # story.append(Spacer(1, 0.5 * cm))

        # for para in transcript_text.split("\n"):
        #     para = para.strip()
        #     if para:
        #         story.append(Paragraph(para, body_style))

        # doc.build(story)
        # buffer.seek(0)

        html_content = f"""
            <html>
            <head>
            <meta charset="UTF-8">
            <style>
            body {{ font-family: sans-serif; font-size: 11pt; }}
            h1 {{ color: #1a1a2e; }}
            .meta {{ color: #6b7280; font-size: 9pt; }}
            </style>
            </head>
            <body>
            <h1>{meeting_title}</h1>
            <p class="meta">Platform: {platform} | Date: {completed_at} | Words: {word_count}</p>
            <hr/>
            <p>{transcript_text.replace(chr(10), '<br>')}</p>
            </body>
            </html>
            """

        buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"transcript_{transcription_id}.pdf",
            mimetype="application/pdf",
        )

    except Exception as e:
        logger.error(
            f"download_transcript_pdf error for user {user_id} due to {str(e)}",
            exception=e,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Failed to generate for this transcription",
                    "error": {"status": 404, "type": "FAILED_TO_GENERATE_PDF"},
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
