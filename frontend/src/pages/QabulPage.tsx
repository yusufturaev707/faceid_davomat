import { useCallback, useEffect, useRef, useState } from "react";
import type { QabulStats } from "../interfaces";
import { getQabulStatsApi } from "../api";
import PageLoader from "../components/PageLoader";
import { extractErrorMessage } from "../utils/errorMessage";

const POLL_MS = 30_000; // 30s realtime polling

function fmt(n: number): string {
  return Math.round(n || 0)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function pct(part: number, whole: number): number {
  return whole ? (part / whole) * 100 : 0;
}

/** Material 3 ko'rinishidagi progress bar. */
function Bar({
  value,
  total,
  color,
}: {
  value: number;
  total: number;
  color: string;
}) {
  const p = Math.max(0, Math.min(100, pct(value, total)));
  return (
    <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-slate-700/60 overflow-hidden">
      <div
        className={`h-full rounded-full ${color} transition-[width] duration-700 ease-out`}
        style={{ width: `${p}%` }}
      />
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  sub?: React.ReactNode;
  icon: React.ReactNode;
  tint: string; // icon bg + text
  accent: string; // left accent bar
}

function MetricCard({ label, value, sub, icon, tint, accent }: MetricCardProps) {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700/60 p-5 transition-shadow hover:shadow-md">
      <span className={`absolute left-0 top-0 h-full w-1 ${accent}`} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[12.5px] font-medium text-gray-500 dark:text-slate-400 truncate">
            {label}
          </p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white tabular-nums">
            {value}
          </p>
          {sub && <div className="mt-2 text-xs">{sub}</div>}
        </div>
        <div
          className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${tint}`}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

export default function QabulPage() {
  const [stats, setStats] = useState<QabulStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<number | null>(null);

  const load = useCallback(async (force = false) => {
    try {
      if (force) setRefreshing(true);
      const data = await getQabulStatsApi(force);
      setStats(data);
      setLastUpdated(new Date());
      setError("");
    } catch (e: any) {
      setError(extractErrorMessage(e) || "Ma'lumotlarni yuklashda xatolik");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
    timerRef.current = window.setInterval(() => void load(), POLL_MS);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [load]);

  if (loading) return <PageLoader />;

  if (!stats) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-red-500 dark:text-red-400">{error || "Ma'lumot yo'q"}</p>
        <button onClick={() => void load(true)} className="btn-primary mt-4">
          Qayta urinish
        </button>
      </div>
    );
  }

  const trend = stats.total - stats.total_prev;
  const trendPct = stats.total_prev
    ? (trend / stats.total_prev) * 100
    : 0;
  const maxRegion = stats.regions[0]?.count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="section-title flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
            Qabul-{stats.year}
          </h2>
          <p className="section-subtitle">
            {stats.year}–{stats.year + 1} o'quv yili abituriyentlar qabuli — jonli statistika
            {lastUpdated && (
              <span className="ml-1 text-gray-400 dark:text-slate-500">
                · yangilandi {lastUpdated.toLocaleTimeString("uz-UZ")}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => void load(true)}
          disabled={refreshing}
          className="btn-primary flex items-center gap-2"
        >
          <svg
            className={`w-5 h-5 ${refreshing ? "animate-spin" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {refreshing ? "Yangilanmoqda..." : "Yangilash"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Primary metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Ro'yxatdan o'tganlar"
          value={fmt(stats.total)}
          tint="bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400"
          accent="bg-primary-500"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 00-3-3.87" />
            </svg>
          }
          sub={
            <span
              className={`inline-flex items-center gap-1 font-medium ${
                trend >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-red-500 dark:text-red-400"
              }`}
            >
              {trend >= 0 ? "▲" : "▼"} {fmt(Math.abs(trend))}
              {stats.total_prev > 0 && ` (${trendPct >= 0 ? "+" : ""}${trendPct.toFixed(1)}%)`}
              <span className="text-gray-400 dark:text-slate-500 font-normal">
                2025: {fmt(stats.total_prev)}
              </span>
            </span>
          }
        />

        <MetricCard
          label="Erkaklar"
          value={fmt(stats.male)}
          tint="bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
          accent="bg-blue-500"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          }
          sub={
            <span className="text-gray-500 dark:text-slate-400">
              {pct(stats.male, stats.total).toFixed(1)}% ulush
            </span>
          }
        />

        <MetricCard
          label="Ayollar"
          value={fmt(stats.female)}
          tint="bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400"
          accent="bg-pink-500"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          }
          sub={
            <span className="text-gray-500 dark:text-slate-400">
              {pct(stats.female, stats.total).toFixed(1)}% ulush
            </span>
          }
        />

        <MetricCard
          label="To'lov qilganlar"
          value={fmt(stats.paid)}
          tint="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
          accent="bg-emerald-500"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          sub={
            <span className="text-gray-500 dark:text-slate-400">
              {pct(stats.paid, stats.total).toFixed(1)}% · to'lamagan {fmt(stats.unpaid)}
            </span>
          }
        />
      </div>

      {/* Distribution panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gender + payment */}
        <div className="rounded-3xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700/60 p-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Jins va to'lov bo'yicha taqsimot
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-600 dark:text-slate-300">🙎🏻‍♂️ Erkaklar</span>
                <span className="font-medium tabular-nums text-gray-900 dark:text-white">
                  {fmt(stats.male)} ({pct(stats.male, stats.total).toFixed(1)}%)
                </span>
              </div>
              <Bar value={stats.male} total={stats.total} color="bg-blue-500" />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-600 dark:text-slate-300">🙍🏻‍♀️ Ayollar</span>
                <span className="font-medium tabular-nums text-gray-900 dark:text-white">
                  {fmt(stats.female)} ({pct(stats.female, stats.total).toFixed(1)}%)
                </span>
              </div>
              <Bar value={stats.female} total={stats.total} color="bg-pink-500" />
            </div>
            <div className="pt-2 border-t border-gray-100 dark:border-slate-700">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-600 dark:text-slate-300">✅ To'lov qilgan</span>
                <span className="font-medium tabular-nums text-gray-900 dark:text-white">
                  {fmt(stats.paid)} ({pct(stats.paid, stats.total).toFixed(1)}%)
                </span>
              </div>
              <Bar value={stats.paid} total={stats.total} color="bg-emerald-500" />
            </div>
          </div>

          {/* Graduates */}
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-gray-50 dark:bg-slate-900/40 p-4">
              <p className="text-xs text-gray-500 dark:text-slate-400">🎓 Joriy yil bitiruvchilari</p>
              <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white tabular-nums">
                {fmt(stats.graduated)}
              </p>
            </div>
            <div className="rounded-2xl bg-gray-50 dark:bg-slate-900/40 p-4">
              <p className="text-xs text-gray-500 dark:text-slate-400">🔹 Avvalgi yil bitiruvchilari</p>
              <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white tabular-nums">
                {fmt(stats.graduated_not)}
              </p>
            </div>
          </div>
        </div>

        {/* Language */}
        <div className="rounded-3xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700/60 p-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Ta'lim tili bo'yicha
          </h3>
          <div className="space-y-4">
            {[
              { label: "🇺🇿 O'zbek", v: stats.uz, c: "bg-sky-500" },
              { label: "🇷🇺 Rus", v: stats.ru, c: "bg-violet-500" },
              { label: "📗 Qoraqalpoq", v: stats.qq, c: "bg-amber-500" },
              { label: "🌐 Boshqa", v: stats.lang_other, c: "bg-gray-400" },
            ].map((row) => (
              <div key={row.label}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-gray-600 dark:text-slate-300">{row.label}</span>
                  <span className="font-medium tabular-nums text-gray-900 dark:text-white">
                    {fmt(row.v)} ({pct(row.v, stats.total).toFixed(1)}%)
                  </span>
                </div>
                <Bar value={row.v} total={stats.total} color={row.c} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Region ranking */}
      <div className="rounded-3xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700/60 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Hududlar bo'yicha taqsimot
          <span className="ml-2 text-xs font-normal text-gray-400 dark:text-slate-500">
            ({stats.regions.length} ta hudud)
          </span>
        </h3>
        <div className="space-y-2.5">
          {stats.regions.map((r, i) => {
            const medal = ["🥇", "🥈", "🥉"][i];
            return (
              <div
                key={r.region_name + i}
                className="flex items-center gap-3 rounded-2xl px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-slate-700/40 transition-colors"
              >
                <span className="w-7 shrink-0 text-center text-sm font-semibold text-gray-400 dark:text-slate-500">
                  {medal ?? i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {r.region_name}
                    </span>
                    <span className="text-xs tabular-nums text-gray-500 dark:text-slate-400 shrink-0">
                      {fmt(r.count)} · {r.share.toFixed(1)}%
                    </span>
                  </div>
                  <Bar value={r.count} total={maxRegion} color="bg-primary-500" />
                </div>
              </div>
            );
          })}
          {stats.regions.length === 0 && (
            <p className="text-center text-sm text-gray-400 dark:text-slate-500 py-8">
              Hudud ma'lumotlari yo'q
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
