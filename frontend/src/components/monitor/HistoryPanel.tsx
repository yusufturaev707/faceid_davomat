import { useCallback, useEffect, useState } from "react";
import { getServerHistoryApi } from "../../api";
import type { MonitorHistoryPoint, MonitorHistoryResponse } from "../../interfaces";
import { extractErrorMessage } from "../../utils/errorMessage";
import { formatRate } from "./format";
import MetricChart, { type ChartPoint } from "./MetricChart";

/**
 * Yuklama tarixi — Celery beat har daqiqada yozgan nuqtalar (24 soatgacha).
 * Har ko'rsatkich o'z grafigida (small multiples) — turli birliklar bitta
 * o'qqa yig'ilmaydi.
 */

const RANGES = [
  { minutes: 60, label: "1 soat" },
  { minutes: 360, label: "6 soat" },
  { minutes: 1440, label: "24 soat" },
];

const pct = (v: number) => `${v.toFixed(0)}%`;
const count = (v: number) => (v >= 10 ? v.toFixed(0) : v.toFixed(1).replace(/\.0$/, ""));

type Key = keyof Omit<MonitorHistoryPoint, "t">;

const CHARTS: { key: Key; title: string; format: (v: number) => string; yMax?: number }[] = [
  { key: "cpu", title: "CPU yuklamasi", format: pct, yMax: 100 },
  { key: "mem", title: "RAM band", format: pct, yMax: 100 },
  { key: "load1", title: "Load average (1 daq)", format: count },
  { key: "disk", title: "Disk band (ilova bo'limi)", format: pct, yMax: 100 },
  { key: "net_rx", title: "Tarmoq — kiruvchi", format: formatRate },
  { key: "net_tx", title: "Tarmoq — chiquvchi", format: formatRate },
  { key: "disk_r", title: "Disk — o'qish", format: formatRate },
  { key: "disk_w", title: "Disk — yozish", format: formatRate },
  { key: "q_verify", title: "Celery verify navbati", format: count },
  { key: "db_conn", title: "PostgreSQL ulanishlari", format: count },
];

export default function HistoryPanel() {
  const [minutes, setMinutes] = useState(60);
  const [data, setData] = useState<MonitorHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setData(await getServerHistoryApi(minutes));
      setError(null);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [minutes]);

  useEffect(() => {
    setLoading(true);
    load();
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 60000);
    return () => clearInterval(id);
  }, [load]);

  const toMs = Date.now();
  const fromMs = toMs - minutes * 60000;
  const intervalMs = (data?.interval_seconds ?? 60) * 1000;
  const points = data?.points ?? [];
  const series = (key: Key): ChartPoint[] =>
    points.map((p) => ({ t: new Date(p.t).getTime(), v: p[key] as number | null }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] text-gray-500 dark:text-slate-400">
          Har daqiqada bitta o'lchov (Celery beat → <code>tasks.monitor_sample</code>), 24 soat saqlanadi.
        </p>
        <div className="inline-flex rounded-full bg-gray-100 dark:bg-slate-800 p-1">
          {RANGES.map((r) => (
            <button
              key={r.minutes}
              type="button"
              onClick={() => setMinutes(r.minutes)}
              className={`px-4 h-8 rounded-full text-[12.5px] font-medium transition-colors ${
                minutes === r.minutes
                  ? "bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-[13px] bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </div>
      )}
      {!loading && !error && points.length === 0 && (
        <div className="rounded-xl px-4 py-3 text-[13px] bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          Tarix hali yo'q. Celery beat va storage worker ishlayotganini tekshiring — birinchi nuqta
          bir daqiqada paydo bo'ladi.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {CHARTS.map((c) => (
          <MetricChart
            key={c.key}
            title={c.title}
            points={series(c.key)}
            format={c.format}
            yMax={c.yMax}
            fromMs={fromMs}
            toMs={toMs}
            intervalMs={intervalMs}
          />
        ))}
      </div>
    </div>
  );
}
