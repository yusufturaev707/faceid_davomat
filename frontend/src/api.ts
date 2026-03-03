import axios from "axios";
import type {
  CreateUserRequest,
  DashboardStats,
  LoginRequest,
  PaginatedLogs,
  PhotoVerifyRequest,
  PhotoVerifyResponse,
  TokenPairResponse,
  UserResponse,
  VerificationLogResponse,
} from "./interfaces";
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./tokenStore";

const API_BASE = "/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
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
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return Promise.reject(new Error("No refresh token"));
  }
  // Raw axios ishlatamiz (interceptordan o'tmaydi)
  const res = await axios.post<TokenPairResponse>(
    `${API_BASE}/auth/refresh`,
    { refresh_token: refreshToken },
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
        setRefreshToken(tokens.refresh_token);
        originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
        return apiClient(originalRequest);
      } catch {
        // Refresh muvaffaqiyatsiz — tokenlarni tozalash
        setAccessToken(null);
        setRefreshToken(null);
        // React Router orqali redirect (window.location emas)
      } finally {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  },
);

// === Auth API ===
export async function loginApi(data: LoginRequest): Promise<TokenPairResponse> {
  const res = await apiClient.post<TokenPairResponse>("/auth/login", data);
  return res.data;
}

export async function refreshApi(refreshToken: string): Promise<TokenPairResponse> {
  const res = await axios.post<TokenPairResponse>(`${API_BASE}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  return res.data;
}

export async function logoutApi(refreshToken: string): Promise<void> {
  await apiClient.post("/auth/logout", { refresh_token: refreshToken });
}

export async function getMeApi(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>("/auth/me");
  return res.data;
}

// === Photo API ===
export async function verifyPhoto(data: PhotoVerifyRequest): Promise<PhotoVerifyResponse> {
  const res = await apiClient.post<PhotoVerifyResponse>("/photo/verify-photo", data);
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

/** Faylni base64 ga aylantirish */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
  });
}
