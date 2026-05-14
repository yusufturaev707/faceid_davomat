from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings

# psycopg2/libpq connect_args — bular ULANISH darajasidagi parametrlar
# (startup paketida emas), shuning uchun PgBouncer orqali ham ishlaydi:
#   - connect_timeout: yangi ulanish o'rnatish uchun cap (DB unreachable
#     bo'lsa ham tez xato beradi, osilmaydi).
#   - keepalives*: pooldagi idle ulanishlarni tirik tutadi (NAT mapping warm
#     qoladi) va o'lgan socketni ~80s ichida aniqlaydi: 30 + 10*5. Shusiz
#     yarim ochiq (half-open) socketdagi `SELECT 1` (pool_pre_ping) TCP
#     retransmit timeout'igacha (Linux'da 15+ daqiqa) blok bo'lib turardi.
#
# DIQQAT: `options="-c statement_timeout=..."` BU YERGA QO'SHILMAYDI — u
# startup parametri sifatida yuboriladi va PgBouncer uni rad etadi
# ("unsupported startup parameter in options"). statement_timeout o'rniga
# pastdagi `connect` event listener ulanishdan KEYIN `SET` qiladi.
_connect_args = {
    "connect_timeout": settings.DB_CONNECT_TIMEOUT,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
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


# statement_timeout — ulanish o'rnatilgandan KEYIN oddiy `SET` bilan beriladi
# (startup parametri emas → PgBouncer rad etmaydi). PgBouncer session-pooling
# rejimida bu to'g'ridan-to'g'ri ishlaydi. transaction-pooling rejimida esa
# eng ishonchli yo'l — Postgres rolida sozlash:
#     ALTER ROLE <db_user> SET statement_timeout = '60s';
if settings.DB_STATEMENT_TIMEOUT_MS > 0:

    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_connection, connection_record):
        timeout_ms = int(settings.DB_STATEMENT_TIMEOUT_MS)
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {timeout_ms}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
