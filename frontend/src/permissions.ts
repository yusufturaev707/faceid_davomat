/**
 * Permission codename konstantalari. Backend `app/core/permissions.py`
 * dagi `P` sinfi bilan bir xil codename larga ega bo'lishi kerak.
 */
export const PERM = {
  // Dashboard
  DASHBOARD_READ: "dashboard:read",
  DASHBOARD_STATS: "dashboard:stats",

  // Rasm tekshirish / yuz solishtirish (xizmatlar)
  PHOTO_VERIFY: "photo:verify",
  PHOTO_VERIFY_TWO_FACE: "photo:verify_two_face",

  // Embedding xizmati
  EMBEDDING_EXTRACT: "embedding:extract",

  // Tekshiruv loglari
  LOG_READ: "log:read",
  LOG_DELETE: "log:delete",

  // Yuz solishtirish loglari
  FACE_LOG_READ: "face_log:read",
  FACE_LOG_DELETE: "face_log:delete",

  // API kalitlar
  API_KEY_READ: "api_key:read",
  API_KEY_CREATE: "api_key:create",
  API_KEY_DELETE: "api_key:delete",

  // Foydalanuvchilar
  USER_READ: "user:read",
  USER_CREATE: "user:create",
  USER_UPDATE: "user:update",
  USER_DELETE: "user:delete",

  // Online foydalanuvchilar (aktiv login sessiyalari)
  ONLINE_USERS_READ: "online_users:read",

  // Rollar
  ROLE_READ: "role:read",
  ROLE_CREATE: "role:create",
  ROLE_UPDATE: "role:update",
  ROLE_DELETE: "role:delete",

  // Permissionlar (meta)
  PERMISSION_READ: "permission:read",
  PERMISSION_CREATE: "permission:create",
  PERMISSION_UPDATE: "permission:update",
  PERMISSION_DELETE: "permission:delete",

  // Test sessiyalar
  TEST_SESSION_READ: "test_session:read",
  TEST_SESSION_CREATE: "test_session:create",
  TEST_SESSION_UPDATE: "test_session:update",
  TEST_SESSION_DELETE: "test_session:delete",

  // Studentlar
  STUDENT_READ: "student:read",
  STUDENT_CREATE: "student:create",
  STUDENT_UPDATE: "student:update",
  STUDENT_DELETE: "student:delete",

  // Student loglari
  STUDENT_LOG_READ: "student_log:read",
  STUDENT_LOG_CREATE: "student_log:create",
  STUDENT_LOG_UPDATE: "student_log:update",
  STUDENT_LOG_DELETE: "student_log:delete",

  // Qoidabuzarlik loglari
  CHEATING_LOG_READ: "cheating_log:read",
  CHEATING_LOG_CREATE: "cheating_log:create",
  CHEATING_LOG_UPDATE: "cheating_log:update",
  CHEATING_LOG_DELETE: "cheating_log:delete",

  // Ma'lumotnomalar (umumiy)
  LOOKUP_READ: "lookup:read",
  LOOKUP_CREATE: "lookup:create",
  LOOKUP_UPDATE: "lookup:update",
  LOOKUP_DELETE: "lookup:delete",

  // Xavfsizlik auditi
  FAILED_LOGIN_READ: "failed_login:read",

  // Test sessiya statistika dashboard
  STATISTICS_READ: "statistics:read",

  // Pasport ma'lumotlari (GTSP)
  PASPORT_INFO_READ: "pasport_info:read",

  // Davomat bot foydalanuvchilari (Telegram bot)
  DAVOMAT_BOT_READ: "davomat_bot:read",
  DAVOMAT_BOT_CREATE: "davomat_bot:create",
  DAVOMAT_BOT_UPDATE: "davomat_bot:update",
  DAVOMAT_BOT_DELETE: "davomat_bot:delete",

  // Statistika bot foydalanuvchilari (Telegram bot)
  STATISTIC_BOT_READ: "statistic_bot:read",
  STATISTIC_BOT_CREATE: "statistic_bot:create",
  STATISTIC_BOT_UPDATE: "statistic_bot:update",
  STATISTIC_BOT_DELETE: "statistic_bot:delete",

  // Qabul realtime statistika (yil dinamik)
  QABUL_READ: "qabul:read",
} as const;

export type PermCode = (typeof PERM)[keyof typeof PERM];

// Alias'lar — kod bazada turli joylarda ikkala nom ishlatilgan bo'lishi mumkin.
export const P = PERM;
export type PermissionCode = PermCode;
