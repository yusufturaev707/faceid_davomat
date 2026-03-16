from sqlalchemy import text
from app.db.session import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    print("Current:", [r[0] for r in result])
    conn.execute(
        text("UPDATE alembic_version SET version_num = :new WHERE version_num = :old"),
        {"new": "5a684258487e", "old": "eafc580c32d0"},
    )
    conn.commit()
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    print("Updated:", [r[0] for r in result])
