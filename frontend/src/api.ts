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
  UserResponse,
  VerificationLogResponse,
} from "./interfaces";
import { getAccessToken, setAccessToken } from "./tokenStore";

const API_BASE = "/api/v1";

const apiClient = axios.create({ baseURL: API_BASE, withCredentials: true });

// Request interceptor — access tokenni headerga qo'shish
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor — 401 bo'lganda token yangilash
let refreshPromise: Promise<string> | null = null;

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && !original.url?.includes("/auth/")) {
      original._retry = true;
      try {
        // Bir vaqtda faqat bitta refresh so'rov yuboriladi
        if (!refreshPromise) {
          refreshPromise = refreshApi()
            .then((tokens) => {
              setAccessToken(tokens.access_token);
              return tokens.access_token;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const newToken = await refreshPromise;
        original.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(original);
      } catch {
        setAccessToken(null);
      }
    }
    return Promise.reject(error);
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

export async function updateUserApi(userId: number, data: Record<string, unknown>): Promise<UserResponse> {
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
}> {
  const res = await apiClient.get(`/test-sessions/${sessionId}/embedding-progress`);
  return res.data;
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

// === Student Logs API ===
export async function getStudentLogsApi(params: Record<string, string | number>): Promise<import("./interfaces").StudentLogListResponse> {
  const res = await apiClient.get("/students/logs", { params });
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
