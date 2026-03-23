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
    
    # PLAN ACCESS CHECK - Centralized protection for both manual and automatic creation
    try:
        from app.models.userModel import userModel
        from app.helper.plan_access import PlanConfig
        
        user = userModel.query.filter_by(user_id=job.user_id).first()
        if not user:
            return {"error": "User not found", "access_denied": True}
        
        # Super admins bypass all restrictions
        if not user.is_super_admin():
            # Check active subscription
            if not user.has_active_subscription():
                logger.warning(f"Bot access denied - no active subscription: user {job.user_id}, job {job_id}")
                job.status = "Failed"
                job.error_message = "Access denied: No active subscription"
                job.ended_at = get_ist_now()
                db.session.commit()
                return {"status": "failed", "job_id": job_id, "error": "Access denied: No active subscription", "access_denied": True}
            
            # Check plan access for recording feature
            if user.plan and not PlanConfig.has_feature_access(user.plan.plan_type, 'recording'):
                logger.warning(f"Bot access denied - recording not in plan: user {job.user_id}, plan {user.plan.plan_type.value}, job {job_id}")
                job.status = "Failed"
                job.error_message = "Access denied: Recording not available in your plan"
                job.ended_at = get_ist_now()
                db.session.commit()
                return {"status": "failed", "job_id": job_id, "error": "Access denied: Recording not available in your plan", "access_denied": True}
            
            # Check meeting limits
            plan_limits = PlanConfig.get_plan_limits(user.plan.plan_type)
            max_meetings = plan_limits['max_meetings']
            if not plan_limits['unlimited_meetings'] and max_meetings is not None:
                if user.meetings >= max_meetings:
                    logger.warning(f"Bot access denied - meeting limit exceeded: user {job.user_id}, limit {max_meetings}, job {job_id}")
                    job.status = "Failed"
                    job.error_message = f"Access denied: Meeting limit ({max_meetings}) exceeded"
                    job.ended_at = get_ist_now()
                    db.session.commit()
                    return {"status": "failed", "job_id": job_id, "error": f"Access denied: Meeting limit ({max_meetings}) exceeded", "access_denied": True}
        
        logger.info(f"Bot access granted: user {job.user_id}, job {job_id}")
        
    except Exception as e:
        logger.error(f"Plan access check failed for job {job_id}, user {job.user_id}: {e}")
        job.status = "Failed"
        job.error_message = "Access check failed"
        job.ended_at = get_ist_now()
        db.session.commit()
        return {"status": "failed", "job_id": job_id, "error": "Access check failed", "access_denied": True}
    
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
