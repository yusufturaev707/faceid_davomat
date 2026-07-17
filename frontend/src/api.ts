import axios from "axios";
import type {
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  CreateUserRequest,
  DashboardStats,
  EmbeddingRequest,
  EmbeddingResponse,
  FaceLogResponse,
  LoginRequest,
  PaginatedFaceLogs,
  PaginatedLogs,
  PhotoVerifyRequest,
  TaskStatusResponse,
  TaskSubmitResponse,
  TokenPairResponse,
  TwoFaceTaskStatusResponse,
  TwoFaceVerifyRequest,
  UpdateUserRequest,
  UserResponse,
  VerificationLogResponse,
} from "./interfaces";
import { getAccessToken, setAccessToken } from "./tokenStore";

const API_BASE = "/api/v1";

const apiClient = axios.create({ baseURL: API_BASE, withCredentials: true });

/** `csrf_token` cookiesini o'qish (HttpOnly emas, JS o'qiy oladi). */
function readCsrfTokenCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const CSRF_METHODS = new Set(["post", "put", "patch", "delete"]);

// Request interceptor — access token + CSRF header (state-changing methods uchun)
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;

  const method = (config.method || "get").toLowerCase();
  if (CSRF_METHODS.has(method)) {
    const csrf = readCsrfTokenCookie();
    if (csrf) config.headers["X-CSRF-Token"] = csrf;
  }
  return config;
});

// Response interceptor — 401 bo'lganda token yangilash.
// Race fix: bir vaqtda faqat bitta refresh; muvaffaqiyatsiz bo'lsa, pending
// so'rovlarning HAMMASI bir marta rad etiladi va keyingi retry bloklanadi.
let refreshPromise: Promise<TokenPairResponse> | null = null;
let refreshFailedUntil = 0; // unix ms — shu vaqtgacha retry urinmaymiz

/** Singleton refresh — interceptor va AuthContext init bir xil promise'dan foydalanadi. */
export function refreshTokensOnce(): Promise<TokenPairResponse> {
  if (Date.now() < refreshFailedUntil) {
    return Promise.reject(new Error("refresh_recently_failed"));
  }
  if (!refreshPromise) {
    refreshPromise = refreshApi()
      .then((tokens) => {
        setAccessToken(tokens.access_token);
        return tokens;
      })
      .catch((err) => {
        refreshFailedUntil = Date.now() + 5000;
        throw err;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

// Logout callbackni AuthContext tomonidan o'rnatiladi.
// Race fix: `unauthorizedFiredUntil` window davomida faqat bir marta chaqirilishini ta'minlaydi.
let onUnauthorized: (() => void) | null = null;
let unauthorizedFiredUntil = 0;
export function setOnUnauthorized(cb: (() => void) | null) {
  onUnauthorized = cb;
}

function fireUnauthorizedOnce() {
  const now = Date.now();
  if (now < unauthorizedFiredUntil) return;
  unauthorizedFiredUntil = now + 1000; // 1s debounce
  if (onUnauthorized) onUnauthorized();
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const is401 = error.response?.status === 401;
    const isAuthUrl = original?.url?.includes("/auth/");

    if (!is401 || original?._retry || isAuthUrl) {
      return Promise.reject(error);
    }

    // Oxirgi refresh muvaffaqiyatsiz bo'lgan bo'lsa, darhol rad etamiz
    if (Date.now() < refreshFailedUntil) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      const tokens = await refreshTokensOnce();
      original.headers.Authorization = `Bearer ${tokens.access_token}`;
      return apiClient(original);
    } catch (refreshErr) {
      setAccessToken(null);
      fireUnauthorizedOnce();
      return Promise.reject(refreshErr);
    }
  }
);

// === Utility ===
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// === Auth API ===
export async function loginApi(data: LoginRequest): Promise<TokenPairResponse> {
  const form = new URLSearchParams();
  form.append("username", data.username);
  form.append("password", data.password);
  const res = await apiClient.post<TokenPairResponse>("/auth/login", form);
  return res.data;
}

export async function refreshApi(): Promise<TokenPairResponse> {
  const res = await apiClient.post<TokenPairResponse>("/auth/refresh");
  return res.data;
}

export async function logoutApi(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function getMeApi(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>("/auth/me");
  return res.data;
}

// === Photo Verify API ===
export async function submitVerifyPhoto(data: PhotoVerifyRequest): Promise<TaskSubmitResponse> {
  const res = await apiClient.post<TaskSubmitResponse>("/photo/verify-photo", data);
  return res.data;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await apiClient.get<TaskStatusResponse>(`/photo/verify-photo/status/${taskId}`);
  return res.data;
}

// === Two Face API ===
export async function submitVerifyTwoFace(data: TwoFaceVerifyRequest): Promise<TaskSubmitResponse> {
  const res = await apiClient.post<TaskSubmitResponse>("/photo/verify-two-face", data);
  return res.data;
}

export async function getTwoFaceTaskStatus(taskId: string): Promise<TwoFaceTaskStatusResponse> {
  const res = await apiClient.get<TwoFaceTaskStatusResponse>(`/photo/verify-two-face/status/${taskId}`);
  return res.data;
}

// === Embedding API ===
export async function extractEmbeddingApi(data: EmbeddingRequest): Promise<EmbeddingResponse> {
  const res = await apiClient.post<EmbeddingResponse>("/embedding/extract", data);
  return res.data;
}

// === Admin API ===
export async function getLogByIdApi(logId: number): Promise<VerificationLogResponse> {
  const res = await apiClient.get<VerificationLogResponse>(`/admin/logs/${logId}`);
  return res.data;
}

export async function getLogsApi(params: Record<string, string | number>): Promise<PaginatedLogs> {
  const res = await apiClient.get<PaginatedLogs>("/admin/logs", { params });
  return res.data;
}

export async function getStatsApi(): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>("/admin/stats");
  return res.data;
}

export async function getFaceStatsApi(): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>("/admin/face-stats");
  return res.data;
}

export async function getFaceLogsApi(params: Record<string, string | number>): Promise<PaginatedFaceLogs> {
  const res = await apiClient.get<PaginatedFaceLogs>("/admin/face-logs", { params });
  return res.data;
}

export async function getFaceLogByIdApi(logId: number): Promise<FaceLogResponse> {
  const res = await apiClient.get<FaceLogResponse>(`/admin/face-logs/${logId}`);
  return res.data;
}

// === Users API ===
export async function getUsersApi(): Promise<UserResponse[]> {
  const res = await apiClient.get<UserResponse[]>("/admin/users");
  return res.data;
}

export async function createUserApi(data: CreateUserRequest): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>("/admin/users", data);
  return res.data;
}

export async function updateUserApi(userId: number, data: UpdateUserRequest): Promise<UserResponse> {
  const res = await apiClient.patch<UserResponse>(`/admin/users/${userId}`, data);
  return res.data;
}

export async function deleteUserApi(userId: number): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`);
}

// === API Keys ===
export async function createApiKeyApi(data: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
  const res = await apiClient.post<ApiKeyCreateResponse>("/admin/api-keys", data);
  return res.data;
}

export async function getApiKeysApi(): Promise<ApiKeyResponse[]> {
  const res = await apiClient.get<ApiKeyResponse[]>("/admin/api-keys");
  return res.data;
}

export async function revokeApiKeyApi(keyId: number): Promise<void> {
  await apiClient.delete(`/admin/api-keys/${keyId}`);
}

// === Failed Login Audit ===
export async function getFailedLoginsApi(params?: {
  username?: string;
  since?: string;
  limit?: number;
}): Promise<import("./interfaces").FailedLoginAttemptResponse[]> {
  const clean: Record<string, string | number> = {};
  if (params?.username) clean.username = params.username;
  if (params?.since) clean.since = params.since;
  if (params?.limit) clean.limit = params.limit;
  const res = await apiClient.get<import("./interfaces").FailedLoginAttemptResponse[]>(
    "/admin/failed-logins",
    { params: clean }
  );
  return res.data;
}

export async function getFailedLoginsCountApi(params?: {
  username?: string;
  since?: string;
}): Promise<import("./interfaces").FailedLoginCount> {
  const clean: Record<string, string> = {};
  if (params?.username) clean.username = params.username;
  if (params?.since) clean.since = params.since;
  const res = await apiClient.get<import("./interfaces").FailedLoginCount>(
    "/admin/failed-logins/count",
    { params: clean }
  );
  return res.data;
}

// === Auth Image ===
export async function getAuthImageUrl(src: string): Promise<string> {
  const res = await apiClient.get(src, { responseType: "blob" });
  return URL.createObjectURL(res.data);
}

// === Test Sessions API ===
export async function getTestSessionsApi(params: Record<string, string | number>): Promise<import("./interfaces").TestSessionListResponse> {
  const res = await apiClient.get("/test-sessions", { params });
  return res.data;
}

export async function getTestSessionApi(sessionId: number): Promise<import("./interfaces").TestSessionResponse> {
  const res = await apiClient.get(`/test-sessions/${sessionId}`);
  return res.data;
}

export async function createTestSessionApi(data: import("./interfaces").TestSessionCreateRequest): Promise<import("./interfaces").TestSessionResponse> {
  const res = await apiClient.post("/test-sessions", data);
  return res.data;
}

export async function updateTestSessionApi(sessionId: number, data: import("./interfaces").TestSessionUpdateRequest): Promise<import("./interfaces").TestSessionResponse> {
  const res = await apiClient.patch(`/test-sessions/${sessionId}`, data);
  return res.data;
}

export async function changeSessionStateApi(sessionId: number, testStateId: number): Promise<import("./interfaces").TestSessionResponse> {
  const res = await apiClient.patch(`/test-sessions/${sessionId}/state`, { test_state_id: testStateId });
  return res.data;
}

export async function getEmbeddingProgressApi(sessionId: number): Promise<{
  current: number;
  total: number;
  success: number;
  no_image: number;
  no_face: number;
  errors: number;
  failed: number;
  percent: number;
  status: string;
  message?: string;
}> {
  const res = await apiClient.get(`/test-sessions/${sessionId}/embedding-progress`);
  return res.data;
}

export async function getStudentLoadProgressApi(sessionId: number): Promise<{
  current: number;
  total: number;
  pages_done: number;
  pages_total: number;
  skipped: number;
  percent: number;
  status: "idle" | "processing" | "completed" | "error" | "cancelled";
  message: string;
  // DB'ga insert bo'lmagan studentlar (imie + xato sababi). Maksimal 500 ta.
  failed_items?: { imie: string; reason: string }[];
  // Parsing/smena/dublikat bois o'tkazib yuborilgan studentlar. Maksimal 500 ta.
  skipped_items?: { imie: string; reason: string }[];
}> {
  const res = await apiClient.get(`/test-sessions/${sessionId}/student-load-progress`);
  return res.data;
}

/**
 * Davom etayotgan student yuklashni bekor qilish. Backend Redis'ga cancel
 * flag yozadi — loader keyingi sahifada to'xtab, state'ni qaytaradi va
 * progress "cancelled" bo'ladi (polling orqali ko'rinadi).
 */
export async function cancelStudentLoadApi(sessionId: number): Promise<{ detail: string }> {
  const res = await apiClient.post(`/test-sessions/${sessionId}/cancel-student-load`);
  return res.data;
}

/**
 * Studentlarni QAYTA yuklash (resumable) — faqat tugamagan/xato bergan kunlar.
 * Muvaffaqiyatli yuklangan kunlar o'tkazib yuboriladi.
 */
export async function reloadStudentLoadApi(sessionId: number): Promise<{ detail: string }> {
  const res = await apiClient.post(`/test-sessions/${sessionId}/reload-student-load`);
  return res.data;
}

/**
 * Tanlangan ko'lam (scope) uchun dashboard statistikasini olish:
 *  - scope="smena"   — `sessionSmenaId` majburiy (bitta kun + smena)
 *  - scope="day"     — `day` (YYYY-MM-DD) majburiy (bitta kunning barcha smenalari)
 *  - scope="overall" — qo'shimcha parametr kerak emas (butun sessiya)
 *
 * `is_realtime=true` (session state.key=4) bo'lsa frontend polling qiladi.
 */
export async function getSessionDashboardStatsApi(
  sessionId: number,
  opts: {
    scope: import("./interfaces").StatsScope;
    sessionSmenaId?: number | null;
    day?: string | null;
  },
  signal?: AbortSignal,
): Promise<import("./interfaces").DashboardStatsResponse> {
  const params: Record<string, string | number> = { scope: opts.scope };
  if (opts.scope === "smena" && opts.sessionSmenaId != null) {
    params.session_smena_id = opts.sessionSmenaId;
  }
  if (opts.scope === "day" && opts.day) {
    params.day = opts.day;
  }
  const res = await apiClient.get(
    `/test-sessions/${sessionId}/dashboard-stats`,
    // signal — eskirgan/unmount so'rovni bekor qilish; timeout — osilib
    // qolgan so'rov brauzerda cheksiz kutmasligi uchun.
    { params, signal, timeout: 20000 },
  );
  return res.data;
}

/**
 * Online foydalanuvchilar — aktiv login sessiyalari va qurilmalar.
 * Har bir foydalanuvchi uchun qurilmalar soni va online holati qaytadi.
 */
export async function getOnlineUsersApi(): Promise<
  import("./interfaces").OnlineUsersResponse
> {
  const res = await apiClient.get("/admin/online-users");
  return res.data;
}

/**
 * Tanlangan ko'lam (scope) statistikasini rasmiy "МАЪЛУМОТ" ko'rinishidagi
 * Excel (.xlsx) hisobotiga eksport qilib yuklab olish. Parametrlar
 * `getSessionDashboardStatsApi` bilan bir xil. Brauzer faylni saqlaydi.
 */
export async function exportSessionDashboardStatsApi(
  sessionId: number,
  opts: {
    scope: import("./interfaces").StatsScope;
    sessionSmenaId?: number | null;
    day?: string | null;
    alphabet?: "cyrillic" | "latin";
    // Viloyatlar tartibi: dtm (region raqami) | vm (k_number) | iiv (s_number)
    orderBy?: "dtm" | "vm" | "iiv";
  },
): Promise<void> {
  const params: Record<string, string | number> = { scope: opts.scope };
  if (opts.scope === "smena" && opts.sessionSmenaId != null) {
    params.session_smena_id = opts.sessionSmenaId;
  }
  if (opts.scope === "day" && opts.day) {
    params.day = opts.day;
  }
  if (opts.alphabet) {
    params.alphabet = opts.alphabet;
  }
  if (opts.orderBy) {
    params.order_by = opts.orderBy;
  }
  try {
    const res = await apiClient.get(
      `/test-sessions/${sessionId}/dashboard-stats/export`,
      { params, responseType: "blob" },
    );
    const cd = (res.headers["content-disposition"] as string | undefined) ?? "";
    const match = /filename="?([^";]+)"?/.exec(cd);
    const filename = match ? match[1] : "statistika.xlsx";

    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Xato javob blob ko'rinishida keladi — ichidagi {detail} ni o'qib chiqaramiz
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text());
        throw new Error(parsed.detail || "Eksport amalga oshmadi");
      } catch (e) {
        if (e instanceof Error && e.message) throw e;
      }
    }
    throw err;
  }
}

/**
 * Tanlangan ko'lam (scope) uchun kelmaganlar ro'yxatini .xlsx ga eksport qilib
 * yuklab olish. Har bir kelmagan talabgor alohida qatorda, sana → region →
 * zone → smena → guruh tartibida. Brauzer faylni saqlaydi.
 */
export async function exportSessionAbsenteesApi(
  sessionId: number,
  opts: {
    scope: import("./interfaces").StatsScope;
    sessionSmenaId?: number | null;
    day?: string | null;
  },
): Promise<void> {
  const params: Record<string, string | number> = { scope: opts.scope };
  if (opts.scope === "smena" && opts.sessionSmenaId != null) {
    params.session_smena_id = opts.sessionSmenaId;
  }
  if (opts.scope === "day" && opts.day) {
    params.day = opts.day;
  }
  try {
    const res = await apiClient.get(
      `/test-sessions/${sessionId}/dashboard-stats/absentees-export`,
      { params, responseType: "blob" },
    );
    const cd = (res.headers["content-disposition"] as string | undefined) ?? "";
    const match = /filename="?([^";]+)"?/.exec(cd);
    const filename = match ? match[1] : "kelmaganlar.xlsx";

    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Xato javob blob ko'rinishida keladi — ichidagi {detail} ni o'qib chiqaramiz
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text());
        throw new Error(parsed.detail || "Eksport amalga oshmadi");
      } catch (e) {
        if (e instanceof Error && e.message) throw e;
      }
    }
    throw err;
  }
}

/**
 * Test sessiyaga Excel orqali studentlarni yuklash. Backend Celery task
 * boshlaydi va darhol 202 qaytaradi — natijani `getStudentLoadProgressApi`
 * orqali polling qiling. Task yakunida sessiya state.key=2 ga o'tadi.
 */
export async function uploadStudentsExcelApi(
  sessionId: number,
  file: File,
): Promise<{ task_id: string; status: string; message: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post(
    `/test-sessions/${sessionId}/upload-excel`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

/**
 * Studentlar ro'yxati uchun bo'sh Excel shablonini yuklab olish.
 * Brauzer "students_template.xlsx" sifatida saqlaydi.
 */
export async function downloadStudentsExcelTemplate(): Promise<void> {
  const res = await apiClient.get("/test-sessions/excel-template", {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = "students_template.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Paste qilingan qatorlar (jshshir, ps_ser, ps_num) bo'yicha sessiyadagi
 * talabalar passportini ommaviy yangilash. Sinxron — natija darhol qaytadi.
 */
export async function updateSessionPassportsApi(
  sessionId: number,
  rows: import("./interfaces").PassportUpdateRow[],
): Promise<import("./interfaces").PassportUpdateResult> {
  const res = await apiClient.post(
    `/test-sessions/${sessionId}/passport-update`,
    { rows },
  );
  return res.data;
}

/**
 * `.xlsx` fayl (jshshir, ps_ser, ps_num) orqali passportlarni yangilash.
 * Fayl serverda o'qiladi; natija sinxron qaytadi.
 */
export async function uploadSessionPassportsExcelApi(
  sessionId: number,
  file: File,
): Promise<import("./interfaces").PassportUpdateResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post(
    `/test-sessions/${sessionId}/passport-update/excel`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
}

/** Passport yangilash shabloni (.xlsx: jshshir, ps_ser, ps_num) yuklab olish. */
export async function downloadPassportTemplate(): Promise<void> {
  const res = await apiClient.get("/test-sessions/passport-template", {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = "passport_template.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function deleteTestSessionApi(sessionId: number): Promise<void> {
  await apiClient.delete(`/test-sessions/${sessionId}`);
}

export async function addSmenaToSessionApi(sessionId: number, body: { test_smena_id: number; day: string }): Promise<import("./interfaces").TestSessionSmenaResponse> {
  const res = await apiClient.post(`/test-sessions/${sessionId}/smenas`, body);
  return res.data;
}

export async function removeSmenaFromSessionApi(sessionId: number, smenaId: number): Promise<void> {
  await apiClient.delete(`/test-sessions/${sessionId}/smenas/${smenaId}`);
}

export async function getSessionStudentStatsApi(sessionId: number): Promise<{
  total: number;
  ready: number;
  not_ready: number;
  no_image: number;
  no_face: number;
}> {
  const res = await apiClient.get(`/test-sessions/${sessionId}/student-stats`);
  return res.data;
}

export async function retryEmbeddingApi(sessionId: number): Promise<{ message: string; not_ready: number }> {
  const res = await apiClient.post(`/test-sessions/${sessionId}/retry-embedding`);
  return res.data;
}

// === Test Sessions Lookups ===
export async function getTestsLookupApi(): Promise<import("./interfaces").TestResponse[]> {
  const res = await apiClient.get("/test-sessions/tests");
  return res.data;
}

export async function getSmenasLookupApi(): Promise<import("./interfaces").SmenaResponse[]> {
  const res = await apiClient.get("/test-sessions/smenas");
  return res.data;
}

export async function getSessionStatesLookupApi(): Promise<import("./interfaces").SessionStateResponse[]> {
  const res = await apiClient.get("/test-sessions/states");
  return res.data;
}

// === Lookup CRUD APIs ===

// Tests
export async function getTestsListApi(): Promise<import("./interfaces").LookupTestResponse[]> {
  const res = await apiClient.get("/lookup/tests");
  return res.data;
}
export async function createTestApi(data: import("./interfaces").LookupTestCreate): Promise<import("./interfaces").LookupTestResponse> {
  const res = await apiClient.post("/lookup/tests", data);
  return res.data;
}
export async function updateTestApi(id: number, data: import("./interfaces").LookupTestUpdate): Promise<import("./interfaces").LookupTestResponse> {
  const res = await apiClient.patch(`/lookup/tests/${id}`, data);
  return res.data;
}
export async function deleteTestApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/tests/${id}`);
}

// Smenas
export async function getSmenasListApi(): Promise<import("./interfaces").LookupSmenaResponse[]> {
  const res = await apiClient.get("/lookup/smenas");
  return res.data;
}
export async function createSmenaApi(data: import("./interfaces").LookupSmenaCreate): Promise<import("./interfaces").LookupSmenaResponse> {
  const res = await apiClient.post("/lookup/smenas", data);
  return res.data;
}
export async function updateSmenaApi(id: number, data: import("./interfaces").LookupSmenaUpdate): Promise<import("./interfaces").LookupSmenaResponse> {
  const res = await apiClient.patch(`/lookup/smenas/${id}`, data);
  return res.data;
}
export async function deleteSmenaApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/smenas/${id}`);
}

// Session States
export async function getSessionStatesListApi(): Promise<import("./interfaces").LookupSessionStateResponse[]> {
  const res = await apiClient.get("/lookup/session-states");
  return res.data;
}
export async function createSessionStateApi(data: import("./interfaces").LookupSessionStateCreate): Promise<import("./interfaces").LookupSessionStateResponse> {
  const res = await apiClient.post("/lookup/session-states", data);
  return res.data;
}
export async function updateSessionStateApi(id: number, data: import("./interfaces").LookupSessionStateUpdate): Promise<import("./interfaces").LookupSessionStateResponse> {
  const res = await apiClient.patch(`/lookup/session-states/${id}`, data);
  return res.data;
}
export async function deleteSessionStateApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/session-states/${id}`);
}

// Regions
export async function getRegionsListApi(): Promise<import("./interfaces").LookupRegionResponse[]> {
  const res = await apiClient.get("/lookup/regions");
  return res.data;
}
export async function createRegionApi(data: import("./interfaces").LookupRegionCreate): Promise<import("./interfaces").LookupRegionResponse> {
  const res = await apiClient.post("/lookup/regions", data);
  return res.data;
}
export async function updateRegionApi(id: number, data: import("./interfaces").LookupRegionUpdate): Promise<import("./interfaces").LookupRegionResponse> {
  const res = await apiClient.patch(`/lookup/regions/${id}`, data);
  return res.data;
}
export async function deleteRegionApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/regions/${id}`);
}

// Zones
export async function getZonesListApi(): Promise<import("./interfaces").LookupZoneResponse[]> {
  const res = await apiClient.get("/lookup/zones");
  return res.data;
}
export async function getZonesByRegionApi(regionId: number): Promise<import("./interfaces").LookupZoneResponse[]> {
  const res = await apiClient.get("/lookup/zones", { params: { region_id: regionId } });
  return res.data;
}
export async function createZoneApi(data: import("./interfaces").LookupZoneCreate): Promise<import("./interfaces").LookupZoneResponse> {
  const res = await apiClient.post("/lookup/zones", data);
  return res.data;
}
export async function updateZoneApi(id: number, data: import("./interfaces").LookupZoneUpdate): Promise<import("./interfaces").LookupZoneResponse> {
  const res = await apiClient.patch(`/lookup/zones/${id}`, data);
  return res.data;
}
export async function deleteZoneApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/zones/${id}`);
}
// OTM tashqi API'dan binolarni sinxronizatsiya qilish ("Yangilash" tugmasi).
export interface ZoneSyncFieldChange {
  field: "name" | "number" | "region" | "is_active" | string;
  old: string | number | boolean | null;
  new: string | number | boolean | null;
}
export interface ZoneSyncEntry {
  building_id: number;
  name: string;
  number: number;
  region_name: string | null;
  changes: ZoneSyncFieldChange[];
}
export interface ZoneSyncResult {
  received: number;
  created: number;
  updated: number;
  unchanged: number;
  skipped_no_region: number;
  invalid: number;
  created_items: ZoneSyncEntry[];
  updated_items: ZoneSyncEntry[];
}
export async function syncZonesFromOtmApi(): Promise<ZoneSyncResult> {
  const res = await apiClient.post("/lookup/zones/sync-from-otm");
  return res.data;
}

// Roles
export async function getRolesListApi(): Promise<import("./interfaces").LookupRoleResponse[]> {
  const res = await apiClient.get("/lookup/roles");
  return res.data;
}
export async function createRoleApi(data: import("./interfaces").LookupRoleCreate): Promise<import("./interfaces").LookupRoleResponse> {
  const res = await apiClient.post("/lookup/roles", data);
  return res.data;
}
export async function updateRoleApi(id: number, data: import("./interfaces").LookupRoleUpdate): Promise<import("./interfaces").LookupRoleResponse> {
  const res = await apiClient.patch(`/lookup/roles/${id}`, data);
  return res.data;
}
export async function deleteRoleApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/roles/${id}`);
}

// Reasons
export async function getReasonsListApi(): Promise<import("./interfaces").LookupReasonResponse[]> {
  const res = await apiClient.get("/lookup/reasons");
  return res.data;
}
export async function createReasonApi(data: import("./interfaces").LookupReasonCreate): Promise<import("./interfaces").LookupReasonResponse> {
  const res = await apiClient.post("/lookup/reasons", data);
  return res.data;
}
export async function updateReasonApi(id: number, data: import("./interfaces").LookupReasonUpdate): Promise<import("./interfaces").LookupReasonResponse> {
  const res = await apiClient.patch(`/lookup/reasons/${id}`, data);
  return res.data;
}
export async function deleteReasonApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/reasons/${id}`);
}

// Reason Types
export async function getReasonTypesListApi(): Promise<import("./interfaces").LookupReasonTypeResponse[]> {
  const res = await apiClient.get("/lookup/reason-types");
  return res.data;
}
export async function createReasonTypeApi(data: import("./interfaces").LookupReasonTypeCreate): Promise<import("./interfaces").LookupReasonTypeResponse> {
  const res = await apiClient.post("/lookup/reason-types", data);
  return res.data;
}
export async function updateReasonTypeApi(id: number, data: import("./interfaces").LookupReasonTypeUpdate): Promise<import("./interfaces").LookupReasonTypeResponse> {
  const res = await apiClient.patch(`/lookup/reason-types/${id}`, data);
  return res.data;
}
export async function deleteReasonTypeApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/reason-types/${id}`);
}

// Blacklist
export async function getBlacklistApi(): Promise<import("./interfaces").LookupBlacklistResponse[]> {
  const res = await apiClient.get("/lookup/blacklist");
  return res.data;
}
export async function createBlacklistApi(data: import("./interfaces").LookupBlacklistCreate): Promise<import("./interfaces").LookupBlacklistResponse> {
  const res = await apiClient.post("/lookup/blacklist", data);
  return res.data;
}
export async function updateBlacklistApi(id: number, data: import("./interfaces").LookupBlacklistUpdate): Promise<import("./interfaces").LookupBlacklistResponse> {
  const res = await apiClient.patch(`/lookup/blacklist/${id}`, data);
  return res.data;
}
export async function deleteBlacklistApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/blacklist/${id}`);
}

// Genders
export async function getGendersListApi(): Promise<import("./interfaces").LookupGenderResponse[]> {
  const res = await apiClient.get("/lookup/genders");
  return res.data;
}
export async function createGenderApi(data: import("./interfaces").LookupGenderCreate): Promise<import("./interfaces").LookupGenderResponse> {
  const res = await apiClient.post("/lookup/genders", data);
  return res.data;
}
export async function updateGenderApi(id: number, data: import("./interfaces").LookupGenderUpdate): Promise<import("./interfaces").LookupGenderResponse> {
  const res = await apiClient.patch(`/lookup/genders/${id}`, data);
  return res.data;
}
export async function deleteGenderApi(id: number): Promise<void> {
  await apiClient.delete(`/lookup/genders/${id}`);
}

// === Students API ===
export async function getStudentsApi(params?: Record<string, unknown>): Promise<import("./interfaces").StudentListResponse> {
  const res = await apiClient.get("/students", { params });
  return res.data;
}

export async function getStudentApi(id: number): Promise<import("./interfaces").StudentResponse> {
  const res = await apiClient.get(`/students/${id}`);
  return res.data;
}

export async function createStudentApi(data: import("./interfaces").StudentCreate): Promise<import("./interfaces").StudentResponse> {
  const res = await apiClient.post("/students", data);
  return res.data;
}

export async function updateStudentApi(id: number, data: import("./interfaces").StudentUpdate): Promise<import("./interfaces").StudentResponse> {
  const res = await apiClient.patch(`/students/${id}`, data);
  return res.data;
}

export async function deleteStudentApi(id: number): Promise<void> {
  await apiClient.delete(`/students/${id}`);
}

export async function uploadStudentImageApi(studentId: number, ps_img: string): Promise<import("./interfaces").StudentResponse> {
  const res = await apiClient.post(`/students/${studentId}/upload-image`, { ps_img });
  return res.data;
}

export async function fetchGtspImageApi(studentId: number): Promise<import("./interfaces").StudentResponse> {
  const res = await apiClient.post(`/students/${studentId}/fetch-gtsp`);
  return res.data;
}

// Filtr/qidiruvga mos barcha studentlar uchun GTSP rasm yuklash (bulk).
// Parametrlar getStudentsApi bilan bir xil (sahifalashsiz).
export async function fetchGtspBulkApi(
  params?: Record<string, unknown>
): Promise<import("./interfaces").GtspBulkResult> {
  const res = await apiClient.post("/students/fetch-gtsp-bulk", null, { params });
  return res.data;
}

/**
 * Filtrlangan barcha talabalarni tanlangan binoga (zone) biriktirish.
 * Filtr parametrlari getStudentsApi bilan bir xil (sahifalashsiz).
 */
export async function reassignZoneBulkApi(
  params: Record<string, unknown>,
  targetZoneId: number,
): Promise<import("./interfaces").ReassignZoneResult> {
  const res = await apiClient.post("/students/reassign-zone-bulk", null, {
    params: { ...params, target_zone_id: targetZoneId },
  });
  return res.data;
}

/**
 * Filtrlangan talabalar ro'yxatini Excel (.xlsx) yoki PDF qilib yuklab olish.
 * Parametrlar getStudentsApi bilan bir xil (sahifalashsiz). Brauzer faylni saqlaydi.
 */
export async function exportStudentsApi(
  params: Record<string, unknown>,
  fmt: "xlsx" | "pdf",
): Promise<void> {
  try {
    const res = await apiClient.get("/students/export", {
      params: { ...params, fmt },
      responseType: "blob",
    });
    // Fayl nomini Content-Disposition'dan olamiz (bo'lmasa — standart)
    const cd = (res.headers["content-disposition"] as string | undefined) ?? "";
    const match = /filename="?([^";]+)"?/.exec(cd);
    const filename = match ? match[1] : `talabalar.${fmt}`;

    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Xato javob blob ko'rinishida keladi — ichidagi {detail} ni o'qib chiqaramiz
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text());
        throw new Error(parsed.detail || "Eksport amalga oshmadi");
      } catch (e) {
        if (e instanceof Error && e.message) throw e;
      }
    }
    throw err;
  }
}

// === Student Logs API ===
export async function getStudentLogsApi(
  params: Record<string, string | number | boolean | undefined | null>
): Promise<import("./interfaces").StudentLogListResponse> {
  const clean: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") clean[k] = v;
  }
  const res = await apiClient.get("/students/logs", { params: clean });
  return res.data;
}

export async function getStudentLogDetailApi(
  id: number
): Promise<import("./interfaces").StudentLogDetailResponse> {
  const res = await apiClient.get(`/students/logs/${id}`);
  return res.data;
}

export async function createStudentLogApi(data: import("./interfaces").StudentLogCreate): Promise<import("./interfaces").StudentLogResponse> {
  const res = await apiClient.post("/students/logs", data);
  return res.data;
}

export async function updateStudentLogApi(id: number, data: import("./interfaces").StudentLogUpdate): Promise<import("./interfaces").StudentLogResponse> {
  const res = await apiClient.patch(`/students/logs/${id}`, data);
  return res.data;
}

export async function deleteStudentLogApi(id: number): Promise<void> {
  await apiClient.delete(`/students/logs/${id}`);
}

// === Cheating Logs API ===
export async function getCheatingLogsApi(params: Record<string, string | number>): Promise<import("./interfaces").CheatingLogListResponse> {
  const res = await apiClient.get("/students/cheating-logs", { params });
  return res.data;
}

export async function createCheatingLogApi(data: import("./interfaces").CheatingLogCreate): Promise<import("./interfaces").CheatingLogResponse> {
  const res = await apiClient.post("/students/cheating-logs", data);
  return res.data;
}

export async function updateCheatingLogApi(id: number, data: import("./interfaces").CheatingLogUpdate): Promise<import("./interfaces").CheatingLogResponse> {
  const res = await apiClient.patch(`/students/cheating-logs/${id}`, data);
  return res.data;
}

export async function deleteCheatingLogApi(id: number): Promise<void> {
  await apiClient.delete(`/students/cheating-logs/${id}`);
}

// === Permissions API ===
export async function getPermissionsApi(): Promise<import("./interfaces").PermissionResponse[]> {
  const res = await apiClient.get("/permissions");
  return res.data;
}

export async function getRolesWithPermissionsApi(): Promise<import("./interfaces").RolePermissionsResponse[]> {
  const res = await apiClient.get("/permissions/roles");
  return res.data;
}

export async function assignPermissionsToRoleApi(roleId: number, data: import("./interfaces").AssignPermissionsRequest): Promise<import("./interfaces").RolePermissionsResponse> {
  const res = await apiClient.put(`/permissions/roles/${roleId}`, data);
  return res.data;
}

// === Pasport info (GTSP) ===

export interface PasportInfoRequest {
  ps_ser: string;
  ps_num: string;
  imei: string; // JShShIR (PINFL) — GTSP uchun majburiy
}

export interface PasportInfoResponse {
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  sex: number | null;
  sex_label: string | null;
  ps_ser: string;
  ps_num: string;
  imei: string | null;
  photo: string | null;
  birth_place: string | null;
  birth_date: string | null;
  birth_country: string | null;
  livestatus: string | null;
  nationality: string | null;
  doc_give_place: string | null;
  matches_date_begin_document: string | null;
  matches_date_end_document: string | null;
}

export async function getPasportInfoApi(
  data: PasportInfoRequest,
): Promise<PasportInfoResponse> {
  const res = await apiClient.post<PasportInfoResponse>("/pasport-info", data);
  return res.data;
}

// === Davomat bot foydalanuvchilari (admin) ===

export async function getDavomatBotsApi(): Promise<import("./interfaces").DavomatBotAdminResponse[]> {
  const res = await apiClient.get("/admin/davomat-bots");
  return res.data;
}

export async function createDavomatBotApi(
  data: import("./interfaces").DavomatBotCreateRequest,
): Promise<import("./interfaces").DavomatBotAdminResponse> {
  const res = await apiClient.post("/admin/davomat-bots", data);
  return res.data;
}

export async function updateDavomatBotApi(
  id: number,
  data: import("./interfaces").DavomatBotUpdateRequest,
): Promise<import("./interfaces").DavomatBotAdminResponse> {
  const res = await apiClient.patch(`/admin/davomat-bots/${id}`, data);
  return res.data;
}

export async function deleteDavomatBotApi(id: number): Promise<void> {
  await apiClient.delete(`/admin/davomat-bots/${id}`);
}

// === Statistika bot foydalanuvchilari (admin) ===

export async function getStatisticBotsApi(): Promise<import("./interfaces").StatisticBotAdminResponse[]> {
  const res = await apiClient.get("/admin/statistic-bots");
  return res.data;
}

export async function createStatisticBotApi(
  data: import("./interfaces").StatisticBotCreateRequest,
): Promise<import("./interfaces").StatisticBotAdminResponse> {
  const res = await apiClient.post("/admin/statistic-bots", data);
  return res.data;
}

export async function updateStatisticBotApi(
  id: number,
  data: import("./interfaces").StatisticBotUpdateRequest,
): Promise<import("./interfaces").StatisticBotAdminResponse> {
  const res = await apiClient.patch(`/admin/statistic-bots/${id}`, data);
  return res.data;
}

export async function deleteStatisticBotApi(id: number): Promise<void> {
  await apiClient.delete(`/admin/statistic-bots/${id}`);
}

// === Qabul realtime statistika (yil dinamik) ===

export async function getQabulStatsApi(
  force = false,
): Promise<import("./interfaces").QabulStats> {
  const res = await apiClient.get("/statistic-bot/qabul", {
    params: force ? { force: true } : undefined,
  });
  return res.data;
}

// === Natija uchun tahlil ===

export type ResultAnalysisMode =
  | "in_face_not_excluded_no_result"
  | "in_face_excluded_has_result"
  | "not_in_face_has_result";

/** Textarea'dan olingan bitta natija qatori (solishtiruvga kerakli maydonlar). */
export interface ResultAnalysisRow {
  imei: string | null;
  abitur_id: string | null;
  tday: string | null;
  common_ball: string | null;
  deleted: boolean; // tahlil mantiqi uchun (parsed)
  deleted_raw: string | null; // ko'rsatish uchun (xom qiymat)
}

export interface ResultAnalysisRequest {
  test_session_id: number;
  day: string | null; // YYYY-MM-DD; null → "Umumiy" (barcha kunlar)
  mode: ResultAnalysisMode;
  rows: ResultAnalysisRow[];
}

export interface ResultAnalysisItem {
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  imei: string | null;
  region_name: string | null;
  zone_name: string | null;
  test_day: string | null;
  smena_name: string | null;
  abitur_id: string | null;
  tday: string | null;
  deleted: string | null;
}

export interface ResultAnalysisResponse {
  mode: ResultAnalysisMode;
  count: number;
  scope_total: number;
  pasted_total: number;
  pasted_result_count: number;
  items: ResultAnalysisItem[];
}

export interface ResultAnalysisScopeSession {
  id: number;
  name: string;
  number: number;
  days: string[]; // ISO "YYYY-MM-DD", o'sish tartibida
}

/** Test bo'yicha aktiv sessiyalar + test kunlari (forma ko'lam tanlovi uchun). */
export async function getResultAnalysisSessionsApi(
  testId: number,
): Promise<ResultAnalysisScopeSession[]> {
  const res = await apiClient.get<ResultAnalysisScopeSession[]>(
    "/result-analysis/sessions",
    { params: { test_id: testId } },
  );
  return res.data;
}

export async function analyzeResultsApi(
  data: ResultAnalysisRequest,
): Promise<ResultAnalysisResponse> {
  const res = await apiClient.post<ResultAnalysisResponse>(
    "/result-analysis/analyze",
    data,
  );
  return res.data;
}

/** Tahlil natijasini .xlsx qilib yuklab olish (brauzer faylni saqlaydi). */
export async function exportResultAnalysisApi(
  data: ResultAnalysisRequest,
): Promise<void> {
  try {
    const res = await apiClient.post("/result-analysis/export", data, {
      responseType: "blob",
    });
    const cd = (res.headers["content-disposition"] as string | undefined) ?? "";
    const match = /filename="?([^";]+)"?/.exec(cd);
    const filename = match ? match[1] : "natija_tahlil.xlsx";

    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    // Xato javob blob ko'rinishida keladi — ichidagi {detail} ni o'qiymiz.
    const data2 = (err as { response?: { data?: unknown } })?.response?.data;
    if (data2 instanceof Blob) {
      try {
        const parsed = JSON.parse(await data2.text());
        throw new Error(parsed.detail || "Eksport amalga oshmadi");
      } catch (e) {
        if (e instanceof Error && e.message) throw e;
      }
    }
    throw err;
  }
}
