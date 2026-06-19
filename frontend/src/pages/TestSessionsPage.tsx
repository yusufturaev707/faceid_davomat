import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type {
  SessionStateResponse,
  SmenaResponse,
  TestResponse,
  TestSessionListResponse,
} from "../interfaces";
import {
  createTestSessionApi,
  getSessionStatesLookupApi,
  getSmenasLookupApi,
  getTestSessionsApi,
  getTestsLookupApi,
} from "../api";
import Md3Select from "../components/Md3Select";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

export default function TestSessionsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<TestSessionListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Lookups
  const [tests, setTests] = useState<TestResponse[]>([]);
  const [smenas, setSmenas] = useState<SmenaResponse[]>([]);
  const [sessionStates, setSessionStates] = useState<SessionStateResponse[]>([]);

  // Filters
  const [filterTestId, setFilterTestId] = useState("");
  const [filterStateId, setFilterStateId] = useState("");
  const [filterActive, setFilterActive] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const activeFilterCount =
    (filterTestId ? 1 : 0) +
    (filterStateId ? 1 : 0) +
    (filterActive ? 1 : 0);
  const hasFilters = activeFilterCount > 0;
  const resetFilters = () => {
    setFilterTestId("");
    setFilterStateId("");
    setFilterActive("");
    setPage(1);
  };

  // Form state
  const [formName, setFormName] = useState("");
  const [formTestId, setFormTestId] = useState<number>(0);
  const [formStartDate, setFormStartDate] = useState("");
  const [formFinishDate, setFormFinishDate] = useState("");
  const [formSmPerDay, setFormSmPerDay] = useState(1);
  const [formSmenas, setFormSmenas] = useState<
    { test_smena_id: number; day: string }[]
  >([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = {
        page,
        per_page: 20,
      };
      if (filterTestId) params.test_id = Number(filterTestId);
      if (filterStateId) params.test_state_id = Number(filterStateId);
      if (filterActive === "true") params.is_active = true;
      else if (filterActive === "false") params.is_active = false;
      const result = await getTestSessionsApi(
        params as Record<string, string | number>,
      );
      setData(result);
    } finally {
      setLoading(false);
    }
  }, [page, filterTestId, filterStateId, filterActive]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Filter dropdownlari uchun lookup'lar — bir marta yuklab, qayta-qayta
  // chiqarishlardan saqlanamiz.
  useEffect(() => {
    getTestsLookupApi().then(setTests).catch(() => {});
    getSessionStatesLookupApi().then(setSessionStates).catch(() => {});
  }, []);

  const openCreateModal = async () => {
    setError("");
    setFormName("");
    setFormTestId(0);
    setFormStartDate("");
    setFormFinishDate("");
    setFormSmPerDay(1);
    setFormSmenas([]);
    try {
      // Tests filter uchun mount'da yuklanadi; smena lookup faqat modal
      // ochilganda kerak — bir martagina fetch qilamiz.
      const s = smenas.length ? smenas : await getSmenasLookupApi();
      setSmenas(s);
      if (tests.length > 0) setFormTestId(tests[0].id);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
    setShowModal(true);
  };

  const addSmenaRow = () => {
    setFormSmenas([
      ...formSmenas,
      { test_smena_id: smenas[0]?.id || 0, day: formStartDate },
    ]);
  };

  const removeSmenaRow = (idx: number) => {
    setFormSmenas(formSmenas.filter((_, i) => i !== idx));
  };

  const updateSmenaRow = (
    idx: number,
    field: "test_smena_id" | "day",
    value: string | number,
  ) => {
    const copy = [...formSmenas];
    if (field === "test_smena_id") copy[idx].test_smena_id = Number(value);
    else copy[idx].day = String(value);
    setFormSmenas(copy);
  };

  const handleCreate = async () => {
    setError("");
    if (!formName.trim()) {
      setError("Nom kiritilmagan");
      return;
    }
    if (!formTestId) {
      setError("Test tanlanmagan");
      return;
    }
    if (!formStartDate || !formFinishDate) {
      setError("Sanalar kiritilmagan");
      return;
    }
    if (formFinishDate < formStartDate) {
      setError("Tugash sanasi boshlanishdan oldin");
      return;
    }

    // Smena dublikat tekshirish
    const smenaKeys = formSmenas.map((s) => `${s.test_smena_id}_${s.day}`);
    if (new Set(smenaKeys).size !== smenaKeys.length) {
      setError("Bir xil smena va sana kombinatsiyasi ikki marta kiritilgan");
      return;
    }

    setSubmitting(true);
    try {
      await createTestSessionApi({
        test_id: formTestId,
        name: formName.trim(),
        start_date: formStartDate,
        finish_date: formFinishDate,
        count_sm_per_day: formSmPerDay,
        smenas: formSmenas,
      });
      setShowModal(false);
      fetchSessions();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="section-title">Test Sessiyalar</h2>
          <p className="section-subtitle">Test sessiyalarni boshqarish</p>
        </div>
        <PermissionGate permission={PERM.TEST_SESSION_CREATE}>
          <button onClick={openCreateModal} className="btn-primary">
            + Yangi sessiya
          </button>
        </PermissionGate>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
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
          {data && (
            <span className="ml-auto self-center text-xs text-gray-400 dark:text-slate-500">
              Jami:{" "}
              <span className="font-semibold text-gray-600 dark:text-slate-300">
                {data.total}
              </span>{" "}
              ta
            </span>
          )}
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
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
                label="Holat"
                value={filterStateId}
                onChange={(v) => {
                  setFilterStateId(v);
                  setPage(1);
                }}
                options={sessionStates.map((s) => ({
                  value: String(s.id),
                  label: s.name,
                }))}
              />
              <FilterSelect
                label="Faolligi"
                value={filterActive}
                onChange={(v) => {
                  setFilterActive(v);
                  setPage(1);
                }}
                options={[
                  { value: "true", label: "Faol" },
                  { value: "false", label: "Faol emas" },
                ]}
              />
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
            Test sessiyalar topilmadi
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    #
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Nomi
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Test
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Holat
                  </th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">
                    Smenalar soni
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Boshlanish
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Tugash
                  </th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">
                    Umumiy soni
                  </th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">
                    Faol
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => navigate(`/test-sessions/${s.id}`)}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition cursor-pointer"
                  >
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                      {s.number}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">
                      {s.name}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                      {s.test?.name || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                        {s.test_state?.name || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-400">
                      {s.smenas.length}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                      {s.start_date}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                      {s.finish_date}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-400">
                      {s.count_total_student}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full ${s.is_active ? "bg-emerald-500" : "bg-red-400"}`}
                      />
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

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-5 border-b border-gray-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Yangi test sessiya
              </h3>
            </div>
            <div className="px-6 py-5 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Sessiya nomi
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="input-field"
                  placeholder="Masalan: 2026 - Mart imtihoni"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Test
                </label>
                <Md3Select
                  value={formTestId ? String(formTestId) : ""}
                  onChange={(v) => setFormTestId(Number(v))}
                  options={tests.map((t) => ({
                    value: String(t.id),
                    label: t.name,
                  }))}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    Boshlanish sanasi
                  </label>
                  <input
                    type="date"
                    value={formStartDate}
                    onChange={(e) => setFormStartDate(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    Tugash sanasi
                  </label>
                  <input
                    type="date"
                    value={formFinishDate}
                    onChange={(e) => setFormFinishDate(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Kuniga smenalar soni
                </label>
                <input
                  type="number"
                  min={1}
                  value={formSmPerDay}
                  onChange={(e) => setFormSmPerDay(Number(e.target.value))}
                  className="input-field"
                />
              </div>

              {/* Smena rows */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-slate-300">
                    Smenalar
                  </label>
                  <button
                    type="button"
                    onClick={addSmenaRow}
                    className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
                  >
                    + Smena qo'shish
                  </button>
                </div>
                {formSmenas.length === 0 && (
                  <p className="text-xs text-gray-400 dark:text-slate-500">
                    Smena qo'shilmagan
                  </p>
                )}
                <div className="space-y-2">
                  {formSmenas.map((row, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Md3Select
                        value={row.test_smena_id ? String(row.test_smena_id) : ""}
                        onChange={(v) =>
                          updateSmenaRow(idx, "test_smena_id", v)
                        }
                        options={smenas.map((sm) => ({
                          value: String(sm.id),
                          label: sm.name,
                        }))}
                        className="flex-1"
                      />
                      <input
                        type="date"
                        value={row.day}
                        onChange={(e) =>
                          updateSmenaRow(idx, "day", e.target.value)
                        }
                        className="input-field !py-1.5 text-sm flex-1"
                      />
                      <button
                        type="button"
                        onClick={() => removeSmenaRow(idx)}
                        className="text-red-400 hover:text-red-600 p-1"
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
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="btn-secondary"
                disabled={submitting}
              >
                Bekor qilish
              </button>
              <button
                onClick={handleCreate}
                className="btn-primary"
                disabled={submitting}
              >
                {submitting ? "Yaratilmoqda..." : "Yaratish"}
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
        clearable
        placeholder="Barchasi"
        options={options}
        className="w-full"
      />
    </div>
  );
}
