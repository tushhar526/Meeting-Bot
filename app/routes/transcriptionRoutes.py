from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controller.transcriptController import (
    make_transcript,
    get_transcript,
    update_transcript,
    get_transcript_status,
    list_transcripts,
    download_transcript_json,
    download_transcript_pdf,
)

transcript_bp = Blueprint("transcript_bp", __name__, url_prefix="/transcription")


@transcript_bp.route("/start", methods=["POST"])
@jwt_required()
def start_transcription():
    """Start transcription for a completed job."""
    user_id = get_jwt_identity()
    return make_transcript(request, user_id)


@transcript_bp.route("/all", methods=["GET"])
@jwt_required()
def list_transcripts_route():
    """List all transcriptions for the current user."""
    user_id = get_jwt_identity()
    return list_transcripts(user_id)


@transcript_bp.route("/<int:transcription_id>", methods=["GET"])
@jwt_required()
def fetch_transcript(transcription_id):
    """Get full transcript content."""
    user_id = get_jwt_identity()
    return get_transcript(transcription_id, user_id)


@transcript_bp.route("/<int:transcription_id>", methods=["PATCH"])
@jwt_required()
def edit_transcript(transcription_id):
    """Update transcript text after user edits."""
    user_id = get_jwt_identity()
    return update_transcript(transcription_id, user_id, request)


@transcript_bp.route("/<int:transcription_id>/status", methods=["GET"])
@jwt_required()
def transcript_status(transcription_id):
    """Get transcription status — used by frontend polling."""
    user_id = get_jwt_identity()
    return get_transcript_status(transcription_id, user_id)


@transcript_bp.route("/<int:transcription_id>/download", methods=["GET"])
@jwt_required()
def download_json(transcription_id):
    """Download transcript as JSON file."""
    user_id = get_jwt_identity()
    return download_transcript_json(transcription_id, user_id)


@transcript_bp.route("/<int:transcription_id>/download/pdf", methods=["GET"])
@jwt_required()
def download_pdf(transcription_id):
    """Download transcript as PDF."""
    user_id = get_jwt_identity()
    return download_transcript_pdf(transcription_id, user_id)