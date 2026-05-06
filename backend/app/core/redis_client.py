"""Redis client + token blacklist + login lockout helperlari.

JWT'ni stateless deb biluvchi joylarda blacklist Redis'da `jti` orqali ishlaydi.
TTL token'ning `exp` qiymatiga teng — eskirgan jti'lar avtomatik o'chiriladi.
"""

import logging
import time
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger("faceid.core.redis")

_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Singleton Redis client (decode_responses=True)."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


# === JWT Blacklist (jti) ===

_BLACKLIST_KEY = "jwt:bl:{jti}"


def blacklist_jti(jti: str, exp_ts: int) -> None:
    """jti'ni blacklist'ga qo'shish. TTL = (exp - now)."""
    ttl = exp_ts - int(time.time())
    if ttl <= 0:
        return
    try:
        get_redis().setex(_BLACKLIST_KEY.format(jti=jti), ttl, "1")
    except redis.RedisError:
        logger.warning("Redis blacklist yozish xatoligi (jti=%s)", jti)


def is_jti_blacklisted(jti: str) -> bool:
    """Redis ulanish xatosi = bloklanmagan deb qaraladi (fail-open).

    Bu auth bypass emas, chunki access token TTL qisqa (15 daqiqa).
    """
    try:
        return get_redis().exists(_BLACKLIST_KEY.format(jti=jti)) == 1
    except redis.RedisError:
        logger.warning("Redis blacklist tekshiruv xatoligi (jti=%s)", jti)
        return False


# === Login lockout (per username) ===

_FAIL_KEY = "login:fail:{username}"
_LOCK_KEY = "login:lock:{username}"


def _norm_username(username: str) -> str:
    return (username or "").strip().lower()


def is_login_locked(username: str) -> bool:
    try:
        return get_redis().exists(_LOCK_KEY.format(username=_norm_username(username))) == 1
    except redis.RedisError:
        return False


def register_login_failure(username: str) -> int:
    """Failed urinishni qayd qilish. Limit oshib ketsa, lockout qo'yiladi.

    Returns: hozirgi failure soni.
    """
    uname = _norm_username(username)
    try:
        r = get_redis()
        key = _FAIL_KEY.format(username=uname)
        count = r.incr(key)
        if count == 1:
            r.expire(key, settings.LOGIN_LOCKOUT_WINDOW_SECONDS)
        if count >= settings.LOGIN_LOCKOUT_MAX_ATTEMPTS:
            r.setex(
                _LOCK_KEY.format(username=uname),
                settings.LOGIN_LOCKOUT_DURATION_SECONDS,
                "1",
            )
            logger.warning(
                "Login lockout: username=%s, attempts=%d",
                uname,
                count,
            )
        return count
    except redis.RedisError:
        return 0


def reset_login_failures(username: str) -> None:
    """Muvaffaqiyatli login'dan keyin counter va lockout'ni tozalash."""
    uname = _norm_username(username)
    try:
        r = get_redis()
        r.delete(_FAIL_KEY.format(username=uname), _LOCK_KEY.format(username=uname))
    except redis.RedisError:
        pass
