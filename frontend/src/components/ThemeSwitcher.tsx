import { useTheme, type ThemeColor } from "../contexts/ThemeContext";

const themes: { value: ThemeColor; label: string; swatch: string }[] = [
  { value: "blue", label: "Ko'k", swatch: "bg-blue-500" },
  { value: "emerald", label: "Yashil", swatch: "bg-emerald-500" },
  { value: "violet", label: "Binafsha", swatch: "bg-violet-500" },
];

interface ThemeSwitcherProps {
  compact?: boolean;
}

export default function ThemeSwitcher({ compact = false }: ThemeSwitcherProps) {
  const { color, mode, setColor, toggleMode } = useTheme();

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {themes.map((t) => (
          <button
            key={t.value}
            onClick={() => setColor(t.value)}
            className={`w-6 h-6 rounded-full ${t.swatch} transition-all duration-200 ${
              color === t.value
                ? "ring-2 ring-offset-2 ring-offset-surface dark:ring-offset-slate-800 ring-gray-400 dark:ring-slate-400 scale-110"
                : "opacity-50 hover:opacity-80"
            }`}
            title={t.label}
          />
        ))}
        <div className="w-px h-5 bg-gray-200 dark:bg-slate-600 mx-1" />
        <button
          onClick={toggleMode}
          className="p-1.5 rounded-lg text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
          title={mode === "dark" ? "Yorug' rejim" : "Qorong'u rejim"}
        >
          {mode === "dark" ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="label-text mb-3">Rang sxemasi</p>
        <div className="flex gap-3">
          {themes.map((t) => (
            <button
              key={t.value}
              onClick={() => setColor(t.value)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all duration-200 ${
                color === t.value
                  ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                  : "border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500"
              }`}
            >
              <div className={`w-4 h-4 rounded-full ${t.swatch}`} />
              <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                {t.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="label-text mb-3">Rejim</p>
        <div className="flex gap-3">
          <button
            onClick={() => toggleMode()}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all duration-200 ${
              mode === "light"
                ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                : "border-gray-200 dark:border-slate-600 hover:border-gray-300"
            }`}
          >
            <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">Yorug'</span>
          </button>
          <button
            onClick={() => toggleMode()}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all duration-200 ${
              mode === "dark"
                ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                : "border-gray-200 dark:border-slate-600 hover:border-gray-300"
            }`}
          >
            <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">Qorong'u</span>
          </button>
        </div>
      </div>
    </div>
  );
}
