import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { TestSessionListResponse } from "../interfaces";
import { getTestSessionsApi } from "../api";
import PageLoader from "../components/PageLoader";

/* ============================================================
 * Test Dashboard — test sessiyalari bo'yicha umumiy, tahliliy
 * statistika. Barcha ko'rsatkichlar `getTestSessionsApi` javobidan
 * hosil qilinadi (qo'shimcha backend so'rovsiz). Material Design 3
 * uslubida: gradientli KPI kartalar, rangli taqsimot grafikalari.
 * ========================================================== */

type StatColor =
  | "primary"
  | "emerald"
  | "violet"
  | "amber"
  | "sky"
  | "rose";

const COLOR_MAP: Record<
  StatColor,
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
  emerald: {
    bg: "bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/20 dark:to-slate-900",
    ring: "ring-emerald-200/60 dark:ring-emerald-800/40",
    valueColor: "text-emerald-800 dark:text-emerald-200",
    iconBg:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    blob: "bg-emerald-400",
  },
  violet: {
    bg: "bg-gradient-to-br from-violet-50 to-white dark:from-violet-900/20 dark:to-slate-900",
    ring: "ring-violet-200/60 dark:ring-violet-800/40",
    valueColor: "text-violet-800 dark:text-violet-200",
    iconBg:
      "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
    blob: "bg-violet-400",
  },
  amber: {
    bg: "bg-gradient-to-br from-amber-50 to-white dark:from-amber-900/20 dark:to-slate-900",
    ring: "ring-amber-200/60 dark:ring-amber-800/40",
    valueColor: "text-amber-800 dark:text-amber-200",
    iconBg:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    blob: "bg-amber-400",
  },
  sky: {
    bg: "bg-gradient-to-br from-sky-50 to-white dark:from-sky-900/20 dark:to-slate-900",
    ring: "ring-sky-200/60 dark:ring-sky-800/40",
    valueColor: "text-sky-800 dark:text-sky-200",
    iconBg: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
    blob: "bg-sky-400",
  },
  rose: {
    bg: "bg-gradient-to-br from-rose-50 to-white dark:from-rose-900/20 dark:to-slate-900",
    ring: "ring-rose-200/60 dark:ring-rose-800/40",
    valueColor: "text-rose-800 dark:text-rose-200",
    iconBg: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
    blob: "bg-rose-400",
  },
};

// SessionState.key bo'yicha rang (StatisticsPage palitrasi bilan mos)
const STATE_BAR: Record<number, { bar: string; dot: string }> = {
  1: { bar: "bg-slate-400", dot: "bg-slate-400" },
  2: { bar: "bg-sky-500", dot: "bg-sky-500" },
  3: { bar: "bg-amber-500", dot: "bg-amber-500" },
  4: { bar: "bg-emerald-500", dot: "bg-emerald-500" },
  5: { bar: "bg-violet-500", dot: "bg-violet-500" },
};
const STATE_BAR_FALLBACK = { bar: "bg-gray-400", dot: "bg-gray-400" };

function stateTone(key: number | null | undefined) {
  if (key == null) return STATE_BAR_FALLBACK;
  return STATE_BAR[key] ?? STATE_BAR_FALLBACK;
}

export default function TestDashboardPage() {
  const [data, setData] = useState<TestSessionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getTestSessionsApi({ page: 1, per_page: 100 })
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const sessions = useMemo(() => data?.items ?? [], [data]);

  // === Hosilaviy (derived) statistika ===
  const metrics = useMemo(() => {
    const totalSessions = sessions.length;
    const activeSessions = sessions.filter((s) => s.is_active).length;
    const totalStudents = sessions.reduce(
      (sum, s) => sum + s.count_total_student,
      0,
    );
    const totalSmenas = sessions.reduce((sum, s) => sum + s.smenas.length, 0);

    // Noyob testlar
    const testSet = new Set<string>();
    sessions.forEach((s) => testSet.add(s.test?.name || `#${s.test_id}`));

    // Noyob imtihon kunlari (barcha smenalar bo'yicha)
    const daySet = new Set<string>();
    sessions.forEach((s) => s.smenas.forEach((sm) => daySet.add(sm.day)));

    const avgStudents =
      totalSessions > 0 ? Math.round(totalStudents / totalSessions) : 0;
    const avgSmenas =
      totalSessions > 0
        ? Math.round((totalSmenas / totalSessions) * 10) / 10
        : 0;
    const activePct =
      totalSessions > 0
        ? Math.round((activeSessions / totalSessions) * 100)
        : 0;

    // Tayyor (ready, key=4) holatdagi sessiyalar soni
    const readyCount = sessions.filter((s) => s.test_state?.key === 4).length;

    return {
      totalSessions,
      activeSessions,
      totalStudents,
      totalSmenas,
      uniqueTests: testSet.size,
      uniqueDays: daySet.size,
      avgStudents,
      avgSmenas,
      activePct,
      readyCount,
    };
  }, [sessions]);

  // Tayyor (jonli) sessiyalar — real vaqt jarayonidagilar (SessionState.key=4)
  const readySessions = useMemo(
    () => sessions.filter((s) => s.test_state?.key === 4),
    [sessions],
  );

  // Talabgorlar holat (state) bo'yicha taqsimlangan
  const studentsByState = useMemo(() => {
    const map = new Map<
      string,
      { name: string; key: number | null; students: number }
    >();
    sessions.forEach((s) => {
      const name = s.test_state?.name || "Noma'lum";
      const key = s.test_state?.key ?? null;
      const cur = map.get(name) || { name, key, students: 0 };
      cur.students += s.count_total_student;
      map.set(name, cur);
    });
    return [...map.values()]
      .filter((g) => g.students > 0)
      .sort((a, b) => b.students - a.students);
  }, [sessions]);

  // Holat (state) bo'yicha guruhlash
  const stateGroups = useMemo(() => {
    const map = new Map<
      string,
      { name: string; key: number | null; count: number; students: number }
    >();
    sessions.forEach((s) => {
      const name = s.test_state?.name || "Noma'lum";
      const key = s.test_state?.key ?? null;
      const cur = map.get(name) || { name, key, count: 0, students: 0 };
      cur.count += 1;
      cur.students += s.count_total_student;
      map.set(name, cur);
    });
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [sessions]);

  // Testlar bo'yicha guruhlash (sessiyalar soni + talabgorlar)
  const testGroups = useMemo(() => {
    const map = new Map<string, { name: string; count: number; students: number }>();
    sessions.forEach((s) => {
      const name = s.test?.name || `Test #${s.test_id}`;
      const cur = map.get(name) || { name, count: 0, students: 0 };
      cur.count += 1;
      cur.students += s.count_total_student;
      map.set(name, cur);
    });
    return [...map.values()].sort((a, b) => b.students - a.students);
  }, [sessions]);

  // Eng katta sessiyalar (talabgorlar soni bo'yicha)
  const topSessions = useMemo(
    () =>
      [...sessions]
        .sort((a, b) => b.count_total_student - a.count_total_student)
        .slice(0, 5),
    [sessions],
  );

  // Faol va kelayotgan sessiyalar
  const upcomingSessions = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return sessions
      .filter((s) => {
        const finish = new Date(s.finish_date);
        return finish >= today && s.is_active;
      })
      .sort(
        (a, b) =>
          new Date(a.start_date).getTime() - new Date(b.start_date).getTime(),
      );
  }, [sessions]);

  if (loading) return <PageLoader />;

  return (
    <div>
      <div className="page-header mb-5 sm:mb-6">
        <div className="min-w-0">
          <h2 className="section-title">Test Dashboard</h2>
          <p className="section-subtitle">
            Test sessiyalari bo'yicha umumiy va tahliliy statistika
          </p>
        </div>
        <button
          onClick={() => navigate("/test-sessions")}
          className="inline-flex items-center gap-1.5 px-3.5 h-9 rounded-full text-[12.5px] font-semibold text-primary-700 dark:text-primary-300 bg-primary-50 hover:bg-primary-100 dark:bg-primary-900/30 dark:hover:bg-primary-900/50 ring-1 ring-primary-200/60 dark:ring-primary-700/50 transition-colors self-start sm:self-auto shrink-0"
        >
          <ListIcon className="w-4 h-4" />
          <span>Sessiyalar</span>
        </button>
      </div>

      {/* KPI kartalar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3.5 mb-3 sm:mb-3.5">
        <StatCard
          title="Jami sessiyalar"
          value={metrics.totalSessions}
          sub={`${metrics.activeSessions} ta faol`}
          color="primary"
          icon={<CalendarIcon />}
        />
        <StatCard
          title="Faol sessiyalar"
          value={metrics.activeSessions}
          sub={`${metrics.activePct}% faol holatda`}
          color="emerald"
          icon={<CheckCircleIcon />}
        />
        <StatCard
          title="Jami talabgorlar"
          value={metrics.totalStudents}
          sub={`o'rtacha ${metrics.avgStudents.toLocaleString("uz-UZ")}/sessiya`}
          color="violet"
          icon={<UsersIcon />}
        />
        <StatCard
          title="Jami smenalar"
          value={metrics.totalSmenas}
          sub={`o'rtacha ${metrics.avgSmenas}/sessiya`}
          color="amber"
          icon={<ClockIcon />}
        />
      </div>

      {/* Qo'shimcha ko'rsatkichlar — ixcham strip */}
      <div className="glass-card px-4 sm:px-5 py-3 mb-5 sm:mb-6 flex flex-wrap items-center gap-x-6 sm:gap-x-9 gap-y-2.5">
        <Highlight
          label="Tayyor (jonli)"
          value={metrics.readyCount}
          tone="text-emerald-700 dark:text-emerald-300"
        />
        <Highlight
          label="Testlar turi"
          value={metrics.uniqueTests}
          tone="text-sky-700 dark:text-sky-300"
        />
        <Highlight
          label="Imtihon kunlari"
          value={metrics.uniqueDays}
          tone="text-rose-700 dark:text-rose-300"
        />
        <Highlight
          label="o'rtacha talabgor / sessiya"
          value={metrics.avgStudents.toLocaleString("uz-UZ")}
          tone="text-violet-700 dark:text-violet-300"
        />
        <Highlight
          label="faollik darajasi"
          value={`${metrics.activePct}%`}
          tone="text-amber-700 dark:text-amber-300"
        />
      </div>

      {/* Jonli (tayyor) sessiyalar — harakatlanuvchi progress bilan */}
      {readySessions.length > 0 && (
        <div className="rounded-2xl ring-1 ring-emerald-200/70 dark:ring-emerald-800/40 bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/15 dark:to-slate-900 p-4 sm:p-5 mb-5 sm:mb-6 shadow-sm">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2.5">
              <span className="relative flex w-2.5 h-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </span>
              <h3 className="text-[14px] font-bold text-emerald-800 dark:text-emerald-200 leading-tight">
                Jonli (tayyor) sessiyalar
              </h3>
            </div>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 shrink-0">
              {readySessions.length} ta faol
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {readySessions.slice(0, 6).map((s) => (
              <div
                key={s.id}
                onClick={() => navigate("/test-sessions")}
                className="cursor-pointer rounded-xl bg-white/70 dark:bg-slate-800/50 ring-1 ring-emerald-100 dark:ring-slate-700/50 p-3 hover:ring-emerald-300 dark:hover:ring-emerald-700 hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <p className="text-[13px] font-semibold text-gray-900 dark:text-white truncate">
                    {s.name}
                  </p>
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold tabular-nums text-emerald-700 dark:text-emerald-300 shrink-0">
                    <UsersIcon className="w-3.5 h-3.5" />
                    {s.count_total_student.toLocaleString("uz-UZ")}
                  </span>
                </div>
                <LiveProgress />
                <div className="flex items-center justify-between mt-2 text-[11px] text-gray-500 dark:text-slate-400 gap-2">
                  <span className="truncate">{s.test?.name || "—"}</span>
                  <span className="shrink-0 font-medium text-emerald-600 dark:text-emerald-400">
                    {s.smenas.length} smena
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Holat + Testlar taqsimoti */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 sm:gap-4 mb-5 sm:mb-6">
        {/* Holat bo'yicha taqsimot */}
        <SectionCard
          title="Holat bo'yicha taqsimot"
          subtitle={`${metrics.totalSessions} ta sessiya`}
        >
          {stateGroups.length > 0 ? (
            <>
              {/* Stacked umumiy bar */}
              <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700/50 mb-4">
                {stateGroups.map((g) => {
                  const pct =
                    metrics.totalSessions > 0
                      ? (g.count / metrics.totalSessions) * 100
                      : 0;
                  return (
                    <div
                      key={g.name}
                      className={`h-full ${stateTone(g.key).bar} transition-[width] duration-700`}
                      style={{ width: `${pct}%` }}
                      title={`${g.name}: ${g.count}`}
                    />
                  );
                })}
              </div>
              <div className="space-y-3">
                {stateGroups.map((g) => {
                  const pct =
                    metrics.totalSessions > 0
                      ? Math.round((g.count / metrics.totalSessions) * 100)
                      : 0;
                  return (
                    <div key={g.name}>
                      <div className="flex items-center justify-between mb-1 gap-2">
                        <span className="inline-flex items-center gap-2 min-w-0">
                          <span
                            className={`w-2.5 h-2.5 rounded-full shrink-0 ${stateTone(g.key).dot}`}
                          />
                          <span className="text-[13px] text-gray-600 dark:text-slate-300 truncate">
                            {g.name}
                          </span>
                        </span>
                        <span className="text-[12px] shrink-0 tabular-nums text-gray-400 dark:text-slate-500">
                          <span className="font-bold text-gray-900 dark:text-white">
                            {g.count}
                          </span>{" "}
                          sessiya ·{" "}
                          <span className="font-semibold text-gray-600 dark:text-slate-300">
                            {g.students.toLocaleString("uz-UZ")}
                          </span>{" "}
                          talabgor · {pct}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 dark:bg-slate-700/50 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full ${stateTone(g.key).bar} transition-all duration-700`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <EmptyText />
          )}
        </SectionCard>

        {/* Testlar bo'yicha taqsimot */}
        <SectionCard
          title="Testlar bo'yicha taqsimot"
          subtitle={`${metrics.uniqueTests} ta test`}
        >
          {testGroups.length > 0 ? (
            <div className="space-y-3">
              {testGroups.slice(0, 7).map((g, i) => {
                const maxStudents = testGroups[0].students || 1;
                const pct = (g.students / maxStudents) * 100;
                return (
                  <div key={g.name}>
                    <div className="flex items-center justify-between mb-1 gap-2">
                      <span className="text-[13px] text-gray-600 dark:text-slate-300 truncate">
                        {g.name}
                      </span>
                      <span className="text-[12px] shrink-0 tabular-nums text-gray-500 dark:text-slate-400">
                        <span className="font-bold text-gray-900 dark:text-white">
                          {g.students.toLocaleString("uz-UZ")}
                        </span>{" "}
                        talabgor · {g.count} sessiya
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-slate-700/50 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full bg-gradient-to-r ${
                          i === 0
                            ? "from-primary-400 to-primary-600"
                            : "from-sky-400 to-sky-500"
                        } transition-all duration-700`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyText />
          )}
        </SectionCard>
      </div>

      {/* Talabgorlar holat bo'yicha — to'liq kenglik */}
      <div className="mb-5 sm:mb-6">
        <SectionCard
          title="Talabgorlar holat bo'yicha"
          subtitle={`${metrics.totalStudents.toLocaleString("uz-UZ")} ta talabgor`}
        >
          {studentsByState.length > 0 ? (
            <>
              <div className="flex h-3 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700/50 mb-3.5">
                {studentsByState.map((g) => {
                  const pct =
                    metrics.totalStudents > 0
                      ? (g.students / metrics.totalStudents) * 100
                      : 0;
                  return (
                    <div
                      key={g.name}
                      className={`h-full ${stateTone(g.key).bar} transition-[width] duration-700`}
                      style={{ width: `${pct}%` }}
                      title={`${g.name}: ${g.students.toLocaleString("uz-UZ")}`}
                    />
                  );
                })}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                {studentsByState.map((g) => {
                  const pct =
                    metrics.totalStudents > 0
                      ? Math.round((g.students / metrics.totalStudents) * 100)
                      : 0;
                  return (
                    <div
                      key={g.name}
                      className="rounded-xl bg-gray-50/80 dark:bg-slate-800/50 ring-1 ring-gray-100 dark:ring-slate-700/50 px-3 py-2"
                    >
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span
                          className={`w-2 h-2 rounded-full shrink-0 ${stateTone(g.key).dot}`}
                        />
                        <span className="text-[11px] text-gray-500 dark:text-slate-400 truncate">
                          {g.name}
                        </span>
                      </div>
                      <p className="text-base sm:text-lg font-bold tabular-nums text-gray-900 dark:text-white leading-none">
                        {g.students.toLocaleString("uz-UZ")}
                      </p>
                      <p className="text-[10.5px] text-gray-400 dark:text-slate-500 mt-1">
                        {pct}%
                      </p>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <EmptyText />
          )}
        </SectionCard>
      </div>

      {/* Eng katta sessiyalar + Kelayotgan sessiyalar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 sm:gap-4 mb-5 sm:mb-6">
        {/* Eng katta sessiyalar */}
        <SectionCard
          title="Eng katta sessiyalar"
          subtitle="talabgorlar soni bo'yicha"
        >
          {topSessions.length > 0 ? (
            <div className="space-y-2.5">
              {topSessions.map((s, i) => {
                const max = topSessions[0].count_total_student || 1;
                const pct = (s.count_total_student / max) * 100;
                return (
                  <div
                    key={s.id}
                    onClick={() => navigate("/test-sessions")}
                    className="cursor-pointer group"
                  >
                    <div className="flex items-center justify-between mb-1 gap-2">
                      <span className="inline-flex items-center gap-2 min-w-0">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-md text-[10.5px] font-bold bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300 shrink-0 tabular-nums">
                          {i + 1}
                        </span>
                        <span className="text-[13px] font-medium text-gray-800 dark:text-slate-100 truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                          {s.name}
                        </span>
                      </span>
                      <span className="text-[13px] font-bold tabular-nums text-gray-900 dark:text-white shrink-0">
                        {s.count_total_student.toLocaleString("uz-UZ")}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-slate-700/50 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-violet-400 to-violet-600 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyText />
          )}
        </SectionCard>

        {/* Faol va kelayotgan sessiyalar */}
        <SectionCard
          title="Faol va kelayotgan sessiyalar"
          subtitle={`${upcomingSessions.length} ta`}
        >
          {upcomingSessions.length > 0 ? (
            <div className="space-y-1.5 max-h-72 overflow-y-auto -mr-1 pr-1">
              {upcomingSessions.slice(0, 12).map((s) => (
                <div
                  key={s.id}
                  onClick={() => navigate("/test-sessions")}
                  className="flex items-center justify-between gap-3 p-2.5 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700/40 cursor-pointer transition-colors ring-1 ring-transparent hover:ring-gray-100 dark:hover:ring-slate-700/60"
                >
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-gray-900 dark:text-white truncate">
                      {s.name}
                    </p>
                    <p className="text-[11px] text-gray-400 dark:text-slate-500 truncate">
                      {s.test?.name || "—"} · {s.smenas.length} smena ·{" "}
                      {s.count_total_student.toLocaleString("uz-UZ")} talabgor
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10.5px] font-semibold ${
                        STATE_BAR[s.test_state?.key ?? 0]
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                          : "bg-gray-100 text-gray-600 dark:bg-slate-700/50 dark:text-slate-300"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${stateTone(s.test_state?.key).dot}`}
                      />
                      {s.test_state?.name || "—"}
                    </span>
                    <p className="text-[11px] text-gray-400 dark:text-slate-500 mt-1 tabular-nums">
                      {s.start_date}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyText label="Faol sessiya yo'q" />
          )}
        </SectionCard>
      </div>

      {/* Oxirgi sessiyalar jadvali */}
      <SectionCard
        title="Oxirgi sessiyalar"
        action={
          <button
            onClick={() => navigate("/test-sessions")}
            className="text-[12px] text-primary-600 dark:text-primary-400 hover:underline font-semibold"
          >
            Barchasini ko'rish →
          </button>
        }
      >
        <div className="overflow-x-auto -mx-1">
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="border-b border-gray-100 dark:border-slate-700/60">
                {["#", "Nomi", "Test", "Holat", "Talabgor", "Smena", "Sana"].map(
                  (h) => (
                    <th
                      key={h}
                      className={`px-3 py-2 text-[11px] font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide ${
                        h === "Talabgor" || h === "Smena"
                          ? "text-right"
                          : "text-left"
                      }`}
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 8).map((s) => (
                <tr
                  key={s.id}
                  onClick={() => navigate("/test-sessions")}
                  className="border-b border-gray-50 dark:border-slate-700/40 hover:bg-gray-50/60 dark:hover:bg-slate-700/30 transition-colors cursor-pointer"
                >
                  <td className="px-3 py-3 text-[13px] text-gray-500 dark:text-slate-400 tabular-nums">
                    {s.number}
                  </td>
                  <td className="px-3 py-3 text-[13px] font-medium text-gray-900 dark:text-white max-w-[200px] truncate">
                    {s.name}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-gray-600 dark:text-slate-300 max-w-[160px] truncate">
                    {s.test?.name || "—"}
                  </td>
                  <td className="px-3 py-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-700 dark:bg-slate-700/50 dark:text-slate-200">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${stateTone(s.test_state?.key).dot}`}
                      />
                      {s.test_state?.name || "—"}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-[13px] font-semibold text-gray-900 dark:text-white text-right tabular-nums">
                    {s.count_total_student.toLocaleString("uz-UZ")}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-gray-600 dark:text-slate-300 text-right tabular-nums">
                    {s.smenas.length}
                  </td>
                  <td className="px-3 py-3 text-[11px] text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    {s.start_date} — {s.finish_date}
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-10 text-center text-gray-400 dark:text-slate-500 text-sm"
                  >
                    Sessiya yo'q
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

/* ============== Sub-komponentlar ============== */

function StatCard({
  title,
  value,
  sub,
  icon,
  color,
}: {
  title: string;
  value: number;
  sub?: string;
  icon: React.ReactNode;
  color: StatColor;
}) {
  const tone = COLOR_MAP[color];
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl ring-1 ${tone.bg} ${tone.ring} p-3.5 sm:p-4 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300`}
    >
      <div
        className={`pointer-events-none absolute -right-6 -top-9 w-28 h-28 rounded-full blur-2xl opacity-20 dark:opacity-[0.18] ${tone.blob}`}
        aria-hidden
      />
      <div
        className={`relative w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center shadow-sm ring-1 ring-white/40 dark:ring-white/5 mb-3 ${tone.iconBg}`}
      >
        {icon}
      </div>
      <p
        className={`relative text-2xl sm:text-3xl font-extrabold tabular-nums tracking-tight leading-none ${tone.valueColor}`}
      >
        {value.toLocaleString("uz-UZ")}
      </p>
      <p className="relative mt-1.5 text-[12px] font-semibold text-gray-600 dark:text-slate-300 leading-tight">
        {title}
      </p>
      {sub && (
        <p className="relative mt-1 text-[11px] text-gray-400 dark:text-slate-500 truncate">
          {sub}
        </p>
      )}
    </div>
  );
}

function SectionCard({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-card p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="text-[14px] font-bold text-gray-800 dark:text-slate-100 leading-tight">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[11.5px] text-gray-400 dark:text-slate-500 mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function EmptyText({ label = "Ma'lumot yo'q" }: { label?: string }) {
  return (
    <p className="text-sm text-gray-400 dark:text-slate-500 py-6 text-center">
      {label}
    </p>
  );
}

/** Ixcham ko'rsatkich — strip ichidagi son + label. */
function Highlight({
  label,
  value,
  tone = "text-gray-900 dark:text-white",
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`text-xl font-extrabold tabular-nums leading-none ${tone}`}>
        {value}
      </span>
      <span className="text-[11.5px] text-gray-500 dark:text-slate-400 leading-tight">
        {label}
      </span>
    </div>
  );
}

/**
 * Harakatlanuvchi (indeterminate) progress — tayyor/jonli sessiya jarayonini
 * bildiradi. CSS `.live-progress-bar` keyframe'i bilan chapdan o'ngga suriladi.
 */
function LiveProgress() {
  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-emerald-100/70 dark:bg-emerald-900/30">
      <div className="live-progress-bar bg-gradient-to-r from-emerald-400 to-emerald-600" />
    </div>
  );
}

/* ============== Iconlar ============== */

function CalendarIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

function CheckCircleIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function UsersIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    </svg>
  );
}

function ClockIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function ListIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h16"
      />
    </svg>
  );
}
