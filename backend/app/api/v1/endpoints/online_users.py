"""Online foydalanuvchilar — aktiv login sessiyalari va qurilmalar.

Manba: `refresh_tokens` jadvali. Har bir aktiv (revoke qilinmagan, muddati
tugamagan) refresh token oilasi (`family_id`) — bitta qurilmadagi (device)
login sessiyasini bildiradi. Rotatsiyada `family_id` o'zgarmaydi, eski token
revoke qilinadi — shu sababli har oilada bitta aktiv token bo'ladi va uning
`created_at` qiymati shu qurilmadagi oxirgi faollik vaqtini ko'rsatadi.

"Online" — oxirgi faollik (rotatsiya) `ONLINE_WINDOW_MINUTES` ichida bo'lsa.
Oyna access-token amal qilish muddatidan kengroq olinadi, chunki ilova ochiq
turganda refresh token taxminan access-token muddatida bir marta yangilanadi.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.permissions import P
from app.dependencies import PermissionChecker, get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User

router = APIRouter()

# Online deb hisoblanish oynasi — eng katta access-token muddati + zaxira.
# Ilova ochiq bo'lganda refresh token shu oraliqda yangilanib turadi.
ONLINE_WINDOW_MINUTES = (
    max(
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    + 15
)


class OnlineDevice(BaseModel):
    """Bitta qurilmadagi (token oilasi) login sessiyasi."""

    family_id: str
    first_login: datetime
    last_active: datetime
    expires_at: datetime
    is_online: bool


class OnlineUser(BaseModel):
    """Aktiv sessiyasi bor foydalanuvchi va uning qurilmalari."""

    user_id: int
    username: str
    full_name: str | None
    role: str
    device_count: int
    online_device_count: int
    last_active: datetime
    is_online: bool
    devices: list[OnlineDevice]


class OnlineUsersResponse(BaseModel):
    online_users: int
    total_users_with_sessions: int
    online_devices: int
    total_devices: int
    window_minutes: int
    users: list[OnlineUser]


@router.get(
    "/online-users",
    response_model=OnlineUsersResponse,
    summary="Online foydalanuvchilar va ularning qurilmalari",
)
def list_online_users(
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.USER_READ.code)),
):
    """Hozir aktiv login sessiyasi (refresh token) bor foydalanuvchilar.

    Har bir foydalanuvchi uchun qurilmalar soni, oxirgi faollik vaqti va
    qaysilari online (oxirgi `window_minutes` daqiqada faol) ekani qaytariladi.
    Username tanlanganda frontend shu javobdagi `devices` ro'yxatini ochadi.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=ONLINE_WINDOW_MINUTES)

    rows = db.execute(
        select(
            RefreshToken.user_id,
            RefreshToken.family_id,
            RefreshToken.created_at,
            RefreshToken.expires_at,
        ).where(
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        )
    ).all()

    # (user_id, family_id) bo'yicha agregatsiya: first/last faollik va muddat.
    fam: dict[tuple[int, str], dict] = {}
    for user_id, family_id, created_at, expires_at in rows:
        key = (int(user_id), str(family_id))
        cur = fam.get(key)
        if cur is None:
            fam[key] = {
                "first_login": created_at,
                "last_active": created_at,
                "expires_at": expires_at,
            }
        else:
            if created_at < cur["first_login"]:
                cur["first_login"] = created_at
            if created_at > cur["last_active"]:
                cur["last_active"] = created_at
            if expires_at > cur["expires_at"]:
                cur["expires_at"] = expires_at

    # Foydalanuvchi bo'yicha qurilmalarni guruhlash
    devices_by_user: dict[int, list[OnlineDevice]] = defaultdict(list)
    for (user_id, family_id), info in fam.items():
        is_online = info["last_active"] >= window_start
        devices_by_user[user_id].append(
            OnlineDevice(
                family_id=family_id,
                first_login=info["first_login"],
                last_active=info["last_active"],
                expires_at=info["expires_at"],
                is_online=is_online,
            )
        )

    if not devices_by_user:
        return OnlineUsersResponse(
            online_users=0,
            total_users_with_sessions=0,
            online_devices=0,
            total_devices=0,
            window_minutes=ONLINE_WINDOW_MINUTES,
            users=[],
        )

    user_ids = list(devices_by_user.keys())
    user_map = {
        u.id: u
        for u in db.execute(select(User).where(User.id.in_(user_ids)))
        .scalars()
        .unique()
    }

    users: list[OnlineUser] = []
    online_devices = 0
    total_devices = 0
    online_users = 0
    for user_id, devices in devices_by_user.items():
        u = user_map.get(user_id)
        if u is None:
            continue
        devices.sort(key=lambda d: d.last_active, reverse=True)
        online_count = sum(1 for d in devices if d.is_online)
        last_active = max(d.last_active for d in devices)
        is_online = online_count > 0
        total_devices += len(devices)
        online_devices += online_count
        if is_online:
            online_users += 1
        users.append(
            OnlineUser(
                user_id=user_id,
                username=u.username,
                full_name=u.full_name,
                role=u.role or "",
                device_count=len(devices),
                online_device_count=online_count,
                last_active=last_active,
                is_online=is_online,
                devices=devices,
            )
        )

    # Online'lar tepada, so'ng oxirgi faollik bo'yicha
    users.sort(key=lambda x: (x.is_online, x.last_active), reverse=True)

    return OnlineUsersResponse(
        online_users=online_users,
        total_users_with_sessions=len(users),
        online_devices=online_devices,
        total_devices=total_devices,
        window_minutes=ONLINE_WINDOW_MINUTES,
        users=users,
    )
