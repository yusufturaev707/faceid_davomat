import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * Faqat superadmin (backend `is_super_admin`) kira oladi — permission orqali
 * berilmaydigan bo'limlar uchun (server monitoringi). Bu faqat UI qatlami:
 * haqiqiy tekshiruv backenddagi `require_super_admin`.
 */
export default function SuperAdminRoute() {
  const { isSuperAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!isSuperAdmin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
