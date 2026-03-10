import axios from "axios";
import type {
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  CreateUserRequest,
  DashboardStats,
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

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // Cookie yuborish uchun
});

// Request interceptor: JWT Bearer token qo'shish
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Concurrent refresh himoyasi — faqat bitta refresh so'rov yuboriladi
let refreshPromise: Promise<TokenPairResponse> | null = null;

async function doRefresh(): Promise<TokenPairResponse> {
  // Cookie avtomatik yuboriladi (withCredentials: true)
  const res = await axios.post<TokenPairResponse>(
    `${API_BASE}/auth/refresh`,
    {},
    { withCredentials: true },
  );
  return res.data;
}

// Response interceptor: 401 da auto-refresh (race-condition safe)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Faqat 401 va auth bo'lmagan endpointlar uchun retry
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/")
    ) {
      originalRequest._retry = true;

      try {
        // Agar allaqachon refresh bo'layotgan bo'lsa, o'sha promise ni kutamiz
        if (!refreshPromise) {
          refreshPromise = doRefresh();
        }
        const tokens = await refreshPromise;

        setAccessToken(tokens.access_token);
        originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
        return apiClient(originalRequest);
      } catch {
        // Refresh muvaffaqiyatsiz — tokenni tozalash
        setAccessToken(null);
      } finally {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  },
);

// === Auth API ===
export async function loginApi(data: LoginRequest): Promise<TokenPairResponse> {
  const formData = new URLSearchParams();
  formData.append("username", data.username);
  formData.append("password", data.password);
  const res = await apiClient.post<TokenPairResponse>("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
}

export async function refreshApi(): Promise<TokenPairResponse> {
  // Cookie avtomatik yuboriladi
  const res = await apiClient.post<TokenPairResponse>("/auth/refresh", {});
  return res.data;
}

export async function logoutApi(): Promise<void> {
  await apiClient.post("/auth/logout", {});
}

export async function getMeApi(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>("/auth/me");
  return res.data;
}

// === Photo API ===
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

// === Admin API ===
export async function getLogByIdApi(logId: number): Promise<VerificationLogResponse> {
  const res = await apiClient.get<VerificationLogResponse>(`/admin/logs/${logId}`);
  return res.data;
}

export async function getLogsApi(params: {
  page?: number;
  per_page?: number;
  user_id?: number;
  date_from?: string;
  date_to?: string;
}): Promise<PaginatedLogs> {
  const res = await apiClient.get<PaginatedLogs>("/admin/logs", { params });
  return res.data;
}

export async function getStatsApi(): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>("/admin/stats");
  return res.data;
}

export async function getUsersApi(): Promise<UserResponse[]> {
  const res = await apiClient.get<UserResponse[]>("/admin/users");
  return res.data;
}

export async function createUserApi(data: CreateUserRequest): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>("/admin/users", data);
  return res.data;
}

// === Admin Face Logs API ===
export async function getFaceLogsApi(params: {
  page?: number;
  per_page?: number;
  user_id?: number;
  date_from?: string;
  date_to?: string;
}): Promise<PaginatedFaceLogs> {
  const res = await apiClient.get<PaginatedFaceLogs>("/admin/face-logs", { params });
  return res.data;
}

export async function getFaceLogByIdApi(logId: number): Promise<FaceLogResponse> {
  const res = await apiClient.get<FaceLogResponse>(`/admin/face-logs/${logId}`);
  return res.data;
}

export async function getFaceStatsApi(): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>("/admin/face-stats");
  return res.data;
}

// === Admin API Keys ===
export async function getApiKeysApi(): Promise<ApiKeyResponse[]> {
  const res = await apiClient.get<ApiKeyResponse[]>("/admin/api-keys");
  return res.data;
}

export async function createApiKeyApi(data: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
  const res = await apiClient.post<ApiKeyCreateResponse>("/admin/api-keys", data);
  return res.data;
}

export async function revokeApiKeyApi(keyId: number): Promise<void> {
  await apiClient.delete(`/admin/api-keys/${keyId}`);
}

/** Authenticated rasm URL olish (blob URL qaytaradi) */
export async function getAuthImageUrl(url: string): Promise<string> {
  const res = await apiClient.get(url, { responseType: "blob" });
  return URL.createObjectURL(res.data);
}

/** Faylni base64 ga aylantirish */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
  });
}
