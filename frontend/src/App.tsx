import { Navigate, Route, Routes } from "react-router-dom";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import LogDetailPage from "./pages/LogDetailPage";
import LogsPage from "./pages/LogsPage";
import FaceLogsPage from "./pages/FaceLogsPage";
import FaceLogDetailPage from "./pages/FaceLogDetailPage";
import ApiKeysPage from "./pages/ApiKeysPage";
import EmbeddingPage from "./pages/EmbeddingPage";
import NotFoundPage from "./pages/NotFoundPage";
import VerifyPage from "./pages/VerifyPage";
import SettingsPage from "./pages/SettingsPage";
import TestSessionsPage from "./pages/TestSessionsPage";
import TestSessionDetailPage from "./pages/TestSessionDetailPage";
import TestDashboardPage from "./pages/TestDashboardPage";
import UsersPage from "./pages/UsersPage";
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

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/verify" replace />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/verify-two-face" element={<VerifyTwoFacePage />} />
          <Route path="/embedding" element={<EmbeddingPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route element={<AdminRoute />}>
            {/* Boshqaruv */}
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/logs/:id" element={<LogDetailPage />} />
            <Route path="/face-logs" element={<FaceLogsPage />} />
            <Route path="/face-logs/:id" element={<FaceLogDetailPage />} />
            <Route path="/api-keys" element={<ApiKeysPage />} />
            {/* Test markazi */}
            <Route path="/test-dashboard" element={<TestDashboardPage />} />
            <Route path="/test-sessions" element={<TestSessionsPage />} />
            <Route path="/test-sessions/:id" element={<TestSessionDetailPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/student-logs" element={<StudentLogsPage />} />
            <Route path="/cheating-logs" element={<CheatingLogsPage />} />
            <Route path="/users" element={<UsersPage />} />
            {/* Sozlamalar (lookup) */}
            <Route path="/manage-tests" element={<TestsPage />} />
            <Route path="/manage-smenas" element={<SmenasPage />} />
            <Route path="/manage-session-states" element={<SessionStatesPage />} />
            <Route path="/manage-regions" element={<RegionsPage />} />
            <Route path="/manage-zones" element={<ZonesPage />} />
            <Route path="/manage-roles" element={<RolesPage />} />
            <Route path="/manage-permissions" element={<RolePermissionsPage />} />
            <Route path="/manage-reasons" element={<ReasonsPage />} />
            <Route path="/manage-reason-types" element={<ReasonTypesPage />} />
            <Route path="/manage-blacklist" element={<BlacklistPage />} />
            <Route path="/manage-genders" element={<GendersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
