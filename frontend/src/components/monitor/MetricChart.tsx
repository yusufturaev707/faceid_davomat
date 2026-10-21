import { useRef, useState } from "react";

/* ============================================================
 * Yuklama tarixi uchun bitta ko'rsatkich grafigi (small multiple).
 *
 * Forma: chiziq — vaqt bo'yicha uzluksiz o'lchov. Har grafikda bitta seriya,
 * shuning uchun legenda yo'q: sarlavha nimani ko'rsatayotganini aytadi,
 * oxirgi qiymat va cho'qqi sarlavha qatorida yoziladi. Bir nechta o'lchov
 * (CPU, RAM, tarmoq) bitta o'qqa yig'ilmaydi — har biri o'z grafigida.
 *
 * Rang `primary` tokenidan (yorug'da 600, qorong'ida 500), chiziq 2px.
 * Nuqtalar orasida 3 intervaldan katta bo'shliq bo'lsa (beat to'xtagan) chiziq
 * uziladi — yo'q ma'lumot ustidan yolg'on qiyalik chizilmaydi.
 * Hover: vertikal kursor + eng yaqin nuqta qiymati.
 * ========================================================== */

export interface ChartPoint {
  t: number; // ms
  v: number | null;
}

interface Props {
  title: string;
  points: ChartPoint[];
  format: (v: number) => string;
  /** Berilsa — o'q shu qiymatgacha (foizlar uchun 100). */
  yMax?: number;
  fromMs: number;
  toMs: number;
  intervalMs: number;
}

const W = 1000;
const H = 160;

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const exp = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) {
    if (v <= m * exp) return m * exp;
  }
  return 10 * exp;
}

function clock(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export default function MetricChart({ title, points, format, yMax, fromMs, toMs, intervalMs }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  const values = points.filter((p) => p.v != null) as { t: number; v: number }[];
  const last = values.length ? values[values.length - 1] : null;
  const peak = values.reduce<{ t: number; v: number } | null>(
    (best, p) => (best == null || p.v > best.v ? p : best),
    null,
  );
  const top = yMax ?? niceMax((peak?.v ?? 0) * 1.1);
  const span = Math.max(1, toMs - fromMs);

  const x = (t: number) => ((t - fromMs) / span) * W;
  const y = (v: number) => H - (Math.min(v, top) / top) * H;

  // 1440 nuqtagacha — har renderda qayta hisoblash arzon.
  let line = "";
  let area = "";
  let segStart: number | null = null;
  let prevT: number | null = null;
  let prevX = 0;
  const closeArea = () => {
    if (segStart != null) area += `L${prevX.toFixed(1)},${H}L${segStart.toFixed(1)},${H}Z`;
  };
  for (const p of points) {
    if (p.v == null) {
      closeArea();
      segStart = null;
      prevT = null;
      continue;
    }
    const px = x(p.t);
    const py = y(p.v);
    const gap = prevT != null && p.t - prevT > intervalMs * 3;
    if (segStart == null || gap) {
      if (gap) closeArea();
      line += `M${px.toFixed(1)},${py.toFixed(1)}`;
      area += `M${px.toFixed(1)},${H}L${px.toFixed(1)},${py.toFixed(1)}`;
      segStart = px;
    } else {
      line += `L${px.toFixed(1)},${py.toFixed(1)}`;
      area += `L${px.toFixed(1)},${py.toFixed(1)}`;
    }
    prevT = p.t;
    prevX = px;
  }
  closeArea();

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const box = boxRef.current?.getBoundingClientRect();
    if (!box || values.length === 0) return;
    const t = fromMs + ((e.clientX - box.left) / box.width) * span;
    let best = 0;
    for (let i = 1; i < values.length; i++) {
      if (Math.abs(values[i].t - t) < Math.abs(values[best].t - t)) best = i;
    }
    setHover(best);
  };

  const h = hover != null ? values[hover] : null;

  return (
    <div className="glass-card p-4">
      <div className="flex items-baseline justify-between gap-2 mb-3">
        <h3 className="text-[13px] font-semibold text-gray-900 dark:text-white truncate">{title}</h3>
        <div className="text-right shrink-0">
          <span className="text-[15px] font-bold tabular-nums text-gray-900 dark:text-white">
            {last ? format(last.v) : "—"}
          </span>
          {peak && (
            <span className="ml-2 text-[11px] text-gray-500 dark:text-slate-400 tabular-nums">
              cho'qqi {format(peak.v)}
            </span>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <div className="w-14 shrink-0 h-32 flex flex-col justify-between items-end text-[10px] tabular-nums text-gray-400 dark:text-slate-500">
          <span>{format(top)}</span>
          <span>{format(top / 2)}</span>
          <span>{format(0)}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div
            ref={boxRef}
            className="relative h-32 cursor-crosshair"
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
          >
            {/* Yordamchi chiziqlar — sust */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
              {[0, 1, 2].map((i) => (
                <div key={i} className="border-t border-gray-100 dark:border-slate-700/60" />
              ))}
            </div>
            {values.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center text-[12px] text-gray-400 dark:text-slate-500">
                Ma'lumot yo'q
              </div>
            ) : (
              <svg
                viewBox={`0 0 ${W} ${H}`}
                preserveAspectRatio="none"
                className="absolute inset-0 w-full h-full text-primary-600 dark:text-primary-500 overflow-visible"
                aria-label={`${title} grafigi`}
                role="img"
              >
                <path d={area} fill="currentColor" fillOpacity={0.1} stroke="none" />
                <path
                  d={line}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>
            )}
            {h && (
              <>
                <div
                  className="absolute top-0 bottom-0 w-px bg-gray-400/70 dark:bg-slate-400/60 pointer-events-none"
                  style={{ left: `${(x(h.t) / W) * 100}%` }}
                />
                <div
                  className="absolute w-2.5 h-2.5 -ml-[5px] -mt-[5px] rounded-full bg-primary-600 dark:bg-primary-500 ring-2 ring-white dark:ring-slate-900 pointer-events-none"
                  style={{ left: `${(x(h.t) / W) * 100}%`, top: `${(y(h.v) / H) * 100}%` }}
                />
                <div
                  className="absolute -top-2 z-10 px-2 py-1 rounded-lg bg-gray-900/90 dark:bg-slate-700 text-white pointer-events-none whitespace-nowrap"
                  style={{
                    left: `${(x(h.t) / W) * 100}%`,
                    transform: `translate(${x(h.t) / W > 0.7 ? "calc(-100% - 8px)" : "8px"}, 0)`,
                  }}
                >
                  <p className="text-[12px] font-bold tabular-nums leading-tight">{format(h.v)}</p>
                  <p className="text-[10.5px] text-gray-300 leading-tight">{new Date(h.t).toLocaleString("uz-UZ", { hour12: false })}</p>
                </div>
              </>
            )}
          </div>
          <div className="flex justify-between mt-1 text-[10px] tabular-nums text-gray-400 dark:text-slate-500">
            <span>{clock(fromMs)}</span>
            <span>{clock(fromMs + span / 2)}</span>
            <span>{clock(toMs)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
