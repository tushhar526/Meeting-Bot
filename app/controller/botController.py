from app.models.jobModel import JobModel
from flask import jsonify, send_file
from app.extension import db
from app.helper.tasks import start_bot
import os


def create_bot(request, user_id):
    data = request.json
    meeting_url = data.get("meeting_url")
    platform = data.get("platform")

    if not meeting_url:
        return jsonify({"message": "Meeting url is required"}), 401

    job = JobModel(job_url=meeting_url, user_id=user_id, platform=platform)
    job.audio_path = f"app/recordings/job_{job.job_id}_audio.mp3"

    db.session.add(job)
    db.session.commit()

    start_bot.delay(job.job_id, job.audio_path, meeting_url)

    return (
        jsonify(
            {
                "message": "recording started succesfully",
                "job": job.to_json,
            }
        ),
        200,
    )


def get_job_status(job_id, user_id):
    job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "id": job.job_id,
        "meeting_url": job.job_url,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "has_recording": False,
    }

    if job.status == "Completed" and job.audio_path and os.path.exists(job.audio_path):
        response["has_recording"] = True
        response["download_url"] = f"/bot/recording/{job_id}"
        response["stream_url"] = f"/bot/stream/{job_id}"

    return jsonify(response), 200


def download_recording(job_id, user_id):
    job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status != "Completed":
        return jsonify({"error": "Recording not ready"}), 400

    if not job.audio_path or not os.path.exists(job.audio_path):
        return jsonify({"error": "Recording file not found"}), 404

    return send_file(
        job.audio_path,
        as_attachment=True,
        download_name=f"meeting_recording_{job_id}.mp3",
        mimetype="audio/mpeg",
    )


def stream_recording(job_id, user_id):
    """Stream audio file for playback in frontend"""
    job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status != "Completed":
        return jsonify({"error": "Recording not ready"}), 400

    if not job.audio_path or not os.path.exists(job.audio_path):
        return jsonify({"error": "Recording file not found"}), 404

    return send_file(
        job.audio_path,
        as_attachment=False,  # Stream instead of download
        mimetype="audio/mpeg",
        conditional=True,  # Support HTTP range requests for seeking
        max_age=3600  # Cache for 1 hour
    )


def list_recordings(user_id):
    """List all recording files for a specific user with id, name, and time"""
    try:
        # Get all jobs that have audio files for the specific user
        recordings = (
            db.session.query(JobModel)
            .filter(JobModel.user_id == user_id)
            .filter(JobModel.audio_path.isnot(None))
            .filter(JobModel.audio_path != "")
            .order_by(JobModel.created_at.desc())
            .all()
        )
        
        recordings_list = []
        for recording in recordings:
            # Extract filename from path
            filename = os.path.basename(recording.audio_path) if recording.audio_path else f"recording_{recording.job_id}.mp3"
            
            recordings_list.append({
                "id": recording.job_id,
                "name": filename,
                "created_at": recording.created_at.isoformat() if recording.created_at else None,
                "created_at_formatted": recording.created_at.strftime('%d-%m-%Y %I:%M %p') if recording.created_at else None,
                "status": recording.status,
                "meeting_url": recording.job_url
            })
        
        return jsonify({
            "recordings": recordings_list,
            "total_count": len(recordings_list)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to list recordings: {str(e)}"}), 500
