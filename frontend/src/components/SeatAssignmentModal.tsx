import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  assignSeatsApi,
  getProctoringSchedulesApi,
  getSeatAssignmentSummaryApi,
  type ProctoringSchedule,
  type SeatAssignmentResult,
  type SmenaSeatSummary,
} from "../api";
import { extractErrorMessage } from "../utils/errorMessage";
import Md3Select from "./Md3Select";

/**
 * «Kompyuterlarni biriktirish» — Proctoring'dagi ishchi kompyuterlar
 * nomzodlarga o'tirish o'rni (`sp_n`) sifatida yoziladi.
 *
 * UCH QADAM, ekranda ham uch bo'lim: kun+smena → Proctoring sessiyasi →
 * tekshirish va biriktirish. «Tekshirish» hech narsa yozmaydi — biriktirish
 * 10 minglab nomzodning `sp_n` ini o'zgartiradi va admin sonlarni (kompyuter
 * yetadimi, qaysi bino Proctoring'da topilmadi) OLDIN ko'rishi kerak.
 */

const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];

const fmtNum = (n: number) => n.toLocaleString("ru-RU");

/** "2026-05-11" → "11-may, 2026" (sana satri — vaqt zonasi siljimasin). */
function fmtDay(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d}-${UZ_MONTHS[m - 1]}, ${y}`;
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });

export default function SeatAssignmentModal({
  sessionId,
  onClose,
}: {
  sessionId: number;
  onClose: () => void;
}) {
  const [smenas, setSmenas] = useState<SmenaSeatSummary[]>([]);
  const [schedules, setSchedules] = useState<ProctoringSchedule[]>([]);
  const [smenaId, setSmenaId] = useState("");
  const [scheduleId, setScheduleId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"check" | "assign" | null>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<SeatAssignmentResult | null>(null);
  const [done, setDone] = useState<SeatAssignmentResult | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([getSeatAssignmentSummaryApi(sessionId), getProctoringSchedulesApi()])
      .then(([summary, list]) => {
        if (!alive) return;
        setSmenas(summary);
        setSchedules(list);
      })
      .catch((e) => alive && setError(extractErrorMessage(e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [sessionId]);

  // ESC — MD3 dialog xulqi (ish ketayotganda yopilmaydi).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !busy && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  const smena = smenas.find((s) => String(s.session_smena_id) === smenaId);
  const schedule = schedules.find((s) => String(s.id) === scheduleId);

  // Faqat SHU SANADAGI Proctoring sessiyalari — boshqa kunga biriktirish
  // oson qilinadigan va qimmatga tushadigan xato. Mos sana topilmasa hammasi.
  const sameDay = useMemo(
    () => (smena ? schedules.filter((s) => s.exam_date === smena.day) : []),
    [schedules, smena],
  );
  const scheduleChoices = smena && sameDay.length ? sameDay : schedules;

  // Tanlov o'zgarsa eski hisobot endi boshqa savolga javob.
  useEffect(() => {
    setPreview(null);
    setDone(null);
    setError("");
  }, [smenaId, scheduleId]);

  // Smena tanlanganda — oldin shu smenaga biriktirilgan sessiya bo'lsa, u.
  useEffect(() => {
    if (!smena) return;
    const previous = smena.schedule_ids.find((id) => schedules.some((s) => s.id === id));
    setScheduleId(previous ? String(previous) : "");
  }, [smena, schedules]);

  const run = async (dryRun: boolean) => {
    setBusy(dryRun ? "check" : "assign");
    setError("");
    try {
      const result = await assignSeatsApi(sessionId, {
        session_smena_id: Number(smenaId),
        schedule_id: Number(scheduleId),
        dry_run: dryRun,
      });
      if (dryRun) {
        setPreview(result);
      } else {
        setDone(result);
        setPreview(null);
        setSmenas(await getSeatAssignmentSummaryApi(sessionId));
      }
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const report = done ?? preview;
  const step = !smena ? 1 : !schedule ? 2 : 3;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && !busy && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="seat-dialog-title"
        className="flex w-full sm:max-w-4xl max-h-[94vh] sm:max-h-[90vh] flex-col overflow-hidden rounded-t-[28px] sm:rounded-[28px] bg-white dark:bg-slate-800 shadow-2xl"
      >
        {/* Sarlavha */}
        <div className="flex items-start gap-4 px-6 pt-6 pb-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
            <DesktopIcon className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 id="seat-dialog-title" className="text-[22px] font-semibold leading-tight text-gray-900 dark:text-white">
              Kompyuterlarni biriktirish
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
              Proctoring'dagi ishchi kompyuterlar nomzodlarning o'tirish o'rni bo'ladi
            </p>
          </div>
          <button onClick={onClose} disabled={!!busy} aria-label="Yopish" className="btn-icon -mr-2 -mt-1">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tana */}
        <div className="flex-1 space-y-5 overflow-y-auto px-6 pb-6">
          <Notice tone="info" title="Qanday ishlaydi">
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>
                Har bino ichida kompyuterlar nomzodlarga <b>guruh va familiya tartibida</b> beriladi —
                raqam <code className="rounded bg-black/5 px-1 dark:bg-white/10">sp_n</code> ga yoziladi
                va Face ID ekranida <b>«JOY»</b> bo'lib ko'rinadi.
              </li>
              <li>
                Kompyuter faqat <b>ariza bermagan</b> nomzodlarga beriladi. Arizali nomzodlar sonda ham
                hisoblanmaydi; keyin ariza bergan nomzodning joyi qayta biriktirilganda bo'shaydi.
              </li>
              <li>Qayta ishga tushirish to'g'ri biriktiruvlarga tegmaydi — faqat buzilgan yoki yangi joylar o'zgaradi.</li>
              <li>
                Desktop client ma'lumotni <b>biriktirishdan keyin</b> yuklab olishi kerak.
              </li>
            </ul>
          </Notice>

          {error && <Notice tone="error" title="Xatolik">{error}</Notice>}

          {loading ? (
            <div className="space-y-4">
              {[0, 1].map((i) => (
                <div key={i} className="h-14 animate-pulse rounded-2xl bg-gray-100 dark:bg-slate-700/50" />
              ))}
            </div>
          ) : (
            <>
              <Step number={1} title="Kun va smena" done={step > 1} active={step === 1}>
                <Md3Select
                  size="lg"
                  ariaLabel="Kun va smena"
                  value={smenaId}
                  onChange={setSmenaId}
                  placeholder="Qaysi kun va smena uchun?"
                  options={smenas.map((s) => ({
                    value: String(s.session_smena_id),
                    label: `${fmtDay(s.day)} · ${s.smena_name}`,
                    sublabel:
                      s.assigned === 0
                        ? `${fmtNum(s.candidates)} nomzod · hali biriktirilmagan`
                        : `${fmtNum(s.candidates)} nomzod · biriktirilgan: ${fmtNum(s.assigned)}`,
                    dot:
                      s.assigned === 0
                        ? "bg-gray-300 dark:bg-slate-500"
                        : s.assigned >= s.candidates
                          ? "bg-emerald-500"
                          : "bg-amber-500",
                  }))}
                />
                {smena && <CoverageBar assigned={smena.assigned} total={smena.candidates} />}
              </Step>

              <Step number={2} title="Proctoring sessiyasi" done={step > 2} active={step === 2} disabled={!smena}>
                <Md3Select
                  size="lg"
                  ariaLabel="Proctoring sessiyasi"
                  value={scheduleId}
                  onChange={setScheduleId}
                  disabled={!smena}
                  placeholder={smena ? "Ochiq sessiyani tanlang" : "Avval kun va smenani tanlang"}
                  options={scheduleChoices.map((s) => ({
                    value: String(s.id),
                    label: s.exam_name,
                    sublabel: `${fmtDay(s.exam_date)} · ${fmtTime(s.starts_at)}–${fmtTime(s.ends_at)} · ${
                      s.zone ? `${s.zone.zone_name} (${s.zone.region_name})` : "Barcha binolar"
                    }`,
                  }))}
                />
                {smena && schedules.length === 0 && (
                  <Notice tone="warning" title="Ochiq sessiya yo'q">
                    Proctoring'da tugamagan imtihon jadvali topilmadi. Uni Proctoring panelidagi
                    «Imtihon jadvali» bo'limida yarating.
                  </Notice>
                )}
                {smena && schedules.length > 0 && !sameDay.length && (
                  <Notice tone="warning" title="Sana mos kelmadi">
                    {fmtDay(smena.day)} uchun Proctoring sessiyasi yo'q — barcha ochiq sessiyalar
                    ko'rsatildi. Sanani tekshirib tanlang.
                  </Notice>
                )}
                {schedule && (
                  <div className="flex flex-wrap gap-2">
                    <Chip icon={<CalendarIcon />}>{fmtDay(schedule.exam_date)}</Chip>
                    <Chip icon={<ClockIcon />}>
                      {fmtTime(schedule.starts_at)}–{fmtTime(schedule.ends_at)}
                    </Chip>
                    <Chip icon={<BuildingIcon />}>
                      {schedule.zone ? schedule.zone.zone_name : "Barcha binolar"}
                    </Chip>
                  </div>
                )}
              </Step>

              <Step number={3} title="Tekshirish va biriktirish" done={!!done} active={step === 3} disabled={!schedule}>
                {!report && (
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    «Tekshirish» bosilganda bino kesimida hisobot chiqadi — hali hech narsa yozilmaydi.
                  </p>
                )}
                {report && <SeatReport report={report} />}
                {done && (
                  <Notice tone="success" title="Biriktirildi">
                    {fmtNum(done.changed_rows)} ta nomzodning o'rni yangilandi. Desktop client'larda
                    ma'lumotni qayta yuklab oling — ekrandagi «JOY» shundan keyin yangilanadi.
                  </Notice>
                )}
              </Step>
            </>
          )}
        </div>

        {/* Amallar */}
        {/* Telefonda ikki asosiy amal yonma-yon (yopish — sarlavhadagi ×):
            ustma-ust uch tugma ro'yxatdan ~200 px joy olardi. */}
        <div className="grid grid-cols-2 gap-2 border-t border-gray-200 px-6 py-4 dark:border-slate-700 sm:flex sm:items-center">
          <p className="col-span-2 text-xs text-gray-500 dark:text-slate-400 sm:mr-auto">
            {preview
              ? preview.changed_rows
                ? `${fmtNum(preview.changed_rows)} ta nomzodning o'rni o'zgaradi`
                : "O'zgarish yo'q — hammasi biriktirilgan"
              : "Avval tekshiring, keyin biriktiring"}
          </p>
          <button onClick={onClose} className="btn-text hidden justify-center sm:inline-flex" disabled={!!busy}>
            Yopish
          </button>
          <button
            onClick={() => run(true)}
            disabled={!!busy || !smenaId || !scheduleId}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-primary-100 px-5 text-sm font-medium text-primary-800 transition hover:bg-primary-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-primary-900/40 dark:text-primary-200 dark:hover:bg-primary-900/60"
          >
            {busy === "check" ? <Spinner /> : <SearchIcon />}
            {busy === "check" ? "Tekshirilmoqda..." : "Tekshirish"}
          </button>
          <button
            onClick={() => run(false)}
            className="btn-primary"
            disabled={!!busy || !preview || preview.changed_rows === 0}
            title={!preview ? "Avval «Tekshirish» ni bosing" : undefined}
          >
            {busy === "assign" ? <Spinner /> : <CheckIcon />}
            {busy === "assign" ? "Biriktirilmoqda..." : "Biriktirish"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Hisobot ────────────────────────────────────────────────────────────

function SeatReport({ report }: { report: SeatAssignmentResult }) {
  const t = report.totals;
  const tiles: { label: string; value: number; hint: string; tone: string }[] = [
    { label: "Nomzodlar", value: t.candidates, hint: "JShShIR bo'yicha", tone: "text-gray-900 dark:text-white" },
    { label: "Kompyuterlar", value: t.computers, hint: "ishchi va bo'sh", tone: "text-gray-900 dark:text-white" },
    { label: "Saqlanadi", value: t.kept, hint: "joyi o'zgarmaydi", tone: "text-emerald-600 dark:text-emerald-400" },
    { label: "Yangi", value: t.assigned, hint: "joy beriladi", tone: "text-primary-600 dark:text-primary-400" },
    {
      label: "Joysiz",
      value: t.unassigned,
      hint: t.unassigned ? "kompyuter yetmadi" : "hammaga yetdi",
      tone: t.unassigned ? "text-red-600 dark:text-red-400" : "text-gray-900 dark:text-white",
    },
  ];

  return (
    <div className="space-y-4">
      {report.dry_run && (
        <div className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          <EyeIcon /> Tekshiruv natijasi — hali hech narsa yozilmagan
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {tiles.map((tile) => (
          <div key={tile.label} className="surface-tonal px-4 py-3">
            <div className="text-xs font-medium text-gray-500 dark:text-slate-400">{tile.label}</div>
            <div className={`mt-1 text-2xl font-bold tabular-nums ${tile.tone}`}>{fmtNum(tile.value)}</div>
            <div className="text-[11px] text-gray-400 dark:text-slate-500">{tile.hint}</div>
          </div>
        ))}
      </div>

      {t.unassigned > 0 && (
        <Notice tone="error" title={`${fmtNum(t.unassigned)} ta nomzodga kompyuter yetmadi`}>
          Ularning o'rni bo'sh qoladi (Face ID ekranida «—»). Proctoring'da kompyuter qo'shing yoki
          buzilgan deb belgilanganlarni tekshiring, so'ng qayta tekshiring.
        </Notice>
      )}

      {report.missing_zones.length > 0 && (
        <Notice tone="warning" title="Bu binolar Proctoring sessiyasida yo'q — ularga tegilmaydi">
          <div className="mt-2 flex flex-wrap gap-2">
            {report.missing_zones.map((z) => (
              <span
                key={z.zone_id}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300/70 bg-white/70 px-2.5 py-1 text-xs font-medium text-amber-900 dark:border-amber-700/60 dark:bg-slate-900/40 dark:text-amber-200"
              >
                {z.zone_name}
                <span className="text-amber-700/70 dark:text-amber-300/70">
                  {z.region_number}-{z.zone_number} · {fmtNum(z.candidates)} nomzod
                </span>
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs">
            Bino raqami Proctoring'dagi bilan mos bo'lishi kerak: viloyat raqami (DTM) + bino raqami.
          </p>
        </Notice>
      )}

      {report.zones.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-gray-200 dark:border-slate-700">
          <div className="max-h-72 overflow-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead className="sticky top-0 bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:bg-slate-700/60 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 text-left">Bino</th>
                  <th className="px-4 py-3 text-right">Nomzod</th>
                  <th className="px-4 py-3 text-right">Kompyuter</th>
                  <th className="px-4 py-3 text-right">Saqlanadi</th>
                  <th className="px-4 py-3 text-right">Yangi</th>
                  <th className="px-4 py-3 text-right">Joysiz</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {report.zones.map((z) => (
                  <tr key={z.zone_id} className={z.unassigned ? "bg-red-50/60 dark:bg-red-900/10" : ""}>
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-gray-900 dark:text-white">{z.zone_name}</div>
                      <div className="text-xs text-gray-400 dark:text-slate-500">
                        {z.region_number}-viloyat · {z.zone_number}-bino
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmtNum(z.candidates)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmtNum(z.computers)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-emerald-600 dark:text-emerald-400">
                      {fmtNum(z.kept)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-primary-600 dark:text-primary-400">
                      {fmtNum(z.assigned)}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right tabular-nums ${
                        z.unassigned ? "font-bold text-red-600 dark:text-red-400" : "text-gray-400"
                      }`}
                    >
                      {fmtNum(z.unassigned)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Kichik MD3 bo'laklar ───────────────────────────────────────────────

function Step({
  number,
  title,
  done,
  active,
  disabled,
  children,
}: {
  number: number;
  title: string;
  done?: boolean;
  active?: boolean;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={`flex gap-4 ${disabled ? "opacity-60" : ""}`}>
      <div className="flex flex-col items-center">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors ${
            done
              ? "bg-primary-600 text-white"
              : active
                ? "bg-primary-100 text-primary-800 ring-2 ring-primary-500 dark:bg-primary-900/50 dark:text-primary-200"
                : "bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400"
          }`}
        >
          {done ? <CheckIcon className="h-4 w-4" /> : number}
        </div>
        <div className="mt-2 w-px flex-1 bg-gray-200 dark:bg-slate-700" />
      </div>
      <div className="min-w-0 flex-1 space-y-3 pb-2">
        <h4 className="pt-1 text-base font-semibold text-gray-900 dark:text-white">{title}</h4>
        {children}
      </div>
    </section>
  );
}

const NOTICE_TONES = {
  info: {
    box: "bg-primary-50 border-primary-200 text-primary-900 dark:bg-primary-900/20 dark:border-primary-800 dark:text-primary-100",
    icon: "text-primary-600 dark:text-primary-300",
    path: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  warning: {
    box: "bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-100",
    icon: "text-amber-600 dark:text-amber-300",
    path: "M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z",
  },
  error: {
    box: "bg-red-50 border-red-200 text-red-900 dark:bg-red-900/20 dark:border-red-800 dark:text-red-100",
    icon: "text-red-600 dark:text-red-300",
    path: "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  success: {
    box: "bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-100",
    icon: "text-emerald-600 dark:text-emerald-300",
    path: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
} as const;

function Notice({
  tone,
  title,
  children,
}: {
  tone: keyof typeof NOTICE_TONES;
  title: string;
  children: ReactNode;
}) {
  const t = NOTICE_TONES[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex gap-3 rounded-2xl border px-4 py-3.5 ${t.box}`}>
      <svg className={`mt-0.5 h-5 w-5 shrink-0 ${t.icon}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={t.path} />
      </svg>
      <div className="min-w-0 flex-1 text-sm leading-relaxed">
        <div className="font-semibold">{title}</div>
        <div className="opacity-90">{children}</div>
      </div>
    </div>
  );
}

function CoverageBar({ assigned, total }: { assigned: number; total: number }) {
  const pct = total ? Math.min(100, Math.round((assigned / total) * 100)) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700">
        <div
          className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-emerald-500" : pct ? "bg-amber-500" : "bg-gray-300"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="shrink-0 text-xs font-medium tabular-nums text-gray-500 dark:text-slate-400">
        Biriktirilgan {fmtNum(assigned)} / {fmtNum(total)} ({pct}%)
      </span>
    </div>
  );
}

function Chip({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-gray-300 px-3 text-sm text-gray-700 dark:border-slate-600 dark:text-slate-200">
      <span className="text-gray-500 dark:text-slate-400">{icon}</span>
      {children}
    </span>
  );
}

// ─── Ikonkalar ──────────────────────────────────────────────────────────

function Icon({ d, className = "h-4 w-4" }: { d: string; className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d} />
    </svg>
  );
}
const DesktopIcon = ({ className }: { className?: string }) => (
  <Icon className={className} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
);
const CheckIcon = ({ className }: { className?: string }) => <Icon className={className} d="M5 13l4 4L19 7" />;
const SearchIcon = () => <Icon d="M21 21l-4.35-4.35M17 10.5a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />;
const EyeIcon = () => (
  <Icon d="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.46 12C3.73 7.94 7.52 5 12 5s8.27 2.94 9.54 7c-1.27 4.06-5.06 7-9.54 7s-8.27-2.94-9.54-7z" />
);
const CalendarIcon = () => <Icon d="M8 7V3m8 4V3M4 11h16M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />;
const ClockIcon = () => <Icon d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />;
const BuildingIcon = () => <Icon d="M3 21h18M5 21V5a2 2 0 012-2h10a2 2 0 012 2v16M9 7h1m4 0h1M9 11h1m4 0h1M9 15h1m4 0h1" />;

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />;
}
