import type { AttendanceCounts, SmenaInfo } from "../types";

const MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];
const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];

/** `YYYY-MM-DD` ni vaqt zonasiz o'qish (`new Date(str)` UTC deb oladi va kunni surib yuboradi). */
function parseDay(day: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

/** `2026-05-11` → `11-may, 2026` */
export function formatDay(day: string): string {
  const date = parseDay(day);
  if (!date) return day;
  return `${date.getDate()}-${MONTHS[date.getMonth()]}, ${date.getFullYear()}`;
}

/** `2026-05-11` → `Dushanba` */
export function formatWeekday(day: string): string {
  const date = parseDay(day);
  return date ? WEEKDAYS[date.getDay()] : "";
}

export function formatNumber(value: number): string {
  return value.toLocaleString("ru-RU").replace(/ /g, " ");
}

export function attendancePercent(counts: Pick<AttendanceCounts, "total" | "entered">): number {
  if (!counts.total) return 0;
  return Math.round((counts.entered / counts.total) * 1000) / 10;
}

export function sumCounts(items: AttendanceCounts[]): AttendanceCounts {
  return items.reduce(
    (acc, item) => ({
      total: acc.total + item.total,
      entered: acc.entered + item.entered,
      not_entered: acc.not_entered + item.not_entered,
      cheating: acc.cheating + item.cheating,
    }),
    { total: 0, entered: 0, not_entered: 0, cheating: 0 },
  );
}

/** Smenalarni kun bo'yicha guruhlash — backend (kun, smena raqami) tartibida yuboradi. */
export function groupSmenasByDay(smenas: SmenaInfo[]): { day: string; smenas: SmenaInfo[] }[] {
  const groups: { day: string; smenas: SmenaInfo[] }[] = [];
  for (const smena of smenas) {
    const last = groups[groups.length - 1];
    if (last && last.day === smena.day) last.smenas.push(smena);
    else groups.push({ day: smena.day, smenas: [smena] });
  }
  return groups;
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
