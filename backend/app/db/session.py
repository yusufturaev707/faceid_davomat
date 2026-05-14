from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# psycopg2/libpq connect_args — idle ulanish "yarim ochiq" (half-open) holatga
# tushib qolganda so'rov cheksiz osilib qolishining oldini oladi:
#   - connect_timeout: yangi ulanish o'rnatish uchun cap (DB unreachable bo'lsa
#     ham tez xato beradi, osilmaydi).
#   - keepalives*: pooldagi idle ulanishlarni tirik tutadi (NAT mapping warm
#     qoladi) va o'lgan socketni ~80s ichida aniqlaydi: 30 + 10*5. Shusiz
#     yarim ochiq socketdagi `SELECT 1` (pool_pre_ping) TCP retransmit
#     timeout'igacha (Linux'da 15+ daqiqa) blok bo'lib turardi.
#   - statement_timeout: server tomonida har bir so'rov uchun qattiq limit —
#     hech qanday so'rov "pending" bo'lib cheksiz qolib ketmaydi.
_connect_args = {
    "connect_timeout": settings.DB_CONNECT_TIMEOUT,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "options": f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}",
}

engine = create_engine(
    settings.DATABASE_URL,
    # Har checkout'da ulanish tirikligini tekshiradi (yengil ping).
    pool_pre_ping=True,
    # Ulanish shu yoshdan oshsa — checkout'da yangisi bilan almashtiriladi.
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    # Pool to'lganda yangi so'rov bu qadar kutadi, keyin xato beradi
    # (cheksiz kutib osilib qolmaydi).
    pool_timeout=settings.DB_POOL_TIMEOUT,
    # LIFO — kichik "issiq" ishchi to'plamni ushlab turadi, qolgan ulanishlar
    # tabiiy ravishda pool_recycle orqali eskirib yangilanadi.
    pool_use_lifo=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
