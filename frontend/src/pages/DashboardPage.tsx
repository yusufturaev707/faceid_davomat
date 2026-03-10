import { useEffect, useState } from "react";
import type { DailyChartItem, DashboardStats } from "../interfaces";
import { getFaceStatsApi, getStatsApi } from "../api";
import StatsCard from "../components/StatsCard";

export default function DashboardPage() {
  const [photoStats, setPhotoStats] = useState<DashboardStats | null>(null);
  const [faceStats, setFaceStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStatsApi(), getFaceStatsApi()])
      .then(([photo, face]) => { setPhotoStats(photo); setFaceStats(face); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-10 h-10 spinner" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="section-title">Dashboard</h2>
        <p className="section-subtitle">Umumiy statistika va ko'rsatkichlar</p>
      </div>

      {photoStats && (
        <StatsSection
          title="Rasm tekshiruv (verify-photo)"
          stats={photoStats}
          barColor="bg-primary-400 group-hover:bg-primary-500"
        />
      )}

      {faceStats && (
        <StatsSection
          title="Yuz solishtirish (verify-two-face)"
          stats={faceStats}
          barColor="bg-violet-400 group-hover:bg-violet-500"
        />
      )}

      {!photoStats && !faceStats && (
        <div className="glass-card p-12 text-center">
          <p className="text-gray-500 dark:text-slate-400">Ma'lumotlar yuklanmadi</p>
        </div>
      )}
    </div>
  );
}

function StatsSection({ title, stats, barColor }: { title: string; stats: DashboardStats; barColor: string }) {
  const maxCount = Math.max(...stats.daily_chart.map((d) => d.count), 1);
  const totalInPeriod = stats.daily_chart.reduce((s, d) => s + d.count, 0);

  return (
    <div className="mb-10">
      <h3 className="text-lg font-semibold text-gray-700 dark:text-slate-300 mb-4">{title}</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatsCard title="Jami" value={stats.total_verifications} color="primary" icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>} />
        <StatsCard title="Bugun" value={stats.today_verifications} subtitle="tekshiruv" color="green" icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>} />
        <StatsCard title="Hafta davomida" value={stats.week_verifications} color="purple" icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>} />
        <StatsCard title="Muvaffaqiyat" value={`${stats.success_rate}%`} subtitle={`${stats.unique_users} foydalanuvchi`} color="orange" icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
      </div>

      <BarChart data={stats.daily_chart} maxCount={maxCount} total={totalInPeriod} barColor={barColor} />
    </div>
  );
}

function getGridLines(max: number): number[] {
  if (max <= 0) return [0];
  const steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000];
  const ideal = max / 4;
  const step = steps.find((s) => s >= ideal) || Math.ceil(ideal);
  const lines: number[] = [];
  for (let v = 0; v <= max; v += step) lines.push(v);
  if (lines[lines.length - 1] < max) lines.push(lines[lines.length - 1] + step);
  return lines;
}

function formatShortDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}.${parts[1]}`;
}

function BarChart({ data, maxCount, total, barColor = "bg-primary-400 group-hover:bg-primary-500" }: { data: DailyChartItem[]; maxCount: number; total: number; barColor?: string }) {
  const gridLines = getGridLines(maxCount);
  const gridMax = gridLines[gridLines.length - 1] || 1;
  const labelInterval = data.length > 20 ? 5 : data.length > 10 ? 3 : 1;

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">Oxirgi 30 kun</h3>
        <span className="text-xs text-gray-400 dark:text-slate-500 bg-gray-50 dark:bg-slate-800 px-3 py-1 rounded-full">Jami: {total} ta tekshiruv</span>
      </div>

      <div className="flex">
        <div className="flex flex-col justify-between pr-3" style={{ height: 200 }}>
          {[...gridLines].reverse().map((val) => (
            <span key={val} className="text-[10px] text-gray-400 dark:text-slate-500 leading-none text-right min-w-[24px]">{val}</span>
          ))}
        </div>

        <div className="flex-1 relative" style={{ height: 200 }}>
          {gridLines.map((val) => (
            <div key={val} className="absolute left-0 right-0 border-t border-gray-100 dark:border-slate-700/50" style={{ bottom: `${(val / gridMax) * 100}%` }} />
          ))}
          <div className="relative flex items-end gap-[2px] h-full z-10">
            {data.map((item) => {
              const heightPercent = (item.count / gridMax) * 100;
              const isEmpty = item.count === 0;
              return (
                <div key={item.date} className="flex-1 flex flex-col items-center group relative" style={{ height: "100%" }}>
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-800 dark:bg-slate-600 text-white text-xs px-2.5 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none transition-opacity z-20 shadow-lg">
                    <div className="font-medium">{formatShortDate(item.date)}</div>
                    <div className="text-gray-300 dark:text-slate-400">{item.count} tekshiruv</div>
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800 dark:border-t-slate-600" />
                  </div>
                  <div className="w-full flex-1 flex items-end">
                    <div className={`w-full rounded-t transition-all duration-150 ${isEmpty ? "bg-gray-100 dark:bg-slate-700" : barColor}`} style={{ height: isEmpty ? "2px" : `${Math.max(heightPercent, 2)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="flex ml-[36px] mt-2">
        {data.map((item, i) => (
          <div key={item.date} className="flex-1 text-center">
            {i % labelInterval === 0 ? <span className="text-[10px] text-gray-400 dark:text-slate-500">{formatShortDate(item.date)}</span> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
