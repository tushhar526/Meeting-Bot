# Import all tasks to ensure they are registered with Celery
from .transcriptTasks import transcribe_audio
from .bot_tasks import *
