from app import create_app
from app.extension import celery
from dotenv import load_dotenv

load_dotenv()

app = create_app()


class FlaskTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = FlaskTask
