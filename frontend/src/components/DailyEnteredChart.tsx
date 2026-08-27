import { useCallback, useEffect, useState } from "react";
import type { DailyEnteredResponse } from "../interfaces";
import { getDashboardDailyEnteredApi } from "../api";

/* ============================================================
 * Kunlik kirish grafigi — oy kesimida, oldinga/orqaga o'tish bilan.
 *
 * Forma: ustunli (column) grafik. Kunlik diskret sanoq va ko'p nol kun
 * bo'lgani uchun chiziq emas — chiziq nol kunlar orasidan yolg'on qiyalik
 * o'tkazgan bo'lardi.
 *
 * Bitta seriya bo'lgani uchun legenda yo'q — sarlavha nimani ko'rsatayotganini
 * aytadi. Rang `primary` tokenidan: yorug'da 600, qorong'ida 500. Bu ikki qadam
 * lightness va kontrast tekshiruvidan o'tgan (400 qorong'ida o'tmaydi), shu
 * bilan birga foydalanuvchi tanlagan mavzu rangiga ergashadi.
 *
 * Qiymatlar hover'siz ham yetib boradi: cho'qqi to'g'ridan-to'g'ri belgilangan,
 * qolgani jadval ko'rinishida.
 *
 * Oy o'tkazgich — chart marki emas, oddiy boshqaruv: sarlavha qatorida o'ngda.
 * Chegaralarni server aytadi (`min_month` / `max_month`), shuning uchun bo'sh
 * oylarga cheksiz o'tib ketib bo'lmaydi va kelajakka o'tilmaydi.
 * ========================================================== */

const MONTHS_UZ = [
  "Yanvar",
  "Fevral",
  "Mart",
  "Aprel",
  "May",
  "Iyun",
  "Iyul",
  "Avgust",
  "Sentabr",
  "Oktabr",
  "Noyabr",
  "Dekabr",
];

/** "YYYY-MM" ni `delta` oyga suradi (yil chegarasidan o'zi o'tadi). */
function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${MONTHS_UZ[m - 1] ?? month} ${y}`;
}

export default function DailyEnteredChart() {
  // null — hali birinchi javob kelmagan; server joriy oyni o'zi tanlaydi
  const [month, setMonth] = useState<string | null>(null);
  const [res, setRes] = useState<DailyEnteredResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null);

  const load = useCallback((target: string | null) => {
    setLoading(true);
    setError(null);
    getDashboardDailyEnteredApi(target ?? undefined)
      .then((r) => {
        setRes(r);
        setMonth(r.month);
      })
      .catch(() => setError("Ma'lumotni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(null);
  }, [load]);

  const go = (delta: number) => {
    if (!month) return;
    setHover(null);
    load(shiftMonth(month, delta));
  };

  const data = res?.days ?? [];
  // min_month null bo'lsa qamrovda umuman kirish yo'q — orqaga o'tishning
  // ma'nosi yo'q, aks holda foydalanuvchi bo'sh oylarga cheksiz ketardi.
  const canPrev = !!(res && month && res.min_month && month > res.min_month);
  const canNext = !!(res && month && month < res.max_month);

  const max = Math.max(0, ...data.map((d) => d.count));
  const total = res?.total ?? 0;
  const peakIndex = max > 0 ? data.findIndex((d) => d.count === max) : -1;

  // Y o'qi — toza (yumaloqlangan) qiymatlar
  const niceMax = niceCeil(max);
  const ticks = niceMax > 0 ? [niceMax, Math.round(niceMax / 2), 0] : [0];

  // Teng oraliqdagi 5 ta tayanch sana (birinchi va oxirgi shart)
  const axisDates = [0, 0.25, 0.5, 0.75, 1]
    .map((f) => data[Math.round(f * (data.length - 1))]?.date)
    .filter((d): d is string => Boolean(d));

  const fmt = (n: number) => n.toLocaleString("uz-UZ");
  const fmtDay = (iso: string) => {
    const d = new Date(iso);
    return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
  };

  return (
    <div className="glass-card p-4 sm:p-5 mb-5 sm:mb-6">
      {/* Sarlavha + oy o'tkazgich */}
      <div className="flex items-start justify-between gap-3 gap-y-2 mb-4 flex-wrap">
        <div className="min-w-0">
          <h3 className="text-[14px] font-bold text-gray-900 dark:text-white leading-tight">
            Kunlik kirgan talabgorlar
          </h3>
          <p className="text-[11.5px] text-gray-500 dark:text-slate-400 mt-0.5">
            {month ? monthLabel(month) : "—"} · jami {fmt(total)} ta
          </p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {max > 0 && (
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 tabular-nums mr-1">
              eng yuqori {fmt(max)}
            </span>
          )}
          <NavButton
            label="Oldingi oy"
            disabled={!canPrev || loading}
            onClick={() => go(-1)}
          >
            <ChevronIcon className="w-4 h-4" />
          </NavButton>
          <span className="text-[12px] font-semibold text-gray-700 dark:text-slate-200 min-w-[96px] text-center select-none">
            {month ? monthLabel(month) : "…"}
          </span>
          <NavButton
            label="Keyingi oy"
            disabled={!canNext || loading}
            onClick={() => go(1)}
          >
            <ChevronIcon className="w-4 h-4 rotate-180" />
          </NavButton>
        </div>
      </div>

      {error ? (
        <div className="h-40 flex items-center justify-center text-[12.5px] text-rose-600 dark:text-rose-400">
          {error}
        </div>
      ) : loading && !res ? (
        <div className="h-44 rounded-xl bg-gray-100 dark:bg-slate-700/40 animate-pulse" />
      ) : total === 0 ? (
        <div className="h-40 flex items-center justify-center text-[12.5px] text-gray-400 dark:text-slate-500">
          Bu oyda kirish qayd etilmagan
        </div>
      ) : (
        <>
          <div
            className={`flex gap-2 transition-opacity ${loading ? "opacity-50" : ""}`}
          >
            {/* Y o'qi */}
            <div className="w-11 shrink-0 h-44 flex flex-col justify-between items-end pb-5 text-[10.5px] tabular-nums text-gray-400 dark:text-slate-500">
              {ticks.map((t, i) => (
                <span key={i}>{fmt(t)}</span>
              ))}
            </div>

            {/* Chizma maydoni */}
            <div className="relative flex-1 min-w-0 h-44">
              {/* To'r chiziqlari — surface'dan bir qadam farqli, 1px, uzluksiz */}
              <div className="absolute inset-x-0 top-0 bottom-5 pointer-events-none">
                {ticks.map((_, i) => (
                  <div
                    key={i}
                    className="absolute inset-x-0 border-t border-gray-200/70 dark:border-slate-700/60"
                    style={{ top: `${(i / (ticks.length - 1)) * 100}%` }}
                  />
                ))}
              </div>

              {/* Ustunlar — 2px oraliq, tepasi 4px yumaloq, tagi tekis */}
              <div className="absolute inset-x-0 top-0 bottom-5 flex items-end gap-[2px]">
                {data.map((d, i) => (
                  <div
                    key={d.date}
                    tabIndex={0}
                    role="img"
                    aria-label={`${d.date}: ${fmt(d.count)} ta`}
                    onMouseEnter={() => setHover(i)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(i)}
                    onBlur={() => setHover(null)}
                    className="group relative flex-1 h-full flex items-end justify-center outline-none cursor-default focus-visible:ring-2 focus-visible:ring-primary-400 rounded"
                  >
                    <div
                      className={`w-full max-w-[24px] rounded-t transition-colors ${
                        d.count === 0
                          ? "bg-gray-200 dark:bg-slate-700"
                          : hover === i
                            ? "bg-primary-700 dark:bg-primary-400"
                            : "bg-primary-600 dark:bg-primary-500"
                      }`}
                      style={{
                        height:
                          d.count === 0
                            ? "2px"
                            : `${Math.max(2, (d.count / niceMax) * 100)}%`,
                      }}
                    />
                    {/* Cho'qqi ustidagi yagona to'g'ridan-to'g'ri yorliq */}
                    {i === peakIndex && hover === null && (
                      <span className="absolute -top-4 text-[10px] font-semibold tabular-nums text-gray-600 dark:text-slate-300 whitespace-nowrap">
                        {fmt(d.count)}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {/* X o'qi — 5 ta tayanch sana, slot kengligiga bog'liq emas.
                  Har slotga yorliq qo'yilsa mobil ekranda slot ~8px bo'lib,
                  matn kesilib ketardi. */}
              <div className="absolute inset-x-0 bottom-0 flex justify-between text-[10px] text-gray-400 dark:text-slate-500 whitespace-nowrap">
                {axisDates.map((d) => (
                  <span key={d}>{fmtDay(d)}</span>
                ))}
              </div>

              {/* Tooltip — qiymat oldinda, sana ikkinchi darajali */}
              {hover !== null && data[hover] && (
                <div
                  className={`absolute -top-1 z-10 pointer-events-none rounded-lg bg-gray-900/95 dark:bg-slate-700 px-2.5 py-1.5 shadow-lg ${tipAlign(
                    hover,
                    data.length,
                  )}`}
                  style={{ left: `${((hover + 0.5) / data.length) * 100}%` }}
                >
                  <p className="text-[12px] font-bold text-white tabular-nums leading-tight">
                    {fmt(data[hover].count)}
                  </p>
                  <p className="text-[10.5px] text-gray-300 dark:text-slate-300 leading-tight">
                    {data[hover].date}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Jadval ko'rinishi — qiymatlar hover'siz ham yetib boradi */}
          <details className="mt-3">
            <summary className="text-[11.5px] text-gray-500 dark:text-slate-400 cursor-pointer hover:text-gray-700 dark:hover:text-slate-200 select-none">
              Jadval ko'rinishi
            </summary>
            <div className="mt-2 max-h-44 overflow-y-auto rounded-lg ring-1 ring-gray-200 dark:ring-slate-700">
              <table className="w-full text-[12px]">
                <thead className="sticky top-0 bg-gray-50 dark:bg-slate-800">
                  <tr className="text-left text-gray-500 dark:text-slate-400">
                    <th className="px-3 py-1.5 font-medium">Sana</th>
                    <th className="px-3 py-1.5 font-medium text-right">
                      Kirgan
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data
                    .filter((d) => d.count > 0)
                    .map((d) => (
                      <tr
                        key={d.date}
                        className="border-t border-gray-100 dark:border-slate-700/60"
                      >
                        <td className="px-3 py-1 text-gray-700 dark:text-slate-200">
                          {d.date}
                        </td>
                        <td className="px-3 py-1 text-right tabular-nums font-medium text-gray-800 dark:text-slate-100">
                          {fmt(d.count)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
}

function NavButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700/60 hover:text-gray-700 dark:hover:text-slate-200 disabled:opacity-35 disabled:pointer-events-none transition-colors"
    >
      {children}
    </button>
  );
}

function ChevronIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M15 19l-7-7 7-7"
      />
    </svg>
  );
}

/** Tooltip chekkada kartadan chiqib ketmasligi uchun tekislash. */
function tipAlign(index: number, count: number): string {
  const pos = (index + 0.5) / count;
  if (pos < 0.12) return "translate-x-0";
  if (pos > 0.88) return "-translate-x-full";
  return "-translate-x-1/2";
}

/** Y o'qi uchun qiymatni "toza" songa yumaloqlaydi (1/2/5 × 10^n). */
function niceCeil(value: number): number {
  if (value <= 0) return 0;
  const exp = Math.floor(Math.log10(value));
  const base = Math.pow(10, exp);
  const norm = value / base;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * base;
}
