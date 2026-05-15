import { useCallback, useEffect, useRef, useState } from "react";
import type {
  DashboardStatsResponse,
  GenderStat,
  RegionStatItem,
  SessionStateResponse,
  StatGroup,
  TestSessionResponse,
  TestSessionSmenaResponse,
} from "../interfaces";
import {
  getSessionDashboardStatsApi,
  getSessionStatesLookupApi,
  getTestSessionApi,
  getTestSessionsApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import { extractErrorMessage } from "../utils/errorMessage";

// Real-time polling kechikishi (session ready / state.key=4)
const POLL_INTERVAL_MS = 5000;

/**
 * Sessiya holati (SessionState.key) bo'yicha rang palitrasi.
 * Native <select>/<option> rangini boshqarish uchun hex + Tailwind class.
 */
type StateColor = {
  // -500/-600 darajadagi rang — light va dark mode'da ham yetarli kontrastli
  hex: string;
  accent: string; // select left-border + focus ring
  chipText: string;
  dot: string;
};

const STATE_COLORS: Record<number, StateColor> = {
  // 1 — Yaratilgan
  1: {
    hex: "#64748b", // slate-500
    accent: "border-l-4 border-l-slate-400 focus:ring-slate-300/40",
    chipText: "text-slate-600 dark:text-slate-300",
    dot: "bg-slate-400",
  },
  // 2 — Yuklab olindi
  2: {
    hex: "#0ea5e9", // sky-500
    accent: "border-l-4 border-l-sky-500 focus:ring-sky-300/40",
    chipText: "text-sky-700 dark:text-sky-300",
    dot: "bg-sky-500",
  },
  // 3 — Embedding
  3: {
    hex: "#f59e0b", // amber-500
    accent: "border-l-4 border-l-amber-500 focus:ring-amber-300/40",
    chipText: "text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  // 4 — Tayyor (ready)
  4: {
    hex: "#10b981", // emerald-500
    accent: "border-l-4 border-l-emerald-500 focus:ring-emerald-300/40",
    chipText: "text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  // 5 — Yakunlangan
  5: {
    hex: "#8b5cf6", // violet-500
    accent: "border-l-4 border-l-violet-500 focus:ring-violet-300/40",
    chipText: "text-violet-700 dark:text-violet-300",
    dot: "bg-violet-500",
  },
};

const FALLBACK_COLOR: StateColor = {
  hex: "#64748b",
  accent: "",
  chipText: "text-gray-600 dark:text-slate-300",
  dot: "bg-gray-400",
};

function getStateColor(key: number | null | undefined): StateColor {
  if (key == null) return FALLBACK_COLOR;
  return STATE_COLORS[key] ?? FALLBACK_COLOR;
}

export default function StatisticsPage() {
  // Selektorlar
  const [states, setStates] = useState<SessionStateResponse[]>([]);
  const [statesLoading, setStatesLoading] = useState(true);
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null);

  const [sessions, setSessions] = useState<TestSessionResponse[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [selectedSession, setSelectedSession] =
    useState<TestSessionResponse | null>(null);
  const [selectedSmenaId, setSelectedSmenaId] = useState<number | null>(null);

  // Stats holati
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // === Statuslar (SessionState) ro'yxatini yuklash ===
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await getSessionStatesLookupApi();
        if (!cancelled) {
          // key bo'yicha tartiblash (1..5)
          setStates([...list].sort((a, b) => a.key - b.key));
        }
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setStatesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // === Tanlangan status bo'yicha sessiyalarni yuklash ===
  useEffect(() => {
    // Status tanlanmagan bo'lsa — sessiyalarni tozalaymiz
    if (selectedStateId === null) {
      setSessions([]);
      setSelectedSessionId(null);
      return;
    }

    let cancelled = false;
    setSessionsLoading(true);
    (async () => {
      try {
        const res = await getTestSessionsApi({
          page: 1,
          per_page: 100,
          test_state_id: selectedStateId,
        });
        if (!cancelled) {
          setSessions(res.items);
          // Status o'zgarganda — eski tanlovni reset qilamiz
          setSelectedSessionId(null);
        }
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setSessionsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedStateId]);

  // === Sessiya tanlanganida — to'liq ma'lumotni qayta yuklab smenalarni olamiz ===
  useEffect(() => {
    if (selectedSessionId === null) {
      setSelectedSession(null);
      setSelectedSmenaId(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getTestSessionApi(selectedSessionId);
        if (cancelled) return;
        setSelectedSession(data);
        // Avvalgi tanlovni reset qilish
        setSelectedSmenaId(null);
        setStats(null);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedSessionId]);

  // === Stats fetcher (qayta ishlatiluvchi) ===
  const fetchStats = useCallback(
    async (sessionId: number, sessionSmenaId: number, silent = false) => {
      if (!silent) setStatsLoading(true);
      try {
        const data = await getSessionDashboardStatsApi(
          sessionId,
          sessionSmenaId,
        );
        setStats(data);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        setError(extractErrorMessage(err));
      } finally {
        if (!silent) setStatsLoading(false);
      }
    },
    [],
  );

  // === Tanlov o'zgarganda statsni yuklash + polling ===
  useEffect(() => {
    // Eski polling'ni to'xtatamiz
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    if (!selectedSessionId || !selectedSmenaId) {
      setStats(null);
      return;
    }

    fetchStats(selectedSessionId, selectedSmenaId);
  }, [selectedSessionId, selectedSmenaId, fetchStats]);

  // === Real-time polling — faqat session.state.key=4 bo'lsa ===
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!stats?.is_realtime || !selectedSessionId || !selectedSmenaId) return;

    pollRef.current = setInterval(() => {
      fetchStats(selectedSessionId, selectedSmenaId, true);
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [stats?.is_realtime, selectedSessionId, selectedSmenaId, fetchStats]);

  // === Smenalar tanlovi uchun yordamchi (kun + smena ko'rinishi) ===
  const smenas = selectedSession?.smenas ?? [];

  // === Tanlangan status uchun rang (dropdownlarga visual accent) ===
  const selectedState = selectedStateId
    ? states.find((st) => st.id === selectedStateId) ?? null
    : null;
  const stateColor = getStateColor(selectedState?.key);

  return (
    <div>
      <div className="page-header">
        <div className="min-w-0">
          <h2 className="section-title">Statistika dashboard</h2>
          <p className="section-subtitle">
            Test sessiya, kun va smena tanlang — real vaqt statistikasi (sessiya
            tayyor holatida) yoki oxirgi holat ko'rsatiladi
          </p>
        </div>
        {stats?.is_realtime && (
          <div className="inline-flex items-center gap-2 px-3 h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40 self-start sm:self-auto">
            <span className="relative flex w-2.5 h-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            <span className="text-[12px] font-semibold">Real vaqt</span>
            {lastUpdated && (
              <span className="text-[11px] text-emerald-600/80 dark:text-emerald-400/80">
                {lastUpdated.toLocaleTimeString("uz-UZ")}
              </span>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm flex items-start justify-between gap-3">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="underline shrink-0"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Selektorlar — kompakt MD3 surface */}
      <div className="glass-card p-2.5 sm:p-3 mb-3 sm:mb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 leading-none">
              Holat
            </label>
            <select
              value={selectedStateId ?? ""}
              onChange={(e) =>
                setSelectedStateId(e.target.value ? Number(e.target.value) : null)
              }
              disabled={statesLoading}
              className={`input-field !min-h-0 !py-1.5 !px-3 !text-[13px] w-full disabled:opacity-60 font-semibold ${
                selectedStateId !== null ? stateColor.accent : ""
              }`}
              style={
                selectedStateId !== null
                  ? { color: stateColor.hex }
                  : undefined
              }
            >
              <option value="" style={{ color: "#6b7280" }}>
                — Tanlang —
              </option>
              {states.map((st) => {
                const c = getStateColor(st.key);
                return (
                  <option
                    key={st.id}
                    value={st.id}
                    style={{ color: c.hex, fontWeight: 600 }}
                  >
                    {st.name}
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 leading-none">
              Test sessiya
            </label>
            <select
              value={selectedSessionId ?? ""}
              onChange={(e) =>
                setSelectedSessionId(e.target.value ? Number(e.target.value) : null)
              }
              disabled={selectedStateId === null || sessionsLoading}
              className={`input-field !min-h-0 !py-1.5 !px-3 !text-[13px] w-full disabled:opacity-60 font-semibold ${
                selectedStateId !== null ? stateColor.accent : ""
              }`}
              style={
                selectedStateId !== null
                  ? { color: stateColor.hex }
                  : undefined
              }
            >
              <option value="" style={{ color: "#6b7280", fontWeight: 400 }}>
                {selectedStateId === null
                  ? "— Avval holatni tanlang —"
                  : sessionsLoading
                  ? "— Yuklanmoqda… —"
                  : sessions.length === 0
                  ? "— Bu holatda sessiyalar yo'q —"
                  : "— Tanlang —"}
              </option>
              {sessions.map((s) => {
                const c = getStateColor(s.test_state?.key);
                return (
                  <option
                    key={s.id}
                    value={s.id}
                    style={{ color: c.hex, fontWeight: 600 }}
                  >
                    #{s.number} · {s.name}
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 leading-none">
              Kun va smena
            </label>
            <select
              value={selectedSmenaId ?? ""}
              onChange={(e) =>
                setSelectedSmenaId(e.target.value ? Number(e.target.value) : null)
              }
              disabled={!selectedSession || smenas.length === 0}
              className="input-field !min-h-0 !py-1.5 !px-3 !text-[13px] w-full disabled:opacity-60"
            >
              <option value="">
                {smenas.length ? "— Tanlang —" : "— Avval sessiyani tanlang —"}
              </option>
              {smenas.map((sm) => (
                <option key={sm.id} value={sm.id}>
                  {formatSmenaOption(sm)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Tanlangan statuslar — kompakt chiplar qatori (faqat tegishlilarini ko'rsatamiz) */}
        {(selectedState || (stats && stats.session_state_key != null)) && (
          <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[10.5px]">
            {selectedState && (
              <span
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md ${stateColor.chipText} bg-gray-100 dark:bg-slate-700/40`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${stateColor.dot}`}
                  aria-hidden
                />
                <span className="font-medium leading-none">
                  {selectedState.name}
                </span>
              </span>
            )}
            {selectedSession?.test_state &&
              selectedSession.test_state.key !== selectedState?.key && (
                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md ${
                    getStateColor(selectedSession.test_state.key).chipText
                  } bg-gray-100 dark:bg-slate-700/40`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      getStateColor(selectedSession.test_state.key).dot
                    }`}
                    aria-hidden
                  />
                  <span className="font-medium leading-none">
                    {selectedSession.test_state.name}
                  </span>
                </span>
              )}
            {stats && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-gray-500 dark:text-slate-400">
                <span className="leading-none">·</span>
                <span className="leading-none">
                  joriy:{" "}
                  <span className="font-semibold text-gray-700 dark:text-slate-200">
                    {stateLabel(stats.session_state_key)}
                  </span>
                </span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Empty states */}
      {selectedStateId === null && (
        <EmptyHint text="Boshlash uchun yuqorida sessiya holatini tanlang" />
      )}
      {selectedStateId !== null && !selectedSessionId && (
        <EmptyHint text="Endi test sessiyani tanlang" />
      )}
      {selectedSessionId && !selectedSmenaId && (
        <EmptyHint text="Endi kun va smenani tanlang" />
      )}

      {/* Stats */}
      {selectedSmenaId && statsLoading && !stats && <PageLoader />}

      {stats && (
        <>
          {/* 4 ta asosiy card — kompakt */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-1.5 sm:gap-2 mb-2.5 sm:mb-3">
            <SummaryCard
              title="Umumiy talabgorlar"
              variant="primary"
              breakdown={stats.summary.total}
              icon={<UsersIcon />}
            />
            <SummaryCard
              title="Kelganlar"
              variant="success"
              breakdown={stats.summary.attended}
              icon={<CheckIcon />}
            />
            <SummaryCard
              title="Kelmaganlar"
              variant="warning"
              breakdown={stats.summary.not_attended}
              icon={<XIcon />}
            />
            <CheatingCard cheating={stats.summary.cheating} />
          </div>

          {/* Region cardlari */}
          <div className="flex items-end justify-between mb-2 sm:mb-3">
            <div>
              <h3 className="text-[14px] sm:text-base font-semibold text-gray-900 dark:text-white">
                Viloyatlar bo'yicha taqsimot
              </h3>
              <p className="text-[11px] text-gray-500 dark:text-slate-400">
                Region.number bo'yicha tartiblangan · {stats.regions.length} ta viloyat
              </p>
            </div>
          </div>

          {stats.regions.length === 0 ? (
            <EmptyHint text="Bu sessiya/smena uchun talabgorlar topilmadi" />
          ) : (
            <RegionGrid regions={stats.regions} />
          )}
        </>
      )}
    </div>
  );
}

/* ============== Sub-components ============== */

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="glass-card p-8 sm:p-12 text-center text-gray-500 dark:text-slate-400">
      <svg
        className="w-10 h-10 mx-auto mb-3 text-gray-300 dark:text-slate-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
      <p className="text-sm">{text}</p>
    </div>
  );
}

type Variant = "primary" | "success" | "warning" | "danger";

const VARIANT_STYLES: Record<
  Variant,
  { bg: string; ring: string; valueColor: string; iconBg: string }
> = {
  primary: {
    bg: "bg-gradient-to-br from-primary-50 to-white dark:from-primary-900/20 dark:to-slate-900",
    ring: "ring-primary-200/60 dark:ring-primary-800/40",
    valueColor: "text-primary-800 dark:text-primary-200",
    iconBg:
      "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300",
  },
  success: {
    bg: "bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/20 dark:to-slate-900",
    ring: "ring-emerald-200/60 dark:ring-emerald-800/40",
    valueColor: "text-emerald-800 dark:text-emerald-200",
    iconBg:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
  warning: {
    bg: "bg-gradient-to-br from-amber-50 to-white dark:from-amber-900/20 dark:to-slate-900",
    ring: "ring-amber-200/60 dark:ring-amber-800/40",
    valueColor: "text-amber-800 dark:text-amber-200",
    iconBg: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  },
  danger: {
    bg: "bg-gradient-to-br from-red-50 to-white dark:from-red-900/20 dark:to-slate-900",
    ring: "ring-red-200/60 dark:ring-red-800/40",
    valueColor: "text-red-800 dark:text-red-200",
    iconBg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  },
};

function SummaryCard({
  title,
  breakdown,
  icon,
  variant,
}: {
  title: string;
  breakdown: GenderStat;
  icon: React.ReactNode;
  variant: Variant;
}) {
  const s = VARIANT_STYLES[variant];
  return (
    <div
      className={`relative overflow-hidden rounded-xl ring-1 ${s.bg} ${s.ring} p-2.5 sm:p-3 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-gray-600 dark:text-slate-400 leading-none">
          {title}
        </p>
        <div
          className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl flex items-center justify-center shrink-0 ${s.iconBg}`}
        >
          {icon}
        </div>
      </div>
      <p className={`text-xl sm:text-2xl xl:text-3xl font-bold tabular-nums leading-none ${s.valueColor}`}>
        {breakdown.total.toLocaleString("uz-UZ")}
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-1 text-[10.5px] sm:text-[11px]">
        <GenderChip label="E" count={breakdown.male} accent="sky" />
        <GenderChip label="A" count={breakdown.female} accent="pink" />
        {breakdown.unknown > 0 && (
          <GenderChip label="?" count={breakdown.unknown} accent="slate" />
        )}
      </div>
    </div>
  );
}

function CheatingCard({ cheating }: { cheating: StatGroup["cheating"] }) {
  const s = VARIANT_STYLES.danger;
  return (
    <div
      className={`relative overflow-hidden rounded-xl ring-1 ${s.bg} ${s.ring} p-2.5 sm:p-3 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-gray-600 dark:text-slate-400 leading-none">
          Chetlatilgan
        </p>
        <div
          className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl flex items-center justify-center shrink-0 ${s.iconBg}`}
        >
          <ShieldIcon />
        </div>
      </div>
      <p className={`text-xl sm:text-2xl xl:text-3xl font-bold tabular-nums leading-none ${s.valueColor}`}>
        {cheating.total.toLocaleString("uz-UZ")}
      </p>
      <div className="mt-1.5 grid grid-cols-2 gap-1 text-[10px] sm:text-[10.5px]">
        <div className="bg-white/70 dark:bg-slate-800/60 rounded-md px-1.5 py-1 ring-1 ring-red-100/60 dark:ring-red-900/30">
          <p className="text-gray-500 dark:text-slate-400 leading-none">Kirishda</p>
          <p className="font-bold text-red-700 dark:text-red-300 tabular-nums leading-tight mt-0.5">
            {cheating.at_entry.toLocaleString("uz-UZ")}
          </p>
        </div>
        <div className="bg-white/70 dark:bg-slate-800/60 rounded-md px-1.5 py-1 ring-1 ring-red-100/60 dark:ring-red-900/30">
          <p className="text-gray-500 dark:text-slate-400 leading-none">Testda</p>
          <p className="font-bold text-red-700 dark:text-red-300 tabular-nums leading-tight mt-0.5">
            {cheating.during_test.toLocaleString("uz-UZ")}
          </p>
        </div>
      </div>
    </div>
  );
}

function GenderChip({
  label,
  count,
  accent,
}: {
  label: string;
  count: number;
  accent: "sky" | "pink" | "slate";
}) {
  const cls =
    accent === "sky"
      ? "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
      : accent === "pink"
      ? "bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300"
      : "bg-slate-100 text-slate-600 dark:bg-slate-700/60 dark:text-slate-300";
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md font-medium leading-none ${cls}`}
    >
      <span className="text-[9.5px] opacity-80">{label}</span>
      <span className="tabular-nums font-bold">
        {count.toLocaleString("uz-UZ")}
      </span>
    </span>
  );
}

/**
 * RegionGrid — viloyatlarni MD3 uslubidagi 2-ustunli vertikal tartiblangan
 * gridda chiqaradi. Region.number tartibi vertikal yo'naltirilgan:
 *  - Chap ustun: 1..N/2
 *  - O'ng ustun: N/2+1..N
 *
 * Mobile (<lg) da bitta ustun bo'ladi va tabiiy ravishda 1..N tartib saqlanadi.
 */
function RegionGrid({ regions }: { regions: RegionStatItem[] }) {
  const mid = Math.ceil(regions.length / 2);
  const leftCol = regions.slice(0, mid);
  const rightCol = regions.slice(mid);

  const renderColumn = (col: RegionStatItem[]) => (
    <div className="flex flex-col gap-2.5 sm:gap-3">
      {col.map((r) => (
        <RegionCard key={r.region_id} item={r} />
      ))}
    </div>
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5 sm:gap-3 lg:gap-x-6 xl:gap-x-8">
      {renderColumn(leftCol)}
      {rightCol.length > 0 && renderColumn(rightCol)}
    </div>
  );
}

/** Material 3 uslubidagi region kartochkasi. */
function RegionCard({ item }: { item: RegionStatItem }) {
  const total = item.stats.total.total;
  const attended = item.stats.attended.total;
  const attendancePercent =
    total > 0 ? Math.round((attended / total) * 1000) / 10 : 0;

  // Davomat foiziga qarab progress rang — semantik signal
  const percentTone =
    attendancePercent >= 75
      ? "from-emerald-400 to-emerald-600"
      : attendancePercent >= 50
      ? "from-amber-400 to-amber-500"
      : "from-red-400 to-red-500";
  const percentText =
    attendancePercent >= 75
      ? "text-emerald-700 dark:text-emerald-300"
      : attendancePercent >= 50
      ? "text-amber-700 dark:text-amber-300"
      : "text-red-700 dark:text-red-300";

  return (
    <article
      className="glass-card p-3 sm:p-3.5 hover:-translate-y-0.5 transition-transform duration-200 group"
      aria-label={`Region ${item.region_number}: ${item.region_name}`}
    >
      {/* Header: badge + nom + davomat % */}
      <header className="flex items-center justify-between gap-2.5 mb-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* MD3 filled-tonal badge */}
          <div className="relative shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-white font-bold flex items-center justify-center shadow-md shadow-primary-500/25 ring-1 ring-white/20">
              <span className="text-[13px] tabular-nums leading-none">
                {item.region_number}
              </span>
            </div>
          </div>
          <div className="min-w-0">
            <p
              className="text-[13px] sm:text-sm font-semibold text-gray-900 dark:text-white truncate leading-tight"
              title={item.region_name || `Region #${item.region_number}`}
            >
              {item.region_name || `Region #${item.region_number}`}
            </p>
            <p className="text-[10.5px] text-gray-500 dark:text-slate-400 leading-none mt-0.5">
              Region №{item.region_number}
            </p>
          </div>
        </div>

        {/* Davomat foizi — semantik rangda */}
        <div className="flex flex-col items-end shrink-0">
          <span
            className={`text-base sm:text-[17px] font-bold tabular-nums leading-none ${percentText}`}
          >
            {attendancePercent}%
          </span>
          <span className="text-[9.5px] text-gray-500 dark:text-slate-400 uppercase tracking-wider leading-none mt-0.5">
            davomat
          </span>
        </div>
      </header>

      {/* Linear progress — MD3 thin track */}
      <div
        className="h-1 rounded-full bg-gray-100 dark:bg-slate-700/50 overflow-hidden mb-2.5"
        role="progressbar"
        aria-valuenow={attendancePercent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full bg-gradient-to-r ${percentTone} transition-[width] duration-500 ease-out`}
          style={{ width: `${attendancePercent}%` }}
        />
      </div>

      {/* 4 stat tile */}
      <div className="grid grid-cols-4 gap-1.5 sm:gap-2">
        <MiniStat label="Umumiy" breakdown={item.stats.total} accent="primary" />
        <MiniStat label="Kelgan" breakdown={item.stats.attended} accent="success" />
        <MiniStat label="Kelmagan" breakdown={item.stats.not_attended} accent="warning" />
        <MiniCheating cheating={item.stats.cheating} />
      </div>
    </article>
  );
}

/** MD3 tonal-surface stat tile (Umumiy / Kelgan / Kelmagan). */
function MiniStat({
  label,
  breakdown,
  accent,
}: {
  label: string;
  breakdown: GenderStat;
  accent: Variant;
}) {
  const s = VARIANT_STYLES[accent];
  return (
    <div
      className={`rounded-xl ring-1 ${s.bg} ${s.ring} px-2 py-1.5 sm:px-2.5 sm:py-2 transition-shadow duration-200 hover:shadow-sm`}
    >
      <p className="text-[9.5px] sm:text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 leading-none">
        {label}
      </p>
      <p
        className={`text-base sm:text-lg font-bold tabular-nums leading-tight mt-1 ${s.valueColor}`}
      >
        {breakdown.total.toLocaleString("uz-UZ")}
      </p>
      <div className="flex items-center gap-1.5 mt-1 text-[10px] sm:text-[10.5px] text-gray-600 dark:text-slate-300 leading-none">
        <span
          className="inline-flex items-center gap-0.5"
          title={`Erkak: ${breakdown.male}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
          <span className="tabular-nums font-semibold">{breakdown.male}</span>
        </span>
        <span
          className="inline-flex items-center gap-0.5"
          title={`Ayol: ${breakdown.female}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-pink-500" />
          <span className="tabular-nums font-semibold">{breakdown.female}</span>
        </span>
        {breakdown.unknown > 0 && (
          <span
            className="inline-flex items-center gap-0.5 text-gray-400"
            title={`Jinsi noma'lum: ${breakdown.unknown}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span className="tabular-nums">{breakdown.unknown}</span>
          </span>
        )}
      </div>
    </div>
  );
}

/** Chetlatilganlar uchun maxsus MD3 error-container uslub. */
function MiniCheating({ cheating }: { cheating: StatGroup["cheating"] }) {
  const s = VARIANT_STYLES.danger;
  return (
    <div
      className={`rounded-xl ring-1 ${s.bg} ${s.ring} px-2 py-1.5 sm:px-2.5 sm:py-2 transition-shadow duration-200 hover:shadow-sm`}
    >
      <p className="text-[9.5px] sm:text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 leading-none">
        Chetlat.
      </p>
      <p
        className={`text-base sm:text-lg font-bold tabular-nums leading-tight mt-1 ${s.valueColor}`}
      >
        {cheating.total.toLocaleString("uz-UZ")}
      </p>
      <div className="flex items-center gap-1.5 mt-1 text-[10px] sm:text-[10.5px] text-gray-600 dark:text-slate-300 leading-none">
        <span
          title="Binoga kirishda"
          className="inline-flex items-center gap-0.5"
        >
          <KeyIcon className="w-3 h-3 text-red-500" />
          <span className="tabular-nums font-semibold">{cheating.at_entry}</span>
        </span>
        <span
          title="Test jarayonida"
          className="inline-flex items-center gap-0.5"
        >
          <BookIcon className="w-3 h-3 text-red-500" />
          <span className="tabular-nums font-semibold">
            {cheating.during_test}
          </span>
        </span>
      </div>
    </div>
  );
}

/* ============== Helpers ============== */

function formatSmenaOption(sm: TestSessionSmenaResponse): string {
  const day = sm.day;
  const smName = sm.smena?.name ?? `#${sm.smena?.number ?? sm.test_smena_id}`;
  const smNum = sm.smena?.number ?? sm.test_smena_id;
  return `${day} · ${smName} (smena №${smNum})`;
}

function stateLabel(key: number): string {
  switch (key) {
    case 1:
      return "Yaratilgan";
    case 2:
      return "Yuklab olindi";
    case 3:
      return "Embedding";
    case 4:
      return "Tayyor (ready)";
    case 5:
      return "Yakunlangan";
    default:
      return "—";
  }
}

/* ============== Inline icons ============== */

function UsersIcon() {
  return (
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
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2.5}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function XIcon() {
  return (
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
        d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
      />
    </svg>
  );
}

function ShieldIcon() {
  return (
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
        d="M12 15v2m0 4h.01M5 13a7 7 0 1114 0v6a2 2 0 01-2 2H7a2 2 0 01-2-2v-6z"
      />
    </svg>
  );
}

function KeyIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
      />
    </svg>
  );
}

function BookIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  );
}
