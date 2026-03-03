import { useEffect, useState } from "react";
import type { DailyChartItem, DashboardStats } from "../interfaces";
import { getStatsApi } from "../api";
import StatsCard from "../components/StatsCard";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStatsApi()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!stats) return <p className="text-gray-500">Ma'lumotlar yuklanmadi</p>;

  const maxCount = Math.max(...stats.daily_chart.map((d) => d.count), 1);
  const totalInPeriod = stats.daily_chart.reduce((s, d) => s + d.count, 0);

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard title="Jami tekshiruvlar" value={stats.total_verifications} color="blue" />
        <StatsCard title="Bugun" value={stats.today_verifications} subtitle="tekshiruv" color="green" />
        <StatsCard title="Hafta davomida" value={stats.week_verifications} color="purple" />
        <StatsCard title="Muvaffaqiyat" value={`${stats.success_rate}%`} subtitle={`${stats.unique_users} foydalanuvchi`} color="orange" />
      </div>

      {/* Chart */}
      <BarChart data={stats.daily_chart} maxCount={maxCount} total={totalInPeriod} />
    </div>
  );
}

/** Y o'qi uchun chiroyli grid qiymatlari hisoblash */
function getGridLines(max: number): number[] {
  if (max <= 0) return [0];
  // 4-5 ta grid chiziq
  const steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000];
  const ideal = max / 4;
  const step = steps.find((s) => s >= ideal) || Math.ceil(ideal);
  const lines: number[] = [];
  for (let v = 0; v <= max; v += step) {
    lines.push(v);
  }
  // Eng yuqorisini qo'shish
  if (lines[lines.length - 1] < max) {
    lines.push(lines[lines.length - 1] + step);
  }
  return lines;
}

/** Sana formatlash: "2026-03-01" → "01.03" */
function formatShortDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}.${parts[1]}`;
}

function BarChart({
  data,
  maxCount,
  total,
}: {
  data: DailyChartItem[];
  maxCount: number;
  total: number;
}) {
  const gridLines = getGridLines(maxCount);
  const gridMax = gridLines[gridLines.length - 1] || 1;

  // Har 5-kundan bir label ko'rsatish
  const labelInterval = data.length > 20 ? 5 : data.length > 10 ? 3 : 1;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Sarlavha */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-gray-700">
          Oxirgi 30 kun
        </h3>
        <span className="text-xs text-gray-400 bg-gray-50 px-3 py-1 rounded-full">
          Jami: {total} ta tekshiruv
        </span>
      </div>

      {/* Chart area */}
      <div className="flex">
        {/* Y o'qi raqamlari */}
        <div className="flex flex-col justify-between pr-3 py-0" style={{ height: 200 }}>
          {[...gridLines].reverse().map((val) => (
            <span key={val} className="text-[10px] text-gray-400 leading-none text-right min-w-[24px]">
              {val}
            </span>
          ))}
        </div>

        {/* Barlar va grid */}
        <div className="flex-1 relative" style={{ height: 200 }}>
          {/* Grid chiziqlari */}
          {gridLines.map((val) => {
            const bottom = (val / gridMax) * 100;
            return (
              <div
                key={val}
                className="absolute left-0 right-0 border-t border-gray-100"
                style={{ bottom: `${bottom}%` }}
              />
            );
          })}

          {/* Barlar */}
          <div className="relative flex items-end gap-[2px] h-full z-10">
            {data.map((item) => {
              const heightPercent = (item.count / gridMax) * 100;
              const isEmpty = item.count === 0;
              return (
                <div
                  key={item.date}
                  className="flex-1 flex flex-col items-center group relative"
                  style={{ height: "100%" }}
                >
                  {/* Tooltip */}
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2.5 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 whitespace-nowrap pointer-events-none transition-opacity z-20 shadow-lg">
                    <div className="font-medium">{formatShortDate(item.date)}</div>
                    <div className="text-gray-300">
                      {item.count} tekshiruv
                    </div>
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800" />
                  </div>

                  {/* Bar */}
                  <div className="w-full flex-1 flex items-end">
                    <div
                      className={`w-full rounded-t transition-all duration-150 ${
                        isEmpty
                          ? "bg-gray-100"
                          : "bg-blue-400 group-hover:bg-blue-500"
                      }`}
                      style={{
                        height: isEmpty ? "2px" : `${Math.max(heightPercent, 2)}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* X o'qi — sana labellari */}
      <div className="flex ml-[36px] mt-2">
        {data.map((item, i) => (
          <div key={item.date} className="flex-1 text-center">
            {i % labelInterval === 0 ? (
              <span className="text-[10px] text-gray-400">
                {formatShortDate(item.date)}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
