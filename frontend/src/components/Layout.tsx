import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

/**
 * App shell with Material 3 responsive navigation:
 * - Desktop (lg+): persistent navigation drawer alongside content
 * - Tablet / phone: modal drawer triggered from a top app bar
 */
export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  // Close drawer on route change (mobile UX)
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  // Lock body scroll while the modal drawer is open on small screens
  useEffect(() => {
    if (drawerOpen) {
      const original = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = original;
      };
    }
  }, [drawerOpen]);

  return (
    <div
      className="min-h-screen flex flex-col lg:flex-row"
      style={{ backgroundColor: "rgb(var(--color-bg))" }}
    >
      {/* === Mobile top app bar (< lg) === */}
      <header className="lg:hidden sticky top-0 z-30 h-14 px-3 flex items-center gap-2 bg-surface/90 dark:bg-slate-900/85 backdrop-blur-md border-b border-gray-200/70 dark:border-slate-800 safe-pt">
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Menyu"
          className="btn-icon"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm shadow-primary-500/30 shrink-0">
            <svg
              className="w-4 h-4 text-white"
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
          </div>
          <span className="font-semibold text-[15px] text-gray-900 dark:text-white truncate">
            FaceID Admin
          </span>
        </div>
      </header>

      {/* === Scrim (mobile drawer backdrop) === */}
      {drawerOpen && (
        <button
          type="button"
          aria-label="Yopish"
          onClick={() => setDrawerOpen(false)}
          className="lg:hidden fixed inset-0 z-40 bg-black/40 dark:bg-black/60 backdrop-blur-[2px] animate-fade-in"
        />
      )}

      {/* === Sidebar (desktop static / mobile modal) === */}
      <Sidebar drawerOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* === Main content === */}
      <main className="flex-1 min-w-0 overflow-x-hidden">
        <div className="mx-auto w-full max-w-8xl px-4 py-5 sm:px-6 sm:py-7 lg:px-8 lg:py-8 safe-pb">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
