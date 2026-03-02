from app.models.jobModel import JobModel
from app.logic.BaseBot import BaseBot
from app.extension import celery, db


@celery.task
def start_bot(job_id, audio_path, job_url):
    job = JobModel.query.filter_by(job_id=job_id).first()

    bot = BaseBot(job_id, job_url, audio_path)
    bot.run()

    db.session.commit()
    return
