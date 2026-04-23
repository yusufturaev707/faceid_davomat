import { useCallback, useEffect, useState } from "react";
import type {
  StudentLogListResponse,
  StudentLogResponse,
  StudentLogDetailResponse,
  TestResponse,
  LookupRegionResponse,
  LookupZoneResponse,
  SmenaResponse,
} from "../interfaces";
import {
  getStudentLogsApi,
  getStudentLogDetailApi,
  deleteStudentLogApi,
  getTestsLookupApi,
  getRegionsListApi,
  getZonesByRegionApi,
  getSmenasLookupApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

export default function StudentLogsPage() {
  const [data, setData] = useState<StudentLogListResponse | null>(null);
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
  const [filterGrN, setFilterGrN] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterCheating, setFilterCheating] = useState("");
  const [filterBlacklist, setFilterBlacklist] = useState("");
  const [filterFirstFrom, setFilterFirstFrom] = useState("");
  const [filterFirstTo, setFilterFirstTo] = useState("");
  const [filterLastFrom, setFilterLastFrom] = useState("");
  const [filterLastTo, setFilterLastTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Lookup
  const [tests, setTests] = useState<TestResponse[]>([]);
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);
  const [zones, setZones] = useState<LookupZoneResponse[]>([]);
  const [smenas, setSmenas] = useState<SmenaResponse[]>([]);

  // Detail
  const [detail, setDetail] = useState<StudentLogDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    getTestsLookupApi()
      .then(setTests)
      .catch(() => {});
    getRegionsListApi()
      .then(setRegions)
      .catch(() => {});
    getSmenasLookupApi()
      .then(setSmenas)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!filterRegionId) {
      setZones([]);
      return;
    }
    getZonesByRegionApi(Number(filterRegionId))
      .then(setZones)
      .catch(() => setZones([]));
  }, [filterRegionId]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = {
        page,
        per_page: perPage,
      };
      if (search) params.search = search;
      if (filterTestId) params.test_id = Number(filterTestId);
      if (filterRegionId) params.region_id = Number(filterRegionId);
      if (filterZoneId) params.zone_id = Number(filterZoneId);
      if (filterSmenaId) params.smena_id = Number(filterSmenaId);
      if (filterGrN) params.gr_n = Number(filterGrN);
      if (filterDateFrom) params.e_date_from = filterDateFrom;
      if (filterDateTo) params.e_date_to = filterDateTo;
      if (filterCheating === "true") params.is_cheating = true;
      if (filterCheating === "false") params.is_cheating = false;
      if (filterBlacklist === "true") params.is_blacklist = true;
      if (filterBlacklist === "false") params.is_blacklist = false;
      if (filterFirstFrom) params.first_enter_from = filterFirstFrom;
      if (filterFirstTo) params.first_enter_to = filterFirstTo;
      if (filterLastFrom) params.last_enter_from = filterLastFrom;
      if (filterLastTo) params.last_enter_to = filterLastTo;
      const result = await getStudentLogsApi(params);
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
    filterGrN,
    filterDateFrom,
    filterDateTo,
    filterCheating,
    filterBlacklist,
    filterFirstFrom,
    filterFirstTo,
    filterLastFrom,
    filterLastTo,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = () => {
    setPage(1);
    setSearch(searchInput);
  };

  const resetFilters = () => {
    setSearchInput("");
    setSearch("");
    setFilterTestId("");
    setFilterRegionId("");
    setFilterZoneId("");
    setFilterSmenaId("");
    setFilterGrN("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setFilterCheating("");
    setFilterBlacklist("");
    setFilterFirstFrom("");
    setFilterFirstTo("");
    setFilterLastFrom("");
    setFilterLastTo("");
    setPage(1);
  };

  const activeFilterCount = [
    filterTestId,
    filterRegionId,
    filterZoneId,
    filterSmenaId,
    filterGrN,
    filterDateFrom,
    filterDateTo,
    filterCheating,
    filterBlacklist,
    filterFirstFrom,
    filterFirstTo,
    filterLastFrom,
    filterLastTo,
  ].filter(Boolean).length;

  const hasFilters = !!search || activeFilterCount > 0;

  const formatDateTime = (val: string | null) =>
    val ? new Date(val).toLocaleString("uz-UZ") : "—";

  const formatDateOnly = (val: string | null) => {
    if (!val) return "—";
    try {
      return new Date(val).toLocaleDateString("uz-UZ", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    } catch {
      return val;
    }
  };

  const openDetail = async (log: StudentLogResponse) => {
    setDetailLoading(true);
    setDetail({ ...log, first_captured: null, last_captured: null });
    try {
      const d = await getStudentLogDetailApi(log.id);
      setDetail(d);
    } catch (err) {
      setError(extractErrorMessage(err));
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Haqiqatan o'chirmoqchimisiz?")) return;
    try {
      await deleteStudentLogApi(id);
      if (detail?.id === id) setDetail(null);
      await fetchData();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="section-title">Student kirish loglari</h2>
          <p className="section-subtitle">
            Studentlarning kirish va tekshiruv loglari
          </p>
        </div>
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
                placeholder="Familiya, ism, sharif yoki JSHSHIR..."
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
              <select
                value={perPage}
                onChange={(e) => {
                  setPerPage(Number(e.target.value));
                  setPage(1);
                }}
                className="input-field !py-1 !text-sm !pr-7"
              >
                {[10, 20, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
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
                label="Bino (Zona)"
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
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Guruh
                </label>
                <input
                  type="number"
                  value={filterGrN}
                  onChange={(e) => {
                    setFilterGrN(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Raqam"
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Test sana (dan)
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
                  Test sana (gacha)
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
              <FilterSelect
                label="Cheating"
                value={filterCheating}
                onChange={(v) => {
                  setFilterCheating(v);
                  setPage(1);
                }}
                options={[
                  { value: "true", label: "Ha" },
                  { value: "false", label: "Yo'q" },
                ]}
              />
              <FilterSelect
                label="Qora ro'yxat"
                value={filterBlacklist}
                onChange={(v) => {
                  setFilterBlacklist(v);
                  setPage(1);
                }}
                options={[
                  { value: "true", label: "Ha" },
                  { value: "false", label: "Yo'q" },
                ]}
              />
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Birinchi kirish (dan)
                </label>
                <input
                  type="datetime-local"
                  value={filterFirstFrom}
                  onChange={(e) => {
                    setFilterFirstFrom(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Birinchi kirish (gacha)
                </label>
                <input
                  type="datetime-local"
                  value={filterFirstTo}
                  onChange={(e) => {
                    setFilterFirstTo(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Oxirgi kirish (dan)
                </label>
                <input
                  type="datetime-local"
                  value={filterLastFrom}
                  onChange={(e) => {
                    setFilterLastFrom(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">
                  Oxirgi kirish (gacha)
                </label>
                <input
                  type="datetime-local"
                  value={filterLastTo}
                  onChange={(e) => {
                    setFilterLastTo(e.target.value);
                    setPage(1);
                  }}
                  className="input-field !py-1.5 !text-sm w-full"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
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
                <tr className="bg-gray-50/80 dark:bg-slate-800/80 border-b border-gray-200 dark:border-slate-700">
                  <TH>ID</TH>
                  <TH>Student</TH>
                  <TH>Test / Sessiya</TH>
                  <TH>Zona / Smena</TH>
                  <TH>Test sana</TH>
                  <TH>Birinchi kirish</TH>
                  <TH>Oxirgi kirish</TH>
                  <TH align="center">Ball</TH>
                  <TH align="center">Holat</TH>
                  <TH align="center">Rasm</TH>
                  <TH align="center">Amallar</TH>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => openDetail(log)}
                    className="border-b border-gray-50 dark:border-slate-700/40 cursor-pointer transition-all duration-150 hover:bg-gray-50/70 dark:hover:bg-slate-800/40"
                  >
                    <TD className="text-gray-400 dark:text-slate-500 font-mono">
                      #{log.id}
                    </TD>
                    <TD>
                      <div className="font-medium text-gray-800 dark:text-slate-200">
                        {log.student_full_name || `#${log.student_id}`}
                      </div>
                      {log.imei && (
                        <div className="text-[11px] text-gray-400 dark:text-slate-500 font-mono">
                          {log.imei}
                        </div>
                      )}
                    </TD>
                    <TD>
                      <div className="text-gray-700 dark:text-slate-300 text-xs">
                        {log.test_name || "—"}
                      </div>
                      {log.test_session_id && (
                        <div className="text-[11px] text-gray-400 dark:text-slate-500">
                          #S{log.test_session_id}
                        </div>
                      )}
                    </TD>
                    <TD>
                      <div className="text-gray-700 dark:text-slate-300 text-xs">
                        {log.zone_name || "—"}
                      </div>
                      <div className="text-[11px] text-gray-400 dark:text-slate-500">
                        {log.region_name || ""}
                        {log.smena_name ? ` · ${log.smena_name}` : ""}
                      </div>
                    </TD>
                    <TD className="text-gray-600 dark:text-slate-400 text-xs whitespace-nowrap">
                      {formatDateOnly(log.e_date)}
                    </TD>
                    <TD className="text-gray-600 dark:text-slate-400 text-xs whitespace-nowrap">
                      {formatDateTime(log.first_enter_time)}
                    </TD>
                    <TD className="text-gray-600 dark:text-slate-400 text-xs whitespace-nowrap">
                      {formatDateTime(log.last_enter_time)}
                    </TD>
                    <TD align="center">
                      <span className="font-medium text-gray-800 dark:text-slate-200">
                        {log.score}
                      </span>
                      <span className="text-gray-400 dark:text-slate-500">
                        /{log.max_score}
                      </span>
                    </TD>
                    <TD align="center">
                      <div className="flex items-center justify-center gap-1.5">
                        {log.is_cheating && (
                          <span
                            title="Chetlatilgan"
                            className="px-1.5 py-0.5 text-[10px] font-semibold rounded-md bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          >
                            CH
                          </span>
                        )}
                        {log.is_blacklist && (
                          <span
                            title="Blacklist"
                            className="px-1.5 py-0.5 text-[10px] font-semibold rounded-md bg-slate-800 text-white dark:bg-black"
                          >
                            BL
                          </span>
                        )}
                        {!log.is_cheating && !log.is_blacklist && (
                          <span className="text-xs text-emerald-500">✓</span>
                        )}
                      </div>
                    </TD>
                    <TD align="center">
                      <div className="flex items-center justify-center gap-1">
                        <span
                          title="first_captured"
                          className={`w-2 h-2 rounded-full ${
                            log.has_first_captured
                              ? "bg-emerald-500"
                              : "bg-gray-300 dark:bg-slate-600"
                          }`}
                        />
                        <span
                          title="last_captured"
                          className={`w-2 h-2 rounded-full ${
                            log.has_last_captured
                              ? "bg-amber-500"
                              : "bg-gray-300 dark:bg-slate-600"
                          }`}
                        />
                      </div>
                    </TD>
                    <TD align="center">
                      <div
                        className="flex items-center justify-center gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => openDetail(log)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400"
                          title="Ko'rish"
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
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                        </button>
                        <PermissionGate permission={PERM.STUDENT_LOG_DELETE}>
                          <button
                            onClick={() => handleDelete(log.id)}
                            className="text-red-500 hover:text-red-700 dark:text-red-400"
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
                    </TD>
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

      {/* Detail modal */}
      {detail && (
        <div
          className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setDetail(null)}
        >
          <div
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-800 z-10">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Log #{detail.id}
                </h3>
                <div className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
                  {detail.student_full_name || `Student #${detail.student_id}`}
                </div>
              </div>
              <button
                onClick={() => setDetail(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Badges */}
              <div className="flex items-center gap-2 flex-wrap">
                {detail.is_cheating && (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                    Chetlatilgan
                  </span>
                )}
                {detail.is_blacklist && (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-slate-800 text-white">
                    Blacklist
                  </span>
                )}
                {detail.is_check_hand && (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                    Qo'l tekshiruvi
                  </span>
                )}
                {!detail.is_cheating && !detail.is_blacklist && (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                    Muvaffaqiyatli
                  </span>
                )}
              </div>

              {/* Rasmlar */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <CaptureCard
                  title="Birinchi tasvir"
                  subtitle={formatDateTime(detail.first_enter_time)}
                  image={detail.first_captured}
                  accent="emerald"
                  loading={detailLoading}
                />
                <CaptureCard
                  title="Oxirgi tasvir"
                  subtitle={formatDateTime(detail.last_enter_time)}
                  image={detail.last_captured}
                  accent="amber"
                  loading={detailLoading}
                />
              </div>

              {/* Ma'lumotlar — chap va o'ng ustunlar */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1">
                {/* Chap ustun */}
                <div>
                  <InfoRow label="Familiya" value={detail.last_name} />
                  <InfoRow label="Ism" value={detail.first_name} />
                  <InfoRow label="Sharif" value={detail.middle_name} />
                  <InfoRow label="JSHSHIR" value={detail.imei} mono />
                  <InfoRow label="Test" value={detail.test_name} />
                  <InfoRow
                    label="Test sessiya"
                    value={
                      detail.test_session_id
                        ? `#${detail.test_session_id}`
                        : null
                    }
                  />
                  <InfoRow label="IP manzil" value={detail.ip_address} mono />
                </div>
                {/* O'ng ustun */}
                <div>
                  <InfoRow label="Viloyat" value={detail.region_name} />
                  <InfoRow label="Bino (Zona)" value={detail.zone_name} />
                  <InfoRow
                    label="Test sana"
                    value={formatDateOnly(detail.e_date)}
                  />
                  <InfoRow label="Smena" value={detail.smena_name} />
                  <InfoRow label="Guruh" value={detail.gr_n?.toString()} />
                  <InfoRow
                    label="Score (Ball)"
                    value={`${detail.score} / ${detail.max_score}`}
                  />
                  <InfoRow label="MAC manzil" value={detail.mac_address} mono />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 sticky bottom-0">
              <PermissionGate permission={PERM.STUDENT_LOG_DELETE}>
                <button
                  onClick={() => handleDelete(detail.id)}
                  className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-800 dark:text-red-400"
                >
                  O'chirish
                </button>
              </PermissionGate>
              <button onClick={() => setDetail(null)} className="btn-primary">
                Yopish
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
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="input-field !py-1.5 !text-sm w-full disabled:opacity-50"
      >
        <option value="">Barchasi</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function TH({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "center";
}) {
  return (
    <th
      className={`px-3 py-3 font-semibold text-[11px] uppercase tracking-wider text-gray-400 dark:text-slate-500 whitespace-nowrap ${
        align === "center" ? "text-center" : "text-left"
      }`}
    >
      {children}
    </th>
  );
}

function TD({
  children,
  className = "",
  align = "left",
}: {
  children: React.ReactNode;
  className?: string;
  align?: "left" | "center";
}) {
  return (
    <td
      className={`px-3 py-2.5 ${
        align === "center" ? "text-center" : "text-left"
      } ${className}`}
    >
      {children}
    </td>
  );
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | number | null | undefined;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 border-b border-gray-100 dark:border-slate-700/50">
      <span className="text-gray-500 dark:text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
        {label}
      </span>
      <span
        className={`text-gray-800 dark:text-slate-200 text-right text-sm ${
          mono ? "font-mono text-xs" : ""
        }`}
      >
        {value ?? "—"}
      </span>
    </div>
  );
}

function CaptureCard({
  title,
  subtitle,
  image,
  accent,
  loading,
}: {
  title: string;
  subtitle: string;
  image: string | null;
  accent: "emerald" | "amber";
  loading: boolean;
}) {
  const accentCls = accent === "emerald" ? "bg-emerald-500" : "bg-amber-500";

  return (
    <div className="bg-gray-50 dark:bg-slate-900/40 rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-200 dark:border-slate-700">
        <span className={`w-2 h-2 rounded-full ${accentCls}`} />
        <div className="flex-1">
          <div className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            {title}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-slate-400">
            {subtitle}
          </div>
        </div>
      </div>
      <div className="aspect-square bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
        {loading && !image ? (
          <div className="animate-pulse text-gray-400 dark:text-slate-500 text-xs">
            Yuklanmoqda...
          </div>
        ) : image ? (
          <img
            src={`data:image/jpeg;base64,${image}`}
            alt={title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-gray-400 dark:text-slate-500 text-xs flex flex-col items-center gap-2">
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            Rasm yo'q
          </div>
        )}
      </div>
    </div>
  );
}
