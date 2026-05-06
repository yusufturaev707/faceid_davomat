# Xavfsizlik tuzatishlari — deployment qadamlari

Quyidagi 26 ta zaiflik tuzatildi. Ishga tushirishdan oldin shu qadamlarni bajaring.

## 1. .env yangilash

`.env` fayli endi git'da bo'lmasligi kerak (gitignore'ga qo'shildi). Quyidagi yangi
sozlamalar talab qilinadi:

```
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
API_KEY_PEPPER=<python -c "import secrets; print(secrets.token_urlsafe(48))">
ACCESS_TOKEN_EXPIRE_MINUTES=15
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES=10
JWT_ISSUER=faceid-api
COOKIE_SECURE=true
LOGIN_LOCKOUT_MAX_ATTEMPTS=5
LOGIN_LOCKOUT_WINDOW_SECONDS=900
LOGIN_LOCKOUT_DURATION_SECONDS=900
CSRF_PROTECTION_ENABLED=true
METRICS_AUTH_TOKEN=<token yoki bo'sh — endpointni o'chirish uchun>
COOKIE_DOMAIN=
```

> ⚠ Eski `SECRET_KEY` va `API_KEY_PEPPER` qiymatlari placeholder bo'lganligi
> sababli **app endi ishga tushmaydi** — yangi qiymat berishga majbursiz.

## 2. DB migratsiya

`refresh_tokens` jadvali strukturasi o'zgardi:
- `token` (plaintext) → `token_hash` (SHA-256)
- yangi: `family_id`, `replaced_by_hash`, `reuse_detected_at`

**Eski tokenlar bilan moslik yo'q** — barcha sessiyalar invalidate bo'ladi.
Foydalanuvchilar qayta login qiladi.

```bash
cd backend
alembic revision --autogenerate -m "refresh_token_hash_and_family"
alembic upgrade head
```

Yoki hozircha test/dev uchun:
```bash
psql -d faceid_db -c "DROP TABLE refresh_tokens;"
# keyin app start qilinganda Base.metadata.create_all chaqiriladi (agar create_all ishlatilsa)
# yoki alembic
```

## 3. Admin paroli

`db/seed.py` endi `123` ni qabul qilmaydi. Birinchi seed paytida random parol
chiqariladi (yoki `ADMIN_INITIAL_PASSWORD` env'dan olinadi).

```bash
ADMIN_INITIAL_PASSWORD='StrongPass123' python -m app.db.seed
```

Mavjud admin paroli `123` bo'lsa, kuchli parolga yangilang:
```sql
-- Yoki API orqali: PATCH /admin/users/{id} {"password": "..."}
UPDATE users SET hashed_password = '<bcrypt>' WHERE username = 'admin';
```

## 4. Frontend yangilash

`/auth/refresh` va `/auth/logout` endi **CSRF token** talab qiladi.
Frontend axios interceptor avtomatik `X-CSRF-Token` header yuboradi (cookie'dan
o'qib). Hech qanday qo'shimcha sozlash kerak emas, lekin **brauzer cache'ni
tozalash** kerak (eski sessiyalarda CSRF cookie yo'q).

## 5. Redis

Login lockout va JWT blacklist Redis'ni talab qiladi (Celery uchun ham
ishlatiladi — qo'shimcha resurs kerak emas).

## 6. Production checklist

- [ ] `COOKIE_SECURE=true` (HTTPS terminator orqali)
- [ ] `CORS_ORIGINS` aniq production domain (no wildcard)
- [ ] `METRICS_AUTH_TOKEN` o'rnatilgan yoki bo'sh (endpoint o'chiriladi)
- [ ] HTTPS reverse proxy oldida (nginx/caddy) — HSTS header allaqachon backenddan keladi
- [ ] Default admin paroli o'zgartirilgan
- [ ] `.env` git'da emas: `git ls-files | grep .env` faqat `.env.example` ko'rsatishi kerak
- [ ] `API_IIV_TOKEN` rotatsiya qilingan (eski token git history'da bo'lgan)

## Tuzatilgan zaifliklar

1. ✅ Hardcoded zaif SECRET_KEY/PEPPER → kuchli random + config validator
2. ✅ COOKIE_SECURE=false → true
3. ✅ ACCESS_TOKEN_EXPIRE_MINUTES=1 → 15 (admin: 10)
4. ✅ Refresh token plaintext → SHA-256 hash
5. ✅ Reuse detection → token-family + replaced_by_hash
6. ✅ Parol o'zgartirilganda token revoke
7. ✅ is_active=false rotate qila olmaydi
8. ✅ Login rate limit 50→5/min + per-username lockout
9. ✅ Username enumeration timing fix (dummy bcrypt)
10. ✅ delete_user 1000→10/min
11. ✅ update_user 200→20/min
12. ✅ CSRF double-submit token
13. ✅ JWT'da jti, iat, nbf, iss
14. ✅ Access token Redis blacklist (logout darhol)
15. ✅ Rate limit identity key — JWT sub
16. ✅ API key rate limit — SHA-256 prefix (collision-free)
17. ✅ HSTS, X-Frame, CSP, Referrer-Policy headers
18. ✅ CORS — explicit headers + expose_headers
19. ✅ Password policy 6→8 + complexity (upper/lower/digit)
20. ✅ Default admin parol — random yoki env
21. ✅ update_user username unique tekshiruv
22. ✅ Admin uchun qisqaroq access token TTL
23. (skipped) 2FA — alohida feature
24. ✅ Login failure audit Redis counter
25. ✅ JWT + API key bir vaqtda bersa 400
26. ✅ Refresh grace period olib tashlandi (replaced_by_hash bilan replaced)
27. (already OK) sessionStorage XSS scope
28. ✅ Frontend onUnauthorized debounce
29. ✅ /metrics token-protected
30. ✅ .env gitignore'da
