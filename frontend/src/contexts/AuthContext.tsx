import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { UserResponse } from "../interfaces";
import { getMeApi, loginApi, logoutApi, refreshApi } from "../api";
import {
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../tokenStore";

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = user !== null;
  const isAdmin = user?.role === "admin";

  // Ilovani ochganda refresh token orqali sessiyani tiklash
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        setLoading(false);
        return;
      }
      try {
        const tokens = await refreshApi(refreshToken);
        if (cancelled) return;
        setAccessToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
        if (tokens.user) {
          setUser(tokens.user);
        } else {
          // Agar responseda user bo'lmasa, /auth/me dan olish
          const me = await getMeApi();
          if (!cancelled) setUser(me);
        }
      } catch {
        setAccessToken(null);
        setRefreshToken(null);
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
    setRefreshToken(tokens.refresh_token);
    if (tokens.user) {
      setUser(tokens.user);
    } else {
      // Fallback: /auth/me dan user ma'lumotini olish
      const me = await getMeApi();
      setUser(me);
    }
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await logoutApi(refreshToken);
      } catch {
        // ignore
      }
    }
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isAdmin, loading, login, logout }}
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
