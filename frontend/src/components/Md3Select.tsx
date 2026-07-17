import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";

export type Md3Option = {
  value: string;
  label: string;
  sublabel?: string;
  /** Matn/nuqta rangi (masalan holat ranglari). */
  color?: string;
  /** Tailwind nuqta klassi (masalan "bg-emerald-500"). */
  dot?: string;
  disabled?: boolean;
};

/**
 * Md3Select — native <select> o'rniga to'liq Material Design 3 dropdown.
 * Yorug' rejimda ham chiroyli va aniq: outlined trigger + elevatsiyali menyu,
 * hover state-layer, tanlangan element uchun belgi (✓), ixtiyoriy rang nuqtasi.
 * Tashqariga bosish va ESC bilan yopiladi; ixcham (h-9) balandlik.
 *
 * Ochilgan menyu `document.body`ga PORTAL orqali `fixed` joylashadi — shu bois
 * u hech qanday ota-element `overflow`/stacking-context'i yoki keyingi
 * kartalar/jadvallar ortida qolib ketmaydi (har doim ustda ko'rinadi).
 *
 * Controlled: `value` (string) + `onChange(value)`. Raqamli qiymatlar uchun
 * chaqiruvchi tomon String()/Number() bilan o'rab beradi. Bo'sh tanlov = "".
 */
export default function Md3Select({
  value,
  onChange,
  options,
  placeholder = "Tanlang",
  disabled = false,
  clearable = false,
  valueColor,
  ariaLabel,
  className = "",
  buttonClassName = "",
}: {
  value: string;
  onChange: (value: string) => void;
  options: Md3Option[];
  placeholder?: string;
  disabled?: boolean;
  clearable?: boolean;
  valueColor?: string;
  ariaLabel?: string;
  className?: string;
  buttonClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const selected = options.find((o) => o.value === value) ?? null;

  // Menyu joylashuvini trigger tugmasi rect'idan hisoblaymiz (fixed → viewport).
  const computePosition = useCallback(() => {
    const el = rootRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const gap = 6;
    const spaceBelow = window.innerHeight - r.bottom;
    const spaceAbove = r.top;
    const openUp = spaceBelow < 260 && spaceAbove > spaceBelow;
    const maxHeight = Math.min(288, (openUp ? spaceAbove : spaceBelow) - 12);
    setMenuStyle({
      position: "fixed",
      left: Math.round(r.left),
      width: Math.round(r.width),
      maxHeight: Math.max(120, maxHeight),
      zIndex: 9999,
      ...(openUp
        ? { bottom: Math.round(window.innerHeight - r.top + gap) }
        : { top: Math.round(r.bottom + gap) }),
    });
  }, []);

  // Ochilganda joylashuvni hisoblab, scroll/resize'da qayta hisoblaymiz.
  useLayoutEffect(() => {
    if (!open) return;
    computePosition();
    const onScroll = () => computePosition();
    const onResize = () => computePosition();
    // capture=true — ichki scroll konteynerlar ham ushlanadi.
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open, computePosition]);

  useEffect(() => {
    if (!open) return;
    const onDocPointer = (e: Event) => {
      const t = e.target as Node;
      // Trigger yoki menyu ichi bo'lsa yopmaymiz (menyu portalda — alohida ref).
      if (rootRef.current?.contains(t) || menuRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocPointer);
    document.addEventListener("touchstart", onDocPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocPointer);
      document.removeEventListener("touchstart", onDocPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pick = (v: string) => {
    onChange(v);
    setOpen(false);
  };

  const menu = open ? (
    <div
      ref={menuRef}
      role="listbox"
      style={menuStyle}
      className="p-1 rounded-2xl bg-surface dark:bg-slate-800 border border-gray-200/80 dark:border-slate-700/70 shadow-lg shadow-black/10 dark:shadow-black/40 overflow-auto animate-fade-in"
    >
      {clearable && (
        <button
          type="button"
          onClick={() => pick("")}
          className="w-full text-left px-3 py-2 rounded-xl text-[12.5px] text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors"
        >
          {placeholder}
        </button>
      )}
      {options.length === 0 ? (
        <div className="px-3 py-6 text-center text-[12.5px] text-gray-400 dark:text-slate-500">
          Variant yo'q
        </div>
      ) : (
        options.map((o) => {
          const isActive = o.value === value;
          return (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={isActive}
              disabled={o.disabled}
              title={o.label}
              onClick={() => !o.disabled && pick(o.value)}
              className={`w-full text-left px-3 py-2 rounded-xl flex items-center gap-2 text-[13px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                isActive
                  ? "bg-primary-50 dark:bg-primary-900/30"
                  : "hover:bg-gray-100 dark:hover:bg-slate-700/50"
              }`}
            >
              {o.dot && (
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${o.dot}`}
                  aria-hidden
                />
              )}
              <span
                className={`truncate ${isActive ? "font-semibold" : "font-medium"}`}
                style={o.color ? { color: o.color } : undefined}
              >
                {o.label}
              </span>
              {o.sublabel && (
                <span className="text-gray-400 dark:text-slate-500 text-[12px] shrink-0">
                  · {o.sublabel}
                </span>
              )}
              {isActive && (
                <svg
                  className="w-4 h-4 ml-auto shrink-0 text-primary-600 dark:text-primary-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2.5}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              )}
            </button>
          );
        })
      )}
    </div>
  ) : null;

  return (
    <div ref={rootRef} className={`relative w-full ${className}`}>
      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        title={selected?.label}
        onClick={() => setOpen((o) => !o)}
        className={`h-9 w-full pl-3 pr-2.5 flex items-center gap-2 rounded-xl border bg-surface dark:bg-slate-800 text-left text-[13px] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
          open
            ? "border-primary-500 ring-4 ring-primary-500/15"
            : "border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500"
        } ${buttonClassName}`}
      >
        {selected ? (
          <>
            {selected.dot && (
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${selected.dot}`}
                aria-hidden
              />
            )}
            <span
              className="truncate font-semibold"
              style={
                valueColor || selected.color
                  ? { color: valueColor ?? selected.color }
                  : undefined
              }
            >
              {selected.label}
            </span>
            {selected.sublabel && (
              <span className="text-gray-400 dark:text-slate-500 text-[12px] shrink-0">
                · {selected.sublabel}
              </span>
            )}
          </>
        ) : (
          <span className="truncate text-gray-400 dark:text-slate-500">
            {placeholder}
          </span>
        )}
        <ChevronDownIcon
          className={`w-4 h-4 ml-auto shrink-0 text-gray-400 dark:text-slate-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {menu && createPortal(menu, document.body)}
    </div>
  );
}

function ChevronDownIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}
