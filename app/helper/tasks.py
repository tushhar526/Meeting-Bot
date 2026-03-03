from app.models.jobModel import JobModel, get_ist_now
from app.logic.BaseBot import BaseBot
from app.extension import celery, db
from datetime import datetime, timedelta


@celery.task
def start_bot(job_id, audio_path, job_url):
    job = JobModel.query.filter_by(job_id=job_id).first()
    
    if not job:
        return {"error": "Job not found"}
    
    try:
        # Update job status to "In Progress"
        job.status = "In Progress"
        job.started_at = get_ist_now()
        db.session.commit()
        
        # Run the bot recording
        bot = BaseBot(job_id, job_url, audio_path)
        bot.run()
        
        # Update job status to "Completed" when done
        job.status = "Completed"
        job.ended_at = get_ist_now()
        db.session.commit()
        
        return {"status": "completed", "job_id": job_id}
        
    except Exception as e:
        # Update job status to "Failed" if there's an error
        job.status = "Failed"
        job.ended_at = get_ist_now()
        db.session.commit()
        
        return {"status": "failed", "job_id": job_id, "error": str(e)}
