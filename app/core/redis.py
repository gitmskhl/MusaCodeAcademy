from redis.asyncio import Redis

from app.core.config import settings

redis = Redis.from_url(
    url=settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_timeout=None
)
