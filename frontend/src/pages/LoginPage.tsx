import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import logoBba from "../assets/logo_bba.png";
import { extractErrorMessage } from "../utils/errorMessage";

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  // Asosiy sahifani huquqlarga qarab HomeRedirect tanlaydi (default: test-dashboard)
  if (isAuthenticated) return <Navigate to="/" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-slate-900 px-4 py-10 relative">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Brand lockup: logo + agentlik nomi */}
        <div className="text-center mb-7">
          <img
            src={logoBba}
            alt="BBA logotipi"
            className="h-16 w-auto object-contain select-none mx-auto mb-4"
            draggable={false}
          />
          <p className="text-[13.5px] font-semibold text-gray-700 dark:text-slate-200 tracking-wide leading-snug max-w-[16rem] mx-auto">
            Bilim va malakalarni baholash agentligi
          </p>

          {/* Nozik ajratuvchi — brend va ilova nomini ajratadi */}
          <div className="w-10 h-px bg-gray-200 dark:bg-slate-700 mx-auto my-4" />

          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            FaceID
          </h1>
          <p className="text-gray-500 dark:text-slate-400 text-sm mt-1">
            Identifikatsiya tizimiga kirish
          </p>
        </div>

        {/* Form Card — Material 3 elevated surface */}
        <form
          onSubmit={handleSubmit}
          className="glass-card rounded-3xl p-6 sm:p-8 shadow-lg space-y-5"
        >
          <div>
            <label
              htmlFor="login-username"
              className="block text-[13px] font-semibold text-gray-700 dark:text-slate-300 mb-1.5"
            >
              Login
            </label>
            <div className="relative group">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400 dark:text-slate-500 group-focus-within:text-primary-500 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </span>
              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field !rounded-2xl pl-11"
                placeholder="Foydalanuvchi nomi"
                autoComplete="username"
                autoFocus
                required
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="block text-[13px] font-semibold text-gray-700 dark:text-slate-300 mb-1.5"
            >
              Parol
            </label>
            <div className="relative group">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400 dark:text-slate-500 group-focus-within:text-primary-500 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </span>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field !rounded-2xl pl-11 pr-11"
                placeholder="Parolni kiriting"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/60 text-red-700 dark:text-red-400 px-4 py-3 rounded-2xl text-[13px] animate-fade-in">
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full !h-12 !rounded-2xl text-[15px] font-semibold mt-1"
          >
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-5 h-5 spinner" />
                Kirilmoqda...
              </span>
            ) : (
              "Kirish"
            )}
          </button>
        </form>

        <p className="text-center text-[11px] text-gray-400 dark:text-slate-600 mt-6">
          FaceID Verification System v2.0
        </p>
      </div>
    </div>
  );
}

function EyeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.477 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
    </svg>
  );
}
