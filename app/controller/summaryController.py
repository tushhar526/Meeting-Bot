import os
import json
from http import HTTPStatus
from flask import jsonify, send_file, abort
from app.helper.logger import get_logger
from app.extension import db
from app.helper import get_ist_now
from app.models import (
    TranscriptionsModel,
    SummaryModel,
    SummaryStatus,
    TranscriptionStatus,
)
from app.task.summary_tasks import process_transcription

# from app.summary.summary_pdf import build_summary_pdf


logger = get_logger(__name__)
SUMMARY_DIR = "app/summary"


# ── Create ────────────────────────────────────────────────────────────────────


def create_summary(job_id: int):
    """
    POST /summary
    Creates a SummaryModel row (status=PENDING) and fires the Celery task.
    Returns immediately so the client can start polling.
    """
    transcription = TranscriptionsModel.query.filter_by(job_id=job_id).first()
    if not transcription:
        return jsonify({"error": "Transcription not found"}), HTTPStatus.NOT_FOUND

    if transcription.status != TranscriptionStatus.COMPLETED:
        return jsonify(
            {
                "success": False,
                "message": "Summary cannot be generated because transcription is not available yet",
                "error": {"code": 400, "type": "DEPENDENCY_NOT_READY"},
            }
        )

    # Prevent duplicate in-flight summaries for the same transcription
    existing = (
        SummaryModel.query.filter_by(
            transcription_id=transcription.transcription_id,
            job_id=job_id,
            is_deleted=False,
        )
        .filter(
            SummaryModel.status.in_([SummaryStatus.PENDING, SummaryStatus.PROCESSING])
        )
        .first()
    )
    if existing and existing.status != SummaryStatus.FAILED:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "A summary is already being generated for this transcription.",
                    "error": {
                        "code": 409,
                        "type": "SUMMARY_IN_PROGRESS",
                    },
                    "data": {
                        "summary": _serialize(existing),
                        "status": existing.status,
                    },
                }
            ),
            HTTPStatus.CONFLICT,
        )

    os.makedirs(SUMMARY_DIR, exist_ok=True)
    file_path = os.path.join(SUMMARY_DIR, f"{job_id}_job_summary.json")

    summary = SummaryModel(
        job_id=job_id,
        transcription_id=transcription.transcription_id,
        file_path=file_path,
        status="pending",
    )
    db.session.add(summary)
    db.session.commit()
    logger.info(f"Summary row created: {summary.summary_id} for job {job_id}")

    process_transcription.delay(summary_id=summary.summary_id)

    return (
        jsonify(
            {
                "success": True,
                "message": "Summary generation started.",
                "data": {"summary": _serialize(summary), "status": summary.status},
            }
        ),
        HTTPStatus.ACCEPTED,
    )


# ── List ────────────────────────────────────────────────────────────────────


def list_summaries(user_id):
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


# ── Poll ──────────────────────────────────────────────────────────────────────


def get_summary_status(summary_id: int):
    """
    GET /summary/<summary_id>/status
    Lightweight polling endpoint — returns status + file_path when done.
    """
    summary = SummaryModel.query.filter_by(summary_id=summary_id).first()

    if not summary:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No summary Found",
                    "error": {"code": 400, "type": "DEPENDENCY_NOT_READY"},
                }
            ),
            HTTPStatus.NOT_FOUND,
        )
    return (
        jsonify(
            {
                "success": True,
                "message": "Status for the required Summary is like this",
                "status": summary.status,
            }
        ),
        HTTPStatus.OK,
    )


# ── Full content ──────────────────────────────────────────────────────────────


def get_summary(job_id: int):
    """
    GET /summary/<summary_id>
    Returns the full summary JSON once completed.
    """
    # summary = _get_or_404(job_id)

    summary = SummaryModel.query.filter_by(job_id=job_id, is_deleted=False).first()

    if not summary:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No Summary Found for this Transcription",
                    "error": {"code": 404, "type": "SUMMARY_NOT_FOUND"},
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    if not summary.file_path or not os.path.exists(summary.file_path):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Summary Not completed successfully yet",
                    "data": {"status": summary.status, "summary": _serialize(summary)},
                }
            ),
            HTTPStatus.OK,
        )

    with open(summary.file_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    return (
        jsonify(
            {
                "success": True,
                "message": "Summary Found successfully",
                "data": {"status": summary.status, "content": content},
            }
        ),
        HTTPStatus.OK,
    )


# ── PDF download ──────────────────────────────────────────────────────────────


def download_summary_pdf(summary_id: int):
    """
    GET /summary/<summary_id>/download
    Builds a PDF from the JSON summary (cached next to the JSON) and streams it.
    """
    summary = _get_or_404(summary_id)

    if summary.status != SummaryStatus.COMPLETED:
        return (
            jsonify(
                {
                    "error": "Summary not ready yet.",
                    "status": summary.status,
                }
            ),
            HTTPStatus.ACCEPTED,
        )

    if not summary.file_path or not os.path.exists(summary.file_path):
        return (
            jsonify({"error": "Summary file not found on disk."}),
            HTTPStatus.NOT_FOUND,
        )

    pdf_path = summary.file_path.replace("_summary.json", "_summary.pdf")

    if not os.path.exists(pdf_path):
        with open(summary.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        build_summary_pdf(data, pdf_path)

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=os.path.basename(pdf_path),
    )


# ── Soft delete ───────────────────────────────────────────────────────────────


def delete_summary(summary_id: int):
    """DELETE /summary/<summary_id> — soft-deletes the record."""
    summary = _get_or_404(summary_id)
    summary.is_deleted = True
    summary.deleted_at = get_ist_now()
    db.session.commit()
    return jsonify({"message": "Summary deleted."}), HTTPStatus.OK


# ── Private helpers ───────────────────────────────────────────────────────────


def _get_or_404(job_id: int) -> SummaryModel:
    summary = SummaryModel.query.filter_by(job_id=job_id, is_deleted=False).first()
    if not summary:
        abort(HTTPStatus.NOT_FOUND)
    print(
        f"BRUH WE GOT THE SUMMARY man = {summary.file_path} and status is like this = {summary.status}"
    )
    return summary


def _serialize(summary: SummaryModel) -> dict:
    return {
        "summary_id": summary.summary_id,
        "transcription_id": summary.transcription_id,
        "job_id": summary.job_id,
        "status": summary.status,
        "file_path": summary.file_path,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
    }
