import redis
from app.core.config import setting

# Synchronous Redis client for use in Celery tasks and sync contexts
redis_client = redis.from_url(setting.REDIS_URL, decode_responses=True)
