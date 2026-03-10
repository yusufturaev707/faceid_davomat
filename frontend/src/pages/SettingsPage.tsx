import { useAuth } from "../contexts/AuthContext";
import ThemeSwitcher from "../components/ThemeSwitcher";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h2 className="section-title">Sozlamalar</h2>
        <p className="section-subtitle">Profil va ko'rinish sozlamalari</p>
      </div>

      {/* Profile card */}
      <div className="glass-card p-7 mb-6">
        <h3 className="text-base font-semibold text-gray-800 dark:text-slate-200 mb-5">Profil</h3>
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-600/20">
            <span className="text-2xl font-bold text-white">
              {(user?.full_name || user?.username || "U").charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {user?.full_name || user?.username}
            </p>
            <p className="text-sm text-gray-500 dark:text-slate-400">@{user?.username}</p>
            <span className="inline-block mt-1 px-3 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 capitalize">
              {user?.role}
            </span>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-gray-100 dark:border-slate-700 grid grid-cols-2 gap-4">
          <div>
            <p className="label-text mb-1">Foydalanuvchi ID</p>
            <p className="text-sm font-medium text-gray-800 dark:text-slate-200">#{user?.id}</p>
          </div>
          <div>
            <p className="label-text mb-1">Holat</p>
            <p className="text-sm font-medium">
              {user?.is_active ? (
                <span className="text-emerald-600 dark:text-emerald-400">Faol</span>
              ) : (
                <span className="text-red-600 dark:text-red-400">Nofaol</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Theme settings */}
      <div className="glass-card p-7">
        <h3 className="text-base font-semibold text-gray-800 dark:text-slate-200 mb-5">Ko'rinish</h3>
        <ThemeSwitcher />
      </div>
    </div>
  );
}
