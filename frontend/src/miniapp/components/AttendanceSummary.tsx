import type { AttendanceCounts } from "../types";
import { attendancePercent, formatNumber } from "../utils/format";
import { Card, ProgressBar } from "./ui";

function Metric({ label, value, className }: { label: string; value: number; className: string }) {
  return (
    <div className="rounded-xl bg-tg-secondary px-3 py-2.5">
      <p className={`text-[20px] font-bold leading-none tabular-nums ${className}`}>{formatNumber(value)}</p>
      <p className="mt-1 text-[12px] text-tg-hint">{label}</p>
    </div>
  );
}

/** Davomat kartasi: foiz, progress va 4 ko'rsatkich (bot formatteridagi bilan bir xil). */
export function AttendanceSummary({
  counts,
  title,
  onClick,
}: {
  counts: AttendanceCounts;
  title?: string;
  onClick?: () => void;
}) {
  const percent = attendancePercent(counts);
  const body = (
    <>
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          {title && <p className="truncate text-[14px] text-tg-hint">{title}</p>}
          <p className="mt-0.5 text-[15px] text-tg-text">
            <span className="text-[28px] font-bold tabular-nums">{formatNumber(counts.entered)}</span>
            <span className="text-tg-hint"> / {formatNumber(counts.total)} keldi</span>
          </p>
        </div>
        <p className="text-[24px] font-bold tabular-nums text-tg-button">{percent}%</p>
      </div>
      <div className="mt-3">
        <ProgressBar value={percent} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <Metric label="Jami" value={counts.total} className="text-tg-text" />
        <Metric label="Kelmagan" value={counts.not_entered} className="text-tg-warning" />
        <Metric label="Chetlatilgan" value={counts.cheating} className="text-tg-destructive" />
      </div>
    </>
  );

  if (!onClick) return <Card>{body}</Card>;
  return (
    <button type="button" onClick={onClick} className="block w-full text-left active:opacity-80">
      <Card>{body}</Card>
    </button>
  );
}
