from app.models.jobModel import JobModel, get_ist_now
from app.logic.BaseBot import BaseBot
from app.extension import celery, db
from datetime import datetime, timedelta
import logging
import time

# Global registry to track active bot instances
active_bots = {}

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def start_bot(self, job_id, audio_path, job_url):
    # Use FOR UPDATE to lock the row and prevent duplicate processing
    job = JobModel.query.filter_by(job_id=job_id).with_for_update().first()
    
    if not job:
        return {"error": "Job not found"}
    
    # Check if job is already being processed
    if job.status in ["In Progress", "Completed"]:
        logger.info(f"Job {job_id} already being processed or completed (status: {job.status})")
        return {"status": "skipped", "job_id": job_id, "reason": f"Job already {job.status.lower()}"}
    
    bot = None
    try:
        # Update job status to "In Progress" atomically
        job.status = "In Progress"
        job.started_at = get_ist_now()
        db.session.commit()
        
        # Create and store bot instance
        bot = BaseBot(job_id, job_url, audio_path)
        active_bots[job_id] = bot
        
        # Run bot recording
        bot_success = bot.run()
        
        # Update job status based on result
        if bot_success:
            job.status = "Completed"
        else:
            job.status = "Failed"
            
        job.ended_at = get_ist_now()
        db.session.commit()
        
        return {"status": job.status.lower(), "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Bot task failed for job {job_id}: {str(e)}")
        
        # Clean up bot instance
        if job_id in active_bots:
            del active_bots[job_id]
        
        # Update job status to "Failed"
        try:
            db.session.rollback()
            job.status = "Failed"
            job.ended_at = get_ist_now()
            job.error_message = str(e)
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update job status: {commit_error}")
            
            # Retry the entire task for database errors
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    
    finally:
        # Ensure bot is removed from active bots
        if job_id in active_bots:
            del active_bots[job_id]


def stop_bot_task(job_id):
    """Stop a running bot task by job_id"""
    try:
        if job_id in active_bots:
            bot = active_bots[job_id]
            logger.info(f"Stopping bot for job {job_id}")
            bot.stop()
            del active_bots[job_id]
            return True
        else:
            logger.warning(f"No active bot found for job {job_id}")
            return False
    except Exception as e:
        logger.error(f"Error stopping bot for job {job_id}: {e}")
        return False
