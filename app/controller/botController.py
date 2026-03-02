from app.models.jobModel import JobModel
from flask import jsonify
from app.extension import db
from app.helper.tasks import start_bot


def create_bot(request, user_id):
    data = request.json
    meeting_url = data.get("meeting_url")

    if not meeting_url:
        return jsonify({"message": "Meeting url is required"}), 401

    job = JobModel(job_url=meeting_url)
    job.audio_path = f"app/recordings/job_{job.job_id}_audio.mp3"

    db.session.add(job)
    db.session.commit()

    start_bot.delay(meeting_url)

    return (
        jsonify(
            {
                "message": "recording started succesfully",
                "job": job.to_json,
            }
        ),
        200,
    )
