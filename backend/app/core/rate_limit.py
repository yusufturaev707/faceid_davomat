"""Rate limiting (slowapi).

Identity key:
- API key bo'lsa — `apikey:{db_id}` (DB id'sini cache orqali olamiz)
  Agar DB id bo'lmasa, raw key'ning hash'ining birinchi 16 belgisi (collision-resistant).
- JWT Bearer bo'lsa — `user:{sub}` (decoded). JWT header'i bir xil bo'lgani uchun
  oddiy slice o'rniga `sub` claim ishlatamiz.
- Aks holda — IP.
"""

import hashlib
import logging

from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("faceid.core.rate_limit")


def _identity_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        # SHA-256 prefiksi — collision ehtimoli juda past, raw kalitni log'ga chiqarmaydi
        digest = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"apikey:{digest}"

    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            # Faqat sub claim kerak — verification light (alg whitelist va iss strict)
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                issuer=settings.JWT_ISSUER,
                options={"verify_exp": False, "require": ["sub"]},
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            # Yaroqsiz token — IP bo'yicha cheklash
            pass

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_identity_key, default_limits=[])
