/** Server monitoringi uchun formatlash yordamchilari. */

const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"];

export function formatBytes(bytes: number | null | undefined, digits = 1): string {
  if (bytes == null || Number.isNaN(bytes)) return "—";
  let v = Math.abs(bytes);
  let i = 0;
  while (v >= 1024 && i < BYTE_UNITS.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : digits)} ${BYTE_UNITS[i]}`;
}

export function formatRate(bytesPerSec: number | null | undefined): string {
  if (bytesPerSec == null) return "—";
  return `${formatBytes(bytesPerSec)}/s`;
}

/** Soniyalarni "3 kun 4 soat" / "12 daq" ko'rinishida. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  const s = Math.max(0, Math.floor(seconds));
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d} kun ${h} soat`;
  if (h > 0) return `${h} soat ${m} daq`;
  if (m > 0) return `${m} daq`;
  return `${s} s`;
}

export function sinceSeconds(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : (Date.now() - t) / 1000;
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("uz-UZ").replace(/,/g, " ");
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("uz-UZ", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

/** Foiz chegaralari — backend `_WARN_PCT` / `_CRIT_PCT` bilan bir xil. */
export const WARN_PCT = 85;
export const CRIT_PCT = 95;

export type Tone = "ok" | "warn" | "crit" | "muted";

export function pctTone(pct: number | null | undefined): Tone {
  if (pct == null) return "muted";
  if (pct >= CRIT_PCT) return "crit";
  if (pct >= WARN_PCT) return "warn";
  return "ok";
}
