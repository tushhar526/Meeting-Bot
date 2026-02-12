from flask import Blueprint, request, jsonify
from app.controller.meetbot import create_bot, start_bot
from app.extension import celery

bot_bp = Blueprint("bot_bp", __name__, url_prefix="/bot")


@bot_bp.route("/meeting/start", methods=["POST"])
def create_job():
    data = request.json
    meeting_url = data.get("meeting_url")

    if not meeting_url:
        return jsonify({"message": "Meeting url is required"}), 401

    job = create_bot(meeting_url)

    print(
        "Broker url = ",
        celery.conf.broker_url,
        " and result backend = ",
        celery.conf.result_backend,
    )
    start_bot.delay(job.job_id)

    return (
        jsonify(
            {
                "message": "recording started succesfully",
                "job": job.to_json,
            }
        ),
        200,
    )
