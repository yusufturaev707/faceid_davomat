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
import NotFoundPage from "./pages/NotFoundPage";
import VerifyPage from "./pages/VerifyPage";
import SettingsPage from "./pages/SettingsPage";
import VerifyTwoFacePage from "./pages/VerifyTwoFacePage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/verify" replace />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/verify-two-face" element={<VerifyTwoFacePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/logs/:id" element={<LogDetailPage />} />
            <Route path="/face-logs" element={<FaceLogsPage />} />
            <Route path="/face-logs/:id" element={<FaceLogDetailPage />} />
            <Route path="/api-keys" element={<ApiKeysPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
