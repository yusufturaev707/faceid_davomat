import { useEffect, useState } from "react";
import { exportGenderReportApi, getGenderReportApi } from "../api";
import type { GenderReport } from "../interfaces";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";
import PermissionGate from "./PermissionGate";

/**
 * «Gender info» — tanlangan test va sana oralig'ida viloyatlar bo'yicha
 * erkak/ayol talabgorlar soni. Ustunlar: har (sana, smena) uchun Erkak | Ayol,
 * oxirida viloyat jami. Excel faylida ustun nomlari tekis
 * ("12-oktabr 1-smena Erkak") — backend shunday yozadi.
 */

interface Props {
  /** `GET /students` bilan bir xil filtr parametrlari (test va sana majburiy). */
  params: Record<string, string | number | boolean>;
  /** Test va sanadan tashqari qo'llangan filtrlar soni — ogohlantirish uchun. */
  extraFilterCount: number;
  onClose: () => void;
}

const fmt = (n: number) => n.toLocaleString("uz-UZ").replace(/,/g, " ");

const pct = (part: number, total: number) =>
  total > 0 ? `${((part / total) * 100).toFixed(1).replace(/\.0$/, "")}%` : "0%";

const fmtDate = (iso: string) => {
  const [y, m, d] = iso.split("-");
  return d && m && y ? `${d}.${m}.${y}` : iso;
};

export default function GenderReportModal({ params, extraFilterCount, onClose }: Props) {
  const [report, setReport] = useState<GenderReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getGenderReportApi(params)
      .then((r) => !cancelled && setReport(r))
      .catch((e) => !cancelled && setError(extractErrorMessage(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [params]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleExport = async () => {
    setExporting(true);
    setError("");
    try {
      await exportGenderReportApi(params);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setExporting(false);
    }
  };

  const total = report ? report.male + report.female : 0;
  const hasData = !!report && report.rows.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/45 dark:bg-black/65 backdrop-blur-[3px] p-0 sm:p-4 animate-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="gender-report-title"
    >
      <div
        className="md3-dialog w-full sm:max-w-7xl max-h-[92vh] overflow-hidden rounded-t-3xl sm:rounded-3xl flex flex-col safe-pb animate-modal-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 sm:px-6 pt-5 pb-4 border-b border-gray-100 dark:border-slate-700/60">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300 flex items-center justify-center shrink-0">
                <UsersIcon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h3
                  id="gender-report-title"
                  className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white leading-tight"
                >
                  Jins bo'yicha hisobot
                </h3>
                <p className="text-[12px] text-gray-500 dark:text-slate-400 mt-1 truncate">
                  {report?.test_name ?? "Test"} ·{" "}
                  {fmtDate(String(params.e_date_from))} — {fmtDate(String(params.e_date_to))}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="btn-icon shrink-0"
              aria-label="Yopish"
              title="Yopish (Esc)"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {hasData && (
            <div className="grid grid-cols-3 gap-2 sm:gap-3 mt-4">
              <SummaryTile label="Erkak" value={report.male} share={pct(report.male, total)} />
              <SummaryTile label="Ayol" value={report.female} share={pct(report.female, total)} />
              <SummaryTile
                label="Jami"
                value={total}
                share={`${report.rows.length} viloyat · ${report.columns.length} smena`}
              />
            </div>
          )}
          {extraFilterCount > 0 && (
            <p className="mt-3 text-[11.5px] text-gray-500 dark:text-slate-400">
              Ro'yxatdagi qo'shimcha filtrlar ({extraFilterCount} ta) ham hisobga olingan.
            </p>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-auto">
          {loading ? (
            <div className="p-6 space-y-2" aria-busy="true">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-9 rounded-lg bg-gray-100 dark:bg-slate-700/50 animate-pulse" />
              ))}
            </div>
          ) : error && !report ? (
            <div className="m-6 rounded-2xl px-4 py-3 text-sm bg-red-50 text-red-700 dark:bg-red-900/25 dark:text-red-300">
              {error}
            </div>
          ) : !hasData ? (
            <div className="py-16 text-center">
              <UsersIcon className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-slate-600" />
              <p className="text-sm text-gray-500 dark:text-slate-400">
                Tanlangan test va sana oralig'ida talabgor topilmadi
              </p>
            </div>
          ) : (
            <table className="w-full text-sm border-separate border-spacing-0">
              <thead className="sticky top-0 z-20">
                <tr>
                  <th
                    rowSpan={2}
                    className="sticky left-0 z-30 bg-gray-50 dark:bg-slate-800 px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 border-b border-r border-gray-200 dark:border-slate-700 min-w-[140px] sm:min-w-[190px]"
                  >
                    Viloyat
                  </th>
                  {report.columns.map((c) => (
                    <th
                      key={`${c.day}-${c.smena_number}`}
                      colSpan={2}
                      className="bg-gray-50 dark:bg-slate-800 px-3 pt-2.5 pb-1 text-center text-[12px] font-semibold text-gray-800 dark:text-slate-200 whitespace-nowrap border-l border-gray-200 dark:border-slate-700"
                    >
                      {c.label}
                    </th>
                  ))}
                  <th
                    colSpan={3}
                    className="bg-primary-50 dark:bg-primary-900/30 px-3 pt-2.5 pb-1 text-center text-[12px] font-semibold text-primary-800 dark:text-primary-200 border-l border-gray-200 dark:border-slate-700"
                  >
                    Jami
                  </th>
                </tr>
                <tr>
                  {report.columns.map((c) => (
                    <SubHeads key={`${c.day}-${c.smena_number}`} />
                  ))}
                  <SubHeads tone="primary" withTotal />
                </tr>
              </thead>
              <tbody>
                {report.rows.map((r) => (
                  <tr key={r.region_id} className="group">
                    <td className="sticky left-0 z-10 bg-surface dark:bg-slate-800 group-hover:bg-gray-50 dark:group-hover:bg-slate-700/60 px-4 py-2.5 font-medium text-gray-800 dark:text-slate-200 border-b border-r border-gray-100 dark:border-slate-700/60 max-w-[160px] sm:max-w-none sm:whitespace-nowrap">
                      {r.region_name}
                      {r.unknown > 0 && (
                        <span
                          className="block sm:inline sm:ml-2 text-[10.5px] font-normal text-amber-700 dark:text-amber-400"
                          title="Jinsi aniqlanmagan talabgorlar — ustunlarga kirmagan"
                        >
                          +{fmt(r.unknown)} aniqlanmagan
                        </span>
                      )}
                    </td>
                    {r.cells.map(([m, f], i) => (
                      <PairCells key={i} male={m} female={f} />
                    ))}
                    <PairCells male={r.male} female={r.female} total tone="primary" />
                  </tr>
                ))}
              </tbody>
              <tfoot className="sticky bottom-0 z-20">
                <tr>
                  <td className="sticky left-0 z-30 bg-gray-100 dark:bg-slate-700 px-4 py-2.5 font-semibold text-gray-900 dark:text-white border-t border-r border-gray-200 dark:border-slate-600">
                    Jami
                  </td>
                  {report.totals.map(([m, f], i) => (
                    <PairCells key={i} male={m} female={f} footer />
                  ))}
                  <PairCells male={report.male} female={report.female} total footer tone="primary" />
                </tr>
              </tfoot>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 sm:px-6 py-3.5 border-t border-gray-100 dark:border-slate-700/60 flex flex-wrap items-center gap-3">
          {error && report && (
            <p className="text-[12.5px] text-red-600 dark:text-red-400 mr-auto">{error}</p>
          )}
          {report && report.unknown > 0 && !error && (
            <p className="text-[12px] text-amber-700 dark:text-amber-400 mr-auto">
              {fmt(report.unknown)} ta talabgorning jinsi aniqlanmadi (pasport ma'lumoti va JShShIR yo'q)
              — ular ustunlarga kirmagan.
            </p>
          )}
          <div className="ml-auto flex items-center gap-2">
            <button onClick={onClose} className="btn-text">
              Yopish
            </button>
            <PermissionGate permission={PERM.STUDENT_EXPORT_EXCEL}>
              <button
                onClick={handleExport}
                disabled={!hasData || exporting}
                className="btn-primary !h-10 !min-h-[40px]"
              >
                {exporting ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                )}
                {exporting ? "Tayyorlanmoqda..." : "Excel yuklab olish"}
              </button>
            </PermissionGate>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryTile({ label, value, share }: { label: string; value: number; share: string }) {
  return (
    <div className="surface-tonal px-3.5 py-2.5">
      <p className="text-[11px] font-medium text-gray-500 dark:text-slate-400">{label}</p>
      <p className="text-lg sm:text-xl font-bold tabular-nums text-gray-900 dark:text-white leading-tight mt-0.5">
        {fmt(value)}
      </p>
      <p className="text-[11px] tabular-nums text-gray-500 dark:text-slate-400 truncate">{share}</p>
    </div>
  );
}

function SubHeads({ tone, withTotal }: { tone?: "primary"; withTotal?: boolean }) {
  const base =
    "px-3 pb-2 pt-1 text-right text-[10.5px] font-semibold uppercase tracking-wider border-b border-gray-200 dark:border-slate-700 whitespace-nowrap";
  const bg =
    tone === "primary"
      ? "bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
      : "bg-gray-50 dark:bg-slate-800 text-gray-500 dark:text-slate-400";
  return (
    <>
      <th className={`${base} ${bg} border-l`}>Erkak</th>
      <th className={`${base} ${bg}`}>Ayol</th>
      {withTotal && <th className={`${base} ${bg}`}>Jami</th>}
    </>
  );
}

function PairCells({
  male,
  female,
  total,
  footer,
  tone,
}: {
  male: number;
  female: number;
  total?: boolean;
  footer?: boolean;
  tone?: "primary";
}) {
  const bg = footer
    ? "bg-gray-100 dark:bg-slate-700 font-semibold text-gray-900 dark:text-white border-t border-gray-200 dark:border-slate-600"
    : tone === "primary"
      ? "bg-primary-50/50 dark:bg-primary-900/15 font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-slate-700/60 group-hover:bg-primary-50 dark:group-hover:bg-primary-900/25"
      : "text-gray-700 dark:text-slate-300 border-b border-gray-100 dark:border-slate-700/60 group-hover:bg-gray-50 dark:group-hover:bg-slate-700/40";
  const cell = `px-3 py-2.5 text-right tabular-nums whitespace-nowrap ${bg}`;
  const val = (n: number) =>
    n === 0 && !footer ? <span className="text-gray-300 dark:text-slate-600">0</span> : fmt(n);
  return (
    <>
      <td className={`${cell} border-l border-l-gray-200 dark:border-l-slate-700`}>{val(male)}</td>
      <td className={cell}>{val(female)}</td>
      {total && <td className={cell}>{val(male + female)}</td>}
    </>
  );
}

function UsersIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}
