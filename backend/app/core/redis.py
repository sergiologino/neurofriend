import redis.asyncio as redis

from app.core.config import get_settings

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    global _redis
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis
