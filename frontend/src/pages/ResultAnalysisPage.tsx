import { useEffect, useMemo, useState } from "react";
import {
  analyzeResultsApi,
  getSmenasListApi,
  getTestsListApi,
  type ResultAnalysisItem,
  type ResultAnalysisMode,
  type ResultAnalysisResponse,
  type ResultAnalysisRow,
} from "../api";
import Md3Select, { type Md3Option } from "../components/Md3Select";
import { extractErrorMessage } from "../utils/errorMessage";

/**
 * Natija uchun tahlil.
 *
 * Foydalanuvchi test (aktiv), sana oralig'i va smenani tanlaydi; so'ng tashqi
 * natija tizimidan (Excel/Access) ustunlarni textarea'ga joylaydi:
 *   imei | abitur_id | img | common_ball | tday | deleted   (TAB bilan ajratilgan)
 * Joylangan matn jonli ravishda tekislangan jadvalga ajratiladi — har bir ustun
 * sarlavhasi o'z ma'lumotining kengligiga qarab joylashadi. Backend `imei`
 * bo'yicha FaceID bazasi bilan solishtirib, nomuvofiqliklarni chiqaradi.
 */

const COLUMNS = [
  "imei",
  "abitur_id",
  "img",
  "common_ball",
  "tday",
  "deleted",
] as const;

const MODE_OPTIONS: { value: ResultAnalysisMode; label: string }[] = [
  {
    value: "in_face_not_excluded_no_result",
    label: "Faceda bor - chetlatilmagan - natija chiqmagan",
  },
  {
    value: "in_face_excluded_has_result",
    label: "Faceda bor - chetlatilgan - natija chiqqan",
  },
  {
    value: "not_in_face_has_result",
    label: "Faceda yo'q - natija chiqqan",
  },
];

// Jonli ko'rinish jadvalida ko'p bo'lsa ham cheklangan qator ko'rsatiladi.
const PREVIEW_LIMIT = 50;

// Access/Excel'dan kelishi mumkin bo'lgan "deleted" (o'chirilgan) qiymatlari.
// Access boolean'ni ko'pincha -1/0 yoki True/False ko'rinishida eksport qiladi.
const TRUTHY = new Set([
  "1",
  "-1",
  "true",
  "t",
  "ha",
  "yes",
  "rost",
  "deleted",
  "o'chirilgan",
  "o‘chirilgan",
]);

function parseDeleted(v: string | undefined): boolean {
  return TRUTHY.has((v ?? "").trim().toLowerCase());
}

interface PreviewRow {
  imei: string;
  abitur_id: string;
  img: string;
  common_ball: string;
  tday: string;
  deleted: string;
  isDeleted: boolean;
}

/**
 * Textarea matnini to'liq qatorlarga ajratadi. Ustunlar TAB bilan ajratilgan
 * (Excel/Access'dan copy qilinganda shunday), tartibi COLUMNS bo'yicha.
 * Sarlavha qatori (birinchi katak "imei"/"imie") avtomatik tashlab yuboriladi.
 */
function parseRows(text: string): PreviewRow[] {
  const rows: PreviewRow[] = [];
  for (const rawLine of text.split(/\r?\n/)) {
    if (!rawLine.trim()) continue;
    const c = rawLine.split("\t");
    const imei = (c[0] ?? "").trim();
    if (!imei) continue;
    const lower = imei.toLowerCase();
    if (lower === "imei" || lower === "imie") continue; // sarlavha
    rows.push({
      imei,
      abitur_id: (c[1] ?? "").trim(),
      img: (c[2] ?? "").trim(),
      common_ball: (c[3] ?? "").trim(),
      tday: (c[4] ?? "").trim(),
      deleted: (c[5] ?? "").trim(),
      isDeleted: parseDeleted(c[5]),
    });
  }
  return rows;
}

/** "YYYY-MM-DD" → "DD.MM.YYYY"; boshqa formatlar o'zgarmaydi. */
function formatDay(value: string | null): string {
  if (!value) return "—";
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(value.trim());
  return iso ? `${iso[3]}.${iso[2]}.${iso[1]}` : value;
}

export default function ResultAnalysisPage() {
  const [tests, setTests] = useState<Md3Option[]>([]);
  const [smenas, setSmenas] = useState<Md3Option[]>([]);

  const [testId, setTestId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [smenaId, setSmenaId] = useState("");
  const [mode, setMode] = useState<ResultAnalysisMode | "">("");
  const [pasted, setPasted] = useState("");

  const [result, setResult] = useState<ResultAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Test (faqat aktiv) va smena ro'yxatlarini yuklaymiz.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [testList, smenaList] = await Promise.all([
          getTestsListApi(),
          getSmenasListApi(),
        ]);
        if (!alive) return;
        setTests(
          testList
            .filter((t) => t.is_active)
            .map((t) => ({ value: String(t.id), label: t.name })),
        );
        setSmenas(
          [...smenaList]
            .sort((a, b) => a.number - b.number)
            .map((s) => ({ value: String(s.id), label: s.name })),
        );
      } catch (err) {
        if (alive) setError(extractErrorMessage(err));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Ko'lam to'liq tanlangach textarea/tahlil qismi ochiladi.
  const scopeReady = Boolean(testId && dateFrom && dateTo && smenaId);

  const parsedRows = useMemo(() => parseRows(pasted), [pasted]);
  const deletedCount = useMemo(
    () => parsedRows.reduce((n, r) => n + (r.isDeleted ? 1 : 0), 0),
    [parsedRows],
  );

  // Backend faqat solishtiruvga kerakli maydonlarni oladi (imei, tday, deleted).
  const analysisRows: ResultAnalysisRow[] = useMemo(
    () =>
      parsedRows.map((r) => ({
        imei: r.imei,
        tday: r.tday || null,
        deleted: r.isDeleted,
      })),
    [parsedRows],
  );

  const dateRangeValid = !dateFrom || !dateTo || dateFrom <= dateTo;

  const canSubmit =
    scopeReady &&
    !!mode &&
    analysisRows.length > 0 &&
    dateRangeValid &&
    !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !mode) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeResultsApi({
        test_id: Number(testId),
        smena_id: Number(smenaId),
        date_from: dateFrom,
        date_to: dateTo,
        mode,
        rows: analysisRows,
      });
      setResult(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMode("");
    setPasted("");
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Sarlavha */}
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm shadow-primary-600/25 shrink-0">
          <svg
            className="w-6 h-6 text-white"
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
        </div>
        <div>
          <h2 className="section-title">Natija uchun tahlil</h2>
          <p className="section-subtitle">
            Tashqi natija tizimidan (Excel/Access) joylangan ma'lumotlarni FaceID
            bazasi bilan <span className="font-semibold">imei</span> bo'yicha
            solishtirib, nomuvofiqliklarni aniqlash
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-6 sm:p-7 space-y-6">
        {/* 1-qadam: ko'lam (test + sana oralig'i + smena) */}
        <div className="space-y-4">
          <StepHeader n={1} title="Ko'lamni tanlang" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-5 gap-y-5">
            <Field label="Test (aktiv)">
              <Md3Select
                value={testId}
                onChange={setTestId}
                options={tests}
                placeholder="Testni tanlang"
                ariaLabel="Test"
              />
            </Field>
            <Field label="Sana (dan)">
              <input
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-field"
              />
            </Field>
            <Field label="Sana (gacha)">
              <input
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-field"
              />
            </Field>
            <Field label="Smena">
              <Md3Select
                value={smenaId}
                onChange={setSmenaId}
                options={smenas}
                placeholder="Smenani tanlang"
                ariaLabel="Smena"
              />
            </Field>
          </div>
          {!dateRangeValid && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              "Sana (dan)" "Sana (gacha)" dan katta bo'lmasligi kerak
            </p>
          )}
        </div>

        {/* 2-qadam: ma'lumot joylash + tahlil turi */}
        {scopeReady && (
          <div className="space-y-4 pt-6 border-t border-gray-200/70 dark:border-slate-700/60 animate-fade-in">
            <StepHeader n={2} title="Natija ma'lumotlarini joylang" />

            {/* Ustun tartibi — MD3 assist chip'lar, keng oraliqda */}
            <div>
              <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                Excel yoki Access'dan ustunlarni quyidagi tartibda tanlab
                joylang (ustunlar TAB bilan ajratiladi):
              </p>
              <div className="flex flex-wrap gap-2">
                {COLUMNS.map((c, i) => (
                  <span
                    key={c}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium
                               bg-primary-50 dark:bg-primary-900/25 text-primary-700 dark:text-primary-300
                               border border-primary-100 dark:border-primary-800/60"
                  >
                    <span className="text-[10px] font-semibold opacity-60">
                      {i + 1}
                    </span>
                    <span className="font-mono">{c}</span>
                  </span>
                ))}
              </div>
            </div>

            <textarea
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              rows={7}
              spellCheck={false}
              placeholder={
                "imei\tabitur_id\timg\tcommon_ball\ttday\tdeleted\n" +
                "12345678901234\t1001\t\t145.2\t2026-07-15\t0"
              }
              className="input-field font-mono text-[12.5px] leading-relaxed resize-y"
            />

            {/* Jonli tekislangan ko'rinish — ustun sarlavhalari ma'lumot
                kengligiga qarab joylashadi (haqiqiy jadval) */}
            {parsedRows.length > 0 && (
              <PreviewTable
                rows={parsedRows}
                total={parsedRows.length}
                deletedCount={deletedCount}
              />
            )}

            {/* Tahlil turi + tugmalar */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4 lg:items-end pt-1">
              <Field label="Tahlil turi">
                <Md3Select
                  value={mode}
                  onChange={(v) => setMode(v as ResultAnalysisMode)}
                  options={MODE_OPTIONS}
                  placeholder="Tahlil turini tanlang"
                  ariaLabel="Tahlil turi"
                />
              </Field>
              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className="btn-primary whitespace-nowrap"
                >
                  {loading ? (
                    <>
                      <span className="w-4 h-4 spinner" />
                      Tekshirilmoqda...
                    </>
                  ) : (
                    <>
                      <svg
                        className="w-4 h-4"
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
                      Tekshirish
                    </>
                  )}
                </button>
                {(pasted || mode || result) && (
                  <button
                    type="button"
                    onClick={handleReset}
                    className="btn-secondary whitespace-nowrap"
                  >
                    Tozalash
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Xato */}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm animate-fade-in">
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto underline text-xs"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Natija */}
      {result && <ResultTable result={result} />}
    </div>
  );
}

/* ──────────────── Umumiy MD3 bo'laklar ──────────────── */

function StepHeader({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-6 h-6 rounded-full bg-primary-600 text-white text-[12px] font-semibold flex items-center justify-center shrink-0">
        {n}
      </span>
      <h3 className="text-[15px] font-semibold text-gray-900 dark:text-white">
        {title}
      </h3>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="label-text block">{label}</label>
      {children}
    </div>
  );
}

/* ──────────────── Jonli tekislangan ko'rinish ──────────────── */

function PreviewTable({
  rows,
  total,
  deletedCount,
}: {
  rows: PreviewRow[];
  total: number;
  deletedCount: number;
}) {
  const shown = rows.slice(0, PREVIEW_LIMIT);
  return (
    <div className="surface-tonal p-0 overflow-hidden animate-fade-in">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-gray-200/70 dark:border-slate-700/60">
        <span className="text-[12.5px] font-semibold text-gray-700 dark:text-slate-200">
          Ustunlar ko'rinishi
        </span>
        <span className="badge-info">{total.toLocaleString()} qator</span>
        <span className="badge-success">
          {(total - deletedCount).toLocaleString()} natija chiqqan
        </span>
        {deletedCount > 0 && (
          <span className="badge-warning">
            {deletedCount.toLocaleString()} o'chirilgan
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[10.5px] uppercase tracking-[0.08em] text-gray-500 dark:text-slate-400 border-b border-gray-200/70 dark:border-slate-700/60">
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                imei
              </th>
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                abitur_id
              </th>
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                img
              </th>
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                common_ball
              </th>
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                tday
              </th>
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">
                deleted
              </th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {shown.map((r, i) => (
              <tr
                key={i}
                className="border-b border-gray-100 dark:border-slate-800/70 last:border-0"
              >
                <Cell v={r.imei} strong />
                <Cell v={r.abitur_id} />
                <Cell v={r.img} truncate />
                <Cell v={r.common_ball} />
                <Cell v={r.tday} />
                <td className="px-4 py-2 align-top whitespace-nowrap">
                  {r.deleted === "" ? (
                    <span className="text-gray-300 dark:text-slate-600">—</span>
                  ) : r.isDeleted ? (
                    <span className="badge-warning">{r.deleted}</span>
                  ) : (
                    <span className="text-gray-600 dark:text-slate-300">
                      {r.deleted}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > PREVIEW_LIMIT && (
        <div className="px-4 py-2 text-[12px] text-gray-500 dark:text-slate-400 border-t border-gray-200/70 dark:border-slate-700/60">
          … va yana {(total - PREVIEW_LIMIT).toLocaleString()} qator (tahlilda
          hammasi hisobga olinadi)
        </div>
      )}
    </div>
  );
}

function Cell({
  v,
  strong = false,
  truncate = false,
}: {
  v: string;
  strong?: boolean;
  truncate?: boolean;
}) {
  return (
    <td
      className={`px-4 py-2 align-top whitespace-nowrap ${
        truncate ? "max-w-[180px] truncate" : ""
      } ${
        strong
          ? "font-semibold text-gray-900 dark:text-white"
          : "text-gray-700 dark:text-slate-300"
      }`}
      title={truncate ? v : undefined}
    >
      {v === "" ? (
        <span className="text-gray-300 dark:text-slate-600">—</span>
      ) : (
        v
      )}
    </td>
  );
}

/* ──────────────── Natija jadvali ──────────────── */

function ResultTable({ result }: { result: ResultAnalysisResponse }) {
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Diagnostika */}
      <div className="flex flex-wrap gap-2">
        <Stat label="Ko'lamdagi talabalar" value={result.scope_total} />
        <Stat label="Joylangan imei" value={result.pasted_total} />
        <Stat label="Natija chiqqan" value={result.pasted_result_count} />
        <Stat label="Topildi" value={result.count} highlight />
      </div>

      <div className="glass-card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-gray-500 dark:text-slate-400 border-b border-gray-200 dark:border-slate-700 bg-gray-50/60 dark:bg-slate-800/40">
                <th className="px-4 py-3 font-semibold">#</th>
                <th className="px-4 py-3 font-semibold">Familiya</th>
                <th className="px-4 py-3 font-semibold">Ism</th>
                <th className="px-4 py-3 font-semibold">Sharif</th>
                <th className="px-4 py-3 font-semibold">IMEI</th>
                <th className="px-4 py-3 font-semibold">Viloyat</th>
                <th className="px-4 py-3 font-semibold">Bino</th>
                <th className="px-4 py-3 font-semibold">Test kuni</th>
                <th className="px-4 py-3 font-semibold">Smena</th>
              </tr>
            </thead>
            <tbody>
              {result.items.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="px-4 py-12 text-center text-gray-400 dark:text-slate-500"
                  >
                    Nomuvofiqlik topilmadi
                  </td>
                </tr>
              ) : (
                result.items.map((it, i) => <Row key={i} idx={i + 1} it={it} />)
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Row({ idx, it }: { idx: number; it: ResultAnalysisItem }) {
  return (
    <tr className="border-b border-gray-100 dark:border-slate-800 last:border-0 hover:bg-gray-50/70 dark:hover:bg-slate-800/40 transition-colors">
      <td className="px-4 py-2.5 text-gray-400 dark:text-slate-500 tabular-nums">
        {idx}
      </td>
      <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-white">
        {it.last_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200">
        {it.first_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200">
        {it.middle_name || "—"}
      </td>
      <td className="px-4 py-2.5 font-mono text-[12.5px] text-gray-700 dark:text-slate-300">
        {it.imei || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200">
        {it.region_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200">
        {it.zone_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 tabular-nums">
        {formatDay(it.test_day)}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200">
        {it.smena_name || "—"}
      </td>
    </tr>
  );
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`px-4 py-2.5 rounded-2xl border text-sm ${
        highlight
          ? "bg-primary-50 dark:bg-primary-900/25 border-primary-200 dark:border-primary-800"
          : "surface-tonal"
      }`}
    >
      <span className="text-gray-500 dark:text-slate-400">{label}: </span>
      <span
        className={`font-semibold tabular-nums ${
          highlight
            ? "text-primary-700 dark:text-primary-300"
            : "text-gray-900 dark:text-white"
        }`}
      >
        {value.toLocaleString()}
      </span>
    </div>
  );
}
