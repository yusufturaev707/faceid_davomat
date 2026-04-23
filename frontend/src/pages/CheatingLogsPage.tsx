import { useCallback, useEffect, useState } from "react";
import type { CheatingLogListResponse, CheatingLogCreate, CheatingLogUpdate } from "../interfaces";
import { getCheatingLogsApi, createCheatingLogApi, updateCheatingLogApi, deleteCheatingLogApi } from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

const emptyForm: CheatingLogCreate = {
  student_id: 0,
  reason_id: 0,
  user_id: 0,
  image_path: "",
};

export default function CheatingLogsPage() {
  const [data, setData] = useState<CheatingLogListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<CheatingLogCreate>(emptyForm);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getCheatingLogsApi({ page, per_page: 20 });
      setData(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

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

  const setField = (key: string, value: any) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Qoidabuzarliklar</h2>
          <p className="section-subtitle">Cheating holatlari qayd etilgan loglar</p>
        </div>
        <PermissionGate permission={PERM.CHEATING_LOG_CREATE}>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Yangi qoidabuzarlik
          </button>
        </PermissionGate>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-auto underline text-xs">Yopish</button>
        </div>
      )}

      {data && <div className="mb-5 text-sm text-gray-500 dark:text-slate-400">Jami: {data.total} ta</div>}

      <div className="glass-card overflow-hidden">
        {loading ? <PageLoader /> : !data || data.items.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">Ma'lumot topilmadi</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">ID</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Student</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Sabab</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Qayd etuvchi</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Rasm</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition">
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">#{log.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">{log.student_full_name || `#${log.student_id}`}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        {log.reason_name || `#${log.reason_id}`}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 text-xs">{log.username || `#${log.user_id}`}</td>
                    <td className="px-4 py-3 text-center">
                      {log.image_path ? (
                        <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500" title="Rasm mavjud" />
                      ) : (
                        <span className="text-gray-300 dark:text-slate-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <PermissionGate permission={PERM.CHEATING_LOG_UPDATE}>
                          <button onClick={() => openEdit(log)} className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300" title="Tahrirlash">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                          </button>
                        </PermissionGate>
                        <PermissionGate permission={PERM.CHEATING_LOG_DELETE}>
                          <button onClick={() => handleDelete(log.id)} className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300" title="O'chirish">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
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

      {data && <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editId ? "Qoidabuzarlikni tahrirlash" : "Yangi qoidabuzarlik"}
            </h3>
            {formError && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">{formError}</div>}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Student ID *</label>
                <input type="number" value={form.student_id} onChange={(e) => setField("student_id", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Sabab ID *</label>
                <input type="number" value={form.reason_id} onChange={(e) => setField("reason_id", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">User ID *</label>
                <input type="number" value={form.user_id} onChange={(e) => setField("user_id", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Rasm yo'li</label>
                <input type="text" value={form.image_path || ""} onChange={(e) => setField("image_path", e.target.value || null)} className="input-field w-full" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors">Bekor qilish</button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">{saving ? "Saqlanmoqda..." : "Saqlash"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
