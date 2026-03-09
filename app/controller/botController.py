from app.models.jobModel import JobModel, get_ist_now
from flask import jsonify, send_file
from app.extension import db
from app.helper.tasks import start_bot, stop_bot_task
import os
import logging
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from datetime import timedelta

logger = logging.getLogger(__name__)

def get_audio_metadata(file_path):
    """Extract metadata from audio file including duration"""
    try:
        if not os.path.exists(file_path):
            return None
            
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Try to extract duration using mutagen
        duration_seconds = 0
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration_seconds = audio_file.info.length
        except Exception as e:
            logger.warning(f"Could not extract duration with mutagen: {e}")
        
        # Format duration as human readable
        if duration_seconds > 0:
            duration_str = str(timedelta(seconds=int(duration_seconds)))
            # Remove microseconds and format nicely
            if '.' in duration_str:
                duration_str = duration_str.split('.')[0]
            # Remove leading zeros for hours if less than 1 hour
            if duration_str.startswith('00:'):
                duration_str = duration_str[3:]
        else:
            duration_str = "Unknown"
        
        return {
            "duration_seconds": duration_seconds,
            "duration_formatted": duration_str,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Error getting audio metadata: {e}")
        return None


def create_bot(request, user_id):
    try:
        data = request.json
        meeting_url = data.get("meeting_url")
        platform = data.get("platform")

        if not meeting_url:
            return jsonify({"message": "Meeting url is required"}), 401

        # Get user to access meetings count
        from app.models.userModel import userModel
        user = userModel.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        job = JobModel(job_url=meeting_url, user_id=user_id, platform=platform)
        db.session.add(job)
        db.session.flush()  # Gets the ID without full commit
        
        print(f"the job id is like this: {job.job_id}")
        
        # Increment user's meeting count
        user.meetings += 1
        
        # Use username + meeting count for filename
        job.audio_path = f"app/recordings/{user.username}_meeting_{user.meetings}_audio.mp3"
        print(f"and the recording path is like this: {job.audio_path}")
        
        db.session.commit()  # Single commit saves everything

        start_bot.delay(job.job_id, job.audio_path, meeting_url)

        return (
            jsonify(
                {
                    "message": "recording started successfully",
                    "job": job.to_json,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in create_bot: {str(e)}")
        return jsonify({"error": f"Failed to create bot: {str(e)}"}), 500


def get_job_status(job_id, user_id):
    job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "id": job.job_id,
        "meeting_url": job.job_url,
        "status": job.status,
        "platform":job.platform,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "has_recording": False,
    }

    if job.status == "Completed" and job.audio_path and os.path.exists(job.audio_path):
        response["has_recording"] = True
        response["download_url"] = f"/bot/recording/{job_id}"
        response["stream_url"] = f"/bot/stream/{job_id}"
    elif job.status == "Failed":
        response["error_message"] = "Recording failed due to unknown error"
        response["failure_reason"] = "The bot encountered an error during the meeting"

    return jsonify(response), 200


def download_recording(job_id, user_id):
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
    
    logger.info(f"Downloading audio from: {audio_path}")
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found at: {audio_path}")
        return jsonify({"error": "Recording file not found"}), 404

    return send_file(
        audio_path,
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
    
    logger.info(f"Streaming audio from: {audio_path}")
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found at: {audio_path}")
        return jsonify({"error": "Recording file not found"}), 404

    # Get audio metadata
    metadata = get_audio_metadata(audio_path)
    
    # Create response with file
    response = send_file(
        audio_path,
        as_attachment=False,  # Stream instead of download
        mimetype="audio/mpeg",
        conditional=True,  # Support HTTP range requests for seeking
        max_age=3600,  # Cache for 1 hour
    )
    
    # Add metadata to response headers
    if metadata:
        response.headers['X-Audio-Duration'] = str(metadata['duration_seconds'])
        response.headers['X-Audio-Duration-Formatted'] = metadata['duration_formatted']
        response.headers['X-Audio-File-Size'] = str(metadata['file_size_bytes'])
        response.headers['X-Audio-File-Size-MB'] = str(metadata['file_size_mb'])
        
        # Also expose these headers in CORS
        response.headers['Access-Control-Expose-Headers'] = ', '.join([
            'Content-Range', 'Accept-Ranges', 'Content-Length',
            'X-Audio-Duration', 'X-Audio-Duration-Formatted',
            'X-Audio-File-Size', 'X-Audio-File-Size-MB'
        ])
    
    return response


def update_job_status(request, user_id):
    """Update job status and stop bot if status is Completed or Failed"""
    try:
        data = request.json
        job_id = data.get("job_id")
        new_status = data.get("status")
        
        if not job_id or not new_status:
            return jsonify({"error": "job_id and status are required"}), 400
            
        if new_status not in ["Completed", "Failed", "In Progress"]:
            return jsonify({"error": "Invalid status. Must be 'Completed', 'Failed', or 'In Progress'"}), 400
            
        # Get job and verify ownership
        job = JobModel.query.filter_by(job_id=job_id, user_id=user_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
            
        # Update job status
        job.status = new_status
        if new_status in ["Completed", "Failed"]:
            job.ended_at = get_ist_now()
            if new_status == "Failed":
                job.error_message = data.get("error_message", "Manually marked as failed")
                
            # Stop the bot task if it's running
            try:
                stop_bot_task(job_id)
                logger.info(f"Sent stop signal for job {job_id}")
            except Exception as e:
                logger.warning(f"Could not stop bot task for job {job_id}: {e}")
        
        db.session.commit()
        
        return jsonify({
            "message": f"Job status updated to {new_status}",
            "job_id": job_id,
            "status": new_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating job status: {str(e)}")
        return jsonify({"error": f"Failed to update job status: {str(e)}"}), 500


def list_recordings(user_id):
    """List all recording files for a specific user with id, name, time, and metadata"""
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
            filename = (
                os.path.basename(recording.audio_path)
                if recording.audio_path
                else f"recording_{recording.job_id}.mp3"
            )

            # Get audio metadata if recording is completed
            metadata = None
            if recording.status == "Completed" and recording.audio_path:
                # Fix path issues - normalize and handle container paths
                audio_path = recording.audio_path
                
                # Remove duplicate /app/ prefix if it exists
                if audio_path.startswith("/app/app/"):
                    audio_path = audio_path.replace("/app/app/", "/app/")
                
                # Handle relative paths - convert to absolute if needed
                if not audio_path.startswith("/"):
                    audio_path = os.path.join(os.getcwd(), audio_path)
                
                # Get metadata if file exists
                if os.path.exists(audio_path):
                    metadata = get_audio_metadata(audio_path)

            recordings_list.append(
                {
                    "id": recording.job_id,
                    "name": filename,
                    "created_at": (
                        recording.created_at.isoformat()
                        if recording.created_at
                        else None
                    ),
                    "created_at_formatted": (
                        recording.created_at.strftime("%d-%m-%Y %I:%M %p")
                        if recording.created_at
                        else None
                    ),
                    "status": recording.status,
                    "meeting_url": recording.job_url,
                    "platform": recording.platform,
                    "metadata": metadata,  # Include audio metadata
                    "recording_available": bool(metadata),  # Quick check for frontend
                }
            )

        return (
            jsonify(
                {"recordings": recordings_list, "total_count": len(recordings_list)}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to list recordings: {str(e)}"}), 500
