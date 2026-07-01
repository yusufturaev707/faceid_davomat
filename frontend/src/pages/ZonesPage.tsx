import { useCallback, useEffect, useState } from "react";
import LookupCrudPage, {
  type Column,
  type FormField,
} from "../components/LookupCrudPage";
import {
  getZonesListApi,
  createZoneApi,
  updateZoneApi,
  deleteZoneApi,
  getRegionsListApi,
  syncZonesFromOtmApi,
  type ZoneSyncResult,
  type ZoneSyncEntry,
} from "../api";
import type { LookupRegionResponse, LookupZoneResponse } from "../interfaces";
import { PERM } from "../permissions";
import PermissionGate from "../components/PermissionGate";
import { extractErrorMessage } from "../utils/errorMessage";

export default function ZonesPage() {
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);

  useEffect(() => {
    getRegionsListApi()
      .then(setRegions)
      .catch((err) =>
        console.error("Hududlar ro'yxatini yuklashda xatolik", err),
      );
  }, []);

  const regionMap = Object.fromEntries(regions.map((r) => [r.id, r.name]));

  // Tartib: avval viloyat raqami (region.number), so'ng shu viloyatning bino
  // raqami (zone.number) bo'yicha. Viloyat raqami topilmasa oxiriga suriladi.
  const sortItems = useCallback(
    (items: LookupZoneResponse[]) => {
      const numMap = new Map(regions.map((r) => [r.id, r.number]));
      return [...items].sort((a, b) => {
        const ra = numMap.get(a.region_id) ?? Number.MAX_SAFE_INTEGER;
        const rb = numMap.get(b.region_id) ?? Number.MAX_SAFE_INTEGER;
        if (ra !== rb) return ra - rb;
        return (a.number ?? 0) - (b.number ?? 0);
      });
    },
    [regions],
  );

  const columns: Column[] = [
    { key: "id", label: "T/r" },
    { key: "name", label: "Nomi" },
    { key: "number", label: "Nomer" },
    {
      key: "region_id",
      label: "Hudud",
      render: (val: number) => regionMap[val] || `#${val}`,
    },
    {
      key: "building_id",
      label: "Bino ID (OTM)",
      render: (val: number | null) => (val == null ? "—" : val),
    },
    { key: "is_part", label: "Qo'shimchami?" },
  ];

  const formFields: FormField[] = [
    { key: "name", label: "Nomi", type: "text", required: true },
    { key: "number", label: "Nomer", type: "number", required: true, min: 1, step: 1 },
    {
      key: "region_id",
      label: "Viloyat",
      type: "select",
      required: true,
      options: regions.map((r) => ({ value: r.id, label: r.name })),
    },
    {
      key: "building_id",
      label: "Bino ID (OTM tashqi tizimi)",
      type: "number",
      min: 1,
      step: 1,
      placeholder: "Musbat butun son — tashqi tizimdagi bino ID (ixtiyoriy)",
    },
    {
      key: "is_part",
      label: "Qo'shimcha hududga tegishlimi?",
      type: "checkbox",
    },
  ];

  return (
    <LookupCrudPage
      title="Binolar"
      subtitle="Test o'tkazish binolari"
      columns={columns}
      formFields={formFields}
      fetchAll={getZonesListApi}
      sortItems={sortItems}
      searchKeys={["name", "number", "building_id"]}
      searchPlaceholder="Bino nomi, raqami yoki OTM ID..."
      rowNumbering
      filters={[
        {
          key: "region_id",
          label: "Viloyat",
          options: regions.map((r) => ({ value: r.id, label: r.name })),
        },
        {
          key: "is_active",
          label: "Holat",
          options: [
            { value: "true", label: "Faol" },
            { value: "false", label: "Nofaol" },
          ],
        },
        {
          key: "is_part",
          label: "Qo'shimcha hududga tegishlimi?",
          options: [
            { value: "true", label: "Ha" },
            { value: "false", label: "Yo'q" },
          ],
        },
      ]}
      createItem={createZoneApi}
      updateItem={updateZoneApi}
      deleteItem={deleteZoneApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
      headerActions={(reload) => (
        <PermissionGate permission={PERM.LOOKUP_CREATE}>
          <OtmZoneSyncButton onSynced={reload} />
        </PermissionGate>
      )}
    />
  );
}

/**
 * "Yangilash" tugmasi — tashqi OTM API'dan binolar ro'yxatini sinxronizatsiya
 * qiladi. Moslik `building_id` <-> tashqi `id` bo'yicha: bor bo'lsa update, yo'q
 * bo'lsa insert. Muvaffaqiyatli bo'lsa, qaysi binolar qo'shilgani/yangilangani
 * (aniq maydon o'zgarishlari bilan) Material Design dialogida ko'rsatiladi.
 */
function OtmZoneSyncButton({
  onSynced,
}: {
  onSynced: () => void | Promise<void>;
}) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<ZoneSyncResult | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  const handleSync = useCallback(async () => {
    if (syncing) return;
    setSyncing(true);
    setErrorToast(null);
    try {
      const r: ZoneSyncResult = await syncZonesFromOtmApi();
      setResult(r);
      await onSynced();
    } catch (err) {
      setErrorToast(extractErrorMessage(err));
    } finally {
      setSyncing(false);
    }
  }, [syncing, onSynced]);

  // Xatolik toast'ini 6 soniyadan keyin avtomatik yopamiz.
  useEffect(() => {
    if (!errorToast) return;
    const t = setTimeout(() => setErrorToast(null), 6000);
    return () => clearTimeout(t);
  }, [errorToast]);

  return (
    <>
      <button
        type="button"
        onClick={handleSync}
        disabled={syncing}
        title="Tashqi OTM API'dan binolar ro'yxatini sinxronizatsiya qilish"
        className="inline-flex items-center gap-2 px-4 h-11 rounded-full text-sm font-semibold border border-primary-600 text-primary-700 hover:bg-primary-600 hover:text-white hover:border-primary-600 disabled:opacity-60 disabled:cursor-not-allowed bg-transparent shadow-sm transition-colors dark:text-primary-400 dark:border-primary-500 dark:hover:bg-primary-500 dark:hover:text-white"
      >
        <svg
          className={`w-[18px] h-[18px] ${syncing ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {syncing ? "Yangilanmoqda…" : "Yangilash"}
      </button>

      {result && (
        <ZoneSyncResultDialog result={result} onClose={() => setResult(null)} />
      )}

      {errorToast && (
        <div className="fixed bottom-5 right-5 z-[60] max-w-sm px-4 py-3 rounded-2xl shadow-lg text-sm font-medium ring-1 animate-modal-panel bg-red-50 text-red-700 ring-red-200/70 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800/50">
          <div className="flex items-start gap-2">
            <span className="font-semibold shrink-0">Xatolik:</span>
            <span className="min-w-0">{errorToast}</span>
          </div>
        </div>
      )}
    </>
  );
}

// Sinxronizatsiyada o'zgargan maydon nomlari (UI yorlig'i).
const ZONE_FIELD_LABELS: Record<string, string> = {
  name: "Nomi",
  number: "Raqami",
  region: "Viloyat",
  is_active: "Holati",
};

function formatSyncValue(v: string | number | boolean | null): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Faol" : "Nofaol";
  return String(v);
}

/**
 * Sinxronizatsiya natijasi — Material Design 3 dialogi. Yuqorida umumiy statistika
 * "chip"lari, pastda qo'shilgan va yangilangan binolar ro'yxati (yangilanganlarda
 * aniq maydon o'zgarishlari: eski -> yangi) ko'rsatiladi.
 */
function ZoneSyncResultDialog({
  result,
  onClose,
}: {
  result: ZoneSyncResult;
  onClose: () => void;
}) {
  const hasDetails =
    result.created_items.length > 0 || result.updated_items.length > 0;

  const stats: { label: string; value: number; tone: string }[] = [
    {
      label: "Qo'shildi",
      value: result.created,
      tone: "bg-emerald-100 text-emerald-700 ring-emerald-200/60 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-800/40",
    },
    {
      label: "Yangilandi",
      value: result.updated,
      tone: "bg-amber-100 text-amber-700 ring-amber-200/60 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-800/40",
    },
    {
      label: "O'zgarishsiz",
      value: result.unchanged,
      tone: "bg-gray-100 text-gray-600 ring-gray-200/60 dark:bg-slate-700/40 dark:text-slate-300 dark:ring-slate-600/40",
    },
  ];
  if (result.skipped_no_region > 0)
    stats.push({
      label: "Viloyatsiz",
      value: result.skipped_no_region,
      tone: "bg-orange-100 text-orange-700 ring-orange-200/60 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-800/40",
    });
  if (result.invalid > 0)
    stats.push({
      label: "Yaroqsiz",
      value: result.invalid,
      tone: "bg-red-100 text-red-700 ring-red-200/60 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800/40",
    });

  return (
    <div
      className="fixed inset-0 bg-black/45 dark:bg-black/65 backdrop-blur-[3px] flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-modal-overlay"
      onClick={onClose}
    >
      <div
        className="md3-dialog w-full sm:max-w-lg max-h-[92vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl safe-pb animate-modal-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 sm:px-6 pt-5 pb-4 border-b border-gray-100 dark:border-slate-700/60">
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 ring-1 bg-primary-100 text-primary-600 ring-primary-200/60 dark:bg-primary-900/30 dark:text-primary-400 dark:ring-primary-800/40">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white leading-tight">
              Sinxronizatsiya yakunlandi
            </h3>
            <p className="text-[12px] text-gray-500 dark:text-slate-400 leading-tight mt-0.5 truncate">
              Tashqi OTM API'dan {result.received} ta yozuv qayta ishlandi
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 -mr-1 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors shrink-0"
            aria-label="Yopish"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-5 sm:px-6 py-5 space-y-5">
          {/* Statistika chiplari */}
          <div className="flex flex-wrap gap-2">
            {stats.map((s) => (
              <span
                key={s.label}
                className={`inline-flex items-center gap-1.5 px-3 h-8 rounded-full text-[13px] font-medium ring-1 ${s.tone}`}
              >
                {s.label}
                <span className="font-bold tabular-nums">{s.value}</span>
              </span>
            ))}
          </div>

          {/* Qo'shilganlar */}
          {result.created_items.length > 0 && (
            <ZoneSyncSection
              title="Qo'shilgan binolar"
              count={result.created_items.length}
              accent="emerald"
            >
              {result.created_items.map((it) => (
                <ZoneSyncCard key={`c-${it.building_id}`} entry={it} kind="created" />
              ))}
            </ZoneSyncSection>
          )}

          {/* Yangilanganlar */}
          {result.updated_items.length > 0 && (
            <ZoneSyncSection
              title="Yangilangan binolar"
              count={result.updated_items.length}
              accent="amber"
            >
              {result.updated_items.map((it) => (
                <ZoneSyncCard key={`u-${it.building_id}`} entry={it} kind="updated" />
              ))}
            </ZoneSyncSection>
          )}

          {!hasDetails && (
            <div className="flex flex-col items-center gap-3 py-8 text-gray-400 dark:text-slate-500">
              <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm font-medium">
                Hech qanday o'zgarish yo'q — barcha binolar dolzarb
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 sm:px-6 pb-5 pt-1">
          <button onClick={onClose} className="btn-primary min-w-[110px]">
            Yopish
          </button>
        </div>
      </div>
    </div>
  );
}

function ZoneSyncSection({
  title,
  count,
  accent,
  children,
}: {
  title: string;
  count: number;
  accent: "emerald" | "amber";
  children: React.ReactNode;
}) {
  const dot =
    accent === "emerald"
      ? "bg-emerald-500"
      : "bg-amber-500";
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <h4 className="text-[13px] font-semibold text-gray-700 dark:text-slate-200">
          {title}
        </h4>
        <span className="text-[11px] font-medium text-gray-400 dark:text-slate-500 tabular-nums">
          ({count})
        </span>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function ZoneSyncCard({
  entry,
  kind,
}: {
  entry: ZoneSyncEntry;
  kind: "created" | "updated";
}) {
  return (
    <div className="rounded-2xl border border-gray-100 dark:border-slate-700/50 bg-gray-50/60 dark:bg-slate-800/30 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-800 dark:text-slate-100 truncate">
            {entry.name}
          </p>
          <p className="text-[12px] text-gray-500 dark:text-slate-400 truncate">
            {entry.region_name ?? "—"} · Nomer {entry.number}
          </p>
        </div>
        <span className="shrink-0 inline-flex items-center px-2 h-6 rounded-md bg-gray-100 dark:bg-slate-700/50 text-gray-500 dark:text-slate-400 font-mono tabular-nums text-[11px] font-medium ring-1 ring-inset ring-gray-200/50 dark:ring-slate-600/40">
          ID {entry.building_id}
        </span>
      </div>

      {kind === "updated" && entry.changes.length > 0 && (
        <ul className="mt-2.5 space-y-1.5 border-t border-gray-100 dark:border-slate-700/50 pt-2.5">
          {entry.changes.map((c, i) => (
            <li key={i} className="flex items-center flex-wrap gap-1.5 text-[12px]">
              <span className="font-medium text-gray-600 dark:text-slate-300">
                {ZONE_FIELD_LABELS[c.field] ?? c.field}:
              </span>
              <span className="px-1.5 py-0.5 rounded-md bg-red-50 text-red-600 line-through dark:bg-red-900/20 dark:text-red-300/80">
                {formatSyncValue(c.old)}
              </span>
              <svg className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              <span className="px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-medium dark:bg-emerald-900/20 dark:text-emerald-300">
                {formatSyncValue(c.new)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
