import { useAuth } from "../contexts/AuthContext";
import type { PermissionCode } from "../permissions";

/**
 * Permission tekshirish hook.
 * Admin (role_key=1) seed skriptda AVTOMATIK barcha permissionlarni oladi,
 * shuning uchun "isAdmin" explicit bypass emas — permission listidan o'tadi.
 * `isAdmin` flag faqat UI uchun (masalan, danger zone bannerlari) ishlatilsin.
 */
export function usePermission() {
  const { user } = useAuth();
  const isAdmin = user?.role_key === 1;
  const perms = user?.permissions ?? [];

  const hasPermission = (codename: PermissionCode | string): boolean => {
    if (!user) return false;
    return perms.includes(codename);
  };

  const hasAnyPermission = (...codenames: (PermissionCode | string)[]): boolean => {
    if (!user) return false;
    if (codenames.length === 0) return false;
    return codenames.some((c) => perms.includes(c));
  };

  const hasAllPermissions = (...codenames: (PermissionCode | string)[]): boolean => {
    if (!user) return false;
    if (codenames.length === 0) return true;
    return codenames.every((c) => perms.includes(c));
  };

  return { hasPermission, hasAnyPermission, hasAllPermissions, isAdmin };
}
