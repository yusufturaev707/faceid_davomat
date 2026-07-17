import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  analyzeResultsApi,
  exportResultAnalysisApi,
  getResultAnalysisConfigApi,
  getResultAnalysisSessionsApi,
  getTestsListApi,
  type ResultAnalysisItem,
  type ResultAnalysisMode,
  type ResultAnalysisResponse,
  type ResultAnalysisRow,
  type ResultAnalysisScopeSession,
} from "../api";
import Md3Select, { type Md3Option } from "../components/Md3Select";
import Pagination from "../components/Pagination";
import { extractErrorMessage } from "../utils/errorMessage";

/** BASE_IMG_URL va img qiymatini bitta URL ga birlashtiradi. */
function buildImgUrl(base: string, img: string | null | undefined): string {
  if (!base || !img) return "";
  return `${base.replace(/\/+$/, "")}/${img.replace(/^\/+/, "")}`;
}

/**
 * Natija uchun tahlil.
 *
 * Oqim: test (id bo'yicha) → shu testning aktiv (status=true) test sessiyasi →
 * shu sessiyaning test kunlari (oxirida "Umumiy" — barcha kunlar). So'ng tashqi
 * natija tizimidan (Excel/Access) ustunlar textarea'ga joylanadi:
 *   imei | abitur_id | img | common_ball | tday | deleted   (TAB bilan ajratilgan)
 * Joylangan matn jonli tekislangan jadvalga (pagination bilan) ajratiladi.
 * Backend `imei` bo'yicha FaceID bazasi bilan solishtirib, nomuvofiqliklarni
 * qaytaradi (natija jadvali ham pagination + gorizontal scroll bilan).
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

const DAY_ALL = "all"; // "Umumiy" — sessiyaning barcha kunlari
const PREVIEW_PAGE_SIZE = 20;
const RESULT_PAGE_SIZE = 25;

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
  const [testId, setTestId] = useState("");

  const [sessions, setSessions] = useState<ResultAnalysisScopeSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const [daySel, setDaySel] = useState(""); // "" | DAY_ALL | "YYYY-MM-DD"
  const [mode, setMode] = useState<ResultAnalysisMode | "">("");
  const [pasted, setPasted] = useState("");

  const [result, setResult] = useState<ResultAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [baseImgUrl, setBaseImgUrl] = useState("");
  const [modalUrl, setModalUrl] = useState<string | null>(null);
  const viewImage = (img: string | null | undefined) => {
    const url = buildImgUrl(baseImgUrl, img);
    if (url) setModalUrl(url);
  };

  // Testlar (faqat aktiv, id bo'yicha o'sish tartibida).
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const testList = await getTestsListApi();
        if (!alive) return;
        setTests(
          testList
            .filter((t) => t.is_active)
            .sort((a, b) => a.id - b.id)
            .map((t) => ({ value: String(t.id), label: t.name })),
        );
      } catch (err) {
        if (alive) setError(extractErrorMessage(err));
      }
      // Rasm bazasi URL'i — bo'lmasa rasm ko'rish o'chadi (jimgina).
      try {
        const cfg = await getResultAnalysisConfigApi();
        if (alive) setBaseImgUrl(cfg.base_img_url || "");
      } catch {
        /* e'tiborsiz */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Test tanlanganda — shu testning aktiv (status=true) sessiyalari.
  useEffect(() => {
    setSessions([]);
    setSessionId("");
    setDaySel("");
    if (!testId) return;
    let alive = true;
    setSessionsLoading(true);
    getResultAnalysisSessionsApi(Number(testId))
      .then((res) => {
        if (alive) setSessions(res);
      })
      .catch((err) => {
        if (alive) setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (alive) setSessionsLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [testId]);

  // Sessiya o'zgarsa — test kuni va undan keyingi hamma narsa tozalanadi.
  useEffect(() => {
    setDaySel("");
    setPasted("");
    setMode("");
    setResult(null);
  }, [sessionId]);

  const sessionOptions: Md3Option[] = useMemo(
    () =>
      sessions.map((s) => ({
        value: String(s.id),
        label: s.name,
        sublabel: `#${s.number}`,
      })),
    [sessions],
  );

  const selectedSession = useMemo(
    () => sessions.find((s) => String(s.id) === sessionId) ?? null,
    [sessions, sessionId],
  );

  // Sessiyaning test kunlari (backend o'sish tartibida beradi) + oxirida "Umumiy".
  const dayOptions: Md3Option[] = useMemo(() => {
    if (!selectedSession) return [];
    const opts: Md3Option[] = selectedSession.days.map((d) => ({
      value: d,
      label: formatDay(d),
    }));
    if (selectedSession.days.length > 0) {
      opts.push({ value: DAY_ALL, label: "Umumiy (barcha kunlar)" });
    }
    return opts;
  }, [selectedSession]);

  const scopeReady = Boolean(testId && sessionId && daySel);

  const parsedRows = useMemo(() => parseRows(pasted), [pasted]);
  const deletedCount = useMemo(
    () => parsedRows.reduce((n, r) => n + (r.isDeleted ? 1 : 0), 0),
    [parsedRows],
  );
  // "natija chiqqan" = o'chirilmagan VA common_ball bo'sh emas.
  const hasResultCount = useMemo(
    () =>
      parsedRows.reduce(
        (n, r) => n + (!r.isDeleted && r.common_ball.trim() ? 1 : 0),
        0,
      ),
    [parsedRows],
  );

  // Backend solishtiruv + ko'rsatish uchun maydonlarni oladi.
  const analysisRows: ResultAnalysisRow[] = useMemo(
    () =>
      parsedRows.map((r) => ({
        imei: r.imei,
        abitur_id: r.abitur_id || null,
        img: r.img || null,
        tday: r.tday || null,
        common_ball: r.common_ball || null,
        deleted: r.isDeleted,
        deleted_raw: r.deleted || null,
      })),
    [parsedRows],
  );

  const canSubmit = scopeReady && !!mode && analysisRows.length > 0 && !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !mode) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeResultsApi({
        test_session_id: Number(sessionId),
        day: daySel === DAY_ALL ? null : daySel,
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

  // Test kuni tanlanganda — undan keyingi hamma narsa tozalanadi.
  const handleDayChange = (v: string) => {
    setDaySel(v);
    setPasted("");
    setMode("");
    setResult(null);
    setError(null);
  };

  // Tahlil turi tanlanganda — oldingi natija tozalanadi (qayta Tekshirish kerak).
  const handleModeChange = (v: string) => {
    setMode(v as ResultAnalysisMode);
    setResult(null);
  };

  const handleExport = async () => {
    if (!mode || !scopeReady) return;
    setExporting(true);
    setError(null);
    try {
      await exportResultAnalysisApi({
        test_session_id: Number(sessionId),
        day: daySel === DAY_ALL ? null : daySel,
        mode,
        rows: analysisRows,
      });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setExporting(false);
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
        {/* 1-qadam: ko'lam (test → sessiya → test kuni) */}
        <div className="space-y-4">
          <StepHeader n={1} title="Ko'lamni tanlang" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-5 gap-y-5">
            <Field label="Test">
              <Md3Select
                value={testId}
                onChange={setTestId}
                options={tests}
                placeholder="Testni tanlang"
                ariaLabel="Test"
              />
            </Field>
            <Field label="Test sessiya (aktiv)">
              <Md3Select
                value={sessionId}
                onChange={setSessionId}
                options={sessionOptions}
                placeholder={
                  !testId
                    ? "Avval testni tanlang"
                    : sessionsLoading
                      ? "Yuklanmoqda..."
                      : sessionOptions.length === 0
                        ? "Aktiv sessiya yo'q"
                        : "Sessiyani tanlang"
                }
                disabled={!testId || sessionsLoading || sessionOptions.length === 0}
                ariaLabel="Test sessiya"
              />
            </Field>
            <Field label="Test kuni">
              <Md3Select
                value={daySel}
                onChange={handleDayChange}
                options={dayOptions}
                placeholder={
                  !sessionId ? "Avval sessiyani tanlang" : "Kunni tanlang"
                }
                disabled={!sessionId || dayOptions.length === 0}
                ariaLabel="Test kuni"
              />
            </Field>
          </div>
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

            {/* Jonli tekislangan ko'rinish (pagination bilan) */}
            {parsedRows.length > 0 && (
              <PreviewTable
                rows={parsedRows}
                hasResultCount={hasResultCount}
                deletedCount={deletedCount}
                canViewImg={!!baseImgUrl}
                onViewImage={viewImage}
              />
            )}

            {/* Tahlil turi + tugmalar */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4 lg:items-end pt-1">
              <Field label="Tahlil turi">
                <Md3Select
                  value={mode}
                  onChange={handleModeChange}
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
      {result && (
        <ResultTable
          result={result}
          onExport={handleExport}
          exporting={exporting}
          canViewImg={!!baseImgUrl}
          onViewImage={viewImage}
        />
      )}

      {/* Rasm modali */}
      <ImageModal url={modalUrl} onClose={() => setModalUrl(null)} />
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
  hasResultCount,
  deletedCount,
  canViewImg,
  onViewImage,
}: {
  rows: PreviewRow[];
  hasResultCount: number;
  deletedCount: number;
  canViewImg: boolean;
  onViewImage: (img: string) => void;
}) {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const fullTotal = rows.length;

  // imei yoki abitur_id bo'yicha qidiruv (mijoz tomonida).
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      q
        ? rows.filter(
            (r) =>
              r.imei.toLowerCase().includes(q) ||
              r.abitur_id.toLowerCase().includes(q),
          )
        : rows,
    [rows, q],
  );

  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / PREVIEW_PAGE_SIZE));

  // Ma'lumot yoki qidiruv o'zgarsa — birinchi sahifaga qaytamiz.
  useEffect(() => {
    setPage(1);
  }, [q, fullTotal]);

  const start = (page - 1) * PREVIEW_PAGE_SIZE;
  const shown = filtered.slice(start, start + PREVIEW_PAGE_SIZE);

  return (
    <div className="surface-tonal p-0 overflow-hidden animate-fade-in">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-gray-200/70 dark:border-slate-700/60">
        <span className="text-[12.5px] font-semibold text-gray-700 dark:text-slate-200">
          Ustunlar ko'rinishi
        </span>
        <span className="badge-info">{fullTotal.toLocaleString()} qator</span>
        <span className="badge-success">
          {hasResultCount.toLocaleString()} natija chiqqan
        </span>
        {deletedCount > 0 && (
          <span className="badge-warning">
            {deletedCount.toLocaleString()} o'chirilgan
          </span>
        )}
        {q && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-slate-700/60 dark:text-slate-300">
            Qidiruvda: {total.toLocaleString()}
          </span>
        )}

        {/* MD3 qidiruv — imei / abitur_id */}
        <div className="relative ml-auto w-full sm:w-64">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500 pointer-events-none"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="imei yoki abitur_id qidirish..."
            aria-label="imei yoki abitur_id bo'yicha qidirish"
            className="h-9 w-full pl-9 pr-8 rounded-xl border border-gray-300 dark:border-slate-600 bg-surface dark:bg-slate-800 text-[13px] text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary-500 focus:ring-4 focus:ring-primary-500/15 outline-none transition-all"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Qidiruvni tozalash"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors"
            >
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Gorizontal scroll — kenglikka sig'magan ustunlar uchun */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-[12.5px]">
          <thead>
            <tr className="text-left text-[10.5px] uppercase tracking-[0.08em] text-gray-500 dark:text-slate-400 border-b border-gray-200/70 dark:border-slate-700/60">
              <th className="px-4 py-2.5 font-semibold whitespace-nowrap">#</th>
              {COLUMNS.map((c) => (
                <th
                  key={c}
                  className="px-4 py-2.5 font-semibold whitespace-nowrap"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono">
            {shown.length === 0 ? (
              <tr>
                <td
                  colSpan={COLUMNS.length + 1}
                  className="px-4 py-8 text-center text-gray-400 dark:text-slate-500"
                >
                  {q ? "Qidiruv bo'yicha topilmadi" : "Ma'lumot yo'q"}
                </td>
              </tr>
            ) : (
              shown.map((r, i) => (
                <tr
                  key={start + i}
                  className="border-b border-gray-100 dark:border-slate-800/70 last:border-0"
                >
                <td className="px-4 py-2 align-top whitespace-nowrap text-gray-400 dark:text-slate-500 tabular-nums">
                  {start + i + 1}
                </td>
                <Cell v={r.imei} strong />
                <Cell v={r.abitur_id} />
                <td className="px-4 py-2 align-top whitespace-nowrap">
                  <ImgViewButton
                    img={r.img}
                    canView={canViewImg}
                    onView={onViewImage}
                  />
                </td>
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
              ))
            )}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="px-4 pb-3">
          <Pagination page={page} pages={pages} onPageChange={setPage} />
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

function ResultTable({
  result,
  onExport,
  exporting,
  canViewImg,
  onViewImage,
}: {
  result: ResultAnalysisResponse;
  onExport: () => void;
  exporting: boolean;
  canViewImg: boolean;
  onViewImage: (img: string) => void;
}) {
  const [page, setPage] = useState(1);
  const total = result.items.length;
  const pages = Math.max(1, Math.ceil(total / RESULT_PAGE_SIZE));

  // Har yangi tahlilda birinchi sahifaga qaytamiz.
  useEffect(() => {
    setPage(1);
  }, [result]);

  const start = (page - 1) * RESULT_PAGE_SIZE;
  const shown = result.items.slice(start, start + RESULT_PAGE_SIZE);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Diagnostika + eksport */}
      <div className="flex flex-wrap items-center gap-2">
        <Stat label="Ko'lamdagi talabalar" value={result.scope_total} />
        <Stat label="Joylangan imei" value={result.pasted_total} />
        <Stat label="Natija chiqqan" value={result.pasted_result_count} />
        <Stat label="Topildi" value={result.count} highlight />
        <button
          type="button"
          onClick={onExport}
          disabled={exporting || total === 0}
          className="btn-secondary ml-auto whitespace-nowrap"
        >
          {exporting ? (
            <>
              <span className="w-4 h-4 spinner" />
              Yuklanmoqda...
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
                  d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"
                />
              </svg>
              Excelga yuklab olish
            </>
          )}
        </button>
      </div>

      <div className="glass-card p-0 overflow-hidden">
        {/* Gorizontal scroll — kenglikka sig'magan ustunlar uchun */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1240px] text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.08em] text-gray-500 dark:text-slate-400 border-b border-gray-200 dark:border-slate-700 bg-gray-50/60 dark:bg-slate-800/40">
                <th className="px-4 py-3 font-semibold whitespace-nowrap">#</th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Familiya
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">Ism</th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Sharif
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  IMEI
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Viloyat
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Bino
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Test kuni
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Smena
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  abitur_id
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  tday
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  deleted
                </th>
                <th className="px-4 py-3 font-semibold whitespace-nowrap">
                  Rasm
                </th>
              </tr>
            </thead>
            <tbody>
              {total === 0 ? (
                <tr>
                  <td
                    colSpan={13}
                    className="px-4 py-12 text-center text-gray-400 dark:text-slate-500"
                  >
                    Nomuvofiqlik topilmadi
                  </td>
                </tr>
              ) : (
                shown.map((it, i) => (
                  <Row
                    key={start + i}
                    idx={start + i + 1}
                    it={it}
                    canViewImg={canViewImg}
                    onViewImage={onViewImage}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
        {pages > 1 && (
          <div className="px-4 pb-4">
            <Pagination page={page} pages={pages} onPageChange={setPage} />
          </div>
        )}
      </div>
    </div>
  );
}

function Row({
  idx,
  it,
  canViewImg,
  onViewImage,
}: {
  idx: number;
  it: ResultAnalysisItem;
  canViewImg: boolean;
  onViewImage: (img: string) => void;
}) {
  return (
    <tr className="border-b border-gray-100 dark:border-slate-800 last:border-0 hover:bg-gray-50/70 dark:hover:bg-slate-800/40 transition-colors">
      <td className="px-4 py-2.5 text-gray-400 dark:text-slate-500 tabular-nums">
        {idx}
      </td>
      <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-white whitespace-nowrap">
        {it.last_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 whitespace-nowrap">
        {it.first_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 whitespace-nowrap">
        {it.middle_name || "—"}
      </td>
      <td className="px-4 py-2.5 font-mono text-[12.5px] text-gray-700 dark:text-slate-300 whitespace-nowrap">
        {it.imei || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 whitespace-nowrap">
        {it.region_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 whitespace-nowrap">
        {it.zone_name || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 tabular-nums whitespace-nowrap">
        {formatDay(it.test_day)}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 whitespace-nowrap">
        {it.smena_name || "—"}
      </td>
      <td className="px-4 py-2.5 font-mono text-[12.5px] text-gray-700 dark:text-slate-300 whitespace-nowrap">
        {it.abitur_id || "—"}
      </td>
      <td className="px-4 py-2.5 text-gray-800 dark:text-slate-200 tabular-nums whitespace-nowrap">
        {formatDay(it.tday)}
      </td>
      <td className="px-4 py-2.5 whitespace-nowrap">
        {it.deleted == null || it.deleted === "" ? (
          <span className="text-gray-300 dark:text-slate-600">—</span>
        ) : (
          <span className="font-mono text-[12.5px] text-gray-700 dark:text-slate-300">
            {it.deleted}
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 whitespace-nowrap">
        <ImgViewButton
          img={it.img ?? ""}
          canView={canViewImg}
          onView={onViewImage}
        />
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

/* ──────────────── Rasm: tugma + modal ──────────────── */

function ImgViewButton({
  img,
  canView,
  onView,
}: {
  img: string;
  canView: boolean;
  onView: (img: string) => void;
}) {
  if (!img) return <span className="text-gray-300 dark:text-slate-600">—</span>;
  // Rasm bazasi URL'i sozlanmagan bo'lsa — xom qiymatni ko'rsatamiz.
  if (!canView) {
    return (
      <span
        className="font-mono text-[12px] text-gray-500 dark:text-slate-400 truncate inline-block max-w-[160px] align-middle"
        title={img}
      >
        {img}
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onView(img)}
      title={img}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12.5px] font-medium text-primary-700 dark:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-colors"
    >
      <svg
        className="w-4 h-4 shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      Rasm
    </button>
  );
}

function ImageModal({
  url,
  onClose,
}: {
  url: string | null;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">(
    "loading",
  );

  useEffect(() => {
    if (url) setStatus("loading");
  }, [url]);

  useEffect(() => {
    if (!url) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [url, onClose]);

  if (!url) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="md3-dialog relative w-full max-w-3xl p-3 animate-modal-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-2 pb-2">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Rasm
          </h3>
          <div className="flex items-center gap-1">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-icon"
              title="Yangi oynada ochish"
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
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
            <button
              type="button"
              onClick={onClose}
              className="btn-icon"
              aria-label="Yopish"
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
        </div>

        <div className="relative min-h-[220px] flex items-center justify-center rounded-2xl overflow-hidden bg-gray-50 dark:bg-slate-900">
          {status === "loading" && (
            <span className="w-8 h-8 spinner absolute" aria-label="Yuklanmoqda" />
          )}
          {status === "error" ? (
            <div className="py-16 text-center text-sm text-gray-400 dark:text-slate-500">
              Rasm topilmadi
            </div>
          ) : (
            <img
              src={url}
              alt="Rasm"
              onLoad={() => setStatus("loaded")}
              onError={() => setStatus("error")}
              className={`max-h-[75vh] w-auto object-contain transition-opacity duration-200 ${
                status === "loaded" ? "opacity-100" : "opacity-0"
              }`}
            />
          )}
        </div>

        <p className="mt-2 px-2 text-[11px] text-gray-400 dark:text-slate-500 break-all">
          {url}
        </p>
      </div>
    </div>,
    document.body,
  );
}
