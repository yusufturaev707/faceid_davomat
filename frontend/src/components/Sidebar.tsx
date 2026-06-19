import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { usePermission } from "../hooks/usePermission";
import { PERM } from "../permissions";
import logoBba from "../assets/logo_bba.png";

/**
 * Material 3 "pill" navigation item.
 * - Selected: secondaryContainer-style filled background
 * - Unselected: transparent with subtle hover state-layer
 */
const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `group relative flex items-center gap-3 mx-2 h-11 px-4 rounded-full text-[13.5px] font-medium tracking-[0.005em] transition-colors duration-200 ${
    isActive
      ? "bg-primary-100 dark:bg-primary-900/45 text-primary-800 dark:text-primary-100"
      : "text-gray-700 dark:text-slate-300 hover:bg-gray-100/70 dark:hover:bg-slate-700/40 hover:text-gray-900 dark:hover:text-white"
  }`;

const iconClass = "w-5 h-5 shrink-0";

function SectionHeader({ label, accent }: { label: string; accent: string }) {
  return (
    <div className="px-6 pt-5 pb-2 select-none">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-slate-400 flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${accent}`} />
        {label}
      </p>
    </div>
  );
}

interface SidebarProps {
  /** Mobile/tablet (< lg) drawer state. Ignored on desktop where the drawer is persistent. */
  drawerOpen?: boolean;
  /** Called when the user requests to close the mobile drawer. */
  onClose?: () => void;
}

export default function Sidebar({ drawerOpen = false, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { hasPermission, hasAnyPermission } = usePermission();
  const navigate = useNavigate();

  // Bo'lim ko'rinishi: admin yoki shu bo'limdagi kamida bitta permissioni bor
  const showTestMarkazi = hasAnyPermission(
    PERM.TEST_SESSION_READ,
    PERM.STUDENT_READ,
    PERM.STUDENT_LOG_READ,
    PERM.CHEATING_LOG_READ,
    PERM.STATISTICS_READ,
  );

  const showSozlamalar = hasAnyPermission(
    PERM.USER_READ,
    PERM.ROLE_READ,
    PERM.ROLE_UPDATE,
    PERM.PERMISSION_READ,
    PERM.FAILED_LOGIN_READ,
    PERM.LOOKUP_READ,
  );

  // Botlar — Davomat va Statistika bot foydalanuvchilari alohida guruhda
  const showBotlar = hasAnyPermission(
    PERM.DAVOMAT_BOT_READ,
    PERM.STATISTIC_BOT_READ,
  );

  const showXizmatlar = hasAnyPermission(
    PERM.PHOTO_VERIFY,
    PERM.PHOTO_VERIFY_TWO_FACE,
    PERM.EMBEDDING_EXTRACT,
    PERM.PASPORT_INFO_READ,
    PERM.QABUL_READ,
  );

  // Qabul menyusi yorlig'i — yil dinamik (har yili o'zgaradi).
  const qabulYear = new Date().getFullYear();

  const showBoshqaruv = hasAnyPermission(
    PERM.DASHBOARD_READ,
    PERM.DASHBOARD_STATS,
    PERM.LOG_READ,
    PERM.FACE_LOG_READ,
    PERM.API_KEY_READ,
    PERM.API_KEY_CREATE,
  );

  /**
   * On lg+ the drawer is part of the flex layout (sticky column).
   * On smaller screens it is a fixed modal drawer slid in via transform.
   */
  const drawerClass = `
    fixed top-0 bottom-0 left-0 z-50 w-[280px] max-w-[88vw]
    bg-white dark:bg-slate-900 border-r border-gray-200/70 dark:border-slate-800
    flex flex-col h-screen shadow-md-4
    transition-transform duration-300 ease-md-emphasized
    ${drawerOpen ? "translate-x-0" : "-translate-x-full"}
    lg:sticky lg:top-0 lg:translate-x-0 lg:max-w-none
    lg:shadow-[1px_0_2px_0_rgba(0,0,0,0.02)] dark:lg:shadow-none
  `;

  return (
    <aside className={drawerClass} aria-label="Sidebar">
      {/* Brand */}
      <div className="px-6 pt-6 pb-4 select-none flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <img
            src={logoBba}
            alt="BBA logotipi"
            className="h-10 w-auto object-contain select-none shrink-0"
            draggable={false}
          />
          {/* Vertikal ajratuvchi — brend va ilova nomini ulaydi (co-brand lockup) */}
          <div className="w-px h-9 bg-gray-200 dark:bg-slate-700 shrink-0" />
          <div className="min-w-0">
            <h1 className="text-[15px] font-semibold text-gray-900 dark:text-white tracking-tight leading-tight">
              FaceID Admin
            </h1>
            <p className="text-[10.5px] text-gray-500 dark:text-slate-400 leading-snug mt-0.5 truncate">
              Bilim va malakalarni baholash agentligi
            </p>
          </div>
        </div>
        {/* Close button — mobile drawer only */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Yopish"
          className="lg:hidden btn-icon -mr-2"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 pb-3 space-y-0.5 overflow-y-auto [scrollbar-width:thin]">
        {/* ====== Bo'lim 1: Test markazi ====== */}
        {showTestMarkazi && (
          <>
            <SectionHeader label="Test markazi" accent="bg-emerald-500" />

            {hasAnyPermission(PERM.DASHBOARD_READ, PERM.TEST_SESSION_READ) && (
              <NavLink to="/test-dashboard" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                Test Dashboard
              </NavLink>
            )}

            {hasPermission(PERM.STATISTICS_READ) && (
              <NavLink to="/statistics" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 3v18h18M7 14l3-3 4 4 5-7"
                  />
                </svg>
                Davomat
              </NavLink>
            )}

            {hasPermission(PERM.TEST_SESSION_READ) && (
              <NavLink to="/test-sessions" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                Test sessiyalar
              </NavLink>
            )}

            {hasPermission(PERM.STUDENT_READ) && (
              <NavLink to="/students" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 14l9-5-9-5-9 5 9 5z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"
                  />
                </svg>
                Talabgorlar
              </NavLink>
            )}

            {hasPermission(PERM.STUDENT_LOG_READ) && (
              <NavLink to="/student-logs" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                Binoga kirish loglari
              </NavLink>
            )}

            {hasPermission(PERM.CHEATING_LOG_READ) && (
              <NavLink to="/cheating-logs" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                Chetlatilganlar
              </NavLink>
            )}
          </>
        )}

        {/* ====== Bo'lim 2: Sozlamalar ====== */}
        {showSozlamalar && (
          <>
            <SectionHeader label="Sozlamalar" accent="bg-violet-500" />

            {hasPermission(PERM.USER_READ) && (
              <NavLink to="/users" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                Foydalanuvchilar
              </NavLink>
            )}

            {hasPermission(PERM.ROLE_READ) && (
              <NavLink to="/manage-roles" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  />
                </svg>
                Rollar
              </NavLink>
            )}

            {hasAnyPermission(PERM.ROLE_UPDATE, PERM.PERMISSION_READ) && (
              <NavLink to="/manage-permissions" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
                Huquqlar
              </NavLink>
            )}

            {hasPermission(PERM.FAILED_LOGIN_READ) && (
              <NavLink to="/failed-logins" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                Failed login audit
              </NavLink>
            )}

            {hasPermission(PERM.LOOKUP_READ) && (
              <>
                <NavLink to="/manage-regions" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Hududlar
                </NavLink>

                <NavLink to="/manage-zones" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                    />
                  </svg>
                  Binolar
                </NavLink>

                <NavLink to="/manage-tests" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                    />
                  </svg>
                  Testlar
                </NavLink>

                <NavLink to="/manage-smenas" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Smenalar
                </NavLink>

                <NavLink to="/manage-session-states" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                  Sessiya holatlari
                </NavLink>

                <NavLink to="/manage-reasons" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  Sabablar
                </NavLink>

                <NavLink to="/manage-reason-types" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                  Sabab turi
                </NavLink>

                <NavLink to="/manage-genders" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  Jinslar
                </NavLink>

                <NavLink to="/manage-blacklist" className={navLinkClass}>
                  <svg
                    className={iconClass}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                    />
                  </svg>
                  Qora ro'yxat
                </NavLink>
              </>
            )}
          </>
        )}

        {/* ====== Bo'lim: Botlar ====== */}
        {showBotlar && (
          <>
            <SectionHeader label="Botlar" accent="bg-rose-500" />

            {hasPermission(PERM.DAVOMAT_BOT_READ) && (
              <NavLink to="/davomat-bots" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                Davomat bot foydalanuvchilari
              </NavLink>
            )}

            {hasPermission(PERM.STATISTIC_BOT_READ) && (
              <NavLink to="/statistic-bots" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                Statistika bot foydalanuvchilari
              </NavLink>
            )}
          </>
        )}

        {/* ====== Bo'lim 3: Xizmatlar ====== */}
        {showXizmatlar && (
          <>
            <SectionHeader label="Xizmatlar" accent="bg-sky-500" />

            {hasPermission(PERM.PHOTO_VERIFY) && (
              <NavLink to="/verify" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Rasm tekshirish
              </NavLink>
            )}

            {hasPermission(PERM.PHOTO_VERIFY_TWO_FACE) && (
              <NavLink to="/verify-two-face" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                Yuzlarni solishtirish
              </NavLink>
            )}

            {hasPermission(PERM.EMBEDDING_EXTRACT) && (
              <NavLink to="/embedding" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                  />
                </svg>
                Embedding olish
              </NavLink>
            )}

            {hasPermission(PERM.PASPORT_INFO_READ) && (
              <NavLink to="/pasport-info" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H5a2 2 0 00-2 2v11a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V4a2 2 0 114 0v2m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3 3 0 00-2.83 2M15 11h3m-3 4h2"
                  />
                </svg>
                Pasport info
              </NavLink>
            )}

            {hasPermission(PERM.QABUL_READ) && (
              <NavLink to="/qabul" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                Qabul-{qabulYear}
              </NavLink>
            )}
          </>
        )}

        {/* ====== Bo'lim 4: Boshqaruv ====== */}
        {showBoshqaruv && (
          <>
            <SectionHeader label="Boshqaruv" accent="bg-amber-500" />

            {hasAnyPermission(PERM.DASHBOARD_READ, PERM.DASHBOARD_STATS) && (
              <NavLink to="/dashboard" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                  />
                </svg>
                Dashboard
              </NavLink>
            )}

            {hasPermission(PERM.LOG_READ) && (
              <NavLink to="/logs" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                Ram tekshiruv loglari
              </NavLink>
            )}

            {hasPermission(PERM.FACE_LOG_READ) && (
              <NavLink to="/face-logs" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Yuz solishtirish loglari
              </NavLink>
            )}

            {hasAnyPermission(PERM.API_KEY_READ, PERM.API_KEY_CREATE) && (
              <NavLink to="/api-keys" className={navLinkClass}>
                <svg
                  className={iconClass}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
                  />
                </svg>
                API kalitlar
              </NavLink>
            )}
          </>
        )}
      </nav>

      {/* User card + Logout (Material 3 surface tonal) */}
      <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-slate-800 safe-pb">
        <button
          type="button"
          onClick={() => navigate("/settings")}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl bg-gray-50 dark:bg-slate-800/70 hover:bg-gray-100 dark:hover:bg-slate-800 ring-1 ring-gray-200/60 dark:ring-slate-700/60 transition-colors mb-2 text-left"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white shadow-sm shadow-primary-500/30 shrink-0">
            <span className="text-[13px] font-semibold">
              {(user?.full_name || user?.username || "U")
                .charAt(0)
                .toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-gray-900 dark:text-slate-100 truncate leading-tight">
              {user?.full_name || user?.username}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-slate-400 capitalize mt-0.5">
              {user?.role}
            </p>
          </div>
          <svg
            className="w-4 h-4 text-gray-400 dark:text-slate-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>

        <button
          onClick={logout}
          className="flex items-center justify-center gap-2 w-full h-11 px-4 rounded-full text-[13.5px] font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <svg
            className={iconClass}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          Chiqish
        </button>
      </div>
    </aside>
  );
}
