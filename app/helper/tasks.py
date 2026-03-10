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
    job = JobModel.query.filter_by(job_id=job_id).first()
    
    if not job:
        return {"error": "Job not found"}
    
    try:
        # Update job status to "In Progress"
        job.status = "In Progress"
        job.started_at = get_ist_now()
        
        # Helper function for safe commit with retry
        def safe_commit(max_attempts=3):
            for attempt in range(max_attempts):
                try:
                    db.session.commit()
                    return True
                except Exception as commit_error:
                    logger.warning(f"Commit attempt {attempt + 1} failed: {commit_error}")
                    if attempt < max_attempts - 1:
                        try:
                            db.session.rollback()
                            time.sleep(0.5)  # Brief pause before retry
                        except Exception:
                            pass
                    else:
                        raise commit_error
            return False
        
        # Commit initial status
        if not safe_commit():
            raise Exception("Failed to commit initial job status after multiple attempts")
        
        # Create and store bot instance
        bot = BaseBot(job_id, job_url, audio_path)
        active_bots[job_id] = bot
        
        # Run bot recording
        bot_success = bot.run()
        
        # Remove from active bots when done
        if job_id in active_bots:
            del active_bots[job_id]
        
        # Update job status based on bot result
        if bot_success:
            job.status = "Completed"
            job.ended_at = get_ist_now()
            
            # Commit completion status
            if not safe_commit():
                raise Exception("Failed to commit completion status after multiple attempts")
            
            return {"status": "completed", "job_id": job_id}
        else:
            # Bot failed - status already set to "Failed" by BaseBot
            # Just ensure proper cleanup and commit
            job.ended_at = get_ist_now()
            if not safe_commit():
                raise Exception("Failed to commit failure status after multiple attempts")
            
            return {"status": "failed", "job_id": job_id, "error": "Bot execution failed"}
        
    except Exception as e:
        logger.error(f"Bot task failed for job {job_id}: {str(e)}")
        
        # Remove from active bots on error
        if job_id in active_bots:
            del active_bots[job_id]
        
        # For database-related errors, retry task
        if "disk I/O error" in str(e).lower() or "database" in str(e).lower():
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying task {job_id} due to database error (attempt {self.request.retries + 1})")
                raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        # Make sure we have a clean session before updating error status
        try:
            db.session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        
        # Update job status to "Failed" if there's an error
        try:
            job.status = "Failed"
            job.ended_at = get_ist_now()
            job.error_message = str(e)
            
            # Try to commit error status
            if not safe_commit(max_attempts=2):  # Fewer attempts for error status
                logger.error("Failed to commit error status")
        except Exception as final_error:
            logger.error(f"Failed to update job status: {final_error}")
        
        return {"status": "failed", "job_id": job_id, "error": str(e)}


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
