import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { UserResponse } from "../interfaces";
import { getMeApi, loginApi, logoutApi, refreshTokensOnce, setOnUnauthorized } from "../api";
import { getAccessToken, setAccessToken } from "../tokenStore";

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** `/auth/me` ni qayta o'qib, ruxsatlarni yangilaydi. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = user !== null;
  const isAdmin = user?.role_key === 1;

  // Ilovani ochganda sessiyani tiklash:
  //   1) sessionStorage'da access token bor bo'lsa — to'g'ridan-to'g'ri /me chaqiramiz.
  //      Token muddati tugagan bo'lsa, axios interceptor avtomatik refresh qiladi.
  //   2) Token yo'q bo'lsa (yangi tab/sessiya) — refresh chaqiramiz.
  // Bu F5 da refresh_tokens jadvaliga ortiqcha row qo'shilishini oldini oladi.
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const existingToken = getAccessToken();
        if (existingToken) {
          // Token bor — /me orqali tekshirib ko'ramiz (401 bo'lsa interceptor refresh qiladi)
          const me = await getMeApi();
          if (!cancelled) setUser(me);
        } else {
          // Token yo'q — singleton refresh (interceptor bilan bir xil promise)
          const tokens = await refreshTokensOnce();
          if (cancelled) return;
          if (tokens.user) {
            setUser(tokens.user);
          } else {
            const me = await getMeApi();
            if (!cancelled) setUser(me);
          }
        }
      } catch {
        if (!cancelled) setAccessToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const tokens = await loginApi({ username, password });
    setAccessToken(tokens.access_token);
    if (tokens.user) {
      setUser(tokens.user);
    } else {
      const me = await getMeApi();
      setUser(me);
    }
  }, []);

  // Ruxsatlar faqat login paytida olinardi — admin rolga huquq qo'shsa,
  // foydalanuvchi buni qayta kirmaguncha ko'rmasdi. Endi tab'ga qaytilganda
  // (va qo'lda chaqirilganda) `/auth/me` qayta o'qiladi. Backend baribir har
  // so'rovda DB'dan tekshiradi — bu faqat UI ni haqiqatga moslash uchun.
  const refreshUser = useCallback(async () => {
    try {
      const me = await getMeApi();
      setUser(me);
    } catch {
      // Jimgina — 401 bo'lsa interceptor logout qiladi
    }
  }, []);

  useEffect(() => {
    let lastAt = 0;
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      // Tez-tez tab almashtirishda /auth/me ni bombardimon qilmaymiz
      if (Date.now() - lastAt < 30_000) return;
      lastAt = Date.now();
      if (getAccessToken()) void refreshUser();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } catch {
      // ignore
    }
    setAccessToken(null);
    setUser(null);
  }, []);

  // Refresh muvaffaqiyatsiz bo'lsa, foydalanuvchini darhol logout qilamiz
  useEffect(() => {
    setOnUnauthorized(() => {
      setAccessToken(null);
      setUser(null);
    });
    return () => setOnUnauthorized(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isAdmin, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
