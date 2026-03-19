from flask import Blueprint, request, jsonify
from app.controller.botController import create_bot, get_job_status, download_recording, stream_recording, list_recordings, get_audio_metadata, update_job_status
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.helper.plan_access import require_plan_access

bot_bp = Blueprint("bot_bp", __name__, url_prefix="/bot")


@bot_bp.route("/meeting/start", methods=["POST"])
@jwt_required()
@require_plan_access(required_feature='recording')
def create_job():
    user_id = get_jwt_identity()
    return create_bot(request, user_id)


@bot_bp.route("/status/<int:job_id>", methods=["GET"])
@jwt_required()
@require_plan_access()
def get_job_status_route(job_id):
    user_id = get_jwt_identity()
    return get_job_status(job_id, user_id)


@bot_bp.route("/recording/<int:job_id>", methods=["GET"])
@jwt_required()
@require_plan_access(required_feature='download')
def download_recording_route(job_id):
    user_id = get_jwt_identity()
    return download_recording(job_id, user_id)


@bot_bp.route("/stream/<int:job_id>", methods=["GET"])
@jwt_required()
@require_plan_access(required_feature='streaming')
def stream_recording_route(job_id):
    user_id = get_jwt_identity()
    return stream_recording(job_id, user_id)


@bot_bp.route("/metadata/<int:job_id>", methods=["GET"])
@jwt_required()
@require_plan_access(required_feature='metadata')
def get_audio_metadata_route(job_id):
    """Get audio metadata including duration, file size, etc."""
    user_id = get_jwt_identity()
    
    # Import here to avoid circular imports
    from app.models.jobModel import JobModel
    from app.extension import db
    import os
    
    # Get job
    job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job.status != "Completed":
        return jsonify({"error": "Recording not ready"}), 400
    
    if not job.audio_path:
        return jsonify({"error": "Recording file not found"}), 404
    
    # Fix path issues - normalize and handle container paths
    audio_path = job.audio_path
    
    # Remove duplicate /app/ prefix if it exists
    if audio_path.startswith("/app/app/"):
        audio_path = audio_path.replace("/app/app/", "/app/")
    
    # Handle relative paths - convert to absolute if needed
    if not audio_path.startswith("/"):
        audio_path = os.path.join(os.getcwd(), audio_path)
    
    if not os.path.exists(audio_path):
        return jsonify({"error": "Recording file not found"}), 404
    
    # Get metadata
    metadata = get_audio_metadata(audio_path)
    
    if not metadata:
        return jsonify({"error": "Could not extract audio metadata"}), 500
    
    return jsonify({
        "job_id": job_id,
        "metadata": metadata,
        "audio_path": job.audio_path,
        "status": job.status
    })


@bot_bp.route("/recordings", methods=["GET"])
@jwt_required()
@require_plan_access()
def list_recordings_route():
    user_id = get_jwt_identity()
    return list_recordings(user_id)


@bot_bp.route("/status/update", methods=["POST", "PUT"])
@jwt_required()
@require_plan_access()
def update_job_status_route():
    user_id = get_jwt_identity()
    return update_job_status(request, user_id)
