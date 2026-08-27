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

    # === Photo / Face services ===
    PHOTO_VERIFY = _Perm("photo:verify", "Rasm tekshirish", "photo")
    PHOTO_VERIFY_TWO_FACE = _Perm(
        "photo:verify_two_face", "Yuzlarni solishtirish", "photo"
    )

    # === Embedding service ===
    EMBEDDING_EXTRACT = _Perm("embedding:extract", "Embedding olish", "embedding")

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

    # === Online foydalanuvchilar (aktiv login sessiyalari) ===
    ONLINE_USERS_READ = _Perm(
        "online_users:read",
        "Online foydalanuvchilarni ko'rish",
        "online_users",
    )

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
    # Sessiya jarayonlari — `test_session:update` dan ajratilgan, chunki bular
    # og'ir fon vazifalarini (Celery) ishga tushiradi va imtihon kunida
    # ehtiyotkorlik talab qiladi.
    TEST_SESSION_LOAD_STUDENTS = _Perm(
        "test_session:load_students",
        "Talabgorlarni yuklab olish jarayonini boshlash",
        "test_session",
    )
    TEST_SESSION_EMBEDDING = _Perm(
        "test_session:embedding",
        "Face embedding jarayonini boshlash",
        "test_session",
    )
    TEST_SESSION_CANCEL_PROCESS = _Perm(
        "test_session:cancel_process",
        "Yuklash/embedding jarayonini bekor qilish",
        "test_session",
    )

    # === Students ===
    STUDENT_READ = _Perm("student:read", "Studentlarni ko'rish", "student")
    STUDENT_CREATE = _Perm("student:create", "Student yaratish", "student")
    STUDENT_UPDATE = _Perm("student:update", "Studentni tahrirlash", "student")
    STUDENT_DELETE = _Perm("student:delete", "Studentni o'chirish", "student")
    # Viloyat scope: bu ruxsat BO'LMAGAN foydalanuvchi faqat o'z
    # `region_id` idagi ma'lumotlarni ko'radi. Ilgari bu rol `key`
    # (1/2/3 global, 4 region) bo'yicha qattiq kodlangan edi — natijada
    # yangi rollar permissiondan qat'i nazar 403 olardi.
    STUDENT_ALL_REGIONS = _Perm(
        "student:all_regions",
        "Barcha viloyatlar ma'lumotlarini ko'rish (talabgor, log, qoidabuzarlik)",
        "student",
    )
    # GTSP tashqi xizmatidan rasm/FIO olish — tahrirlashdan alohida, chunki
    # bu tashqi API'ni chaqiradi va ommaviy rejimda og'ir yuk beradi.
    STUDENT_FETCH_GTSP = _Perm(
        "student:fetch_gtsp",
        "GTSP dan rasm va FIO olish",
        "student",
    )
    # Ro'yxatni fayl qilib chiqarish — ko'rishdan alohida boshqariladi:
    # eksport ma'lumotni tizimdan tashqariga olib chiqadi.
    STUDENT_EXPORT_EXCEL = _Perm(
        "student:export_excel",
        "Talabgorlar ro'yxatini Excel'ga yuklash",
        "student",
    )
    STUDENT_EXPORT_PDF = _Perm(
        "student:export_pdf",
        "Talabgorlar ro'yxatini PDF'ga yuklash",
        "student",
    )

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
    # Ro'yxatni faylga chiqarish — ko'rishdan alohida boshqariladi.
    CHEATING_LOG_EXPORT = _Perm(
        "cheating_log:export",
        "Chetlatilganlar ro'yxatini Excel'ga yuklash",
        "cheating_log",
    )

    # === Ma'lumotnomalar (Sozlamalar bo'limi) ===
    # Ilgari bularning hammasi bitta `lookup:*` guruhida edi — ya'ni bir
    # bo'limga ruxsat berish qolganlarini ham ochib yuborardi. Endi har
    # bir ma'lumotnoma o'z guruhida, alohida boshqariladi.

    REGION_READ = _Perm(
        "region:read",
        "Viloyatlarni ko'rish",
        "region",
    )
    REGION_CREATE = _Perm(
        "region:create",
        "Viloyat yaratish",
        "region",
    )
    REGION_UPDATE = _Perm(
        "region:update",
        "Viloyatni tahrirlash",
        "region",
    )
    REGION_DELETE = _Perm(
        "region:delete",
        "Viloyatni o'chirish",
        "region",
    )

    ZONE_READ = _Perm(
        "zone:read",
        "Binolarni ko'rish",
        "zone",
    )
    ZONE_CREATE = _Perm(
        "zone:create",
        "Bino yaratish",
        "zone",
    )
    ZONE_UPDATE = _Perm(
        "zone:update",
        "Binoni tahrirlash",
        "zone",
    )
    ZONE_DELETE = _Perm(
        "zone:delete",
        "Binoni o'chirish",
        "zone",
    )

    TEST_READ = _Perm(
        "test:read",
        "Testlarni ko'rish",
        "test",
    )
    TEST_CREATE = _Perm(
        "test:create",
        "Test yaratish",
        "test",
    )
    TEST_UPDATE = _Perm(
        "test:update",
        "Testni tahrirlash",
        "test",
    )
    TEST_DELETE = _Perm(
        "test:delete",
        "Testni o'chirish",
        "test",
    )

    SMENA_READ = _Perm(
        "smena:read",
        "Smenalarni ko'rish",
        "smena",
    )
    SMENA_CREATE = _Perm(
        "smena:create",
        "Smena yaratish",
        "smena",
    )
    SMENA_UPDATE = _Perm(
        "smena:update",
        "Smenani tahrirlash",
        "smena",
    )
    SMENA_DELETE = _Perm(
        "smena:delete",
        "Smenani o'chirish",
        "smena",
    )

    SESSION_STATE_READ = _Perm(
        "session_state:read",
        "Sessiya holatlarini ko'rish",
        "session_state",
    )
    SESSION_STATE_CREATE = _Perm(
        "session_state:create",
        "Sessiya holati yaratish",
        "session_state",
    )
    SESSION_STATE_UPDATE = _Perm(
        "session_state:update",
        "Sessiya holatini tahrirlash",
        "session_state",
    )
    SESSION_STATE_DELETE = _Perm(
        "session_state:delete",
        "Sessiya holatini o'chirish",
        "session_state",
    )

    REASON_READ = _Perm(
        "reason:read",
        "Chetlatish sabablarini ko'rish",
        "reason",
    )
    REASON_CREATE = _Perm(
        "reason:create",
        "Chetlatish sababi yaratish",
        "reason",
    )
    REASON_UPDATE = _Perm(
        "reason:update",
        "Chetlatish sababini tahrirlash",
        "reason",
    )
    REASON_DELETE = _Perm(
        "reason:delete",
        "Chetlatish sababini o'chirish",
        "reason",
    )

    REASON_TYPE_READ = _Perm(
        "reason_type:read",
        "Chetlatish turlarini ko'rish",
        "reason_type",
    )
    REASON_TYPE_CREATE = _Perm(
        "reason_type:create",
        "Chetlatish turi yaratish",
        "reason_type",
    )
    REASON_TYPE_UPDATE = _Perm(
        "reason_type:update",
        "Chetlatish turini tahrirlash",
        "reason_type",
    )
    REASON_TYPE_DELETE = _Perm(
        "reason_type:delete",
        "Chetlatish turini o'chirish",
        "reason_type",
    )

    GENDER_READ = _Perm(
        "gender:read",
        "Jinslarni ko'rish",
        "gender",
    )
    GENDER_CREATE = _Perm(
        "gender:create",
        "Jins yaratish",
        "gender",
    )
    GENDER_UPDATE = _Perm(
        "gender:update",
        "Jinsni tahrirlash",
        "gender",
    )
    GENDER_DELETE = _Perm(
        "gender:delete",
        "Jinsni o'chirish",
        "gender",
    )

    BLACKLIST_READ = _Perm(
        "blacklist:read",
        "Qora ro'yxatni ko'rish",
        "blacklist",
    )
    BLACKLIST_CREATE = _Perm(
        "blacklist:create",
        "Qora ro'yxatga qo'shish",
        "blacklist",
    )
    BLACKLIST_UPDATE = _Perm(
        "blacklist:update",
        "Qora ro'yxat yozuvini tahrirlash",
        "blacklist",
    )
    BLACKLIST_DELETE = _Perm(
        "blacklist:delete",
        "Qora ro'yxatdan o'chirish",
        "blacklist",
    )

    # === Security audit ===
    FAILED_LOGIN_READ = _Perm(
        "failed_login:read",
        "Failed login audit yozuvlarini ko'rish",
        "security",
    )

    # === Test session statistics dashboard ===
    STATISTICS_READ = _Perm(
        "statistics:read",
        "Test sessiya statistikasini ko'rish",
        "statistics",
    )
    # Davomat bo'limidagi ikkita eksport — ko'rishdan alohida boshqariladi.
    STATISTICS_EXPORT = _Perm(
        "statistics:export",
        "Davomat statistikasini Excel'ga yuklash",
        "statistics",
    )
    STATISTICS_ABSENTEES = _Perm(
        "statistics:absentees",
        "Kelmaganlar ro'yxatini Excel'ga yuklash",
        "statistics",
    )

    # === Passport ma'lumotlari (GTSP orqali) ===
    PASPORT_INFO_READ = _Perm(
        "pasport_info:read",
        "Pasport ma'lumotlarini olish (GTSP)",
        "pasport_info",
    )

    # === Davomat bot foydalanuvchilari (Telegram bot) ===
    DAVOMAT_BOT_READ = _Perm(
        "davomat_bot:read",
        "Davomat bot foydalanuvchilarini ko'rish",
        "davomat_bot",
    )
    DAVOMAT_BOT_CREATE = _Perm(
        "davomat_bot:create",
        "Davomat bot foydalanuvchisi yaratish",
        "davomat_bot",
    )
    DAVOMAT_BOT_UPDATE = _Perm(
        "davomat_bot:update",
        "Davomat bot foydalanuvchisini tahrirlash",
        "davomat_bot",
    )
    DAVOMAT_BOT_DELETE = _Perm(
        "davomat_bot:delete",
        "Davomat bot foydalanuvchisini o'chirish",
        "davomat_bot",
    )

    # === Statistika bot foydalanuvchilari (Telegram bot) ===
    STATISTIC_BOT_READ = _Perm(
        "statistic_bot:read",
        "Statistika bot foydalanuvchilarini ko'rish",
        "statistic_bot",
    )
    STATISTIC_BOT_CREATE = _Perm(
        "statistic_bot:create",
        "Statistika bot foydalanuvchisi yaratish",
        "statistic_bot",
    )
    STATISTIC_BOT_UPDATE = _Perm(
        "statistic_bot:update",
        "Statistika bot foydalanuvchisini tahrirlash",
        "statistic_bot",
    )
    STATISTIC_BOT_DELETE = _Perm(
        "statistic_bot:delete",
        "Statistika bot foydalanuvchisini o'chirish",
        "statistic_bot",
    )

    # === Qabul realtime statistika (yil dinamik) ===
    QABUL_READ = _Perm(
        "qabul:read",
        "Qabul statistikasini ko'rish",
        "qabul",
    )

    # === Natija uchun tahlil (tashqi natija tizimi vs FaceID DB, imei bo'yicha) ===
    RESULT_ANALYSIS_READ = _Perm(
        "result_analysis:read",
        "Natija uchun tahlil (imei bo'yicha)",
        "result_analysis",
    )


ALL_PERMISSIONS: list[_Perm] = [
    value
    for name, value in vars(P).items()
    if not name.startswith("_") and isinstance(value, _Perm)
]


def all_codenames() -> list[str]:
    return [p.code for p in ALL_PERMISSIONS]
