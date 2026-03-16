import { usePermission } from "../hooks/usePermission";

interface PermissionGateProps {
  /** Kerakli permission codename (bitta) */
  permission?: string;
  /** Kamida bitta permission bo'lsa yetarli */
  anyOf?: string[];
  /** Ko'rsatiladigan content */
  children: React.ReactNode;
  /** Permission bo'lmasa ko'rsatiladigan fallback */
  fallback?: React.ReactNode;
}

/**
 * Permission asosida conditional rendering.
 * Admin har doim ko'radi.
 */
export default function PermissionGate({
  permission,
  anyOf,
  children,
  fallback = null,
}: PermissionGateProps) {
  const { hasPermission, hasAnyPermission } = usePermission();

  let allowed = false;
  if (permission) {
    allowed = hasPermission(permission);
  } else if (anyOf && anyOf.length > 0) {
    allowed = hasAnyPermission(...anyOf);
  } else {
    allowed = true;
  }

  return allowed ? <>{children}</> : <>{fallback}</>;
}
