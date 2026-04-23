import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { usePermission } from "../hooks/usePermission";

interface PermissionRouteProps {
  /** Kerakli permission codename (bitta). */
  permission?: string;
  /** Kamida bittasi bo'lsa yetarli. `permission` va `anyOf` bir vaqtda berilsa, `permission` ustun. */
  anyOf?: string[];
  /** Barchasi bo'lishi shart (kamdan-kam kerak, audit/doc sahifalar uchun). */
  allOf?: string[];
  /** Ruxsat yo'q bo'lsa qayerga yo'naltirish. Default: /verify */
  redirectTo?: string;
}

/**
 * Routelarni granular huquqlar bilan himoyalovchi wrapper.
 * Admin (role_key === 1) har doim o'tadi.
 */
export default function PermissionRoute({
  permission,
  anyOf,
  allOf,
  redirectTo = "/verify",
}: PermissionRouteProps) {
  const { isAuthenticated, loading } = useAuth();
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermission();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Admin roliga seed skriptda barcha permissionlar biriktiriladi,
  // shuning uchun hasPermission() admin uchun ham explicit tekshiruv bo'ladi.
  let allowed = false;
  if (permission) {
    allowed = hasPermission(permission);
  } else if (allOf && allOf.length > 0) {
    allowed = hasAllPermissions(...allOf);
  } else if (anyOf && anyOf.length > 0) {
    allowed = hasAnyPermission(...anyOf);
  } else {
    // Hech qanday permission berilmagan bo'lsa, faqat autentifikatsiya yetarli
    allowed = true;
  }

  if (!allowed) {
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
}
