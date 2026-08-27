import { useAuth } from "../contexts/AuthContext";
import ThemeSwitcher from "../components/ThemeSwitcher";
import { PERM } from "../permissions";

/* ============================================================
 * Sozlamalar — profil, qamrov va ko'rinish.
 *
 * Material 3 uslubi: tonal sirtlar, yumaloq burchaklar, ma'lumot juftliklari
 * (label ustida kichkina, qiymat ostida qalin). Ranglar faqat holat va
 * urg'u uchun; qolgan matn ink tokenlarida.
 * ========================================================== */

export default function SettingsPage() {
  const { user } = useAuth();

  const isAdmin = user?.role_key === 1;
  const isGlobal =
    isAdmin || (user?.permissions ?? []).includes(PERM.STUDENT_ALL_REGIONS);
  const initial = (user?.full_name || user?.username || "U")
    .charAt(0)
    .toUpperCase();

  return (
    <div className="max-w-3xl mx-auto">
      <div className="page-header">
        <div className="min-w-0">
          <h2 className="section-title">Sozlamalar</h2>
          <p className="section-subtitle">Profil va ko'rinish sozlamalari</p>
        </div>
      </div>

      {/* ── Profil sarlavhasi ───────────────────────────────── */}
      <div className="glass-card p-5 sm:p-7 mb-4">
        <div className="flex items-start gap-4 sm:gap-5">
          <div className="w-16 h-16 shrink-0 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-600/20">
            <span className="text-2xl font-bold text-white">{initial}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {user?.full_name || user?.username}
            </p>
            <p className="text-sm text-gray-500 dark:text-slate-400 truncate">
              @{user?.username}
            </p>
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              <Chip tone="primary">{user?.role || "Rolsiz"}</Chip>
              {user?.is_active ? (
                <Chip tone="emerald">Faol</Chip>
              ) : (
                <Chip tone="rose">Nofaol</Chip>
              )}
              {isAdmin && <Chip tone="violet">Administrator</Chip>}
            </div>
          </div>
        </div>

        {/* Ma'lumot juftliklari */}
        <dl className="mt-6 pt-6 border-t border-gray-100 dark:border-slate-700/70 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          <Field label="Rol" icon={<ShieldIcon />}>
            {user?.role || "—"}
          </Field>
          <Field label="Viloyat" icon={<MapIcon />}>
            {user?.region_name || <Muted>Biriktirilmagan</Muted>}
          </Field>
          <Field label="Bino (uy zonasi)" icon={<BuildingIcon />}>
            {user?.zone_name || <Muted>Biriktirilmagan</Muted>}
          </Field>
          <Field label="Telegram ID" icon={<SendIcon />}>
            {user?.telegram_id || <Muted>Kiritilmagan</Muted>}
          </Field>
        </dl>
      </div>

      {/* ── Ma'lumot qamrovi ────────────────────────────────── */}
      <div className="surface-tonal p-5 sm:p-6 mb-4">
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 shrink-0 rounded-xl flex items-center justify-center ${
              isGlobal
                ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
                : "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
            }`}
          >
            <span className="w-[18px] h-[18px]">
              <GlobeIcon />
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-gray-800 dark:text-slate-200">
              Ma'lumot qamrovi
            </p>
            <p className="text-[13px] text-gray-600 dark:text-slate-400 mt-0.5 leading-relaxed">
              {isGlobal ? (
                <>
                  Siz <strong>barcha viloyatlar</strong> ma'lumotini ko'rasiz.
                </>
              ) : user?.region_name ? (
                <>
                  Siz faqat <strong>{user.region_name}</strong> ma'lumotini
                  ko'rasiz — talabgorlar, davomat va chetlatilganlar shu viloyat
                  bo'yicha filtrlanadi.
                </>
              ) : (
                <>
                  Sizga viloyat biriktirilmagan, shuning uchun talabgorlar
                  ro'yxati ochilmaydi. Administratorga murojaat qiling.
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* ── Ko'rinish ───────────────────────────────────────── */}
      <div className="glass-card p-5 sm:p-7">
        <h3 className="text-base font-semibold text-gray-800 dark:text-slate-200 mb-5">
          Ko'rinish
        </h3>
        <ThemeSwitcher />
      </div>
    </div>
  );
}

/* ── Kichik qismlar ─────────────────────────────────────── */

function Field({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="w-4 h-4 mt-[3px] shrink-0 text-gray-400 dark:text-slate-500">
        {icon}
      </span>
      <div className="min-w-0">
        <dt className="label-text mb-0.5">{label}</dt>
        <dd className="text-sm font-medium text-gray-800 dark:text-slate-200 break-words">
          {children}
        </dd>
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-normal text-gray-400 dark:text-slate-500">
      {children}
    </span>
  );
}

const CHIP_TONES: Record<string, string> = {
  primary:
    "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300",
  emerald:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  rose: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  violet:
    "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
};

function Chip({
  tone,
  children,
}: {
  tone: keyof typeof CHIP_TONES;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`px-2.5 py-0.5 rounded-full text-[11.5px] font-semibold ${CHIP_TONES[tone]}`}
    >
      {children}
    </span>
  );
}

/* ── Ikonkalar (Material uslubidagi outline) ─────────────── */

const svg = (d: string) => (
  <svg
    className="w-full h-full"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d} />
  </svg>
);

const ShieldIcon = () =>
  svg(
    "M9 12l2 2 4-4M12 3l7 4v5c0 4.418-2.94 8.165-7 9-4.06-.835-7-4.582-7-9V7l7-4z",
  );
const MapIcon = () =>
  svg(
    "M17.657 16.657L13.414 20.9a2 2 0 01-2.828 0l-4.244-4.243a8 8 0 1111.314 0zM15 11a3 3 0 11-6 0 3 3 0 016 0z",
  );
const BuildingIcon = () =>
  svg(
    "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5m14 0h2m-2 0h-4m-6 0H3m2 0h4M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  );
const SendIcon = () => svg("M12 19l9 2-9-18-9 18 9-2zm0 0v-8");
const GlobeIcon = () =>
  svg(
    "M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9",
  );
