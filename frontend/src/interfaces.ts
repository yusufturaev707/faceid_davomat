/** Backend Pydantic sxemalariga mos TypeScript interfeyslari */

// === Photo ===
export interface PhotoVerifyRequest {
  age: number;
  img_b64: string;
}

export interface ImageSize {
  height: number;
  width: number;
}

export interface PalitraRGB {
  min_palitra: number[];
  max_palitra: number[];
}

export interface PhotoVerifyResponse {
  success: boolean;
  back_color: number[];
  size: ImageSize;
  palitra_rgb: PalitraRGB;
  detection: boolean;
  file_size_byte: number;
  error_messages: string[];
}

// === Auth ===
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenPairResponse {
  access_token: string;
  token_type: string;
  user?: UserResponse;
}

export interface UserResponse {
  id: number;
  username: string;
  full_name: string | null;
  role: string;
  role_key: number;
  // region_id — foydalanuvchiga bevosita biriktirilgan viloyat (asosiy
  // bog'lanish). zone_id ixtiyoriy "uy zonasi".
  region_id: number | null;
  region_name: string;
  zone_id: number | null;
  zone_name: string;
  telegram_id: string | null;
  is_active: boolean;
  permissions: string[];
}

// === Failed login audit ===
export interface FailedLoginAttemptResponse {
  id: number;
  username: string;
  ip_address: string;
  user_agent: string | null;
  reason: "no_user" | "wrong_password" | "inactive" | "locked" | string;
  attempted_at: string;
}

export interface FailedLoginCount {
  count: number;
}

// === Permissions (RBAC) ===
export interface PermissionResponse {
  id: number;
  codename: string;
  name: string;
  group: string;
}

export interface PermissionCreate {
  codename: string;
  name: string;
  group: string;
}

export interface PermissionUpdate {
  codename?: string;
  name?: string;
  group?: string;
}

export interface RolePermissionsResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
  permissions: PermissionResponse[];
}

export interface AssignPermissionsRequest {
  permission_ids: number[];
}

// === Admin ===
export interface VerificationLogResponse {
  id: number;
  user_id: number;
  username: string;
  timestamp: string;
  success: boolean;
  detection: boolean;
  image_width: number;
  image_height: number;
  file_size_bytes: number;
  input_age: number;
  back_color: string | null;
  error_message: string | null;
  image_path: string | null;
}

export interface PaginatedLogs {
  items: VerificationLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DailyChartItem {
  date: string;
  count: number;
}

export interface DashboardStats {
  total_verifications: number;
  today_verifications: number;
  week_verifications: number;
  success_rate: number;
  unique_users: number;
  daily_chart: DailyChartItem[];
}

export interface CreateUserRequest {
  username: string;
  password: string;
  full_name?: string;
  role_id?: number | null;
  region_id?: number | null;
  zone_id?: number | null;
  telegram_id?: string | null;
}

export interface UpdateUserRequest {
  username?: string;
  password?: string;
  full_name?: string;
  role_id?: number | null;
  region_id?: number | null;
  zone_id?: number | null;
  telegram_id?: string | null;
  is_active?: boolean;
}

export interface ErrorResponse {
  detail: string;
}

export interface TaskSubmitResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: PhotoVerifyResponse;
  error?: string;
}

// === Ikki yuzni solishtirish ===
export interface TwoFaceVerifyRequest {
  ps_img: string;
  lv_img: string;
}

export interface TwoFaceVerifyResponse {
  score: number;
  thresh_score: number;
  verified: boolean;
  message: string;
  ps_detection: boolean;
  lv_detection: boolean;
  ps_file_size: number;
  lv_file_size: number;
  ps_width: number;
  ps_height: number;
  lv_width: number;
  lv_height: number;
  error_messages: string[];
}

export interface TwoFaceTaskStatusResponse {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: TwoFaceVerifyResponse;
  error?: string;
}

// === Admin: Yuz solishtirish loglari ===
export interface FaceLogResponse {
  id: number;
  user_id: number;
  username: string;
  timestamp: string;
  ps_img: string | null;
  lv_img: string | null;
  ps_file_size: number;
  lv_file_size: number;
  ps_width: number;
  ps_height: number;
  lv_width: number;
  lv_height: number;
  ps_detection: boolean;
  lv_detection: boolean;
  detection: boolean;
  response_time: number;
  score: number;
  thresh_score: number;
  verified: boolean;
  error_message: string | null;
}

export interface PaginatedFaceLogs {
  items: FaceLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// === Embedding ===
export interface EmbeddingRequest {
  img_b64: string;
}

export interface EmbeddingResponse {
  detection: boolean;
  embedding: number[];
  embedding_size: number;
  embedding_b64: string | null;
  embedding_bytes_size: number;
  file_size_byte: number;
  image_width: number;
  image_height: number;
  error_messages: string[];
}

// === API Key ===
export interface ApiKeyCreateRequest {
  name: string;
}

export interface ApiKeyCreateResponse {
  id: number;
  name: string;
  prefix: string;
  raw_key: string;
  created_at: string;
}

export interface ApiKeyResponse {
  id: number;
  user_id: number;
  name: string;
  prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

// === Test Session ===
export interface SessionStateResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
}

export interface TestResponse {
  id: number;
  name: string;
  key: string;
  is_active: boolean;
}

export interface SmenaResponse {
  id: number;
  name: string;
  number: number;
  is_active: boolean;
}

export interface TestSessionSmenaResponse {
  id: number;
  test_session_id: number;
  test_smena_id: number;
  number: number;
  day: string;
  is_active: boolean;
  smena: SmenaResponse | null;
  created_at: string;
}

export interface TestSessionResponse {
  id: number;
  hash_key: string;
  test_state_id: number;
  test_id: number;
  name: string;
  number: number;
  count_sm_per_day: number;
  count_total_student: number;
  start_date: string;
  finish_date: string;
  is_active: boolean;
  test_state: SessionStateResponse | null;
  test: TestResponse | null;
  smenas: TestSessionSmenaResponse[];
  created_at: string;
}

// === Dashboard Statistics (test session) ===

export interface GenderStat {
  total: number;
  male: number;
  female: number;
  unknown: number;
}

export interface CheatingStat {
  total: number;
  at_entry: number;
  during_test: number;
  other: number;
  male: number;
  female: number;
  unknown: number;
}

export interface StatGroup {
  total: GenderStat;
  attended: GenderStat;
  not_attended: GenderStat;
  cheating: CheatingStat;
}

export interface ZoneStatItem {
  zone_id: number;
  zone_number: number;
  zone_name: string;
  stats: StatGroup;
}

export interface RegionStatItem {
  region_id: number;
  region_number: number;
  region_name: string;
  // Muqobil tartiblash identifikatorlari (DTM=number, VM=k_number, IIV=s_number)
  region_s_number: number;
  region_k_number: number;
  stats: StatGroup;
  zones: ZoneStatItem[];
}

/** Statistika ko'lami: bitta smena, bitta kun yoki butun sessiya. */
export type StatsScope = "smena" | "day" | "overall";

export interface DashboardStatsResponse {
  session_id: number;
  scope: StatsScope;
  session_smena_id: number | null;
  day: string | null;
  smena_number: number | null;
  smena_name: string | null;
  /** Nechta smena agregatsiya qilindi (smena=1, day/overall=ko'p). */
  smena_count: number;
  session_state_key: number;
  is_realtime: boolean;
  summary: StatGroup;
  regions: RegionStatItem[];
}

export interface TestSessionListResponse {
  items: TestSessionResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// --- Passport (ps_ser/ps_num) ommaviy yangilash ---
export interface PassportUpdateRow {
  jshshir: string;
  ps_ser: string;
  ps_num: string;
}

export interface PassportInvalidItem {
  row: number;
  jshshir: string;
  error: string;
}

export interface PassportUpdateResult {
  total: number;
  updated: number;
  not_found: string[];
  invalid: PassportInvalidItem[];
}

export interface TestSessionCreateRequest {
  test_id: number;
  name: string;
  start_date: string;
  finish_date: string;
  count_sm_per_day: number;
  smenas: { test_smena_id: number; day: string }[];
}

export interface TestSessionUpdateRequest {
  test_id?: number;
  name?: string;
  start_date?: string;
  finish_date?: string;
  count_sm_per_day?: number;
  is_active?: boolean;
}

// === Lookup tables (CRUD) ===

export interface LookupTestCreate {
  name: string;
  key: string;
  is_active?: boolean;
}
export interface LookupTestUpdate {
  name?: string;
  key?: string;
  is_active?: boolean;
}
export interface LookupTestResponse {
  id: number;
  name: string;
  key: string;
  is_active: boolean;
  created_at: string;
}

export interface LookupSmenaCreate {
  name: string;
  number: number;
  is_active?: boolean;
}
export interface LookupSmenaUpdate {
  name?: string;
  number?: number;
  is_active?: boolean;
}
export interface LookupSmenaResponse {
  id: number;
  name: string;
  number: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupSessionStateCreate {
  name: string;
  key: number;
  is_active?: boolean;
}
export interface LookupSessionStateUpdate {
  name?: string;
  key?: number;
  is_active?: boolean;
}
export interface LookupSessionStateResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupRegionCreate {
  name: string;
  number: number;
  s_number: number;
  k_number: number;
  is_active?: boolean;
}
export interface LookupRegionUpdate {
  name?: string;
  number?: number;
  s_number?: number;
  k_number?: number;
  is_active?: boolean;
}
export interface LookupRegionResponse {
  id: number;
  name: string;
  number: number;
  s_number: number;
  k_number: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupZoneCreate {
  region_id: number;
  name: string;
  number: number;
  is_active?: boolean;
}
export interface LookupZoneUpdate {
  region_id?: number;
  name?: string;
  number?: number;
  is_active?: boolean;
}
export interface LookupZoneResponse {
  id: number;
  region_id: number;
  name: string;
  number: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupRoleCreate {
  name: string;
  key: number;
  is_active?: boolean;
}
export interface LookupRoleUpdate {
  name?: string;
  key?: number;
  is_active?: boolean;
}
export interface LookupRoleResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
  created_at: string;
}

// === Davomat bot (Telegram bot foydalanuvchilari) ===

export interface DavomatBotAdminRegion {
  id: number;
  name: string;
  number: number;
}

export interface DavomatBotAdminResponse {
  id: number;
  fio: string;
  telegram_id: number;
  role_id: number | null;
  role: string;
  role_key: number;
  is_active: boolean;
  regions: DavomatBotAdminRegion[];
  region_ids: number[];
  created_at: string | null;
  updated_at: string | null;
}

export interface DavomatBotCreateRequest {
  fio: string;
  telegram_id: number;
  role_id: number | null;
  is_active: boolean;
  region_ids: number[];
}

export interface DavomatBotUpdateRequest {
  fio?: string;
  telegram_id?: number;
  role_id?: number | null;
  is_active?: boolean;
  region_ids?: number[];
}

// === Statistika bot (Telegram bot foydalanuvchilari) ===
// role: 1=Admin, 2=Rahbar, 3=Xodim

export interface StatisticBotAdminResponse {
  id: number;
  fio: string;
  telegram_id: number;
  role: number;
  role_name: string;
  status: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface StatisticBotCreateRequest {
  fio: string;
  telegram_id: number;
  role: number;
  status: boolean;
}

export interface StatisticBotUpdateRequest {
  fio?: string;
  telegram_id?: number;
  role?: number;
  status?: boolean;
}

// === Qabul realtime statistika (yil dinamik) ===

export interface QabulRegionStat {
  region_name: string;
  count: number;
  male: number;
  female: number;
  paid: number;
  share: number;
}

export interface QabulStats {
  year: number;
  prev_year: number;
  total: number;
  male: number;
  female: number;
  graduated: number;
  graduated_not: number;
  paid: number;
  unpaid: number;
  uz: number;
  ru: number;
  qq: number;
  lang_other: number;
  total_prev: number;
  paid_prev: number;
  male_prev: number;
  female_prev: number;
  regions: QabulRegionStat[];
  fetched_at: string | null;
}

export interface LookupReasonCreate {
  reason_type_id?: number | null;
  name: string;
  key: number;
  is_active?: boolean;
}
export interface LookupReasonUpdate {
  reason_type_id?: number | null;
  name?: string;
  key?: number;
  is_active?: boolean;
}
export interface LookupReasonResponse {
  id: number;
  reason_type_id: number | null;
  name: string;
  key: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupReasonTypeCreate {
  name: string;
  key: number;
  is_active?: boolean;
}
export interface LookupReasonTypeUpdate {
  name?: string;
  key?: number;
  is_active?: boolean;
}
export interface LookupReasonTypeResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
  created_at: string;
}

export interface LookupBlacklistCreate {
  imei?: string | null;
  description?: string | null;
}
export interface LookupBlacklistUpdate {
  imei?: string | null;
  description?: string | null;
}
export interface LookupBlacklistResponse {
  id: number;
  imei: string | null;
  description: string | null;
  created_at: string;
}

// === Gender ===
export interface LookupGenderCreate {
  name: string;
  key: number;
  is_active?: boolean;
}
export interface LookupGenderUpdate {
  name?: string;
  key?: number;
  is_active?: boolean;
}
export interface LookupGenderResponse {
  id: number;
  name: string;
  key: number;
  is_active: boolean;
}

// === Student ===
export interface StudentCreate {
  session_smena_id: number;
  zone_id: number;
  last_name: string;
  first_name: string;
  middle_name?: string | null;
  imei?: string | null;
  gr_n?: number;
  sp_n?: number;
  s_code?: number;
  e_date: string;
  subject_id?: number;
  subject_name?: string | null;
  lang_id?: number;
  level_id?: number;
}

export interface StudentPsDataUpdate {
  ps_ser?: string | null;
  ps_num?: string | null;
  phone?: string | null;
  ps_img?: string | null;
  embedding?: string | null;
}

export interface StudentUpdate {
  session_smena_id?: number;
  zone_id?: number;
  last_name?: string;
  first_name?: string;
  middle_name?: string | null;
  imei?: string | null;
  gr_n?: number;
  sp_n?: number;
  s_code?: number;
  e_date?: string;
  subject_id?: number;
  subject_name?: string | null;
  lang_id?: number;
  level_id?: number;
  is_ready?: boolean;
  is_face?: boolean;
  is_image?: boolean;
  is_cheating?: boolean;
  is_blacklist?: boolean;
  is_entered?: boolean;
  is_applied?: boolean;
  desc_apply?: string | null;
  ps_data?: StudentPsDataUpdate;
}

export interface StudentPsDataResponse {
  id: number;
  student_id: number;
  ps_ser: string;
  ps_num: string;
  phone: string | null;
  ps_img: string | null;
  embedding: string | null;
  gender_id: number | null;
  gender_name: string | null;
}

export interface StudentResponse {
  id: number;
  session_smena_id: number;
  test_session_id: number | null;
  test_name: string | null;
  zone_id: number;
  zone_name: string | null;
  region_name: string | null;
  smena_name: string | null;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  imei: string | null;
  gr_n: number;
  sp_n: number;
  s_code: number;
  e_date: string;
  subject_id: number;
  subject_name: string | null;
  lang_id: number;
  level_id: number;
  is_ready: boolean;
  is_face: boolean;
  is_image: boolean;
  is_cheating: boolean;
  is_blacklist: boolean;
  is_entered: boolean;
  is_applied: boolean;
  desc_apply: string | null;
  ps_data: StudentPsDataResponse | null;
}

export interface StudentListResponse {
  items: StudentResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Filtrlangan studentlar uchun GTSP bulk rasm yuklash natijasi
export interface GtspBulkResult {
  total: number;
  succeeded: number;
  failed: number;
  skipped: number;
}

// === StudentLog ===
export interface StudentLogCreate {
  student_id: number;
  first_captured?: string | null;
  last_captured?: string | null;
  first_enter_time?: string | null;
  last_enter_time?: string | null;
  score?: number;
  max_score?: number;
  is_check_hand?: boolean;
  ip_address?: string | null;
  mac_address?: string | null;
}

export interface StudentLogUpdate {
  student_id?: number;
  first_captured?: string | null;
  last_captured?: string | null;
  first_enter_time?: string | null;
  last_enter_time?: string | null;
  score?: number;
  max_score?: number;
  is_check_hand?: boolean;
  ip_address?: string | null;
  mac_address?: string | null;
}

export interface StudentLogResponse {
  id: number;
  student_id: number;
  first_enter_time: string | null;
  last_enter_time: string | null;
  score: number;
  max_score: number;
  is_check_hand: boolean;
  ip_address: string | null;
  mac_address: string | null;
  has_first_captured: boolean;
  has_last_captured: boolean;
  student_full_name: string | null;
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  imei: string | null;
  gr_n: number | null;
  is_cheating: boolean | null;
  is_blacklist: boolean | null;
  e_date: string | null;
  zone_id: number | null;
  zone_name: string | null;
  region_id: number | null;
  region_name: string | null;
  smena_id: number | null;
  smena_name: string | null;
  test_id: number | null;
  test_name: string | null;
  test_session_id: number | null;
}

export interface StudentLogDetailResponse extends StudentLogResponse {
  first_captured: string | null;
  last_captured: string | null;
}

export interface StudentLogListResponse {
  items: StudentLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// === CheatingLog ===
export interface CheatingLogCreate {
  student_id: number;
  reason_id: number;
  user_id: number;
  image_path?: string | null;
}

export interface CheatingLogUpdate {
  student_id?: number;
  reason_id?: number;
  user_id?: number;
  image_path?: string | null;
}

export interface CheatingLogResponse {
  id: number;
  student_id: number;
  reason_id: number;
  user_id: number;
  image_path: string | null;
  student_full_name: string | null;
  reason_name: string | null;
  username: string | null;
  imei: string | null;
  rejection_type: string | null;
  rejection_reason: string | null;
  test_name: string | null;
  region_name: string | null;
  zone_name: string | null;
  smena_date: string | null;
  smena_name: string | null;
  rejected_at: string | null;
}

export interface CheatingLogListResponse {
  items: CheatingLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
