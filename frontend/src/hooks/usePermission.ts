import { useAuth } from "../contexts/AuthContext";

/**
 * Permission tekshirish hook.
 * Admin (role_key=1) har doim ruxsat oladi.
 */
export function usePermission() {
  const { user } = useAuth();

  const hasPermission = (codename: string): boolean => {
    if (!user) return false;
    if (user.role_key === 1) return true; // Admin bypasses
    return user.permissions?.includes(codename) ?? false;
  };

  const hasAnyPermission = (...codenames: string[]): boolean => {
    if (!user) return false;
    if (user.role_key === 1) return true;
    return codenames.some((c) => user.permissions?.includes(c));
  };

  return { hasPermission, hasAnyPermission };
}
