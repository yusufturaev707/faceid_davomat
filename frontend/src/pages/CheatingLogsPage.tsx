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

      <div className="glass-card overflow-hidden">
        {loading ? (
          <PageLoader />
        ) : !data || data.items.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">
            Ma'lumot topilmadi
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    ID
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    FIO
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    JSHSHIR
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Sabab turi
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Sababi
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Test
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Viloyat
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Bino
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Sana
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Smena
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Chetlatilgan vaqti
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Vakil
                  </th>
                  <th className="px-3 py-3 text-center font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Rasm
                  </th>
                  <th className="px-3 py-3 text-center font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    Amallar
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr
                    key={log.id}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition"
                  >
                    <td className="px-3 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                      #{log.id}
                    </td>
                    <td className="px-3 py-3 font-medium text-gray-800 dark:text-slate-200 whitespace-nowrap">
                      {log.student_full_name || `#${log.student_id}`}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 font-mono text-xs whitespace-nowrap">
                      {log.imei || "—"}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      {log.rejection_type ? (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                          {log.rejection_type}
                        </span>
                      ) : (
                        <span className="text-gray-300 dark:text-slate-600">
                          —
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                        {log.rejection_reason || log.reason_name || `#${log.reason_id}`}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {log.test_name || "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {log.region_name || "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {log.zone_name || "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {log.smena_date || "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {log.smena_name || "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 text-xs whitespace-nowrap">
                      {formatDateTime(log.rejected_at)}
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-slate-400 text-xs whitespace-nowrap">
                      {log.username || `#${log.user_id}`}
                    </td>
                    <td className="px-3 py-3 text-center">
                      {log.image_path ? (
                        <span
                          className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500"
                          title="Rasm mavjud"
                        />
                      ) : (
                        <span className="text-gray-300 dark:text-slate-600 text-xs">
                          —
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-2">
                        <PermissionGate permission={PERM.CHEATING_LOG_UPDATE}>
                          <button
                            onClick={() => openEdit(log)}
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
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
                            className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
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
                ))}
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
