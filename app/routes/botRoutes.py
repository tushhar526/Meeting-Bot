from flask import Blueprint, request
from app.controller.botController import create_bot, get_job_status, download_recording, stream_recording, list_recordings
from flask_jwt_extended import jwt_required, get_jwt_identity

bot_bp = Blueprint("bot_bp", __name__, url_prefix="/bot")


@bot_bp.route("/meeting/start", methods=["POST"])
@jwt_required()
def create_job():
    user_id = get_jwt_identity()
    return create_bot(request, user_id)


@bot_bp.route("/status/<int:job_id>", methods=["GET"])
@jwt_required()
def get_job_status_route(job_id):
    user_id = get_jwt_identity()
    return get_job_status(job_id, user_id)


@bot_bp.route("/recording/<int:job_id>", methods=["GET"])
@jwt_required()
def download_recording_route(job_id):
    user_id = get_jwt_identity()
    return download_recording(job_id, user_id)


@bot_bp.route("/stream/<int:job_id>", methods=["GET"])
@jwt_required()
def stream_recording_route(job_id):
    user_id = get_jwt_identity()
    return stream_recording(job_id, user_id)


@bot_bp.route("/recordings", methods=["GET"])
@jwt_required()
def list_recordings_route():
    user_id = get_jwt_identity()
    return list_recordings(user_id)
