import { useState } from "react";
import { getPasportInfoApi, type PasportInfoResponse } from "../api";
import { extractErrorMessage } from "../utils/errorMessage";

export default function PasportInfoPage() {
  const [psSer, setPsSer] = useState("");
  const [psNum, setPsNum] = useState("");
  const [imei, setImei] = useState("");

  const [result, setResult] = useState<PasportInfoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // GTSP pasportni JShShIR (PINFL) bilan tekshirgani uchun u majburiy (14 xona).
  const canSubmit =
    psSer.trim().length > 0 &&
    psNum.trim().length > 0 &&
    imei.trim().length === 14 &&
    !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getPasportInfoApi({
        ps_ser: psSer.trim().toUpperCase(),
        ps_num: psNum.trim(),
        imei: imei.trim(),
      });
      setResult(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPsSer("");
    setPsNum("");
    setImei("");
    setResult(null);
    setError(null);
  };

  const fullName = result
    ? [result.last_name, result.first_name, result.middle_name]
        .filter(Boolean)
        .join(" ") || "—"
    : "";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="section-title">Pasport ma'lumotlari</h2>
        <p className="section-subtitle">
          Pasport seriya/raqami va IMEI orqali to'liq ma'lumot olish (GTSP)
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="glass-card p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              Pasport seriyasi *
            </label>
            <input
              type="text"
              value={psSer}
              onChange={(e) =>
                setPsSer(e.target.value.replace(/[^a-zA-Z]/g, "").toUpperCase())
              }
              maxLength={5}
              placeholder="AD"
              className="input-field w-full font-mono uppercase"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              Pasport raqami *
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={psNum}
              onChange={(e) => setPsNum(e.target.value.replace(/\D/g, ""))}
              maxLength={10}
              placeholder="1234567"
              className="input-field w-full font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              JShShIR (PINFL) *
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={imei}
              onChange={(e) => setImei(e.target.value.replace(/\D/g, ""))}
              maxLength={14}
              placeholder="14 ta raqam"
              className="input-field w-full font-mono"
            />
            {imei.length > 0 && imei.length < 14 && (
              <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                JShShIR 14 ta raqamdan iborat bo'lishi kerak ({imei.length}/14)
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 spinner" />
                Olinmoqda...
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                Ma'lumot olish
              </>
            )}
          </button>

          {(psSer || psNum || imei || result || error) && (
            <button
              type="button"
              onClick={handleReset}
              className="btn-secondary"
            >
              Tozalash
            </button>
          )}
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto underline text-xs"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-5">
          {/* === Identity card (rasm + FIO + asosiy) === */}
          <div className="glass-card p-6">
            <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
              {/* Photo */}
              <div className="flex justify-center md:justify-start">
                {result.photo ? (
                  <img
                    src={result.photo}
                    alt="Pasport rasmi"
                    className="w-44 h-56 object-cover rounded-2xl border border-gray-200 dark:border-slate-700 shadow-sm bg-gray-50 dark:bg-slate-800"
                  />
                ) : (
                  <div className="w-44 h-56 rounded-2xl border border-dashed border-gray-300 dark:border-slate-700 flex items-center justify-center text-xs text-gray-400 dark:text-slate-500 text-center px-3">
                    Rasm topilmadi
                  </div>
                )}
              </div>

              {/* Identity fields */}
              <div className="space-y-4">
                <div>
                  <p className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-slate-400 font-medium">
                    To'liq ism
                  </p>
                  <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {fullName}
                    </p>
                    {result.sex_label && (
                      <SexBadge sex={result.sex} label={result.sex_label} />
                    )}
                    {result.livestatus && (
                      <LiveStatusBadge value={result.livestatus} />
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Familiya" value={result.last_name} />
                  <Field label="Ism" value={result.first_name} />
                  <Field label="Otasining ismi" value={result.middle_name} />
                  <Field label="Millati" value={result.nationality} />
                  <Field
                    label="Pasport"
                    value={`${result.ps_ser} ${result.ps_num}`}
                    mono
                  />
                  <Field
                    label="IMEI"
                    value={result.imei || "—"}
                    mono
                  />
                </div>
              </div>
            </div>
          </div>

          {/* === Tug'ilish ma'lumotlari === */}
          <SectionCard
            title="Tug'ilish ma'lumotlari"
            accent="from-emerald-500 to-teal-600"
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            }
          >
            <Field label="Tug'ilgan sanasi" value={formatDate(result.birth_date)} />
            <Field label="Tug'ilgan joyi" value={result.birth_place} />
            <Field label="Tug'ilgan davlati" value={result.birth_country} />
          </SectionCard>

          {/* === Hujjat ma'lumotlari === */}
          <SectionCard
            title="Hujjat ma'lumotlari"
            accent="from-amber-500 to-orange-600"
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            }
          >
            <Field label="Hujjat berilgan joy" value={result.doc_give_place} />
            <Field
              label="Berilgan sana"
              value={formatDate(result.matches_date_begin_document)}
            />
            <Field
              label="Amal qilish muddati"
              value={formatDate(result.matches_date_end_document)}
              valueClassName={
                isExpired(result.matches_date_end_document)
                  ? "text-red-600 dark:text-red-400 font-semibold"
                  : isExpiringSoon(result.matches_date_end_document)
                    ? "text-amber-600 dark:text-amber-400 font-semibold"
                    : ""
              }
            />
          </SectionCard>
        </div>
      )}
    </div>
  );
}

/* ──────────────── helper UI bo'laklari ──────────────── */

function Field({
  label,
  value,
  mono = false,
  valueClassName = "",
}: {
  label: string;
  value: string | null;
  mono?: boolean;
  valueClassName?: string;
}) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-slate-400 font-medium">
        {label}
      </p>
      <p
        className={`text-sm text-gray-800 dark:text-slate-200 mt-0.5 ${
          mono ? "font-mono" : ""
        } ${valueClassName}`}
      >
        {value || "—"}
      </p>
    </div>
  );
}

function SectionCard({
  title,
  accent,
  icon,
  children,
}: {
  title: string;
  accent: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-4">
        <div
          className={`w-9 h-9 rounded-xl bg-gradient-to-br ${accent} flex items-center justify-center shadow-sm`}
        >
          <svg
            className="w-4.5 h-4.5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            {icon}
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {children}
      </div>
    </div>
  );
}

function SexBadge({ sex, label }: { sex: number | null; label: string }) {
  const isMale = sex === 1;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
        isMale
          ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          : "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300"
      }`}
    >
      {label}
    </span>
  );
}

function LiveStatusBadge({ value }: { value: string }) {
  const v = value.toLowerCase();
  const isAlive =
    v.includes("tirik") || v.includes("alive") || v.includes("hayot") || v === "1";
  const isDead =
    v.includes("vafot") || v.includes("dead") || v.includes("o'lgan") || v === "0";
  const cls = isDead
    ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
    : isAlive
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
      : "bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${cls}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isDead ? "bg-red-500" : isAlive ? "bg-emerald-500" : "bg-gray-400"
        }`}
      />
      {value}
    </span>
  );
}

/** GTSP "YYYY-MM-DD" yoki "DD.MM.YYYY" formatlarini "DD.MM.YYYY" ko'rinishiga keltiradi. */
function formatDate(value: string | null): string | null {
  if (!value) return null;
  const v = value.trim();
  // YYYY-MM-DD?
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (iso) return `${iso[3]}.${iso[2]}.${iso[1]}`;
  return v;
}

function parseDate(value: string | null): Date | null {
  if (!value) return null;
  const v = value.trim();
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (iso) return new Date(`${iso[1]}-${iso[2]}-${iso[3]}T00:00:00`);
  const dmy = /^(\d{2})\.(\d{2})\.(\d{4})/.exec(v);
  if (dmy) return new Date(`${dmy[3]}-${dmy[2]}-${dmy[1]}T00:00:00`);
  return null;
}

function isExpired(value: string | null): boolean {
  const d = parseDate(value);
  if (!d) return false;
  return d.getTime() < Date.now();
}

function isExpiringSoon(value: string | null): boolean {
  const d = parseDate(value);
  if (!d) return false;
  const diff = d.getTime() - Date.now();
  return diff > 0 && diff < 1000 * 60 * 60 * 24 * 90; // 90 kun
}
