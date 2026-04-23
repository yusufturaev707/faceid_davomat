"""Centralized permission catalog.

Barcha permission codename'lar shu yerda belgilanadi. Endpoint'larda
`PermissionChecker(P.USER_READ)` ko'rinishida ishlatiladi. Seed script
shu ro'yxatdan DB ga yozadi — manba bitta (single source of truth).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _Perm:
    code: str
    name: str
    group: str

    def __str__(self) -> str:
        return self.code


class P:
    # === Dashboard ===
    DASHBOARD_READ = _Perm("dashboard:read", "Dashboard ko'rish", "dashboard")
    DASHBOARD_STATS = _Perm("dashboard:stats", "Dashboard statistikasi", "dashboard")

    # === Verification logs ===
    LOG_READ = _Perm("log:read", "Tekshiruv loglarini ko'rish", "log")
    LOG_DELETE = _Perm("log:delete", "Tekshiruv logini o'chirish", "log")

    # === Face comparison logs ===
    FACE_LOG_READ = _Perm("face_log:read", "Yuz solishtirish loglarini ko'rish", "face_log")
    FACE_LOG_DELETE = _Perm("face_log:delete", "Yuz solishtirish logini o'chirish", "face_log")

    # === API Keys ===
    API_KEY_READ = _Perm("api_key:read", "API kalitlarni ko'rish", "api_key")
    API_KEY_CREATE = _Perm("api_key:create", "API kalit yaratish", "api_key")
    API_KEY_DELETE = _Perm("api_key:delete", "API kalitni bekor qilish", "api_key")

    # === Users ===
    USER_READ = _Perm("user:read", "Foydalanuvchilarni ko'rish", "user")
    USER_CREATE = _Perm("user:create", "Foydalanuvchi yaratish", "user")
    USER_UPDATE = _Perm("user:update", "Foydalanuvchini tahrirlash", "user")
    USER_DELETE = _Perm("user:delete", "Foydalanuvchini o'chirish", "user")

    # === Roles ===
    ROLE_READ = _Perm("role:read", "Rollarni ko'rish", "role")
    ROLE_CREATE = _Perm("role:create", "Rol yaratish", "role")
    ROLE_UPDATE = _Perm("role:update", "Rolni tahrirlash va permission biriktirish", "role")
    ROLE_DELETE = _Perm("role:delete", "Rolni o'chirish", "role")

    # === Permissions (meta) ===
    PERMISSION_READ = _Perm("permission:read", "Huquqlarni ko'rish", "permission")
    PERMISSION_CREATE = _Perm("permission:create", "Huquq yaratish", "permission")
    PERMISSION_UPDATE = _Perm("permission:update", "Huquqni tahrirlash", "permission")
    PERMISSION_DELETE = _Perm("permission:delete", "Huquqni o'chirish", "permission")

    # === Test Sessions ===
    TEST_SESSION_READ = _Perm("test_session:read", "Test sessiyalarni ko'rish", "test_session")
    TEST_SESSION_CREATE = _Perm("test_session:create", "Test sessiya yaratish", "test_session")
    TEST_SESSION_UPDATE = _Perm("test_session:update", "Test sessiyani tahrirlash", "test_session")
    TEST_SESSION_DELETE = _Perm("test_session:delete", "Test sessiyani o'chirish", "test_session")

    # === Students ===
    STUDENT_READ = _Perm("student:read", "Studentlarni ko'rish", "student")
    STUDENT_CREATE = _Perm("student:create", "Student yaratish", "student")
    STUDENT_UPDATE = _Perm("student:update", "Studentni tahrirlash", "student")
    STUDENT_DELETE = _Perm("student:delete", "Studentni o'chirish", "student")

    # === Student Logs ===
    STUDENT_LOG_READ = _Perm("student_log:read", "Student loglarini ko'rish", "student_log")
    STUDENT_LOG_CREATE = _Perm("student_log:create", "Student log yaratish (desktop sync ham)", "student_log")
    STUDENT_LOG_UPDATE = _Perm("student_log:update", "Student logni tahrirlash", "student_log")
    STUDENT_LOG_DELETE = _Perm("student_log:delete", "Student logni o'chirish", "student_log")

    # === Cheating Logs ===
    CHEATING_LOG_READ = _Perm("cheating_log:read", "Qoidabuzarlik loglarini ko'rish", "cheating_log")
    CHEATING_LOG_CREATE = _Perm("cheating_log:create", "Qoidabuzarlik yozish", "cheating_log")
    CHEATING_LOG_UPDATE = _Perm("cheating_log:update", "Qoidabuzarlikni tahrirlash", "cheating_log")
    CHEATING_LOG_DELETE = _Perm("cheating_log:delete", "Qoidabuzarlikni o'chirish", "cheating_log")

    # === Lookup tables (tests, smenas, session_states, regions, zones, reasons, reason_types, blacklist, genders) ===
    LOOKUP_READ = _Perm("lookup:read", "Ma'lumotnomalarni ko'rish", "lookup")
    LOOKUP_CREATE = _Perm("lookup:create", "Ma'lumotnoma yozuvi yaratish", "lookup")
    LOOKUP_UPDATE = _Perm("lookup:update", "Ma'lumotnoma yozuvini tahrirlash", "lookup")
    LOOKUP_DELETE = _Perm("lookup:delete", "Ma'lumotnoma yozuvini o'chirish", "lookup")


ALL_PERMISSIONS: list[_Perm] = [
    value
    for name, value in vars(P).items()
    if not name.startswith("_") and isinstance(value, _Perm)
]


def all_codenames() -> list[str]:
    return [p.code for p in ALL_PERMISSIONS]
