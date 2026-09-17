import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { telegram } from "../telegram";
import { AlertTriangle, CheckCircle, ChevronRight, Info, Refresh, XCircle } from "./icons";

export type Tone = "accent" | "success" | "warning" | "destructive" | "neutral";

const TONE_ICON_CLASS: Record<Tone, string> = {
  accent: "tg-tint text-tg-button",
  success: "tg-tint-success text-tg-success",
  warning: "tg-tint-warning text-tg-warning",
  destructive: "tg-tint-destructive text-tg-destructive",
  neutral: "bg-tg-secondary text-tg-hint",
};

const TONE_TEXT_CLASS: Record<Tone, string> = {
  accent: "text-tg-button",
  success: "text-tg-success",
  warning: "text-tg-warning",
  destructive: "text-tg-destructive",
  neutral: "text-tg-hint",
};

// ─────────────────────────────────────────────────────────────
// Sahifa tuzilmasi
// ─────────────────────────────────────────────────────────────

export function Screen({
  title,
  subtitle,
  action,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="tg-screen mx-auto max-w-xl px-4 pb-28 pt-4">
      <header className="mb-4 flex items-start gap-3 px-1">
        <div className="min-w-0 flex-1">
          <h1 className="text-[22px] font-bold leading-tight text-tg-text">{title}</h1>
          {subtitle && <p className="mt-1 text-sm leading-snug text-tg-hint">{subtitle}</p>}
        </div>
        {action}
      </header>
      <div className="space-y-6">{children}</div>
    </div>
  );
}

export function Section({
  title,
  footer,
  children,
}: {
  title?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      {title && (
        <h2 className="mb-2 px-4 text-[13px] font-medium uppercase tracking-wide text-tg-header">
          {title}
        </h2>
      )}
      <div className="divide-y divide-tg-separator overflow-hidden rounded-2xl bg-tg-section">
        {children}
      </div>
      {footer && <p className="mt-2 px-4 text-[13px] leading-snug text-tg-hint">{footer}</p>}
    </section>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl bg-tg-section p-4 ${className}`}>{children}</div>;
}

export function IconBadge({ tone = "accent", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] ${TONE_ICON_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}

export function Row({
  icon,
  tone = "accent",
  title,
  subtitle,
  after,
  onClick,
  loading = false,
  disabled = false,
  destructive = false,
  chevron,
}: {
  icon?: ReactNode;
  tone?: Tone;
  title: ReactNode;
  subtitle?: ReactNode;
  after?: ReactNode;
  onClick?: () => void;
  loading?: boolean;
  disabled?: boolean;
  destructive?: boolean;
  chevron?: boolean;
}) {
  const interactive = !!onClick;
  const content = (
    <>
      {icon && <IconBadge tone={tone}>{icon}</IconBadge>}
      <span className="min-w-0 flex-1">
        <span
          className={`block text-[16px] leading-snug ${destructive ? "text-tg-destructive" : "text-tg-text"}`}
        >
          {title}
        </span>
        {subtitle && (
          <span className="mt-0.5 block text-[13px] leading-snug text-tg-hint">{subtitle}</span>
        )}
      </span>
      {after}
      {loading ? (
        <Spinner className="text-tg-hint" />
      ) : (
        (chevron ?? interactive) && (
          <span className="text-tg-hint">
            <ChevronRight width={18} height={18} />
          </span>
        )
      )}
    </>
  );

  const className = "flex w-full items-center gap-3 px-4 py-3 text-left";
  if (!interactive) return <div className={className}>{content}</div>;
  return (
    <button
      type="button"
      className={`${className} tg-pressable disabled:opacity-50`}
      onClick={() => {
        telegram.tap();
        onClick();
      }}
      disabled={disabled || loading}
    >
      {content}
    </button>
  );
}

export function DetailRow({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 px-4 py-2.5">
      <span className="shrink-0 text-[14px] text-tg-hint">{label}</span>
      <span className={`min-w-0 text-right text-[15px] text-tg-text ${mono ? "font-mono tracking-tight" : ""}`}>
        {value}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tugmalar
// ─────────────────────────────────────────────────────────────

type ButtonVariant = "primary" | "secondary" | "destructive" | "plain";

const BUTTON_VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "bg-tg-button text-tg-button-text",
  secondary: "tg-tint text-tg-button",
  destructive: "tg-tint-destructive text-tg-destructive",
  plain: "text-tg-link",
};

export function Button({
  children,
  onClick,
  variant = "primary",
  icon,
  loading = false,
  disabled = false,
}: {
  children: ReactNode;
  onClick: () => void;
  variant?: ButtonVariant;
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => {
        telegram.tap();
        onClick();
      }}
      disabled={disabled || loading}
      className={`flex h-12 w-full items-center justify-center gap-2 rounded-xl px-4 text-[16px] font-semibold transition-opacity active:opacity-75 disabled:opacity-50 ${BUTTON_VARIANT_CLASS[variant]}`}
    >
      {loading ? <Spinner /> : icon}
      <span className="truncate">{children}</span>
    </button>
  );
}

export function IconButton({
  onClick,
  label,
  loading = false,
}: {
  onClick: () => void;
  label: string;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={loading}
      className="tg-tint flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-tg-button active:opacity-70"
    >
      {loading ? <Spinner /> : <Refresh width={18} height={18} />}
    </button>
  );
}

function themeColor(key: string, fallback: string): string {
  return telegram.app?.themeParams[key] || fallback;
}

/**
 * Asosiy amal tugmasi. Telegram ichida — native MainButton (klaviatura ustida
 * turadi, platforma uslubida); tashqarida — pastga yopishgan oddiy tugma.
 * Ekranda bir vaqtda bittadan ko'p bo'lmasligi kerak.
 */
export function MainButton({
  text,
  onClick,
  disabled = false,
  loading = false,
  destructive = false,
}: {
  text: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  destructive?: boolean;
}) {
  const native = telegram.hasMainButton;
  const handlerRef = useRef(onClick);
  const activeRef = useRef(!disabled && !loading);
  handlerRef.current = onClick;
  activeRef.current = !disabled && !loading;

  useEffect(() => {
    const app = telegram.app;
    if (!native || !app) return;
    const handler = () => {
      if (activeRef.current) handlerRef.current();
    };
    app.MainButton.onClick(handler);
    return () => {
      app.MainButton.offClick(handler);
      app.MainButton.hideProgress();
      app.MainButton.setParams({ is_visible: false });
    };
  }, [native]);

  useEffect(() => {
    const app = telegram.app;
    if (!native || !app) return;
    const color = destructive
      ? themeColor("destructive_text_color", "#e53935")
      : themeColor("button_color", "#2481cc");
    app.MainButton.setParams({
      text,
      is_visible: true,
      is_active: !disabled && !loading,
      color: disabled ? themeColor("hint_color", "#8e8e93") : color,
      text_color: destructive ? "#ffffff" : themeColor("button_text_color", "#ffffff"),
    });
    if (loading) app.MainButton.showProgress(false);
    else app.MainButton.hideProgress();
  }, [native, text, disabled, loading, destructive]);

  if (native) return null;
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 bg-tg-secondary px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-3">
      <div className="mx-auto max-w-xl">
        <Button
          onClick={onClick}
          disabled={disabled}
          loading={loading}
          variant={destructive ? "destructive" : "primary"}
        >
          {text}
        </Button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Holatlar
// ─────────────────────────────────────────────────────────────

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Yuklanmoqda"
      className={`inline-block h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}

export function LoadingState({ label = "Yuklanmoqda..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 px-4 py-8 text-tg-hint">
      <Spinner />
      <span className="text-[15px]">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-8 text-center">
      <span className="text-tg-destructive">
        <AlertTriangle width={28} height={28} />
      </span>
      <p className="text-[15px] leading-snug text-tg-text">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="text-[15px] font-semibold text-tg-link">
          Qayta urinish
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-8 text-center">
      <span className="text-tg-hint">{icon}</span>
      <p className="text-[16px] font-semibold text-tg-text">{title}</p>
      {text && <p className="text-[14px] leading-snug text-tg-hint">{text}</p>}
    </div>
  );
}

const NOTICE_ICON: Record<Exclude<Tone, "accent" | "neutral">, ReactNode> = {
  success: <CheckCircle width={22} height={22} />,
  warning: <AlertTriangle width={22} height={22} />,
  destructive: <XCircle width={22} height={22} />,
};

/** Natija bloki: sarlavha + izoh, rangli fon. */
export function Notice({
  tone,
  title,
  children,
}: {
  tone: Tone;
  title: ReactNode;
  children?: ReactNode;
}) {
  const icon =
    tone === "success" || tone === "warning" || tone === "destructive" ? (
      NOTICE_ICON[tone]
    ) : (
      <Info width={22} height={22} />
    );
  const bg =
    tone === "success"
      ? "tg-tint-success"
      : tone === "warning"
        ? "tg-tint-warning"
        : tone === "destructive"
          ? "tg-tint-destructive"
          : "tg-tint";
  return (
    <div className={`flex gap-3 rounded-2xl p-4 ${bg}`}>
      <span className={`mt-0.5 ${TONE_TEXT_CLASS[tone]}`}>{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-[16px] font-semibold leading-snug text-tg-text">{title}</p>
        {children && (
          <div className="mt-1 whitespace-pre-line text-[14px] leading-snug text-tg-text opacity-80">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}

export function ProgressBar({
  value,
  tone = "accent",
  marker,
}: {
  value: number;
  tone?: Tone;
  /** 0–100 oralig'idagi belgi (masalan, yuz o'xshashligi chegarasi). */
  marker?: number;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const fill =
    tone === "success"
      ? "bg-tg-success"
      : tone === "warning"
        ? "bg-tg-warning"
        : tone === "destructive"
          ? "bg-tg-destructive"
          : "bg-tg-button";
  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-tg-secondary">
      <div
        className={`h-full rounded-full transition-[width] duration-500 ${fill}`}
        style={{ width: `${clamped}%` }}
      />
      {marker !== undefined && (
        <div
          className="absolute inset-y-0 w-0.5 bg-tg-text opacity-60"
          style={{ left: `${Math.max(0, Math.min(100, marker))}%` }}
        />
      )}
    </div>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string; icon?: ReactNode }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex gap-1 rounded-xl bg-tg-section p-1">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => {
              if (!active) {
                telegram.tap();
                onChange(option.value);
              }
            }}
            className={`flex h-10 flex-1 items-center justify-center gap-2 rounded-lg text-[15px] font-medium transition-colors ${
              active ? "bg-tg-button text-tg-button-text" : "text-tg-hint"
            }`}
          >
            {option.icon}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
  placeholder,
  inputMode,
  hint,
  error,
  onEnter,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: "text" | "numeric";
  hint?: ReactNode;
  error?: string | null;
  onEnter?: () => void;
}) {
  return (
    <label className="block px-4 py-3">
      <span className="text-[13px] text-tg-hint">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && onEnter) {
            (e.target as HTMLInputElement).blur();
            onEnter();
          }
        }}
        placeholder={placeholder}
        inputMode={inputMode}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="characters"
        spellCheck={false}
        enterKeyHint="done"
        className="mt-1 block w-full bg-transparent font-mono text-[20px] tracking-wider text-tg-text outline-none placeholder:font-sans placeholder:text-[17px] placeholder:tracking-normal placeholder:text-tg-hint"
      />
      {error ? (
        <span className="mt-1 block text-[13px] text-tg-destructive">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-[13px] text-tg-hint">{hint}</span>
      )}
    </label>
  );
}

// ─────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────

type ToastTone = "success" | "destructive" | "neutral";
type ShowToast = (message: string, tone?: ToastTone) => void;

const ToastContext = createContext<ShowToast>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ id: number; message: string; tone: ToastTone } | null>(
    null,
  );

  const show = useCallback<ShowToast>((message, tone = "neutral") => {
    setToast({ id: Date.now(), message, tone });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div className="pointer-events-none fixed inset-x-0 top-3 z-50 flex justify-center px-4">
          <div
            key={toast.id}
            role="status"
            className="tg-screen flex max-w-md items-center gap-2 rounded-2xl bg-tg-text px-4 py-3 text-[14px] font-medium leading-snug text-tg-bg shadow-lg"
          >
            {toast.tone === "success" && <CheckCircle width={18} height={18} className="shrink-0 text-tg-success" />}
            {toast.tone === "destructive" && <XCircle width={18} height={18} className="shrink-0 text-tg-destructive" />}
            <span>{toast.message}</span>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ShowToast {
  return useContext(ToastContext);
}
