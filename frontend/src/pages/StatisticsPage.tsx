import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * Modal hayot-sikli yordamchisi:
 *  - `close()` exit animation'ni o'ynatib (310ms) so'ng `onClose`'ni bajaradi.
 *  - ESC bilan yopish.
 *  - Body scroll'ni lock qiladi va scrollbar kengligini padding bilan
 *    kompensatsiya qiladi — modal ochilib/yopilganda orqa fon o'ngga
 *    "sakramasligi" uchun (asosiy noqulaylik shu edi).
 */
function useModalClose(onClose: () => void) {
  const [closing, setClosing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const close = useCallback(() => {
    setClosing(true);
    timerRef.current = setTimeout(onClose, 310);
  }, [onClose]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", handler);

    // Scrollbar yo'qolishi → layout shift'ni oldini olish
    const scrollbarW = window.innerWidth - document.documentElement.clientWidth;
    const prevOverflow = document.body.style.overflow;
    const prevPadRight = document.body.style.paddingRight;
    document.body.style.overflow = "hidden";
    if (scrollbarW > 0) document.body.style.paddingRight = `${scrollbarW}px`;

    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = prevOverflow;
      document.body.style.paddingRight = prevPadRight;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [close]);

  return { closing, close };
}
import type {
  DashboardStatsResponse,
  GenderStat,
  RegionStatItem,
  SessionStateResponse,
  StatGroup,
  StatsScope,
  TestSessionResponse,
  TestSessionSmenaResponse,
  ZoneStatItem,
} from "../interfaces";
import {
  exportSessionAbsenteesApi,
  exportSessionDashboardStatsApi,
  getOnlineUsersApi,
  getSessionDashboardStatsApi,
  getSessionStatesLookupApi,
  getTestSessionApi,
  getTestSessionsApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import Md3Select from "../components/Md3Select";
import { extractErrorMessage } from "../utils/errorMessage";

// Real-time polling kechikishi (session ready / state.key=4)
const POLL_INTERVAL_MS = 5000;

// "Hududiy vakil" role.key — desktop ilovadan kirib davomat oladigan operatorlar.
// Statistika kartasidagi "Onlinedagilar"/"Qurilmalar" shu role bo'yicha sanaladi.
const REP_ROLE_KEY = 4;

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

/**
 * Ishtirok etish (participation) ko'rsatkichlarini hisoblaydi:
 *  - `participated` ("Ishtirok etganlar")  = Kelganlar − Chetlatilganlar
 *  - `notParticipated` ("Ishtirok etmaganlar") = Umumiy − Ishtirok etganlar
 *    (ya'ni kelmaganlar + kirishda va test jarayonida chetlatilganlar).
 *
 * Har bir jins bo'yicha alohida hisoblanadi — chetlatilganlarning jins
 * taqsimoti `cheating.{male,female,unknown}` dan olinadi. Salbiy qiymatdan
 * himoya uchun 0 ga qisiladi.
 */
function deriveParticipation(g: StatGroup): {
  participated: GenderStat;
  notParticipated: GenderStat;
} {
  const sub = (a: number, b: number) => Math.max(0, a - b);
  const participated: GenderStat = {
    total: sub(g.attended.total, g.cheating.total),
    male: sub(g.attended.male, g.cheating.male),
    female: sub(g.attended.female, g.cheating.female),
    unknown: sub(g.attended.unknown, g.cheating.unknown),
  };
  const notParticipated: GenderStat = {
    total: sub(g.total.total, participated.total),
    male: sub(g.total.male, participated.male),
    female: sub(g.total.female, participated.female),
    unknown: sub(g.total.unknown, participated.unknown),
  };
  return { participated, notParticipated };
}

/** Axios/fetch bekor qilish (abort) xatosini aniqlaydi — polling eskirgan
 *  so'rovni bekor qilganda foydalanuvchiga xato ko'rsatmaslik uchun. */
function isAbortError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const e = err as { code?: string; name?: string; message?: string };
  return (
    e.code === "ERR_CANCELED" ||
    e.name === "CanceledError" ||
    e.name === "AbortError" ||
    e.message === "canceled"
  );
}

export default function StatisticsPage() {
  // Selektorlar
  const [states, setStates] = useState<SessionStateResponse[]>([]);
  const [statesLoading, setStatesLoading] = useState(true);
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null);

  const [sessions, setSessions] = useState<TestSessionResponse[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(
    null,
  );
  const [selectedSession, setSelectedSession] =
    useState<TestSessionResponse | null>(null);
  const [selectedSmenaId, setSelectedSmenaId] = useState<number | null>(null);
  // Statistika ko'lami: bitta smena / bitta kun / butun sessiya
  const [scope, setScope] = useState<StatsScope>("smena");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  // Stats holati
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [exporting, setExporting] = useState(false);
  // Kelmaganlar ro'yxati (.xlsx) eksporti — МАЪЛУМОТ jadvalidan alohida tugma
  const [exportingAbsentees, setExportingAbsentees] = useState(false);
  // Excel hisobot alifbosi — krill (default) yoki o'zbek lotin
  const [excelAlphabet, setExcelAlphabet] = useState<"cyrillic" | "latin">(
    "cyrillic",
  );
  // Excel viloyatlar tartibi — dtm (region raqami, default) | vm (k_number) |
  // iiv (s_number)
  const [excelOrder, setExcelOrder] = useState<"dtm" | "vm" | "iiv">("vm");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Polling qattiqligini oshiruvchi ref'lar:
  //  - inFlightRef: so'rov navbatда — yangi (silent) poll o'tkazib yuboriladi
  //    (overlap/pile-up oldini oladi).
  //  - abortRef: joriy so'rovni bekor qilish (eskirgan/unmount).
  const inFlightRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  // Viloyat card bosilganda — shu region zonalari modal'da ko'rsatiladi.
  // Polling natijasi bilan birga avtomatik yangilanishi uchun region_id'ni
  // saqlaymiz, modal render bo'lganda `stats.regions`'dan freshini topadi.
  const [openedRegionId, setOpenedRegionId] = useState<number | null>(null);
  const openedRegion =
    openedRegionId != null
      ? (stats?.regions.find((r) => r.region_id === openedRegionId) ?? null)
      : null;

  // Barcha viloyatlarni bitta jadval-modalda ko'rish
  const [showAllRegions, setShowAllRegions] = useState(false);

  // Tanlangan tartib (DTM/VM/IIV) bo'yicha viloyatlarni qayta saralash — Excel
  // hisoboti bilan bir xil kalitda. Kartalar joylashuvi ham shunga moslashadi.
  const orderedRegions = useMemo(() => {
    const regions = stats?.regions ?? [];
    const sortKey =
      excelOrder === "vm"
        ? (r: RegionStatItem) => r.region_k_number
        : excelOrder === "iiv"
          ? (r: RegionStatItem) => r.region_s_number
          : (r: RegionStatItem) => r.region_number;
    return [...regions].sort((a, b) => sortKey(a) - sortKey(b));
  }, [stats, excelOrder]);

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
        setSelectedDay(null);
        setScope("smena");
        setStats(null);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedSessionId]);

  // === Stats fetcher (qayta ishlatiluvchi) — scope bo'yicha ===
  const fetchStats = useCallback(
    async (
      sessionId: number,
      fetchScope: StatsScope,
      opts: { sessionSmenaId?: number | null; day?: string | null },
      silent = false,
    ) => {
      // Overlap guard — avvalgi (fon) poll hali tugamagan bo'lsa, yangi
      // silent pollni o'tkazib yuboramiz (so'rovlar ustma-ust yig'ilmasin).
      if (silent && inFlightRef.current) return;

      // Eskirgan so'rovni bekor qilamiz va yangisini boshlaymiz.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      inFlightRef.current = true;

      if (!silent) setStatsLoading(true);
      try {
        const data = await getSessionDashboardStatsApi(
          sessionId,
          {
            scope: fetchScope,
            sessionSmenaId: opts.sessionSmenaId,
            day: opts.day,
          },
          controller.signal,
        );
        setStats(data);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        // Bekor qilingan so'rov — jim o'tamiz (xato ko'rsatmaymiz).
        if (isAbortError(err)) return;
        setError(extractErrorMessage(err));
      } finally {
        // Faqat eng oxirgi ("egasi") so'rov holatni tiklaydi — o'rniga
        // yangisi kelgan bo'lsa (superseded), unga tegmaymiz.
        if (abortRef.current === controller) {
          abortRef.current = null;
          inFlightRef.current = false;
          if (!silent) setStatsLoading(false);
        }
      }
    },
    [],
  );

  // === Online presence — Hududiy vakil (role.key=4) operatorlar va ularning
  //     faol qurilmalari. `/admin/online-users` (aktiv refresh-token oilalari)
  //     dan olinadi; ruxsat yo'q/xato bo'lsa kartada "—" ko'rsatiladi. ===
  const [presence, setPresence] = useState<{
    onlineReps: number;
    activeDevices: number;
  } | null>(null);
  const presenceInFlightRef = useRef(false);

  const fetchPresence = useCallback(async () => {
    if (presenceInFlightRef.current) return; // overlap guard
    presenceInFlightRef.current = true;
    try {
      const res = await getOnlineUsersApi();
      const reps = res.users.filter((u) => u.role_key === REP_ROLE_KEY);
      const onlineReps = reps.filter((u) => u.is_online).length;
      const activeDevices = reps.reduce(
        (sum, u) => sum + u.online_device_count,
        0,
      );
      setPresence({ onlineReps, activeDevices });
    } catch {
      setPresence(null);
    } finally {
      presenceInFlightRef.current = false;
    }
  }, []);

  // === Tanlangan statistikani Excel (.xlsx) hisobotiga yuklab olish ===
  const handleExport = useCallback(async () => {
    if (!selectedSessionId || exporting) return;
    setExporting(true);
    try {
      await exportSessionDashboardStatsApi(selectedSessionId, {
        scope,
        sessionSmenaId: selectedSmenaId,
        day: selectedDay,
        alphabet: excelAlphabet,
        orderBy: excelOrder,
      });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setExporting(false);
    }
  }, [
    selectedSessionId,
    exporting,
    scope,
    selectedSmenaId,
    selectedDay,
    excelAlphabet,
    excelOrder,
  ]);

  // === Kelmaganlar ro'yxatini (.xlsx) yuklab olish ===
  const handleExportAbsentees = useCallback(async () => {
    if (!selectedSessionId || exportingAbsentees) return;
    setExportingAbsentees(true);
    try {
      await exportSessionAbsenteesApi(selectedSessionId, {
        scope,
        sessionSmenaId: selectedSmenaId,
        day: selectedDay,
      });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setExportingAbsentees(false);
    }
  }, [
    selectedSessionId,
    exportingAbsentees,
    scope,
    selectedSmenaId,
    selectedDay,
  ]);

  // === Smenalar va kunlar tanlovi uchun yordamchilar ===
  const smenas = selectedSession?.smenas ?? [];
  // Sessiyadagi noyob kunlar (sort qilingan) — "Kunlik" ko'rinish uchun
  const dayOptions = useMemo(() => {
    const set = new Set<string>();
    for (const sm of smenas) set.add(sm.day);
    return [...set].sort();
  }, [smenas]);

  // Tanlangan ko'lamga ko'ra so'rov yuborish mumkinmi (selektor to'liqmi)?
  const scopeReady =
    !!selectedSessionId &&
    (scope === "overall" ||
      (scope === "smena" && !!selectedSmenaId) ||
      (scope === "day" && !!selectedDay));

  // === Tanlov o'zgarganda statsni yuklash ===
  useEffect(() => {
    // Eski polling'ni to'xtatamiz
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    if (!selectedSessionId || !scopeReady) {
      // Joriy so'rovni bekor qilamiz — eskirgan javob tozalangan holatni
      // qayta yozib qo'ymasin.
      abortRef.current?.abort();
      setStats(null);
      return;
    }

    fetchStats(selectedSessionId, scope, {
      sessionSmenaId: selectedSmenaId,
      day: selectedDay,
    });
    fetchPresence();
  }, [
    selectedSessionId,
    scope,
    selectedSmenaId,
    selectedDay,
    scopeReady,
    fetchStats,
    fetchPresence,
  ]);

  // === Real-time polling — faqat session.state.key=4 bo'lsa ===
  // Tab fon(background)ga o'tganda polling to'xtaydi (ko'p admin sahifani ochiq
  // qoldiradi — bu backend yukini keskin kamaytiradi), qaytганда tiklanadi.
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!stats?.is_realtime || !selectedSessionId || !scopeReady) return;

    const poll = () => {
      fetchStats(
        selectedSessionId,
        scope,
        { sessionSmenaId: selectedSmenaId, day: selectedDay },
        true,
      );
      fetchPresence();
    };
    const startPolling = () => {
      if (pollRef.current) return;
      pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    };
    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        // Tab qaytganda darhol bir marta yangilaymiz, so'ng pollingni tiklaymiz.
        poll();
        startPolling();
      }
    };

    // Tab ko'rinib turgan bo'lsagina pollingni boshlaymiz.
    if (!document.hidden) startPolling();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      stopPolling();
    };
  }, [
    stats?.is_realtime,
    selectedSessionId,
    scope,
    selectedSmenaId,
    selectedDay,
    scopeReady,
    fetchStats,
    fetchPresence,
  ]);

  // === Unmount'da joriy so'rovni bekor qilish (osilib qolgan XHR qolmasin) ===
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // === Tanlangan status uchun rang (dropdownlarga visual accent) ===
  const selectedState = selectedStateId
    ? (states.find((st) => st.id === selectedStateId) ?? null)
    : null;
  const stateColor = getStateColor(selectedState?.key);

  return (
    <div>
      <div className="page-header">
        <div className="min-w-0">
          <h2 className="section-title">Davomat dashboard</h2>
          {/*<p className="section-subtitle">
            Ketma-ket tanlang: <b>1) Holat</b> → <b>2) Test sessiya</b> →{" "}
            <b>3) Ko'rinish</b> (smena / kunlik / umumiy) →{" "}
            <b>4) Kun va smena</b>. Sessiya tayyor holatida real vaqt
            statistikasi, aks holda oxirgi holat ko'rsatiladi.
          </p>*/}
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
          <button onClick={() => setError(null)} className="underline shrink-0">
            Yopish
          </button>
        </div>
      )}

      {/* Selektorlar — Material 3 surface. Aniq tartib: 1) Holat → 2) Test
          sessiya → 3) Ko'rinish → 4) Kun va smena. Keng ekranda bitta ixcham
          qatorda joylashadi — davomat cardlarini pastga surmaydi. */}
      <div className="glass-card p-3 sm:p-4 mb-3 sm:mb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-3.5 items-start">
          {/* 1 — Holat */}
          <StepField step={1} label="Holat" done={selectedStateId !== null}>
            <Md3Select
              value={selectedStateId != null ? String(selectedStateId) : ""}
              onChange={(v) => setSelectedStateId(v ? Number(v) : null)}
              disabled={statesLoading}
              clearable
              placeholder={statesLoading ? "Yuklanmoqda…" : "Tanlang"}
              valueColor={selectedStateId !== null ? stateColor.hex : undefined}
              options={states.map((st) => {
                const c = getStateColor(st.key);
                return {
                  value: String(st.id),
                  label: st.name,
                  color: c.hex,
                  dot: c.dot,
                };
              })}
            />
          </StepField>

          {/* 2 — Test sessiya */}
          <StepField
            step={2}
            label="Test sessiya"
            active={selectedStateId !== null}
            done={!!selectedSessionId}
          >
            <Md3Select
              value={selectedSessionId != null ? String(selectedSessionId) : ""}
              onChange={(v) => setSelectedSessionId(v ? Number(v) : null)}
              disabled={selectedStateId === null || sessionsLoading}
              clearable
              placeholder={
                selectedStateId === null
                  ? "Avval holatni tanlang"
                  : sessionsLoading
                    ? "Yuklanmoqda…"
                    : sessions.length === 0
                      ? "Sessiyalar yo'q"
                      : "Tanlang"
              }
              options={sessions.map((s) => {
                const c = getStateColor(s.test_state?.key);
                const testName = s.test?.name || s.name;
                return {
                  value: String(s.id),
                  label: testName,
                  sublabel: s.start_date,
                  color: c.hex,
                  dot: c.dot,
                };
              })}
            />
          </StepField>

          {/* 3 — Ko'rinish (scope) */}
          <StepField step={3} label="Ko'rinish" active={!!selectedSessionId}>
            <ScopeTabs
              value={scope}
              onChange={setScope}
              disabled={!selectedSessionId}
            />
          </StepField>

          {/* 4 — Kun va smena (ko'lamga bog'liq) */}
          <StepField
            step={4}
            label={
              scope === "day"
                ? "Kun"
                : scope === "overall"
                  ? "Ko'lam"
                  : "Kun va smena"
            }
            active={!!selectedSessionId}
            done={
              !!selectedSessionId &&
              (scope === "overall" || !!selectedSmenaId || !!selectedDay)
            }
          >
            {scope === "overall" ? (
              <div className="h-9 px-3 w-full flex items-center gap-2 rounded-xl border border-primary-200/70 dark:border-primary-800/40 bg-primary-50/70 dark:bg-primary-900/15 text-primary-700 dark:text-primary-300 font-semibold text-[13px]">
                <LayersIcon className="w-4 h-4 shrink-0" />
                <span className="truncate">
                  Butun sessiya · {dayOptions.length} ta kun
                </span>
              </div>
            ) : scope === "day" ? (
              <Md3Select
                value={selectedDay ?? ""}
                onChange={(v) => setSelectedDay(v || null)}
                disabled={!selectedSession || dayOptions.length === 0}
                placeholder={
                  dayOptions.length
                    ? "Kunni tanlang"
                    : "Avval sessiyani tanlang"
                }
                options={dayOptions.map((d) => ({
                  value: d,
                  label: formatDayOption(d, smenas),
                }))}
              />
            ) : (
              <Md3Select
                value={selectedSmenaId != null ? String(selectedSmenaId) : ""}
                onChange={(v) => setSelectedSmenaId(v ? Number(v) : null)}
                disabled={!selectedSession || smenas.length === 0}
                placeholder={
                  smenas.length ? "Tanlang" : "Avval sessiyani tanlang"
                }
                options={smenas.map((sm) => ({
                  value: String(sm.id),
                  label: formatSmenaOption(sm),
                }))}
              />
            )}
          </StepField>
        </div>

        {/* Tanlangan statuslar — kompakt chiplar qatori (faqat tegishlilarini ko'rsatamiz) */}
        {(selectedState || (stats && stats.session_state_key != null)) && (
          <div className="flex flex-wrap items-center gap-1.5 mt-3.5 sm:mt-4 pt-3 border-t border-gray-100 dark:border-slate-700/50 text-[10.5px]">
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
      {selectedSessionId && !scopeReady && (
        <EmptyHint
          text={
            scope === "day"
              ? "Endi kunni tanlang"
              : "Endi kun va smenani tanlang"
          }
        />
      )}

      {/* Stats */}
      {scopeReady && statsLoading && !stats && <PageLoader />}

      {stats && (
        <>
          {/* Ko'lam konteksti — qaysi ko'rinish ko'rsatilmoqda + Excel eksport */}
          <div className="flex flex-wrap items-center gap-2 mb-2 sm:mb-2.5">
            <ScopeBadge scope={stats.scope} />
            <span className="text-[12px] sm:text-[12.5px] font-medium text-gray-600 dark:text-slate-300">
              {scopeContextLabel(stats)}
            </span>
            <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
              <OrderToggle
                value={excelOrder}
                onChange={setExcelOrder}
                disabled={exporting}
              />
              <AlphabetToggle
                value={excelAlphabet}
                onChange={setExcelAlphabet}
                disabled={exporting}
              />
              <button
                type="button"
                onClick={handleExport}
                disabled={exporting}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-full text-[12.5px] font-semibold bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed text-white shadow-sm transition-colors"
                title="Tanlangan statistikani Excel (.xlsx) hisobotiga yuklab olish"
              >
                {exporting ? (
                  <>
                    <Spinner className="w-3.5 h-3.5" />
                    <span>Tayyorlanmoqda…</span>
                  </>
                ) : (
                  <>
                    <DownloadIcon className="w-3.5 h-3.5" />
                    <span>Excel</span>
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleExportAbsentees}
                disabled={exportingAbsentees}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-full text-[12.5px] font-semibold border border-emerald-600 text-emerald-700 hover:bg-emerald-600 hover:text-white hover:border-emerald-600 disabled:opacity-60 disabled:cursor-not-allowed bg-transparent shadow-sm transition-colors dark:text-emerald-400 dark:border-emerald-500 dark:hover:bg-emerald-500 dark:hover:text-white"
                title="Tanlangan ko'lam uchun kelmaganlar ro'yxatini Excel (.xlsx) ga yuklab olish (sana → region → zone → smena → guruh tartibida)"
              >
                {exportingAbsentees ? (
                  <>
                    <Spinner className="w-3.5 h-3.5" />
                    <span>Tayyorlanmoqda…</span>
                  </>
                ) : (
                  <>
                    <DownloadIcon className="w-3.5 h-3.5" />
                    <span>Kelmaganlar</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 4 ta asosiy card — kengroq MD3 surface */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-2.5 sm:gap-3.5 mb-3 sm:mb-4">
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

          {/* Umumiy ko'rsatkichlar — davomat darajasi + tahliliy ma'lumotlar */}
          <OverviewPanel stats={stats} presence={presence} />

          {/* Region cardlari */}
          <div className="flex items-center justify-between gap-3 mb-2 sm:mb-3">
            <span className="text-[12px] sm:text-[12.5px] font-medium text-gray-600 dark:text-slate-300">
              Viloyatlar bo'yicha taqsimot - {stats.regions.length} ta viloyat
            </span>
            {stats.regions.length > 0 && (
              <button
                type="button"
                onClick={() => setShowAllRegions(true)}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-full text-[12.5px] font-semibold text-primary-700 dark:text-primary-300 bg-primary-50 hover:bg-primary-100 dark:bg-primary-900/30 dark:hover:bg-primary-900/50 ring-1 ring-primary-200/60 dark:ring-primary-700/50 transition-colors shrink-0"
                title="Barcha viloyatlarni bitta jadvalda ko'rish"
              >
                <TableIcon className="w-4 h-4" />
                <span>Hammasini ko'rish</span>
              </button>
            )}
          </div>

          {stats.regions.length === 0 ? (
            <EmptyHint text="Bu sessiya/smena uchun talabgorlar topilmadi" />
          ) : (
            <RegionGrid
              regions={orderedRegions}
              orderKey={excelOrder}
              onRegionClick={(r) => setOpenedRegionId(r.region_id)}
            />
          )}
        </>
      )}

      {/* Region zone breakdown modali */}
      {openedRegion && (
        <RegionZonesModal
          region={openedRegion}
          orderKey={excelOrder}
          onClose={() => setOpenedRegionId(null)}
        />
      )}

      {/* Barcha viloyatlar — bitta jadval modali */}
      {showAllRegions && stats && (
        <AllRegionsModal
          regions={orderedRegions}
          summary={stats.summary}
          contextLabel={scopeContextLabel(stats)}
          orderKey={excelOrder}
          onClose={() => setShowAllRegions(false)}
        />
      )}
    </div>
  );
}

/* ============== Sub-components ============== */

/**
 * Qadamli maydon — raqamli badge + label + boshqaruv elementi.
 * Tanlash tartibini (1→2→3→4) ko'z bilan aniq ko'rsatadi. MD3 uslubida,
 * yorug' rejimda yumshoq, ammo yetarli kontrastli ranglar bilan.
 */
function StepField({
  step,
  label,
  children,
  active = true,
  done = false,
}: {
  step: number;
  label: string;
  children: React.ReactNode;
  active?: boolean;
  done?: boolean;
}) {
  // Badge holati: bajarilgan (yashil) → faol (primary) → kutilmoqda (kulrang)
  const badgeCls = done
    ? "bg-emerald-500 text-white"
    : active
      ? "bg-primary-600 text-white shadow-sm shadow-primary-600/25"
      : "bg-gray-200 text-gray-400 dark:bg-slate-700/60 dark:text-slate-500";
  const labelCls = active
    ? "text-gray-800 dark:text-slate-100"
    : "text-gray-400 dark:text-slate-500";

  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <span
          className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold leading-none transition-colors ${badgeCls}`}
          aria-hidden
        >
          {done ? (
            <svg
              className="w-2.5 h-2.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3.5}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : (
            step
          )}
        </span>
        <span className={`text-[12px] font-semibold leading-none ${labelCls}`}>
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

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

/* ============== Scope (ko'rinish) tanlovi ============== */

const SCOPE_TABS: {
  key: StatsScope;
  label: string;
  icon: (cls: string) => React.ReactNode;
}[] = [
  { key: "smena", label: "Smena", icon: (c) => <ClockIcon className={c} /> },
  { key: "day", label: "Kunlik", icon: (c) => <CalendarIcon className={c} /> },
  {
    key: "overall",
    label: "Umumiy",
    icon: (c) => <LayersIcon className={c} />,
  },
];

/**
 * Material 3 uslubidagi segmented button — statistika ko'lamini tanlash:
 * bitta smena / bitta kun / butun sessiya.
 */
function ScopeTabs({
  value,
  onChange,
  disabled = false,
}: {
  value: StatsScope;
  onChange: (s: StatsScope) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="tablist"
      aria-label="Statistika ko'rinishi"
      className={`inline-flex w-full rounded-xl bg-gray-100 dark:bg-slate-800/60 p-0.5 ring-1 ring-gray-200/70 dark:ring-slate-700/60 transition-opacity ${
        disabled ? "opacity-50 pointer-events-none" : ""
      }`}
    >
      {SCOPE_TABS.map((t) => {
        const active = value === t.key;
        return (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active}
            disabled={disabled}
            onClick={() => onChange(t.key)}
            className={`flex-1 inline-flex items-center justify-center gap-1 px-1.5 h-8 rounded-[10px] text-[12px] font-semibold transition-all duration-200 ${
              active
                ? "bg-white dark:bg-slate-900 text-primary-700 dark:text-primary-300 shadow-sm ring-1 ring-primary-200/60 dark:ring-primary-700/50"
                : "text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
            }`}
          >
            {t.icon("w-3.5 h-3.5 shrink-0")}
            <span>{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Joriy ko'lamni bildiruvchi rangli chip (cardlar ustida). */
function ScopeBadge({ scope }: { scope: StatsScope }) {
  const meta = SCOPE_TABS.find((t) => t.key === scope) ?? SCOPE_TABS[0];
  const tone =
    scope === "overall"
      ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
      : scope === "day"
        ? "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
        : "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 h-7 rounded-full text-[11.5px] font-bold ${tone}`}
    >
      {meta.icon("w-3.5 h-3.5")}
      {meta.label}
    </span>
  );
}

/**
 * Excel hisobot alifbosini tanlash — krill yoki o'zbek lotin.
 * ScopeTabs bilan bir xil MD3 segmented uslubda, ammo ixchamroq.
 */
function AlphabetToggle({
  value,
  onChange,
  disabled,
}: {
  value: "cyrillic" | "latin";
  onChange: (a: "cyrillic" | "latin") => void;
  disabled?: boolean;
}) {
  const options: { key: "cyrillic" | "latin"; label: string }[] = [
    { key: "cyrillic", label: "Кирилл" },
    { key: "latin", label: "Lotin" },
  ];
  return (
    <div
      role="group"
      aria-label="Excel hisobot alifbosi"
      title="Excel matnlari alifbosi"
      className="inline-flex rounded-full bg-gray-100 dark:bg-slate-800/60 p-0.5 ring-1 ring-gray-200/70 dark:ring-slate-700/60"
    >
      {options.map((o) => {
        const active = value === o.key;
        return (
          <button
            key={o.key}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => onChange(o.key)}
            className={`inline-flex items-center justify-center px-2.5 h-7 rounded-full text-[11.5px] font-semibold transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed ${
              active
                ? "bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-300 shadow-sm ring-1 ring-emerald-200/60 dark:ring-emerald-700/50"
                : "text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Excel hisobotidagi viloyatlar tartibini tanlash — DTM (region raqami),
 * VM (k_number) yoki IIV (s_number) ketma-ketligida. AlphabetToggle bilan bir
 * xil MD3 segmented uslubda, har tugmada tartiblash izohi (title) bilan.
 */
function OrderToggle({
  value,
  onChange,
  disabled,
}: {
  value: "dtm" | "vm" | "iiv";
  onChange: (o: "dtm" | "vm" | "iiv") => void;
  disabled?: boolean;
}) {
  const options: {
    key: "dtm" | "vm" | "iiv";
    label: string;
    title: string;
  }[] = [
    { key: "vm", label: "VM", title: "K-raqami (k_number) tartibida" },
    { key: "dtm", label: "DTM", title: "Viloyat raqami tartibida" },
    { key: "iiv", label: "IIV", title: "S-raqami (s_number) tartibida" },
  ];
  return (
    <div
      role="group"
      aria-label="Excel hisobotida viloyatlar tartibi"
      title="Viloyatlar tartibi"
      className="inline-flex rounded-full bg-gray-100 dark:bg-slate-800/60 p-0.5 ring-1 ring-gray-200/70 dark:ring-slate-700/60"
    >
      {options.map((o) => {
        const active = value === o.key;
        return (
          <button
            key={o.key}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => onChange(o.key)}
            title={o.title}
            className={`inline-flex items-center justify-center px-2.5 h-7 rounded-full text-[11.5px] font-semibold transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed ${
              active
                ? "bg-white dark:bg-slate-900 text-primary-700 dark:text-primary-300 shadow-sm ring-1 ring-primary-200/60 dark:ring-primary-700/50"
                : "text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

type Variant = "primary" | "success" | "warning" | "danger";

const VARIANT_STYLES: Record<
  Variant,
  { bg: string; ring: string; valueColor: string; iconBg: string; blob: string }
> = {
  primary: {
    bg: "bg-gradient-to-br from-primary-50 to-white dark:from-primary-900/20 dark:to-slate-900",
    ring: "ring-primary-200/60 dark:ring-primary-800/40",
    valueColor: "text-primary-800 dark:text-primary-200",
    iconBg:
      "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300",
    blob: "bg-primary-400",
  },
  success: {
    bg: "bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/20 dark:to-slate-900",
    ring: "ring-emerald-200/60 dark:ring-emerald-800/40",
    valueColor: "text-emerald-800 dark:text-emerald-200",
    iconBg:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    blob: "bg-emerald-400",
  },
  warning: {
    bg: "bg-gradient-to-br from-amber-50 to-white dark:from-amber-900/20 dark:to-slate-900",
    ring: "ring-amber-200/60 dark:ring-amber-800/40",
    valueColor: "text-amber-800 dark:text-amber-200",
    iconBg:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    blob: "bg-amber-400",
  },
  danger: {
    bg: "bg-gradient-to-br from-red-50 to-white dark:from-red-900/20 dark:to-slate-900",
    ring: "ring-red-200/60 dark:ring-red-800/40",
    valueColor: "text-red-800 dark:text-red-200",
    iconBg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
    blob: "bg-red-400",
  },
};

function SummaryCard({
  title,
  breakdown,
  icon,
  variant,
  extra,
}: {
  title: string;
  breakdown: GenderStat;
  icon: React.ReactNode;
  variant: Variant;
  /** Ixtiyoriy qo'shimcha ko'rsatkich — jins chiplari yonida chiqadi. */
  extra?: React.ReactNode;
}) {
  const s = VARIANT_STYLES[variant];
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl ring-1 ${s.bg} ${s.ring} p-3.5 sm:p-4 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300`}
    >
      {/* Dekorativ yumshoq rangli nur — MD3 chuqurlik hissi */}
      <div
        className={`pointer-events-none absolute -right-6 -top-9 w-28 h-28 rounded-full blur-2xl opacity-20 dark:opacity-[0.18] ${s.blob}`}
        aria-hidden
      />
      {/* Header: icon chip + sarlavha */}
      <div className="relative flex items-center gap-2.5 mb-3 sm:mb-3.5">
        <div
          className={`w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center shrink-0 shadow-sm ring-1 ring-white/40 dark:ring-white/5 ${s.iconBg}`}
        >
          {icon}
        </div>
        <p className="min-w-0 flex-1 text-[12px] sm:text-[13px] font-semibold text-gray-600 dark:text-slate-300 leading-snug">
          {title}
        </p>
      </div>
      {/* Asosiy son */}
      <p
        className={`relative text-3xl sm:text-[2.5rem] font-extrabold tabular-nums leading-none tracking-tight ${s.valueColor}`}
      >
        {breakdown.total.toLocaleString("uz-UZ")}
      </p>
      {/* Gender breakdown */}
      <div className="relative mt-3 sm:mt-3.5 flex flex-wrap items-center gap-1.5 text-[11px] sm:text-[11.5px]">
        <GenderChip gender="male" count={breakdown.male} />
        <GenderChip gender="female" count={breakdown.female} />
        {breakdown.unknown > 0 && (
          <GenderChip gender="unknown" count={breakdown.unknown} />
        )}
        {extra}
      </div>
    </div>
  );
}

function CheatingCard({ cheating }: { cheating: StatGroup["cheating"] }) {
  const s = VARIANT_STYLES.danger;
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl ring-1 ${s.bg} ${s.ring} p-3.5 sm:p-4 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300`}
    >
      {/* Dekorativ yumshoq rangli nur */}
      <div
        className={`pointer-events-none absolute -right-6 -top-9 w-28 h-28 rounded-full blur-2xl opacity-20 dark:opacity-[0.18] ${s.blob}`}
        aria-hidden
      />
      {/* Header: icon chip + sarlavha */}
      <div className="relative flex items-center gap-2.5 mb-3 sm:mb-3.5">
        <div
          className={`w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center shrink-0 shadow-sm ring-1 ring-white/40 dark:ring-white/5 ${s.iconBg}`}
        >
          <ShieldIcon />
        </div>
        <p className="min-w-0 flex-1 text-[12px] sm:text-[13px] font-semibold text-gray-600 dark:text-slate-300 leading-snug">
          Chetlatilgan
        </p>
      </div>
      {/* Asosiy son */}
      <p
        className={`relative text-3xl sm:text-[2.5rem] font-extrabold tabular-nums leading-none tracking-tight ${s.valueColor}`}
      >
        {cheating.total.toLocaleString("uz-UZ")}
      </p>
      {/* Joy bo'yicha breakdown */}
      <div className="relative mt-3 sm:mt-3.5 flex flex-wrap items-center gap-1.5 text-[11px] sm:text-[11.5px]">
        <span
          title="Binoga kirishda"
          className="inline-flex items-center gap-1 px-2 py-1 rounded-lg font-medium leading-none bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
        >
          <KeyIcon className="w-3.5 h-3.5 shrink-0 opacity-90" />
          <span className="tabular-nums font-bold">
            {cheating.at_entry.toLocaleString("uz-UZ")}
          </span>
        </span>
        <span
          title="Test jarayonida"
          className="inline-flex items-center gap-1 px-2 py-1 rounded-lg font-medium leading-none bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
        >
          <BookIcon className="w-3.5 h-3.5 shrink-0 opacity-90" />
          <span className="tabular-nums font-bold">
            {cheating.during_test.toLocaleString("uz-UZ")}
          </span>
        </span>
      </div>
    </div>
  );
}

/* ============== Umumiy ko'rsatkichlar paneli ============== */

/** Davomat foiziga qarab semantik rang (region kartlari bilan bir xil chegara). */
function attendanceTone(pct: number): {
  ring: string;
  text: string;
  hex: string;
} {
  if (pct >= 75)
    return {
      ring: "from-emerald-400 to-emerald-600",
      text: "text-emerald-700 dark:text-emerald-300",
      hex: "#10b981",
    };
  if (pct >= 50)
    return {
      ring: "from-amber-400 to-amber-500",
      text: "text-amber-700 dark:text-amber-300",
      hex: "#f59e0b",
    };
  return {
    ring: "from-red-400 to-red-500",
    text: "text-red-700 dark:text-red-300",
    hex: "#ef4444",
  };
}

/**
 * MD3 uslubidagi donut (circular progress) — davomat darajasini ko'rsatadi.
 * Markazda foiz, atrofida rangli yoy. SVG `stroke-dasharray` bilan chiziladi.
 */
function AttendanceDonut({ pct }: { pct: number }) {
  const size = 140;
  const stroke = 13;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (Math.min(100, Math.max(0, pct)) / 100) * circ;
  const tone = attendanceTone(pct);
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Davomat darajasi: ${pct}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-gray-100 dark:stroke-slate-700/50"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke={tone.hex}
          strokeDasharray={`${dash} ${circ}`}
          style={{
            transition: "stroke-dasharray 700ms cubic-bezier(0.4,0,0.2,1)",
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={`text-2xl sm:text-[28px] font-extrabold tabular-nums leading-none ${tone.text}`}
        >
          {pct}%
        </span>
        <span className="mt-1 text-[10.5px] font-semibold text-gray-500 dark:text-slate-400">
          Davomat
        </span>
      </div>
    </div>
  );
}

/** Kichik tahliliy plitka — icon + qiymat + label. */
function InsightTile({
  icon,
  value,
  label,
  accent = "text-gray-900 dark:text-white",
}: {
  icon: React.ReactNode;
  value: React.ReactNode;
  label: string;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl bg-gray-50/80 dark:bg-slate-800/50 ring-1 ring-gray-100 dark:ring-slate-700/50 px-3 py-2.5">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-white dark:bg-slate-900/60 ring-1 ring-gray-200/70 dark:ring-slate-700/60 text-gray-500 dark:text-slate-300">
        {icon}
      </div>
      <div className="min-w-0">
        <p className={`text-lg font-bold tabular-nums leading-none ${accent}`}>
          {value}
        </p>
        <p className="mt-1 text-[11px] font-medium text-gray-500 dark:text-slate-400 truncate leading-none">
          {label}
        </p>
      </div>
    </div>
  );
}

/** Eng faol / eng past davomatli viloyatni ko'rsatuvchi qator. */
function RegionHighlight({
  label,
  region,
  up,
}: {
  label: string;
  region: { name: string; number: number; pct: number } | null;
  up: boolean;
}) {
  const tone = region ? attendanceTone(region.pct) : null;
  return (
    <div className="flex items-center gap-2.5 rounded-xl bg-gray-50/80 dark:bg-slate-800/50 ring-1 ring-gray-100 dark:ring-slate-700/50 px-3 py-2.5">
      <div
        className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
          up
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
            : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
        }`}
      >
        {up ? (
          <TrendUpIcon className="w-4 h-4" />
        ) : (
          <TrendDownIcon className="w-4 h-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[10.5px] font-semibold text-gray-400 dark:text-slate-500 leading-none">
          {label}
        </p>
        <p className="mt-1 text-[12.5px] font-bold text-gray-800 dark:text-slate-100 truncate leading-tight">
          {region ? region.name || `#${region.number}` : "—"}
        </p>
      </div>
      {region && (
        <span
          className={`shrink-0 text-sm font-bold tabular-nums ${tone!.text}`}
        >
          {region.pct}%
        </span>
      )}
    </div>
  );
}

/**
 * Umumiy ko'rsatkichlar paneli — davomat darajasi (donut), online operatorlar
 * (Hududiy vakil) va faol qurilmalar soni (`presence`), viloyat/bino soni, jins
 * taqsimoti hamda eng faol/past davomatli viloyatlar.
 */
function OverviewPanel({
  stats,
  presence,
}: {
  stats: DashboardStatsResponse;
  presence: { onlineReps: number; activeDevices: number } | null;
}) {
  const t = stats.summary.total.total;
  // Donut/legend endi ISHTIROK ko'rsatkichini ko'rsatadi:
  //   Ishtirok etdi = Kelganlar − Chetlatilganlar
  //   Qatnashmadi   = Umumiy − Ishtirok etdi (kelmaganlar + chetlatilganlar)
  const { participated, notParticipated } = deriveParticipation(stats.summary);
  const participatedTotal = participated.total;
  const notParticipatedTotal = notParticipated.total;
  const rate = t > 0 ? Math.round((participatedTotal / t) * 1000) / 10 : 0;

  const buildings = stats.regions.reduce(
    (sum, r) => sum + (r.zones?.length ?? 0),
    0,
  );
  const regionsCount = stats.regions.length;

  const male = stats.summary.total.male;
  const female = stats.summary.total.female;
  const unknown = stats.summary.total.unknown;
  const pctOf = (n: number) => (t > 0 ? (n / t) * 100 : 0);

  // Davomat foizi bo'yicha viloyatlar reytingi (faqat talabgori bor viloyatlar)
  const ranked = stats.regions
    .filter((r) => r.stats.total.total > 0)
    .map((r) => ({
      name: r.region_name,
      number: r.region_number,
      pct:
        Math.round((r.stats.attended.total / r.stats.total.total) * 1000) / 10,
    }))
    .sort((a, b) => b.pct - a.pct);
  const best = ranked.length ? ranked[0] : null;
  const worst = ranked.length ? ranked[ranked.length - 1] : null;

  return (
    <div className="glass-card p-4 sm:p-5 mb-3 sm:mb-4">
      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-5 lg:gap-7 items-center">
        {/* Donut + Keldi/Kelmadi legend */}
        <div className="flex items-center justify-center gap-4 sm:gap-5">
          <AttendanceDonut pct={rate} />
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
              <div>
                <p className="text-base font-bold tabular-nums text-gray-900 dark:text-white leading-none">
                  {participatedTotal.toLocaleString("uz-UZ")}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-none mt-0.5">
                  Qatnashdi
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0" />
              <div>
                <p className="text-base font-bold tabular-nums text-gray-900 dark:text-white leading-none">
                  {notParticipatedTotal.toLocaleString("uz-UZ")}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-none mt-0.5">
                  Qatnashmadi
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-gray-300 dark:bg-slate-600 shrink-0" />
              <div>
                <p className="text-base font-bold tabular-nums text-gray-900 dark:text-white leading-none">
                  {t.toLocaleString("uz-UZ")}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-none mt-0.5">
                  Jami
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tahliliy plitkalar */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3 gap-2.5 sm:gap-3">
          <InsightTile
            icon={<OnlineIcon />}
            value={
              presence ? presence.onlineReps.toLocaleString("uz-UZ") : "—"
            }
            label="Onlinedagilar"
            accent="text-emerald-700 dark:text-emerald-300"
          />
          <InsightTile
            icon={<DeviceIcon />}
            value={
              presence ? presence.activeDevices.toLocaleString("uz-UZ") : "—"
            }
            label="Qurilmalar"
            accent="text-sky-700 dark:text-sky-300"
          />
          <InsightTile
            icon={<BuildingIcon className="w-5 h-5" />}
            value={buildings.toLocaleString("uz-UZ")}
            label="Binolar"
          />
          <RegionHighlight label="Eng faol viloyat" region={best} up />
          <RegionHighlight label="Eng past davomat" region={worst} up={false} />
          <InsightTile
            icon={<MapPinIcon className="w-5 h-5" />}
            value={regionsCount.toLocaleString("uz-UZ")}
            label="Viloyatlar"
          />
        </div>
      </div>

      {/* Jins taqsimoti — stacked bar */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700/50">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[12px] font-semibold text-gray-600 dark:text-slate-300">
            Jins taqsimoti
          </span>
          <span className="flex items-center gap-3 text-[11px] font-medium">
            <span className="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400">
              <MaleIcon className="w-3.5 h-3.5" />
              {male.toLocaleString("uz-UZ")} ({Math.round(pctOf(male))}%)
            </span>
            <span className="inline-flex items-center gap-1 text-pink-600 dark:text-pink-400">
              <FemaleIcon className="w-3.5 h-3.5" />
              {female.toLocaleString("uz-UZ")} ({Math.round(pctOf(female))}%)
            </span>
            {unknown > 0 && (
              <span className="inline-flex items-center gap-1 text-gray-400">
                ? {unknown.toLocaleString("uz-UZ")}
              </span>
            )}
          </span>
        </div>
        <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700/50">
          <div
            className="h-full bg-sky-500 transition-[width] duration-700"
            style={{ width: `${pctOf(male)}%` }}
          />
          <div
            className="h-full bg-pink-500 transition-[width] duration-700"
            style={{ width: `${pctOf(female)}%` }}
          />
          {unknown > 0 && (
            <div
              className="h-full bg-gray-300 dark:bg-slate-500 transition-[width] duration-700"
              style={{ width: `${pctOf(unknown)}%` }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

type Gender = "male" | "female" | "unknown";

const GENDER_META: Record<
  Gender,
  {
    cls: string;
    title: string;
    Icon: (p: { className?: string }) => React.ReactNode;
  }
> = {
  male: {
    cls: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
    title: "Erkak",
    Icon: MaleIcon,
  },
  female: {
    cls: "bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300",
    title: "Ayol",
    Icon: FemaleIcon,
  },
  unknown: {
    cls: "bg-slate-100 text-slate-600 dark:bg-slate-700/60 dark:text-slate-300",
    title: "Jinsi noma'lum",
    Icon: ({ className }) => (
      <span className={`font-bold leading-none ${className ?? ""}`}>?</span>
    ),
  },
};

/** Erkak belgisi (Mars ♂) — doira + yuqori-o'ngga strelka. */
function MaleIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="10" cy="14" r="6" />
      <line x1="14.5" y1="9.5" x2="20" y2="4" />
      <polyline points="15 4 20 4 20 9" />
    </svg>
  );
}

/** Ayol belgisi (Venus ♀) — doira + pastdagi xoch. */
function FemaleIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="8" r="6" />
      <line x1="12" y1="14" x2="12" y2="22" />
      <line x1="9" y1="19" x2="15" y2="19" />
    </svg>
  );
}

function GenderChip({ gender, count }: { gender: Gender; count: number }) {
  const m = GENDER_META[gender];
  return (
    <span
      title={m.title}
      aria-label={`${m.title}: ${count}`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md font-medium leading-none ${m.cls}`}
    >
      <m.Icon className="w-3 h-3 shrink-0 opacity-90" />
      <span className="tabular-nums font-bold">
        {count.toLocaleString("uz-UZ")}
      </span>
    </span>
  );
}

/** Tanlangan tartib (DTM/VM/IIV) bo'yicha viloyatning ko'rsatiladigan raqami. */
function regionDisplayNumber(
  r: RegionStatItem,
  orderKey: "dtm" | "vm" | "iiv",
): number {
  if (orderKey === "vm") return r.region_k_number;
  if (orderKey === "iiv") return r.region_s_number;
  return r.region_number;
}

/**
 * RegionGrid — viloyatlarni MD3 uslubidagi 2-ustunli vertikal tartiblangan
 * gridda chiqaradi. Region.number tartibi vertikal yo'naltirilgan:
 *  - Chap ustun: 1..N/2
 *  - O'ng ustun: N/2+1..N
 *
 * Mobile (<lg) da bitta ustun bo'ladi va tabiiy ravishda 1..N tartib saqlanadi.
 */
function RegionGrid({
  regions,
  onRegionClick,
  orderKey,
}: {
  regions: RegionStatItem[];
  onRegionClick: (r: RegionStatItem) => void;
  orderKey: "dtm" | "vm" | "iiv";
}) {
  const mid = Math.ceil(regions.length / 2);
  const leftCol = regions.slice(0, mid);
  const rightCol = regions.slice(mid);

  const renderColumn = (col: RegionStatItem[]) => (
    <div className="flex flex-col gap-2.5 sm:gap-3">
      {col.map((r) => (
        <RegionCard
          key={r.region_id}
          item={r}
          orderKey={orderKey}
          onClick={() => onRegionClick(r)}
        />
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
function RegionCard({
  item,
  onClick,
  orderKey = "dtm",
}: {
  item: RegionStatItem;
  onClick?: () => void;
  orderKey?: "dtm" | "vm" | "iiv";
}) {
  // Badge'da ko'rsatiladigan raqam — tanlangan tartibga (DTM/VM/IIV) mos
  const displayNumber = regionDisplayNumber(item, orderKey);
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

  const zoneCount = item.zones?.length ?? 0;

  return (
    <article
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={`glass-card p-2.5 sm:p-3 hover:-translate-y-0.5 transition-all duration-200 group ${
        onClick
          ? "cursor-pointer hover:shadow-md hover:ring-1 hover:ring-primary-200 dark:hover:ring-primary-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
          : ""
      }`}
      aria-label={`Region ${item.region_number}: ${item.region_name}${
        onClick ? " — binolar bo'yicha taqsimotni ochish" : ""
      }`}
    >
      {/* Header: badge + nom + davomat % */}
      <header className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* MD3 filled-tonal badge */}
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 text-white font-bold flex items-center justify-center shadow-sm shadow-primary-500/25 ring-1 ring-white/20 shrink-0">
            <span className="text-[12px] tabular-nums leading-none">
              {displayNumber}
            </span>
          </div>
          <p
            className="min-w-0 truncate text-[13px] sm:text-sm font-semibold text-gray-900 dark:text-white leading-tight"
            title={item.region_name || `Region #${item.region_number}`}
          >
            {item.region_name || `Region #${item.region_number}`}
          </p>
          {item.is_have_part && (
            <span
              className="shrink-0 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[9.5px] font-bold bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300 ring-1 ring-violet-200/60 dark:ring-violet-800/40"
              title="Bo'limlarga bo'lingan viloyat — binolar bo'lim bo'yicha ajratiladi"
            >
              <LayersIcon className="w-3 h-3" />
              Qo'shimcha hududga ega
            </span>
          )}
        </div>

        {/* Davomat foizi — semantik rangda */}
        <span
          className={`shrink-0 text-base sm:text-[17px] font-bold tabular-nums leading-none ${percentText}`}
        >
          {attendancePercent}%
        </span>
      </header>

      {/* Linear progress — MD3 thin track */}
      <div
        className="h-1 rounded-full bg-gray-100 dark:bg-slate-700/50 overflow-hidden mb-2"
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
      <div className="grid grid-cols-4 gap-1 sm:gap-1.5">
        <MiniStat
          label="Umumiy"
          breakdown={item.stats.total}
          accent="primary"
        />
        <MiniStat
          label="Kelgan"
          breakdown={item.stats.attended}
          accent="success"
        />
        <MiniStat
          label="Kelmagan"
          breakdown={item.stats.not_attended}
          accent="warning"        />
        <MiniCheating cheating={item.stats.cheating} />
      </div>

      {/* Footer — binolar soni + "ko'rsatish" affordance (faqat clickable bo'lsa) */}
      {onClick && (
        <div className="mt-2 flex items-center justify-between text-[11px] text-gray-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1">
            <BuildingIcon className="w-3.5 h-3.5" />
            <span>
              {zoneCount > 0 ? `${zoneCount} ta bino` : "Bino ma'lumotsiz"}
            </span>
          </span>
          <span className="inline-flex items-center gap-0.5 font-medium text-primary-600 dark:text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity">
            Batafsil
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </span>
        </div>
      )}
    </article>
  );
}

/** Stat tile o'lchami — 3 bosqichli ierarxiya (viloyat → hudud → bino). */
type MiniSize = "sm" | "md" | "lg";
const MINI_SIZE: Record<
  MiniSize,
  { box: string; label: string; value: string; gender: string; gicon: string }
> = {
  sm: {
    box: "px-1.5 py-1",
    label: "text-[9px] sm:text-[9.5px]",
    value: "text-[13px] sm:text-sm",
    gender: "text-[9px] sm:text-[9.5px]",
    gicon: "w-2.5 h-2.5",
  },
  md: {
    box: "px-1.5 py-1 sm:px-2 sm:py-1.5",
    label: "text-[10px] sm:text-[10.5px]",
    value: "text-[15px] sm:text-lg",
    gender: "text-[10px] sm:text-[10.5px]",
    gicon: "w-3 h-3",
  },
  lg: {
    box: "px-2.5 py-2 sm:px-3 sm:py-2.5",
    label: "text-[11px] sm:text-xs",
    value: "text-xl sm:text-2xl",
    gender: "text-[11px]",
    gicon: "w-3.5 h-3.5",
  },
};

/** MD3 tonal-surface stat tile (Umumiy / Kelgan / Kelmagan). */
function MiniStat({
  label,
  breakdown,
  accent,
  size = "md",
  extra,
}: {
  label: string;
  breakdown: GenderStat;
  accent: Variant;
  size?: MiniSize;
  /** Jins qatori yonida chiqadigan ixtiyoriy qo'shimcha ko'rsatkich. */
  extra?: React.ReactNode;
}) {
  const s = VARIANT_STYLES[accent];
  const z = MINI_SIZE[size];
  return (
    <div
      className={`rounded-lg ring-1 ${s.bg} ${s.ring} ${z.box} transition-shadow duration-200 hover:shadow-sm`}
    >
      <p
        className={`font-semibold text-gray-600 dark:text-slate-300 leading-tight min-h-[2.4em] ${z.label}`}
      >
        {label}
      </p>
      <p
        className={`font-bold tabular-nums leading-tight mt-0.5 ${z.value} ${s.valueColor}`}
      >
        {breakdown.total.toLocaleString("uz-UZ")}
      </p>
      <div
        className={`flex flex-wrap items-center gap-x-1.5 gap-y-0.5 mt-0.5 text-gray-600 dark:text-slate-300 leading-none ${z.gender}`}
      >
        <span
          className="inline-flex items-center gap-0.5 text-sky-600 dark:text-sky-400"
          title={`Erkak: ${breakdown.male}`}
        >
          <MaleIcon className={`${z.gicon} shrink-0 opacity-90`} />
          <span className="tabular-nums font-semibold">{breakdown.male}</span>
        </span>
        <span
          className="inline-flex items-center gap-0.5 text-pink-600 dark:text-pink-400"
          title={`Ayol: ${breakdown.female}`}
        >
          <FemaleIcon className={`${z.gicon} shrink-0 opacity-90`} />
          <span className="tabular-nums font-semibold">{breakdown.female}</span>
        </span>
        {breakdown.unknown > 0 && (
          <span
            className="inline-flex items-center gap-0.5 text-gray-400"
            title={`Jinsi noma'lum: ${breakdown.unknown}`}
          >
            <span className="font-bold leading-none">?</span>
            <span className="tabular-nums">{breakdown.unknown}</span>
          </span>
        )}
        {extra}
      </div>
    </div>
  );
}

/** Chetlatilganlar uchun maxsus MD3 error-container uslub. */
function MiniCheating({
  cheating,
  size = "md",
}: {
  cheating: StatGroup["cheating"];
  size?: MiniSize;
}) {
  const s = VARIANT_STYLES.danger;
  const z = MINI_SIZE[size];
  return (
    <div
      className={`rounded-lg ring-1 ${s.bg} ${s.ring} ${z.box} transition-shadow duration-200 hover:shadow-sm`}
    >
      <p
        className={`font-semibold text-gray-600 dark:text-slate-300 leading-tight min-h-[2.4em] ${z.label}`}
      >
        Chetlat.
      </p>
      <p
        className={`font-bold tabular-nums leading-tight mt-0.5 ${z.value} ${s.valueColor}`}
      >
        {cheating.total.toLocaleString("uz-UZ")}
      </p>
      <div
        className={`flex items-center gap-1.5 mt-0.5 text-gray-600 dark:text-slate-300 leading-none ${z.gender}`}
      >
        <span
          title="Binoga kirishda"
          className="inline-flex items-center gap-0.5"
        >
          <KeyIcon className={`${z.gicon} text-red-500`} />
          <span className="tabular-nums font-semibold">
            {cheating.at_entry}
          </span>
        </span>
        <span
          title="Test jarayonida"
          className="inline-flex items-center gap-0.5"
        >
          <BookIcon className={`${z.gicon} text-red-500`} />
          <span className="tabular-nums font-semibold">
            {cheating.during_test}
          </span>
        </span>
      </div>
    </div>
  );
}

/* ============== Region Zones Modal ============== */

/**
 * Material Design 3 uslubidagi modal — viloyat ichidagi binolar bo'yicha
 * statistika taqsimoti. RegionCard bosilganda ochiladi. Stats polling yangi
 * ma'lumot kelganda parent `openedRegion`'ni `stats.regions`'dan qaytadan
 * topadi, shuning uchun modal real-time'da ham yangilanadi.
 */
function RegionZonesModal({
  region,
  onClose,
  orderKey = "dtm",
}: {
  region: RegionStatItem;
  onClose: () => void;
  orderKey?: "dtm" | "vm" | "iiv";
}) {
  const { closing, close } = useModalClose(onClose);
  const displayNumber = regionDisplayNumber(region, orderKey);

  const total = region.stats.total.total;
  const attended = region.stats.attended.total;
  const attendancePercent =
    total > 0 ? Math.round((attended / total) * 1000) / 10 : 0;

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
    <div
      className={`fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/45 dark:bg-black/65 backdrop-blur-[3px] p-0 sm:p-4 ${closing ? "animate-modal-overlay-out" : "animate-modal-overlay"}`}
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-label={`${region.region_name} — binolar bo'yicha taqsimot`}
    >
      <div
        className={`md3-dialog w-full sm:max-w-4xl max-h-[92vh] overflow-hidden rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col safe-pb ${closing ? "animate-modal-panel-out" : "animate-modal-panel"}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 sm:px-6 pt-5 pb-3 border-b border-gray-100 dark:border-slate-700/60">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 text-white font-bold flex items-center justify-center shadow-md shadow-primary-500/25 ring-1 ring-white/20 shrink-0">
                <span className="text-base tabular-nums leading-none">
                  {displayNumber}
                </span>
              </div>
              <div className="min-w-0">
                <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate leading-tight">
                  {region.region_name || `Region #${region.region_number}`}
                </h3>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-none mt-1">
                  Binolar bo'yicha taqsimot · {region.zones.length} ta bino
                </p>
              </div>
            </div>

            <button
              onClick={close}
              className="p-2 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors shrink-0"
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

          {/* Region summary — bo'limli viloyatda kattaroq "Viloyat davomati"
              kartasi (tier 1, AttendanceSummary xl); aks holda ixcham ko'rinish. */}
          <div className="mt-4">
            {region.is_have_part ? (
              <AttendanceSummary
                title="Viloyat davomati"
                subtitle={`Barcha hududlar · ${region.zones.length} ta bino`}
                tone="region"
                size="xl"
                icon={<MapPinIcon className="w-5 h-5" />}
                stats={region.stats}
              />
            ) : (
              <>
                <div className="flex items-end justify-between mb-1.5">
                  <span className="text-[12px] font-semibold text-gray-700 dark:text-slate-300">
                    Viloyat davomati
                  </span>
                  <span
                    className={`text-xl font-bold tabular-nums leading-none ${percentText}`}
                  >
                    {attendancePercent}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 dark:bg-slate-700/50 overflow-hidden">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${percentTone} transition-[width] duration-500 ease-out`}
                    style={{ width: `${attendancePercent}%` }}
                  />
                </div>
                <div className="grid grid-cols-4 gap-1.5 sm:gap-2 mt-3">
                  <MiniStat
                    label="Umumiy"
                    breakdown={region.stats.total}
                    accent="primary"
                  />
                  <MiniStat
                    label="Kelgan"
                    breakdown={region.stats.attended}
                    accent="success"
                  />
                  <MiniStat
                    label="Kelmagan"
                    breakdown={region.stats.not_attended}
                    accent="warning"
                  />
                  <MiniCheating cheating={region.stats.cheating} />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Body: zonalar — bo'limli viloyatda (is_have_part) is_part bo'yicha
            ikki guruhga ajraladi, har biri birlashgan davomati bilan. */}
        <div className="overflow-y-auto px-3 sm:px-4 py-3 sm:py-4">
          {region.zones.length === 0 ? (
            <div className="py-12 text-center text-gray-500 dark:text-slate-400 text-sm">
              <BuildingIcon className="w-10 h-10 mx-auto mb-2 text-gray-300 dark:text-slate-600" />
              Bu region uchun bino ma'lumotlari topilmadi
            </div>
          ) : region.is_have_part ? (
            <>
              <ZoneGroupSection
                title="Asosiy hudud"
                subtitle="Qo'shimcha hududga kirmaydigan binolar"
                tone="primary"
                icon={<BuildingIcon className="w-4 h-4" />}
                zones={region.zones.filter((z) => !z.is_part)}
              />
              <ZoneGroupSection
                title="Qo'shimcha hudud"
                subtitle="Qo'shimcha hududga tegishli binolar"
                tone="violet"
                icon={<LayersIcon className="w-4 h-4" />}
                zones={region.zones.filter((z) => z.is_part)}
              />
            </>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 sm:gap-2.5">
              {region.zones.map((z) => (
                <ZoneCard key={z.zone_id} item={z} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============== All Regions Modal (bitta jadval) ============== */

function TableIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M3 10h18M3 14h18M9 6v12M4 6h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1z"
      />
    </svg>
  );
}

/** Jadval katakchasi ichidagi ixcham jins ko'rsatkichi (♂/♀). */
function GenderInline({ g }: { g: GenderStat }) {
  return (
    <div className="flex items-center justify-center gap-2 mt-0.5 text-[10.5px] text-gray-500 dark:text-slate-400">
      <span className="inline-flex items-center gap-0.5" title="Erkak">
        <MaleIcon className="w-2.5 h-2.5 text-sky-500" />
        <span className="tabular-nums">{g.male.toLocaleString("uz-UZ")}</span>
      </span>
      <span className="inline-flex items-center gap-0.5" title="Ayol">
        <FemaleIcon className="w-2.5 h-2.5 text-pink-500" />
        <span className="tabular-nums">{g.female.toLocaleString("uz-UZ")}</span>
      </span>
    </div>
  );
}

/**
 * Barcha viloyatlar statistikasini bitta Material Design 3 jadval-modalda
 * ko'rsatadi. RegionGrid bilan bir xil ma'lumotni (real-time polling natijasi)
 * ishlatadi — mavjud logikani buzmaydi, faqat boshqa ko'rinish. Pastda "Jami"
 * yig'indi qatori `summary`'dan olinadi.
 */
function AllRegionsModal({
  regions,
  summary,
  contextLabel,
  onClose,
  orderKey = "dtm",
}: {
  regions: RegionStatItem[];
  summary: StatGroup;
  contextLabel: string;
  onClose: () => void;
  orderKey?: "dtm" | "vm" | "iiv";
}) {
  const { closing, close } = useModalClose(onClose);

  const pct = (att: number, tot: number) =>
    tot > 0 ? Math.round((att / tot) * 1000) / 10 : 0;
  const toneText = (p: number) =>
    p >= 75
      ? "text-emerald-700 dark:text-emerald-300"
      : p >= 50
        ? "text-amber-700 dark:text-amber-300"
        : "text-red-700 dark:text-red-300";
  const toneBar = (p: number) =>
    p >= 75
      ? "from-emerald-400 to-emerald-600"
      : p >= 50
        ? "from-amber-400 to-amber-500"
        : "from-red-400 to-red-500";

  const totalPct = pct(summary.attended.total, summary.total.total);
  const thCls =
    "px-2.5 py-2.5 text-[11px] font-semibold text-gray-500 dark:text-slate-400 whitespace-nowrap";
  const numCls = "px-2.5 py-2 text-center align-middle";

  return (
    <div
      className={`fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/45 dark:bg-black/65 backdrop-blur-[3px] p-0 sm:p-4 ${closing ? "animate-modal-overlay-out" : "animate-modal-overlay"}`}
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-label="Barcha viloyatlar bo'yicha taqsimot"
    >
      <div
        className={`md3-dialog w-full sm:max-w-7xl max-h-[96vh] overflow-hidden rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col safe-pb ${closing ? "animate-modal-panel-out" : "animate-modal-panel"}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 sm:px-6 pt-5 pb-4 border-b border-gray-100 dark:border-slate-700/60">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 text-white flex items-center justify-center shadow-md shadow-primary-500/25 ring-1 ring-white/20 shrink-0">
                <TableIcon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate leading-tight">
                  Barcha viloyatlar bo'yicha taqsimot
                </h3>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 leading-none mt-1 truncate">
                  {contextLabel} · {regions.length} ta viloyat
                </p>
              </div>
            </div>

            <button
              onClick={close}
              className="p-2 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors shrink-0"
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

        {/* Body: jadval */}
        <div className="overflow-auto">
          <table className="w-full min-w-[720px] border-collapse">
            <thead className="sticky top-0 z-10 bg-gray-50 dark:bg-slate-800 shadow-[0_1px_0_0_rgba(0,0,0,0.06)]">
              <tr>
                <th className={`${thCls} text-center w-12`}>№</th>
                <th className={`${thCls} text-left`}>Viloyat</th>
                <th className={`${thCls} text-center`}>Umumiy</th>
                <th className={`${thCls} text-center`}>Kelgan</th>
                <th className={`${thCls} text-center`}>Kelmagan</th>
                <th className={`${thCls} text-center`}>Chetlatilgan</th>
                <th className={`${thCls} text-center w-40`}>Davomat</th>
              </tr>
            </thead>
            <tbody>
              {regions.map((r) => {
                const p = pct(r.stats.attended.total, r.stats.total.total);
                return (
                  <tr
                    key={r.region_id}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50/80 dark:hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-2.5 py-2 text-center">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-[11px] font-bold tabular-nums">
                        {regionDisplayNumber(r, orderKey)}
                      </span>
                    </td>
                    <td className="px-2.5 py-2 text-left font-semibold text-gray-800 dark:text-slate-100 text-[13px]">
                      {r.region_name || `Region #${r.region_number}`}
                    </td>
                    <td className={numCls}>
                      <div className="font-bold tabular-nums text-gray-900 dark:text-white text-[14px]">
                        {r.stats.total.total.toLocaleString("uz-UZ")}
                      </div>
                      <GenderInline g={r.stats.total} />
                    </td>
                    <td className={numCls}>
                      <div className="font-bold tabular-nums text-emerald-700 dark:text-emerald-300 text-[14px]">
                        {r.stats.attended.total.toLocaleString("uz-UZ")}
                      </div>
                      <GenderInline g={r.stats.attended} />
                    </td>
                    <td className={numCls}>
                      <div className="font-bold tabular-nums text-amber-700 dark:text-amber-300 text-[14px]">
                        {r.stats.not_attended.total.toLocaleString("uz-UZ")}
                      </div>
                      <GenderInline g={r.stats.not_attended} />
                    </td>
                    <td className={numCls}>
                      <div className="font-bold tabular-nums text-red-700 dark:text-red-300 text-[14px]">
                        {r.stats.cheating.total.toLocaleString("uz-UZ")}
                      </div>
                      <div className="text-[10.5px] text-gray-500 dark:text-slate-400 mt-0.5">
                        kirish {r.stats.cheating.at_entry} · test{" "}
                        {r.stats.cheating.during_test}
                      </div>
                    </td>
                    <td className="px-2.5 py-2 align-middle">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full bg-gray-100 dark:bg-slate-700/50 overflow-hidden">
                          <div
                            className={`h-full rounded-full bg-gradient-to-r ${toneBar(p)}`}
                            style={{ width: `${p}%` }}
                          />
                        </div>
                        <span
                          className={`text-[12.5px] font-bold tabular-nums w-12 text-right ${toneText(p)}`}
                        >
                          {p}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="sticky bottom-0 z-10 bg-primary-50/90 dark:bg-primary-900/30 backdrop-blur-sm border-t-2 border-primary-200/70 dark:border-primary-700/50">
              <tr className="font-bold text-primary-800 dark:text-primary-200">
                <td className="px-2.5 py-3 text-center" colSpan={2}>
                  <span className="text-[13px]">Jami:</span>
                </td>
                <td className={numCls}>
                  <div className="font-bold tabular-nums text-[14px]">
                    {summary.total.total.toLocaleString("uz-UZ")}
                  </div>
                  <GenderInline g={summary.total} />
                </td>
                <td className={numCls}>
                  <div className="font-bold tabular-nums text-[14px]">
                    {summary.attended.total.toLocaleString("uz-UZ")}
                  </div>
                  <GenderInline g={summary.attended} />
                </td>
                <td className={numCls}>
                  <div className="font-bold tabular-nums text-[14px]">
                    {summary.not_attended.total.toLocaleString("uz-UZ")}
                  </div>
                  <GenderInline g={summary.not_attended} />
                </td>
                <td className={numCls}>
                  <div className="font-bold tabular-nums text-[14px]">
                    {summary.cheating.total.toLocaleString("uz-UZ")}
                  </div>
                  <div className="text-[10.5px] text-primary-700/80 dark:text-primary-300/80 mt-0.5">
                    kirish {summary.cheating.at_entry} · test{" "}
                    {summary.cheating.during_test}
                  </div>
                </td>
                <td className="px-2.5 py-3 text-right">
                  <span className="text-[13.5px] font-bold tabular-nums">
                    {totalPct}%
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

/** Bino (zone) statistika kartasi — region kartasiga o'xshash, ammo kompaktroq. */
function ZoneCard({
  item,
  compact = false,
}: {
  item: ZoneStatItem;
  /** Bo'limli viloyat guruhlari ichida — tier 3, hudud guruhidan kichikroq. */
  compact?: boolean;
}) {
  const total = item.stats.total.total;
  const attended = item.stats.attended.total;
  const attendancePercent =
    total > 0 ? Math.round((attended / total) * 1000) / 10 : 0;

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

  // Tier 3 o'lchamlari — compact bo'lsa hudud guruhidan kichikroq.
  const pad = compact ? "p-2.5" : "p-3 sm:p-3.5";
  const badge = compact ? "w-7 h-7" : "w-9 h-9";
  const badgeText = compact ? "text-[11px]" : "text-[13px]";
  const pctText = compact ? "text-sm" : "text-base";
  const miniSize: MiniSize = compact ? "sm" : "md";

  return (
    <article
      className={`rounded-2xl bg-white dark:bg-slate-800/70 ring-1 ring-gray-100 dark:ring-slate-700/60 hover:ring-primary-200 dark:hover:ring-primary-700/50 hover:shadow-sm transition-all duration-200 ${pad}`}
      aria-label={`Bino ${item.zone_number}: ${item.zone_name}`}
    >
      <header className="flex items-center justify-between gap-2.5 mb-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className={`${badge} rounded-xl bg-gradient-to-br from-sky-500 to-sky-700 text-white font-bold flex items-center justify-center shadow-sm shadow-sky-500/20 ring-1 ring-white/20 shrink-0`}
          >
            <span className={`${badgeText} tabular-nums leading-none`}>
              {item.zone_number}
            </span>
          </div>
          <div className="min-w-0">
            <p
              className="text-[13px] sm:text-sm font-semibold text-gray-900 dark:text-white truncate leading-tight"
              title={item.zone_name || `Bino #${item.zone_number}`}
            >
              {item.zone_name || `Bino #${item.zone_number}`}
            </p>
            <p className="text-[10px] text-gray-500 dark:text-slate-400 leading-none mt-0.5">
              Bino №{item.zone_number}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end shrink-0">
          <span
            className={`${pctText} font-bold tabular-nums leading-none ${percentText}`}
          >
            {attendancePercent}%
          </span>
          <span className="text-[10px] font-medium text-gray-600 dark:text-slate-300 leading-none mt-0.5">
            davomat
          </span>
        </div>
      </header>

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

      <div className="grid grid-cols-4 gap-1.5">
        <MiniStat
          label="Umumiy"
          breakdown={item.stats.total}
          accent="primary"
          size={miniSize}
        />
        <MiniStat
          label="Kelgan"
          breakdown={item.stats.attended}
          accent="success"
          size={miniSize}
        />
        <MiniStat
          label="Kelmagan"
          breakdown={item.stats.not_attended}
          accent="warning"
          size={miniSize}        />
        <MiniCheating cheating={item.stats.cheating} size={miniSize} />
      </div>
    </article>
  );
}

/* ============== Zone guruhlash (is_part) ============== */

/** Zonalar ro'yxatining birlashgan statistikasi — is_part guruhi davomati uchun. */
function aggregateZoneStats(zones: ZoneStatItem[]): StatGroup {
  const g = (): GenderStat => ({ total: 0, male: 0, female: 0, unknown: 0 });
  const total = g();
  const attended = g();
  const not_attended = g();
  const cheating = {
    total: 0,
    at_entry: 0,
    during_test: 0,
    other: 0,
    male: 0,
    female: 0,
    unknown: 0,
  };
  for (const z of zones) {
    const s = z.stats;
    for (const k of ["total", "male", "female", "unknown"] as const) {
      total[k] += s.total[k];
      attended[k] += s.attended[k];
      not_attended[k] += s.not_attended[k];
    }
    cheating.total += s.cheating.total;
    cheating.at_entry += s.cheating.at_entry;
    cheating.during_test += s.cheating.during_test;
    cheating.other += s.cheating.other;
    cheating.male += s.cheating.male;
    cheating.female += s.cheating.female;
    cheating.unknown += s.cheating.unknown;
  }
  return { total, attended, not_attended, cheating };
}

type SummaryTone = "region" | "primary" | "violet";
type SummarySize = "xl" | "md";

const SUMMARY_TONES: Record<
  SummaryTone,
  { chip: string; ring: string; bar: string }
> = {
  // Viloyat davomati — Asosiy hudud uslubida, ammo to'qroq/prominent gradient.
  region: {
    chip: "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300",
    ring: "ring-primary-300/70 dark:ring-primary-700/50",
    bar: "bg-gradient-to-br from-primary-50 to-white dark:from-primary-900/25 dark:to-slate-900",
  },
  primary: {
    chip: "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300",
    ring: "ring-primary-200/70 dark:ring-primary-800/40",
    bar: "bg-primary-50/70 dark:bg-primary-900/10",
  },
  violet: {
    chip: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
    ring: "ring-violet-200/70 dark:ring-violet-800/40",
    bar: "bg-violet-50/70 dark:bg-violet-900/10",
  },
};

const SUMMARY_SIZE: Record<
  SummarySize,
  {
    pad: string;
    iconBox: string;
    title: string;
    subtitle: string;
    pct: string;
    bar: string;
    grid: string;
    mini: MiniSize;
  }
> = {
  // Tier 1 — Viloyat davomati (eng katta)
  xl: {
    pad: "p-4 sm:p-5",
    iconBox: "w-11 h-11 rounded-2xl",
    title: "text-base sm:text-lg",
    subtitle: "text-[11.5px]",
    pct: "text-4xl sm:text-5xl",
    bar: "h-2.5",
    grid: "gap-2 sm:gap-2.5 mt-3.5",
    mini: "lg",
  },
  // Tier 2 — hudud guruhi (ancha kichik)
  md: {
    pad: "p-3 sm:p-3.5",
    iconBox: "w-7 h-7 rounded-lg",
    title: "text-[13px]",
    subtitle: "text-[10.5px]",
    pct: "text-lg",
    bar: "h-1.5",
    grid: "gap-1.5 mt-2.5",
    mini: "md",
  },
};

/**
 * Davomat xulosa kartasi (MD3 tonal surface) — sarlavha, foiz, progress va 4 ta
 * stat tile. O'lcham (`size`) ierarxiyani belgilaydi: xl=Viloyat davomati,
 * md=hudud guruhi. Bino kartalari undan ham kichik (ZoneCard compact).
 */
function AttendanceSummary({
  title,
  subtitle,
  tone,
  size,
  icon,
  stats,
}: {
  title: string;
  subtitle?: string;
  tone: SummaryTone;
  size: SummarySize;
  icon: React.ReactNode;
  stats: StatGroup;
}) {
  const total = stats.total.total;
  const attended = stats.attended.total;
  const pct = total > 0 ? Math.round((attended / total) * 1000) / 10 : 0;

  const percentTone =
    pct >= 75
      ? "from-emerald-400 to-emerald-600"
      : pct >= 50
        ? "from-amber-400 to-amber-500"
        : "from-red-400 to-red-500";
  const percentText =
    pct >= 75
      ? "text-emerald-700 dark:text-emerald-300"
      : pct >= 50
        ? "text-amber-700 dark:text-amber-300"
        : "text-red-700 dark:text-red-300";

  const t = SUMMARY_TONES[tone];
  const z = SUMMARY_SIZE[size];

  return (
    <div className={`rounded-2xl ring-1 ${t.ring} ${t.bar} ${z.pad}`}>
      <div className="flex items-center justify-between gap-2.5 mb-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`inline-flex items-center justify-center shrink-0 ${z.iconBox} ${t.chip}`}
          >
            {icon}
          </span>
          <div className="min-w-0">
            <p
              className={`font-bold text-gray-900 dark:text-white leading-tight truncate ${z.title}`}
            >
              {title}
            </p>
            {subtitle && (
              <p
                className={`text-gray-500 dark:text-slate-400 leading-none mt-0.5 truncate ${z.subtitle}`}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>
        <span
          className={`shrink-0 font-extrabold tabular-nums leading-none ${z.pct} ${percentText}`}
        >
          {pct}%
        </span>
      </div>
      <div
        className={`rounded-full bg-white/70 dark:bg-slate-700/40 overflow-hidden ${z.bar}`}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full bg-gradient-to-r ${percentTone} transition-[width] duration-500 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className={`grid grid-cols-4 ${z.grid}`}>
        <MiniStat
          label="Umumiy"
          breakdown={stats.total}
          accent="primary"
          size={z.mini}
        />
        <MiniStat
          label="Kelgan"
          breakdown={stats.attended}
          accent="success"
          size={z.mini}
        />
        <MiniStat
          label="Kelmagan"
          breakdown={stats.not_attended}
          accent="warning"
          size={z.mini}
        />
        <MiniCheating cheating={stats.cheating} size={z.mini} />
      </div>
    </div>
  );
}

/**
 * Bo'limli viloyatlarda (region.is_have_part) zonalarni is_part bo'yicha ajratib
 * ko'rsatadigan bo'lim — sarlavhada guruhning birlashgan davomati (tier 2,
 * AttendanceSummary md), so'ng guruhdagi bino kartalari (tier 3, ZoneCard compact).
 */
function ZoneGroupSection({
  title,
  subtitle,
  tone,
  icon,
  zones,
}: {
  title: string;
  subtitle: string;
  tone: "primary" | "violet";
  icon: React.ReactNode;
  zones: ZoneStatItem[];
}) {
  const agg = aggregateZoneStats(zones);

  return (
    <section className="mb-4 last:mb-0">
      {/* Guruh sarlavhasi — birlashgan davomat (tier 2) */}
      <div className="mb-2.5">
        <AttendanceSummary
          title={title}
          subtitle={`${subtitle} · ${zones.length} ta bino`}
          tone={tone}
          size="md"
          icon={icon}
          stats={agg}
        />
      </div>

      {/* Guruhdagi binolar (tier 3 — eng kichik) */}
      {zones.length === 0 ? (
        <p className="px-1 py-2 text-center text-[12px] text-gray-400 dark:text-slate-500">
          Bu guruhda bino yo'q
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 sm:gap-2.5">
          {zones.map((z) => (
            <ZoneCard key={z.zone_id} item={z} compact />
          ))}
        </div>
      )}
    </section>
  );
}

/* ============== Helpers ============== */

function formatSmenaOption(sm: TestSessionSmenaResponse): string {
  const day = sm.day;
  const smName = sm.smena?.name ?? `#${sm.smena?.number ?? sm.test_smena_id}`;
  const smNum = sm.smena?.number ?? sm.test_smena_id;
  return `${day} · ${smName} (smena №${smNum})`;
}

/** "Kunlik" selektor uchun — kun + shu kundagi smenalar soni. */
function formatDayOption(
  day: string,
  smenas: TestSessionSmenaResponse[],
): string {
  const count = smenas.filter((s) => s.day === day).length;
  return `${day} · ${count} ta smena`;
}

/** Cardlar ustidagi kontekst yozuvi — qaysi ko'lam ko'rsatilmoqda. */
function scopeContextLabel(s: DashboardStatsResponse): string {
  if (s.scope === "overall") {
    return `Butun sessiya — barcha kunlar · ${s.smena_count} ta smena`;
  }
  if (s.scope === "day") {
    return `${s.day ?? ""} — kunlik · ${s.smena_count} ta smena`;
  }
  // smena
  const sm =
    s.smena_name || (s.smena_number != null ? `№${s.smena_number}` : "");
  return `${s.day ?? ""}${sm ? ` · ${sm}` : ""}`;
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

function BuildingIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        strokeWidth={1.8}
        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5m14 0h2m-2 0v-5a1 1 0 00-1-1h-2a1 1 0 00-1 1v5M5 21H3m6-12h.01M9 13h.01M9 17h.01M13 9h.01M13 13h.01M13 17h.01"
      />
    </svg>
  );
}

/** Joylashuv belgisi (map pin) — viloyatlar soni uchun. */
function MapPinIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        strokeWidth={1.8}
        d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

/** Online belgisi — signal to'lqinlari (Onlinedagilar plitkasi uchun). */
function OnlineIcon({ className = "w-5 h-5" }: { className?: string }) {
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
        strokeWidth={1.8}
        d="M8.111 16.404a5.5 5.5 0 017.778 0M5.05 12.582a9.5 9.5 0 0113.9 0"
      />
      <circle cx="12" cy="20" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Qurilma belgisi — monitor (Qurilmalar plitkasi uchun). */
function DeviceIcon({ className = "w-5 h-5" }: { className?: string }) {
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
        strokeWidth={1.8}
        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
      />
    </svg>
  );
}

/** O'sish strelkasi — eng faol viloyat uchun. */
function TrendUpIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M3 17l6-6 4 4 8-8m0 0h-5m5 0v5"
      />
    </svg>
  );
}

/** Pasayish strelkasi — eng past davomat uchun. */
function TrendDownIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M3 7l6 6 4-4 8 8m0 0h-5m5 0v-5"
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

function ClockIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function CalendarIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

function LayersIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M12 3l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5"
      />
    </svg>
  );
}

function DownloadIcon({ className = "w-4 h-4" }: { className?: string }) {
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
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}

function Spinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={`${className} animate-spin`}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth={4}
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
