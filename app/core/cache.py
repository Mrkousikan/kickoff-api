import json
import redis.asyncio as aioredis
from typing import Any, Optional
from app.core.config import get_settings

settings = get_settings()
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass
