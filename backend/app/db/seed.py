"""Admin foydalanuvchi yaratish uchun seed script.
Ishlatish: cd backend && python -m app.db.seed
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def seed_admin():
    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.username == "admin")
        ).scalar_one_or_none()

        if existing:
            print("Admin foydalanuvchi allaqachon mavjud.")
            return

        admin = User(
            username="admin",
            hashed_password=hash_password("123"),
            full_name="Administrator",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Admin foydalanuvchi yaratildi: admin / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
