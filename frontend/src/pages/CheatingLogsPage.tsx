import { useCallback, useEffect, useState } from "react";
import type {
  CheatingLogListResponse,
  CheatingLogCreate,
  CheatingLogUpdate,
  TestResponse,
  LookupRegionResponse,
  LookupZoneResponse,
  SmenaResponse,
  LookupReasonResponse,
  LookupReasonTypeResponse,
} from "../interfaces";
import {
  getCheatingLogsApi,
  createCheatingLogApi,
  updateCheatingLogApi,
  deleteCheatingLogApi,
  getTestsLookupApi,
  getRegionsListApi,
  getZonesByRegionApi,
  getSmenasLookupApi,
  getReasonsListApi,
  getReasonTypesListApi,
  exportCheatingLogsApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import Md3Select from "../components/Md3Select";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

const emptyForm: CheatingLogCreate = {
  student_id: 0,
  reason_id: 0,
  user_id: 0,
  image_path: "",
};

// FIO'dan initsial (2 harf) — avatar uchun.
const initialsOf = (name: string): string => {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
};

// Ism bo'yicha barqaror avatar rangi (Material tonal palitrasi).
const AVATAR_TONES = [
  "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
];
const avatarTone = (key: string): string => {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return AVATAR_TONES[h % AVATAR_TONES.length];
};

const formatDateTime = (s: string | null): string => {
  if (!s) return "—";
  try {
    const d = new Date(s);
    if (isNaN(d.getTime())) return s;
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return s;
  }
};

export default function CheatingLogsPage() {
  const [data, setData] = useState<CheatingLogListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  // Search
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  // Filters
  const [filterTestId, setFilterTestId] = useState("");
  const [filterRegionId, setFilterRegionId] = useState("");
  const [filterZoneId, setFilterZoneId] = useState("");
  const [filterSmenaId, setFilterSmenaId] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterReasonTypeId, setFilterReasonTypeId] = useState("");
  const [filterReasonId, setFilterReasonId] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Lookups
  const [tests, setTests] = useState<TestResponse[]>([]);
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);
  const [zones, setZones] = useState<LookupZoneResponse[]>([]);
  const [smenas, setSmenas] = useState<SmenaResponse[]>([]);
  const [reasons, setReasons] = useState<LookupReasonResponse[]>([]);
  const [reasonTypes, setReasonTypes] = useState<LookupReasonTypeResponse[]>([]);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<CheatingLogCreate>(emptyForm);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const activeFilterCount =
    (filterTestId ? 1 : 0) +
    (filterRegionId ? 1 : 0) +
    (filterZoneId ? 1 : 0) +
    (filterSmenaId ? 1 : 0) +
    (filterDateFrom ? 1 : 0) +
    (filterDateTo ? 1 : 0) +
    (filterReasonTypeId ? 1 : 0) +
    (filterReasonId ? 1 : 0);
  const hasFilters = activeFilterCount > 0 || !!search;

  const resetFilters = () => {
    setFilterTestId("");
    setFilterRegionId("");
    setFilterZoneId("");
    setFilterSmenaId("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setFilterReasonTypeId("");
    setFilterReasonId("");
    setSearch("");
    setSearchInput("");
    setPage(1);
  };

  const handleSearch = () => {
    setSearch(searchInput.trim());
    setPage(1);
  };

  // Lookuplarni mount'da bir marta yuklab olamiz.
  useEffect(() => {
    getTestsLookupApi().then(setTests).catch(() => {});
    getRegionsListApi().then(setRegions).catch(() => {});
    getSmenasLookupApi().then(setSmenas).catch(() => {});
    getReasonsListApi().then(setReasons).catch(() => {});
    getReasonTypesListApi().then(setReasonTypes).catch(() => {});
  }, []);

  // Region → Zone cascade
  useEffect(() => {
    if (!filterRegionId) {
      setZones([]);
      return;
    }
    getZonesByRegionApi(Number(filterRegionId))
      .then(setZones)
      .catch(() => setZones([]));
  }, [filterRegionId]);

  // ReasonType → Reason cascade — agar reason_type tanlangan bo'lsa, faqat
  // shu turdagi sabablar reason dropdown'da ko'rsatiladi.
  const filteredReasons = filterReasonTypeId
    ? reasons.filter(
        (r) => String(r.reason_type_id || "") === filterReasonTypeId,
      )
    : reasons;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = {
        page,
        per_page: perPage,
      };
      if (search) params.search = search;
      if (filterTestId) params.test_id = Number(filterTestId);
      if (filterRegionId) params.region_id = Number(filterRegionId);
      if (filterZoneId) params.zone_id = Number(filterZoneId);
      if (filterSmenaId) params.smena_id = Number(filterSmenaId);
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;
      if (filterReasonTypeId)
        params.reason_type_id = Number(filterReasonTypeId);
      if (filterReasonId) params.reason_id = Number(filterReasonId);
      const result = await getCheatingLogsApi(params);
      setData(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [
    page,
    perPage,
    search,
    filterTestId,
    filterRegionId,
    filterZoneId,
    filterSmenaId,
    filterDateFrom,
    filterDateTo,
    filterReasonTypeId,
    filterReasonId,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Joriy filtrlarni (page/per_page'siz) eksport uchun params'ga yig'adi.
  const buildFilterParams = (): Record<string, string | number> => {
    const params: Record<string, string | number> = {};
    if (search) params.search = search;
    if (filterTestId) params.test_id = Number(filterTestId);
    if (filterRegionId) params.region_id = Number(filterRegionId);
    if (filterZoneId) params.zone_id = Number(filterZoneId);
    if (filterSmenaId) params.smena_id = Number(filterSmenaId);
    if (filterDateFrom) params.date_from = filterDateFrom;
    if (filterDateTo) params.date_to = filterDateTo;
    if (filterReasonTypeId) params.reason_type_id = Number(filterReasonTypeId);
    if (filterReasonId) params.reason_id = Number(filterReasonId);
    return params;
  };

  const handleExport = async () => {
    setExporting(true);
    setError("");
    try {
      await exportCheatingLogsApi(buildFilterParams());
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setFormError("");
    setShowModal(true);
  };

  const openEdit = (log: any) => {
    setEditId(log.id);
    setForm({
      student_id: log.student_id,
      reason_id: log.reason_id,
      user_id: log.user_id,
      image_path: log.image_path || "",
    });
    setFormError("");
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.student_id || !form.reason_id || !form.user_id) {
      setFormError("Student ID, Sabab ID va User ID majburiy");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      if (editId) {
        await updateCheatingLogApi(editId, form as CheatingLogUpdate);
      } else {
        await createCheatingLogApi(form);
      }
      setShowModal(false);
      await fetchData();
    } catch (err: any) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Haqiqatan o'chirmoqchimisiz?")) return;
    try {
      await deleteCheatingLogApi(id);
      await fetchData();
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  const setField = (key: string, value: any) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Qoidabuzarliklar</h2>
          <p className="section-subtitle">
            Cheating holatlari qayd etilgan loglar
          </p>
        </div>
        <PermissionGate permission={PERM.CHEATING_LOG_CREATE}>
          <button
            onClick={openCreate}
            className="btn-primary flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            Yangi qoidabuzarlik
          </button>
        </PermissionGate>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-auto underline text-xs"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Search + Filters */}
      <div className="glass-card p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[220px]">
            <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
              Qidirish
            </label>
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
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
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="FIO yoki JSHSHIR..."
                className="input-field !py-2 !pl-9 !text-sm w-full"
              />
            </div>
          </div>
          <button onClick={handleSearch} className="btn-primary !py-2 text-sm">
            Qidirish
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary !py-2 text-sm flex items-center gap-1.5 ${
              showFilters ? "ring-2 ring-primary-300 dark:ring-primary-600" : ""
            }`}
          >
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
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
              />
            </svg>
            Filterlar
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-primary-500 text-white rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
          {hasFilters && (
            <button
              onClick={resetFilters}
              className="btn-secondary !py-2 text-sm"
            >
              Tozalash
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            title="Joriy filtr bo'yicha chetlatilganlar ro'yxatini Excel (.xlsx) ga yuklab olish"
            className="inline-flex items-center gap-1.5 px-3 !py-2 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed text-white shadow-sm transition-colors"
          >
            {exporting ? (
              <svg
                className="w-4 h-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
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
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            )}
            <span>{exporting ? "Tayyorlanmoqda…" : "Excel"}</span>
          </button>
          <div className="flex items-center gap-3 ml-auto self-center">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 font-semibold">
                Sahifada
              </span>
              <Md3Select
                value={String(perPage)}
                onChange={(v) => {
                  setPerPage(Number(v));
                  setPage(1);
                }}
                options={[10, 20, 50, 100].map((n) => ({
                  value: String(n),
                  label: String(n),
                }))}
                className="w-20"
              />
            </div>
            {data && (
              <span className="text-xs text-gray-400 dark:text-slate-500">
                Jami:{" "}
                <span className="font-semibold text-gray-600 dark:text-slate-300">
                  {data.total}
                </span>{" "}
                ta
              </span>
            )}
          </div>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <FilterSelect
                label="Test"
                value={filterTestId}
                onChange={(v) => {
                  setFilterTestId(v);
                  setPage(1);
                }}
                options={tests.map((t) => ({
                  value: String(t.id),
                  label: t.name,
                }))}
              />
              <FilterSelect
                label="Viloyat"
                value={filterRegionId}
                onChange={(v) => {
                  setFilterRegionId(v);
                  setFilterZoneId("");
                  setPage(1);
                }}
                options={regions.map((r) => ({
                  value: String(r.id),
                  label: r.name,
                }))}
              />
              <FilterSelect
                label="Bino"
                value={filterZoneId}
                onChange={(v) => {
                  setFilterZoneId(v);
                  setPage(1);
                }}
                disabled={!filterRegionId}
                options={zones.map((z) => ({
                  value: String(z.id),
                  label: z.name,
                }))}
              />
              <FilterSelect
                label="Smena"
                value={filterSmenaId}
                onChange={(v) => {
                  setFilterSmenaId(v);
                  setPage(1);
                }}
                options={smenas.map((s) => ({
                  value: String(s.id),
                  label: s.name,
                }))}
              />
              <FilterSelect
                label="Sabab turi"
                value={filterReasonTypeId}
                onChange={(v) => {
                  setFilterReasonTypeId(v);
                  // Sabab turi o'zgarganda — tanlangan sabab boshqa turga
                  // tegishli bo'lib qolishi mumkin, shuni tozalash.
                  setFilterReasonId("");
                  setPage(1);
                }}
                options={reasonTypes.map((rt) => ({
                  value: String(rt.id),
                  label: rt.name,
                }))}
              />
              <FilterSelect
                label="Sababi"
                value={filterReasonId}
                onChange={(v) => {
                  setFilterReasonId(v);
                  setPage(1);
                }}
                options={filteredReasons.map((r) => ({
                  value: String(r.id),
                  label: r.name,
                }))}
              />
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Sana (dan)
                </label>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => {
                    setFilterDateFrom(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Sana (gacha)
                </label>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => {
                    setFilterDateTo(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="glass-card overflow-hidden !p-0">
        {loading ? (
          <PageLoader />
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center mb-3">
              <svg
                className="w-7 h-7 text-gray-300 dark:text-slate-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <p className="text-gray-500 dark:text-slate-400 font-medium">
              Ma'lumot topilmadi
            </p>
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              Tanlangan filtr bo'yicha chetlatilgan yo'q
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-separate border-spacing-0">
              <thead>
                <tr className="bg-gradient-to-b from-gray-50 to-gray-100/70 dark:from-slate-800 dark:to-slate-800/70">
                  {[
                    "Talabgor",
                    "JSHSHIR",
                    "Sabab turi",
                    "Sababi",
                    "Test",
                    "Viloyat",
                    "Bino",
                    "Sana",
                    "Smena",
                    "Chetlatilgan vaqti",
                    "Vakil",
                  ].map((h) => (
                    <th
                      key={h}
                      className="sticky top-0 z-10 bg-inherit px-3 py-3 text-left text-[10.5px] font-bold uppercase tracking-wider text-gray-500 dark:text-slate-400 whitespace-nowrap border-b border-gray-200 dark:border-slate-700"
                    >
                      {h}
                    </th>
                  ))}
                  <th className="sticky top-0 z-10 bg-inherit px-3 py-3 text-center text-[10.5px] font-bold uppercase tracking-wider text-gray-500 dark:text-slate-400 whitespace-nowrap border-b border-gray-200 dark:border-slate-700">
                    Rasm
                  </th>
                  <th className="sticky top-0 z-10 bg-inherit px-3 py-3 text-center text-[10.5px] font-bold uppercase tracking-wider text-gray-500 dark:text-slate-400 whitespace-nowrap border-b border-gray-200 dark:border-slate-700">
                    Amallar
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => {
                  const fio = log.student_full_name || `#${log.student_id}`;
                  return (
                    <tr
                      key={log.id}
                      className="group odd:bg-white even:bg-gray-50/50 dark:odd:bg-transparent dark:even:bg-slate-800/30 hover:bg-primary-50/60 dark:hover:bg-primary-900/15 transition-colors"
                    >
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold ${avatarTone(
                              fio,
                            )}`}
                          >
                            {initialsOf(fio)}
                          </span>
                          <div className="min-w-0">
                            <div className="font-semibold text-gray-800 dark:text-slate-100 truncate max-w-[220px]">
                              {fio}
                            </div>
                            <div className="text-[10.5px] text-gray-400 dark:text-slate-500 tabular-nums">
                              #{log.id}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 whitespace-nowrap">
                        {log.imei ? (
                          <span className="inline-block px-2 py-0.5 rounded-md bg-gray-100 dark:bg-slate-700/60 text-gray-700 dark:text-slate-300 font-mono text-xs tracking-tight">
                            {log.imei}
                          </span>
                        ) : (
                          <span className="text-gray-300 dark:text-slate-600">
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 whitespace-nowrap">
                        {log.rejection_type ? (
                          <span className="inline-flex items-center px-2.5 py-1 text-[11px] font-semibold rounded-full bg-amber-50 text-amber-700 ring-1 ring-amber-200/70 dark:bg-amber-900/20 dark:text-amber-300 dark:ring-amber-800/40">
                            {log.rejection_type}
                          </span>
                        ) : (
                          <span className="text-gray-300 dark:text-slate-600">
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded-full bg-red-50 text-red-700 ring-1 ring-red-200/70 dark:bg-red-900/20 dark:text-red-300 dark:ring-red-800/40">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 dark:bg-red-400" />
                          {log.rejection_reason ||
                            log.reason_name ||
                            `#${log.reason_id}`}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                        {log.test_name || "—"}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                        {log.region_name || "—"}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                        {log.zone_name || "—"}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 whitespace-nowrap tabular-nums">
                        {log.smena_date || "—"}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                        {log.smena_name || "—"}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-500 dark:text-slate-400 text-xs whitespace-nowrap tabular-nums">
                        {formatDateTime(log.rejected_at)}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-gray-600 dark:text-slate-300 text-xs whitespace-nowrap">
                        {log.username || `#${log.user_id}`}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-center">
                        {log.image_path ? (
                          <span
                            className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
                            title="Rasm mavjud"
                          >
                            <svg
                              className="w-3.5 h-3.5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                              />
                            </svg>
                          </span>
                        ) : (
                          <span className="text-gray-300 dark:text-slate-600 text-xs">
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 border-b border-gray-100 dark:border-slate-700/50 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1.5 opacity-70 group-hover:opacity-100 transition-opacity">
                          <PermissionGate permission={PERM.CHEATING_LOG_UPDATE}>
                            <button
                              onClick={() => openEdit(log)}
                              className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors"
                              title="Tahrirlash"
                            >
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
                                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                />
                              </svg>
                            </button>
                          </PermissionGate>
                          <PermissionGate permission={PERM.CHEATING_LOG_DELETE}>
                            <button
                              onClick={() => handleDelete(log.id)}
                              className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-red-500 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30 transition-colors"
                              title="O'chirish"
                            >
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
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                            </button>
                          </PermissionGate>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          onPageChange={setPage}
        />
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editId ? "Qoidabuzarlikni tahrirlash" : "Yangi qoidabuzarlik"}
            </h3>
            {formError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                {formError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Talabgor ID *
                </label>
                <input
                  type="number"
                  value={form.student_id}
                  onChange={(e) =>
                    setField("student_id", Number(e.target.value))
                  }
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Sabab ID *
                </label>
                <input
                  type="number"
                  value={form.reason_id}
                  onChange={(e) =>
                    setField("reason_id", Number(e.target.value))
                  }
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                  User ID *
                </label>
                <input
                  type="number"
                  value={form.user_id}
                  onChange={(e) => setField("user_id", Number(e.target.value))}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Rasm yo'li
                </label>
                <input
                  type="text"
                  value={form.image_path || ""}
                  onChange={(e) =>
                    setField("image_path", e.target.value || null)
                  }
                  className="input-field w-full"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
        {label}
      </label>
      <Md3Select
        value={value}
        onChange={onChange}
        disabled={disabled}
        placeholder="Barchasi"
        clearable
        options={options.map((o) => ({ value: o.value, label: o.label }))}
      />
    </div>
  );
}
