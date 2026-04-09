from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.controller import (
    create_summary,
    get_summary,
    get_summary_status,
    download_summary_pdf,
    delete_summary,
)

summary_bp = Blueprint("summary", __name__, url_prefix="/summary")


@summary_bp.post("/start")
@jwt_required()
def route_create_summary():
    """
    POST /summary/
    Body: { "transcription_id": int, "job_id": int }
    """
    body = request.get_json(force=True)
    job_id = body.get("job_id")
    print("JOB = ", job_id)

    if not job_id:
        return {"error": "transcription_id and job_id are required."}, 400

    return create_summary(job_id=job_id)


@summary_bp.get("/<int:job_id>")
@jwt_required()
def route_get_summary(job_id: int):
    """
    GET /summary/<summary_id>
    Returns the full summary JSON content.
    """
    return get_summary(job_id)


@summary_bp.get("/<int:summary_id>/status")
@jwt_required()
def route_get_summary_status(summary_id: int):
    """
    GET /summary/<summary_id>/status
    Polling endpoint — lightweight status + metadata only.
    """
    return get_summary_status(summary_id)


@summary_bp.get("/<int:summary_id>/download")
@jwt_required()
def route_download_summary_pdf(summary_id: int):
    """
    GET /summary/<summary_id>/download
    Streams the summary as a downloadable PDF.
    """
    return download_summary_pdf(summary_id)


@summary_bp.delete("/<int:summary_id>")
@jwt_required()
def route_delete_summary(summary_id: int):
    """
    DELETE /summary/<summary_id>
    Soft-deletes the summary record.
    """
    return delete_summary(summary_id)
