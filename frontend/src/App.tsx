import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import PermissionRoute from "./components/PermissionRoute";
import ProtectedRoute from "./components/ProtectedRoute";
import { usePermission } from "./hooks/usePermission";
import { PERM } from "./permissions";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import LogDetailPage from "./pages/LogDetailPage";
import LogsPage from "./pages/LogsPage";
import FaceLogsPage from "./pages/FaceLogsPage";
import FaceLogDetailPage from "./pages/FaceLogDetailPage";
import ApiKeysPage from "./pages/ApiKeysPage";
import EmbeddingPage from "./pages/EmbeddingPage";
import PasportInfoPage from "./pages/PasportInfoPage";
import NotFoundPage from "./pages/NotFoundPage";
import VerifyPage from "./pages/VerifyPage";
import SettingsPage from "./pages/SettingsPage";
import TestSessionsPage from "./pages/TestSessionsPage";
import TestSessionDetailPage from "./pages/TestSessionDetailPage";
import TestDashboardPage from "./pages/TestDashboardPage";
import UsersPage from "./pages/UsersPage";
import DavomatBotsPage from "./pages/DavomatBotsPage";
import TestsPage from "./pages/TestsPage";
import SmenasPage from "./pages/SmenasPage";
import SessionStatesPage from "./pages/SessionStatesPage";
import RegionsPage from "./pages/RegionsPage";
import ZonesPage from "./pages/ZonesPage";
import RolesPage from "./pages/RolesPage";
import ReasonsPage from "./pages/ReasonsPage";
import ReasonTypesPage from "./pages/ReasonTypesPage";
import BlacklistPage from "./pages/BlacklistPage";
import GendersPage from "./pages/GendersPage";
import VerifyTwoFacePage from "./pages/VerifyTwoFacePage";
import StudentsPage from "./pages/StudentsPage";
import StudentLogsPage from "./pages/StudentLogsPage";
import CheatingLogsPage from "./pages/CheatingLogsPage";
import RolePermissionsPage from "./pages/RolePermissionsPage";
import FailedLoginsPage from "./pages/FailedLoginsPage";
import StatisticsPage from "./pages/StatisticsPage";

/**
 * Asosiy sahifani foydalanuvchining huquqlariga qarab tanlash.
 * Xizmat sahifalari endi permission-gate'lanadi, shuning uchun root'ni
 * doim /verify ga yuborib bo'lmaydi — ruxsati yo'q user redirect halqasiga
 * tushib qolardi.
 */
function HomeRedirect() {
  const { hasPermission, hasAnyPermission } = usePermission();

  if (hasPermission(PERM.PHOTO_VERIFY)) return <Navigate to="/verify" replace />;
  if (hasPermission(PERM.PHOTO_VERIFY_TWO_FACE))
    return <Navigate to="/verify-two-face" replace />;
  if (hasPermission(PERM.EMBEDDING_EXTRACT))
    return <Navigate to="/embedding" replace />;
  if (hasAnyPermission(PERM.DASHBOARD_READ, PERM.DASHBOARD_STATS))
    return <Navigate to="/dashboard" replace />;
  if (hasAnyPermission(PERM.TEST_SESSION_READ))
    return <Navigate to="/test-dashboard" replace />;
  return <Navigate to="/settings" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<HomeRedirect />} />

          <Route element={<PermissionRoute permission={PERM.PHOTO_VERIFY} redirectTo="/settings" />}>
            <Route path="/verify" element={<VerifyPage />} />
          </Route>

          <Route
            element={
              <PermissionRoute
                permission={PERM.PHOTO_VERIFY_TWO_FACE}
                redirectTo="/settings"
              />
            }
          >
            <Route path="/verify-two-face" element={<VerifyTwoFacePage />} />
          </Route>

          <Route
            element={
              <PermissionRoute
                permission={PERM.EMBEDDING_EXTRACT}
                redirectTo="/settings"
              />
            }
          >
            <Route path="/embedding" element={<EmbeddingPage />} />
          </Route>

          <Route
            element={
              <PermissionRoute
                permission={PERM.PASPORT_INFO_READ}
                redirectTo="/settings"
              />
            }
          >
            <Route path="/pasport-info" element={<PasportInfoPage />} />
          </Route>

          <Route path="/settings" element={<SettingsPage />} />

          {/* Boshqaruv */}
          <Route
            element={
              <PermissionRoute
                anyOf={[PERM.DASHBOARD_READ, PERM.DASHBOARD_STATS]}
              />
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
          </Route>

          <Route element={<PermissionRoute permission={PERM.LOG_READ} />}>
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/logs/:id" element={<LogDetailPage />} />
          </Route>

          <Route element={<PermissionRoute permission={PERM.FACE_LOG_READ} />}>
            <Route path="/face-logs" element={<FaceLogsPage />} />
            <Route path="/face-logs/:id" element={<FaceLogDetailPage />} />
          </Route>

          <Route
            element={
              <PermissionRoute
                anyOf={[PERM.API_KEY_READ, PERM.API_KEY_CREATE]}
              />
            }
          >
            <Route path="/api-keys" element={<ApiKeysPage />} />
          </Route>

          <Route
            element={<PermissionRoute permission={PERM.STATISTICS_READ} />}
          >
            <Route path="/statistics" element={<StatisticsPage />} />
          </Route>

          {/* Test markazi */}
          <Route
            element={
              <PermissionRoute
                anyOf={[PERM.DASHBOARD_READ, PERM.TEST_SESSION_READ]}
              />
            }
          >
            <Route path="/test-dashboard" element={<TestDashboardPage />} />
          </Route>

          <Route
            element={<PermissionRoute permission={PERM.TEST_SESSION_READ} />}
          >
            <Route path="/test-sessions" element={<TestSessionsPage />} />
            <Route
              path="/test-sessions/:id"
              element={<TestSessionDetailPage />}
            />
          </Route>

          <Route element={<PermissionRoute permission={PERM.STUDENT_READ} />}>
            <Route path="/students" element={<StudentsPage />} />
          </Route>

          <Route
            element={<PermissionRoute permission={PERM.STUDENT_LOG_READ} />}
          >
            <Route path="/student-logs" element={<StudentLogsPage />} />
          </Route>

          <Route
            element={<PermissionRoute permission={PERM.CHEATING_LOG_READ} />}
          >
            <Route path="/cheating-logs" element={<CheatingLogsPage />} />
          </Route>

          {/* Tizim sozlamalari */}
          <Route element={<PermissionRoute permission={PERM.USER_READ} />}>
            <Route path="/users" element={<UsersPage />} />
          </Route>

          <Route element={<PermissionRoute permission={PERM.DAVOMAT_BOT_READ} />}>
            <Route path="/davomat-bots" element={<DavomatBotsPage />} />
          </Route>

          <Route element={<PermissionRoute permission={PERM.ROLE_READ} />}>
            <Route path="/manage-roles" element={<RolesPage />} />
          </Route>

          <Route
            element={
              <PermissionRoute
                anyOf={[PERM.ROLE_UPDATE, PERM.PERMISSION_READ]}
              />
            }
          >
            <Route
              path="/manage-permissions"
              element={<RolePermissionsPage />}
            />
          </Route>

          <Route
            element={<PermissionRoute permission={PERM.FAILED_LOGIN_READ} />}
          >
            <Route path="/failed-logins" element={<FailedLoginsPage />} />
          </Route>

          {/* Ma'lumotnomalar */}
          <Route element={<PermissionRoute permission={PERM.LOOKUP_READ} />}>
            <Route path="/manage-tests" element={<TestsPage />} />
            <Route path="/manage-smenas" element={<SmenasPage />} />
            <Route
              path="/manage-session-states"
              element={<SessionStatesPage />}
            />
            <Route path="/manage-regions" element={<RegionsPage />} />
            <Route path="/manage-zones" element={<ZonesPage />} />
            <Route path="/manage-reasons" element={<ReasonsPage />} />
            <Route
              path="/manage-reason-types"
              element={<ReasonTypesPage />}
            />
            <Route path="/manage-blacklist" element={<BlacklistPage />} />
            <Route path="/manage-genders" element={<GendersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
