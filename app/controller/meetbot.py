from app.models.jobModel import JobModel
from datetime import datetime
from app.extension import db
from app.logic.BaseBot import BaseBot
from app.extension import celery


def create_bot(meeting_url):
    job = JobModel(job_url=meeting_url)

    db.session.add(job)
    db.session.commit()

    return job


@celery.task
def start_bot(job_id):
    job = JobModel.query.filter_by(job_id=job_id).first()
    print("YEAH DIS LINE GOT EXECUTED")

    job.started_at = datetime.now()
    bot = BaseBot(job.job_id, job.job_url)
    success = bot.run()
    job.ended_at = datetime.now()

    if success:
        job.audio_path = f"app/recording/{job.job_id}"
        job.status = "completed"
    else:
        job.status = "failed"

    db.session.commit()
    return success
