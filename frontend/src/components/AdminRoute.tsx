import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AdminRoute() {
  const { user, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  // Admin yoki kamida bitta permissioni bor foydalanuvchi kiroladi
  const hasAnyPermission = isAdmin || (user?.permissions && user.permissions.length > 0);

  if (!hasAnyPermission) {
    return <Navigate to="/verify" replace />;
  }

  return <Outlet />;
}
