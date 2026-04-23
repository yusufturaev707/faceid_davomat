"""Rate limiting (slowapi) — login/verify brute-force himoyasi.

Limits:
- login: 5 / 1 daqiqa per IP (brute-force himoyasi)
- photo_verify: 30 / 1 daqiqa per identity (API key yoki user)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _identity_key(request: Request) -> str:
    """API key bo'lsa uni, bo'lmasa user-id, bo'lmasa IP ni olish."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"apikey:{api_key[:12]}"
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return f"bearer:{auth[7:27]}"
    return get_remote_address(request)


limiter = Limiter(key_func=_identity_key, default_limits=[])
