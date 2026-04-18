import redis.asyncio as redis
from app.core import setting

redis_client = redis.from_url(setting.REDIS_URL, decode_responses=True)
