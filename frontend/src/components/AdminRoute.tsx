import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * Faqat admin (role_key === 1) kira oladi.
 * Granular huquqlar asosida kirish uchun <PermissionRoute /> ishlatilsin.
 */
export default function AdminRoute() {
  const { isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/verify" replace />;
  }

  return <Outlet />;
}
