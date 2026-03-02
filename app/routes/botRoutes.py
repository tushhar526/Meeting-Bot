from flask import Blueprint, request
from app.controller.botController import create_bot
from flask_jwt_extended import jwt_required, get_jwt_identity

bot_bp = Blueprint("bot_bp", __name__, url_prefix="/bot")


@bot_bp.route("/meeting/start", methods=["POST"])
@jwt_required()
def create_job():
    user_id = get_jwt_identity()
    return create_bot(request, user_id)
