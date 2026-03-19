import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { UserResponse } from "../interfaces";
import { getMeApi, loginApi, logoutApi, refreshApi } from "../api";
import { setAccessToken } from "../tokenStore";

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
  const isAdmin = user?.role_key === 1;

  // Ilovani ochganda cookie dagi refresh token orqali sessiyani tiklash
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const tokens = await refreshApi();
        if (cancelled) return;
        setAccessToken(tokens.access_token);
        if (tokens.user) {
          setUser(tokens.user);
        } else {
          const me = await getMeApi();
          if (!cancelled) setUser(me);
        }
      } catch {
        if (!cancelled) setAccessToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    // Brauzer cookie ni saqlashiga vaqt berish (Ctrl+Shift+R)
    const timerId = setTimeout(init, 50);
    return () => {
      cancelled = true;
      clearTimeout(timerId);
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

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } catch {
      // ignore
    }
    setAccessToken(null);
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
