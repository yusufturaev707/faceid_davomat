"""HTTP security headers middleware + double-submit CSRF helperi.

Headerlar OWASP Secure Headers Project tavsiyalariga muvofiq.
"""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_SECURITY_HEADERS = {
    # Faqat HTTPS — 1 yil
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # MIME sniffing himoyasi
    "X-Content-Type-Options": "nosniff",
    # Clickjacking himoyasi (CSP frame-ancestors yetarli, lekin legacy clientlar uchun)
    "X-Frame-Options": "DENY",
    # Referrer info ozaytirish
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Browser feature siyosati
    "Permissions-Policy": (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    ),
    # CSP — API JSON qaytaradi, JS yuklanmaydi (admin UI alohida origin'da).
    # frame-ancestors=none clickjacking himoyasi.
    "Content-Security-Policy": (
        "default-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Har bir javobga xavfsizlik headerlarini qo'shadi."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


# === CSRF (double-submit cookie) ===
#
# Refresh endpoint uchun himoya:
# - Login/refresh/logoutda yangi `csrf_token` cookie (HttpOnly emas) qo'yiladi.
# - Frontend uni o'qib, `X-CSRF-Token` header'ida yuboradi.
# - Server cookie qiymati == header qiymati ekanini tekshiradi.
#
# SameSite=lax bilan birga ishlaganda double-submit pattern CSRF'dan saqlaydi.

CSRF_COOKIE_KEY = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def generate_csrf_token() -> str:
    """Cryptographically random token."""
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request) -> None:
    """CSRF tekshiruvi. Production'da CSRF_PROTECTION_ENABLED=True bo'lsa ishlaydi.

    Cookie va headerdagi qiymatlarni constant-time taqqoslaydi.
    """
    from app.config import settings

    if not settings.CSRF_PROTECTION_ENABLED:
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_KEY)
    header_token = request.headers.get(CSRF_HEADER)
    if not cookie_token or not header_token:
        from fastapi import HTTPException, status as http_status

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="CSRF token topilmadi",
        )
    if not secrets.compare_digest(cookie_token, header_token):
        from fastapi import HTTPException, status as http_status

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="CSRF token mos kelmadi",
        )
